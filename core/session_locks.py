# core/session_locks.py
"""
会话级并发与状态锁控制模块
功能：
1. 会话级别的处理锁（同一会话同一时间只有一个 LLM 请求）
2. pending_futures 管理
3. pending_events 队列
4. 会话状态机
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class SessionState(Enum):
    """会话状态"""

    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    PAUSED = "paused"


@dataclass
class SessionContext:
    """会话上下文"""

    session_id: str
    state: SessionState = SessionState.IDLE
    current_future: Optional[asyncio.Future] = None
    pending_events: deque = field(default_factory=deque)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    created_at: float = field(default_factory=lambda: __import__("time").time())
    last_activity: float = field(default_factory=lambda: __import__("time").time())


@dataclass
class LockManagerConfig:
    """锁管理器配置"""

    enabled: bool = True

    max_pending_events: int = 100

    session_timeout_seconds: float = 3600.0

    cleanup_interval_seconds: float = 600.0


class SessionLockManager:
    """会话锁管理器"""

    def __init__(self, config: Optional[LockManagerConfig] = None):
        self.config = config or LockManagerConfig()

        self._sessions: Dict[str, SessionContext] = {}
        self._processing_sessions: Set[str] = set()
        self._global_lock = asyncio.Lock()

        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._background_tasks: Set[asyncio.Task] = set()

    async def start(self):
        """启动锁管理器"""
        if self._is_running:
            return

        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("[SessionLockManager] 已启动")

    async def stop(self):
        """停止锁管理器"""
        self._is_running = False

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("[SessionLockManager] 已停止")

    async def acquire_session(self, session_id: str, wait: bool = True) -> bool:
        """
        尝试获取会话处理锁

        Args:
            session_id: 会话ID
            wait: 是否等待锁释放

        Returns:
            是否成功获取锁
        """
        if not self.config.enabled:
            return True

        async with self._global_lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionContext(session_id=session_id)

            ctx = self._sessions[session_id]
            ctx.last_activity = __import__("time").time()

        if wait:
            await ctx.lock.acquire()
        else:
            if not ctx.lock.locked():
                await ctx.lock.acquire()
            else:
                return False

        async with self._global_lock:
            ctx.state = SessionState.PROCESSING
            self._processing_sessions.add(session_id)

        logger.debug(f"[SessionLockManager] 获取会话锁: {session_id}")
        return True

    def release_session(self, session_id: str):
        """
        释放会话处理锁

        Args:
            session_id: 会话ID
        """
        if not self.config.enabled:
            return

        task = asyncio.create_task(self._release_session_async(session_id))
        task.add_done_callback(lambda t: self._background_tasks.discard(t) if t in self._background_tasks else None)
        self._background_tasks.add(task)

    async def _release_session_async(self, session_id: str):
        """异步释放会话锁"""
        async with self._global_lock:
            if session_id not in self._sessions:
                return

            ctx = self._sessions[session_id]

            if session_id in self._processing_sessions:
                self._processing_sessions.remove(session_id)

            if ctx.lock.locked():
                ctx.lock.release()

            if ctx.pending_events:
                ctx.state = SessionState.WAITING
            else:
                ctx.state = SessionState.IDLE

            ctx.last_activity = __import__("time").time()

        logger.debug(f"[SessionLockManager] 释放会话锁: {session_id}")

        await self._process_pending(session_id)

    async def add_pending_event(self, session_id: str, event: Any, process_callback: Optional[Callable] = None) -> bool:
        """
        添加待处理事件

        Args:
            session_id: 会话ID
            event: 事件数据
            process_callback: 处理回调（可选）

        Returns:
            是否成功添加
        """
        async with self._global_lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionContext(session_id=session_id)

            ctx = self._sessions[session_id]

            if len(ctx.pending_events) >= self.config.max_pending_events:
                logger.warning(f"[SessionLockManager] 待处理事件队列已满，丢弃: {session_id}")
                return False

            ctx.pending_events.append((event, process_callback))
            ctx.last_activity = __import__("time").time()

        logger.debug(f"[SessionLockManager] 添加待处理事件: {session_id}, 队列长度: {len(ctx.pending_events)}")

        if ctx.state == SessionState.IDLE:
            await self._process_pending(session_id)

        return True

    async def _process_pending(self, session_id: str):
        """处理待处理事件"""
        async with self._global_lock:
            if session_id not in self._sessions:
                return

            ctx = self._sessions[session_id]

            if not ctx.pending_events:
                return

            if ctx.state == SessionState.PROCESSING:
                return

        acquired = await self.acquire_session(session_id, wait=False)
        if not acquired:
            return

        try:
            event, callback = None, None
            async with self._global_lock:
                if ctx.pending_events:
                    event, callback = ctx.pending_events.popleft()

            if event and callback:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"[SessionLockManager] 处理待处理事件失败: {e}")
        finally:
            self.release_session(session_id)

    def is_processing(self, session_id: str) -> bool:
        """检查会话是否正在处理中"""
        return session_id in self._processing_sessions

    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """获取会话状态"""
        if session_id in self._sessions:
            return self._sessions[session_id].state
        return None

    async def _cleanup_loop(self):
        """清理循环"""
        while self._is_running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SessionLockManager] 清理循环出错: {e}")

    async def _cleanup_expired_sessions(self):
        """清理过期会话"""
        now = __import__("time").time()
        expired_sessions = []

        async with self._global_lock:
            for session_id, ctx in list(self._sessions.items()):
                if now - ctx.last_activity > self.config.session_timeout_seconds:
                    if ctx.state == SessionState.IDLE and not ctx.pending_events:
                        expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self._sessions[session_id]
                if session_id in self._processing_sessions:
                    self._processing_sessions.remove(session_id)

        if expired_sessions:
            logger.info(f"[SessionLockManager] 清理过期会话: {len(expired_sessions)} 个")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "enabled": self.config.enabled,
            "total_sessions": len(self._sessions),
            "processing_sessions": len(self._processing_sessions),
            "idle_sessions": sum(1 for ctx in self._sessions.values() if ctx.state == SessionState.IDLE),
            "waiting_sessions": sum(1 for ctx in self._sessions.values() if ctx.state == SessionState.WAITING),
            "total_pending": sum(len(ctx.pending_events) for ctx in self._sessions.values()),
        }


_lock_manager_instance: Optional[SessionLockManager] = None


def get_session_lock_manager() -> SessionLockManager:
    """获取全局会话锁管理器实例"""
    global _lock_manager_instance
    if _lock_manager_instance is None:
        _lock_manager_instance = SessionLockManager()
    return _lock_manager_instance


def set_session_lock_manager(manager: SessionLockManager):
    """设置全局会话锁管理器实例"""
    global _lock_manager_instance
    _lock_manager_instance = manager
