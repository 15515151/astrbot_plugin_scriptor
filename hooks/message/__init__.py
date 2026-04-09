# hooks/message/__init__.py
"""消息处理钩子模块"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class MessageHook(ABC):
    """消息钩子基类"""

    @abstractmethod
    async def on_before_recording(self, event: Any) -> bool:
        """
        消息记录前调用

        Args:
            event: 消息事件

        Returns:
            True 继续记录，False 跳过记录
        """
        return True

    @abstractmethod
    async def on_after_recording(self, event: Any, uid: str, group_id: str):
        """
        消息记录后调用

        Args:
            event: 消息事件
            uid: 用户ID
            group_id: 群组ID
        """
        pass

    @abstractmethod
    async def on_buffer_flush(self, session_id: str, messages: List[str]):
        """
        消息缓冲刷新时调用

        Args:
            session_id: 会话ID
            messages: 待刷新消息列表
        """
        pass


class RecordingHook(MessageHook):
    """记录钩子 - 可继承自定义记录行为"""

    async def on_before_recording(self, event: Any) -> bool:
        return True

    async def on_after_recording(self, event: Any, uid: str, group_id: str):
        pass

    async def on_buffer_flush(self, session_id: str, messages: List[str]):
        pass
