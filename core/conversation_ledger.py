# core/conversation_ledger.py
"""简化版对话总账 - Scriptor 专用"""

import asyncio
import hashlib
import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


@dataclass
class LedgerMessage:
    """总账消息实体"""

    message_id: str
    timestamp: float
    role: str
    content: str
    source: str  # 来源：user_input, ai_response, tool_call, tool_result
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ConversationLedger:
    """
    简化版对话总账 - Scriptor 的权威消息记录中心

    核心思想：
    1. 使用 SQLite (WAL 模式) 替代全量 JSON 覆写，大幅降低 SSD 损耗
    2. 文件即记忆理念
    3. 只保留必要功能
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.ledger_dir = data_dir / "ledger"
        self.ledger_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.ledger_dir / "ledger.db"
        self._init_db()

        self._lock = asyncio.Lock()
        self._cache: Dict[str, List[LedgerMessage]] = {}
        self._cache_access_times: Dict[str, float] = {}

        self.MAX_MESSAGES_PER_SESSION = 500
        self.MAX_CACHED_SESSIONS = 50

        logger.info("[Scriptor] 对话总账初始化完成 (SQLite WAL 模式)")

    def _init_db(self):
        """初始化 SQLite 数据库并开启 WAL 模式"""
        with sqlite3.connect(self.db_path) as conn:
            # 开启 WAL 模式，提升并发写入性能，降低 I/O 损耗
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session_time ON messages(session_id, timestamp)")
            conn.commit()

    def _get_session_file(self, session_id: str) -> Path:
        """获取会话文件路径"""
        safe_id = hashlib.md5(session_id.encode()).hexdigest()
        return self.ledger_dir / f"{safe_id}.json"

    async def _load_session(self, session_id: str):
        """从文件加载会话到缓存"""
        if session_id in self._cache:
            self._cache_access_times[session_id] = time.time()
            return

        if len(self._cache) >= self.MAX_CACHED_SESSIONS:
            sorted_caches = sorted(self._cache_access_times.items(), key=lambda x: x[1])
            remove_count = max(1, len(sorted_caches) // 5)
            for sid_to_remove, _ in sorted_caches[:remove_count]:
                if sid_to_remove in self._cache:
                    asyncio.create_task(self._save_session(sid_to_remove))
                    del self._cache[sid_to_remove]
                if sid_to_remove in self._cache_access_times:
                    del self._cache_access_times[sid_to_remove]

        file_path = self._get_session_file(session_id)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache[session_id] = [LedgerMessage(**msg) for msg in data]
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"[Scriptor] 加载会话失败: {e}")
                self._cache[session_id] = []
        else:
            self._cache[session_id] = []
        self._cache_access_times[session_id] = time.time()

    async def _save_session(self, session_id: str):
        """将会话从缓存保存到文件"""
        if session_id not in self._cache:
            return

        file_path = self._get_session_file(session_id)
        try:
            data = [asdict(msg) for msg in self._cache[session_id]]
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"[Scriptor] 保存会话失败: {e}")

    def _generate_message_id(self) -> str:
        """生成唯一消息ID"""
        return f"{int(time.time() * 1000000)}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"

    async def add_message(
        self, session_id: str, role: str, content: str, source: str = "user_input", metadata: Dict = None
    ) -> str:
        """
        添加消息到总账

        Args:
            session_id: 会话ID
            role: 角色 (user, assistant, system, tool)
            content: 消息内容
            source: 来源 (user_input, ai_response, tool_call, tool_result)
            metadata: 额外元数据

        Returns:
            message_id: 消息ID
        """
        async with self._lock:
            await self._load_session(session_id)

            message_id = self._generate_message_id()
            message = LedgerMessage(
                message_id=message_id,
                timestamp=time.time(),
                role=role,
                content=content,
                source=source,
                metadata=metadata,
            )

            self._cache[session_id].append(message)

            # 限制消息数量
            if len(self._cache[session_id]) > self.MAX_MESSAGES_PER_SESSION:
                self._cache[session_id] = self._cache[session_id][-self.MAX_MESSAGES_PER_SESSION :]

            # 异步保存（不阻塞）
            asyncio.create_task(self._save_session(session_id))

            return message_id

    async def get_messages(
        self, session_id: str, limit: int = None, start_time: float = None, end_time: float = None
    ) -> List[LedgerMessage]:
        """
        获取会话消息

        Args:
            session_id: 会话ID
            limit: 返回消息数量限制
            start_time: 开始时间戳
            end_time: 结束时间戳

        Returns:
            消息列表
        """
        async with self._lock:
            await self._load_session(session_id)

            messages = self._cache.get(session_id, [])

            # 时间过滤
            if start_time:
                messages = [m for m in messages if m.timestamp >= start_time]
            if end_time:
                messages = [m for m in messages if m.timestamp <= end_time]

            # 数量限制
            if limit:
                messages = messages[-limit:]

            return messages.copy()

    async def get_recent_context(self, session_id: str, message_count: int = 10) -> List[Dict]:
        """
        获取最近的对话上下文（用于提示词注入）

        Args:
            session_id: 会话ID
            message_count: 消息数量

        Returns:
            简化的消息字典列表
        """
        messages = await self.get_messages(session_id, limit=message_count)

        return [{"role": msg.role, "content": msg.content, "timestamp": msg.timestamp} for msg in messages]

    async def clear_session(self, session_id: str):
        """清空会话"""

        def _delete():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                conn.commit()

        await asyncio.to_thread(_delete)

    async def get_session_stats(self, session_id: str) -> Dict:
        """获取会话统计信息"""

        def _stats():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM messages WHERE session_id = ?", (session_id,)
                )
                count, min_ts, max_ts = cursor.fetchone()
                return {
                    "total_messages": count,
                    "earliest_timestamp": min_ts,
                    "latest_timestamp": max_ts,
                    "source_counts": {},
                }

        return await asyncio.to_thread(_stats)

    async def cleanup_old_sessions(self, days_old: int = 30):
        """清理过期会话"""
        cutoff = time.time() - (days_old * 86400)

        def _cleanup():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,))
                conn.commit()

        await asyncio.to_thread(_cleanup)
        logger.info(f"[Scriptor] 清理了 {days_old} 天前的过期会话记录")
