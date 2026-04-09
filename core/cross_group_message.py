# core/cross_group_message.py
"""Scriptor 跨群消息传递模块"""

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class CrossGroupMessageType(str, Enum):
    """跨群消息类型"""

    TASK = "task"
    REMINDER = "reminder"
    INFO = "info"
    DECISION = "decision"


@dataclass
class CrossGroupMessage:
    """跨群消息/任务传递"""

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_group: str = ""
    target_groups: List[str] = field(default_factory=list)
    content: str = ""
    message_type: str = CrossGroupMessageType.INFO.value
    created_at: float = field(default_factory=time.time)
    delivered: bool = False
    delivered_at: Optional[float] = None
    expires_at: float = field(default_factory=lambda: time.time() + 86400 * 7)
    author_uid: str = ""
    author_name: str = ""
    remind_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CrossGroupMessage":
        return cls(**data)

    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > self.expires_at


class CrossGroupMessageSystem:
    """跨群消息传递系统 - 使用防抖写入优化I/O"""

    def __init__(self, data_dir: Path, config, identity_manager, group_manager):
        self.data_dir = data_dir
        self.config = config
        self.identity_manager = identity_manager
        self.group_manager = group_manager

        self.messages_file = data_dir / "cross_group_messages.json"
        self.pending_messages: List[CrossGroupMessage] = []
        self._debounced_writer: Optional[Any] = None
        self._load()

    def _load(self):
        """加载跨群消息"""
        if self.messages_file.exists():
            try:
                with open(self.messages_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for msg_data in data.get("messages", []):
                        msg = CrossGroupMessage.from_dict(msg_data)
                        if not msg.is_expired():
                            self.pending_messages.append(msg)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"[Scriptor] 加载跨群消息失败: {e}")

    async def start(self):
        """启动防抖写入器"""
        from tools.storage.debounced_writer import DebouncedWriter

        self._debounced_writer = DebouncedWriter(
            flush_interval=30.0,
            batch_size=50,
            file_path=self.messages_file,
            serializer=lambda x: json.dumps(x, ensure_ascii=False, indent=2),
            file_mode="json",
        )
        await self._debounced_writer.start({"messages": [msg.to_dict() for msg in self.pending_messages]})

    async def stop(self):
        """停止防抖写入器并确保数据落盘"""
        if self._debounced_writer:
            await self._debounced_writer.stop()

    def _save(self):
        """保存跨群消息（通过防抖写入器）"""
        if self._debounced_writer:
            self._debounced_writer.set_data({"messages": [msg.to_dict() for msg in self.pending_messages]})
        else:
            self._save_direct()

    def _save_direct(self):
        """直接保存（防抖写入器未启动时备用）"""
        try:
            data = {"messages": [msg.to_dict() for msg in self.pending_messages]}
            self.messages_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.messages_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"[Scriptor] 保存跨群消息失败: {e}")

    async def detect_and_route(self, group_id: str, content: str, author_uid: str, author_name: str = "") -> bool:
        """
        检测并路由跨群信息

        Returns:
            bool: 是否检测到跨群信息
        """
        if not self.config.cross_group_enabled:
            return False

        if not self._is_cross_group_task(content):
            return False

        task_info = self._parse_task_info(content)
        target_groups = await self._determine_target_groups(author_uid, group_id, task_info)

        if not target_groups:
            return False

        author_name = author_name or self.identity_manager.get_user_primary_name(author_uid)

        message = CrossGroupMessage(
            source_group=group_id,
            target_groups=target_groups,
            content=content,
            message_type=CrossGroupMessageType.TASK.value,
            author_uid=author_uid,
            author_name=author_name,
            remind_at=task_info.get("remind_at"),
        )

        self.pending_messages.append(message)
        self._save()

        logger.info(f"[Scriptor] 创建跨群消息: {message.message_id}, 目标: {target_groups}")

        return True

    def _is_cross_group_task(self, content: str) -> bool:
        """检测是否为跨群任务"""
        cross_keywords = [
            "提醒我",
            "稍后提醒",
            "下班前",
            "今晚提醒",
            "明天提醒",
            "任务",
            "待办",
            "todo",
            "提醒大家",
            "帮我记着",
            "别忘了",
            "记得提醒",
        ]
        return any(kw in content for kw in cross_keywords)

    def _parse_task_info(self, content: str) -> Dict:
        """解析任务信息"""
        info = {"content": content, "remind_at": "today"}

        content_lower = content.lower()
        if "今晚" in content or "今天晚上" in content:
            info["remind_at"] = "tonight"
        elif "明天" in content:
            info["remind_at"] = "tomorrow"
        elif "下周" in content:
            info["remind_at"] = "next_week"

        return info

    async def _determine_target_groups(self, author_uid: str, source_group: str, task_info: Dict) -> List[str]:
        """确定目标群体"""
        target_groups = self.group_manager.get_other_groups(author_uid, source_group)

        if not target_groups:
            return []

        content = task_info.get("content", "").lower()

        if any(w in content for w in ["工作", "项目", "会议", "同事"]):
            filtered = [g for g in target_groups if "work" in g.lower() or "工作" in g.lower()]
            if filtered:
                return filtered

        if any(w in content for w in ["家庭", "爸妈", "老婆", "老公", "家人"]):
            filtered = [g for g in target_groups if "family" in g.lower() or "家庭" in g.lower()]
            if filtered:
                return filtered

        return target_groups[:2]

    async def create_reminder(
        self,
        source_group: str,
        target_groups: List[str],
        message: str,
        author_uid: str,
        author_name: str = "",
        remind_at: str = "today",
    ) -> CrossGroupMessage:
        """创建提醒"""
        author_name = author_name or self.identity_manager.get_user_primary_name(author_uid)

        msg = CrossGroupMessage(
            source_group=source_group,
            target_groups=target_groups,
            content=message,
            message_type=CrossGroupMessageType.REMINDER.value,
            author_uid=author_uid,
            author_name=author_name,
            remind_at=remind_at,
            expires_at=time.time() + 86400 * 7,
        )

        self.pending_messages.append(msg)
        self._save()

        return msg

    def get_pending_messages(self, group_id: str) -> List[CrossGroupMessage]:
        """获取群体待投递消息"""
        messages = []
        for msg in self.pending_messages:
            if group_id in msg.target_groups and not msg.delivered:
                messages.append(msg)
        return messages

    def mark_delivered(self, message_id: str):
        """标记消息已投递"""
        for msg in self.pending_messages:
            if msg.message_id == message_id:
                msg.delivered = True
                msg.delivered_at = time.time()
                self._save()
                break

    def cleanup_expired(self):
        """清理过期消息"""
        self.pending_messages = [msg for msg in self.pending_messages if not msg.is_expired()]
        self._save()

    def format_pending_notifications(self, group_id: str) -> str:
        """格式化待投递通知"""
        messages = self.get_pending_messages(group_id)
        if not messages:
            return ""

        parts = ["## 跨群待办提醒\n"]
        for msg in messages:
            time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(msg.created_at))
            # 尝试获取人类可读的群名
            source_group_name = self.group_manager.get_group_name(msg.source_group)
            parts.append(
                f"- **{msg.author_name}** (来自群: {source_group_name}): {msg.content}\n" f"  - 创建时间: {time_str}\n"
            )

        return "\n".join(parts)
