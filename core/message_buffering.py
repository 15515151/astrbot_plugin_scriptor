# core/message_buffering.py
"""
消息扣押与延迟处理模块（防刷屏利器）
功能：
1. 前台消息缓存（时间窗口聚合）
2. 耐心计时器（默认3-5秒）
3. 消息聚合与综合判断
4. 秘书决策逻辑
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


@dataclass
class BufferedMessage:
    """缓存的消息条目"""

    content: str
    timestamp: float
    sender_id: str
    message_id: Optional[str] = None


@dataclass
class BufferConfig:
    """缓冲器配置"""

    enabled: bool = True

    patience_seconds: float = 3.0

    max_patience_seconds: float = 10.0

    min_messages_to_trigger: int = 1

    max_buffer_size: int = 50

    enable_smart_aggregation: bool = True

    aggregation_separator: str = "\n"


class MessageBuffer:
    """消息缓冲器"""

    def __init__(self, config: Optional[BufferConfig] = None):
        self.config = config or BufferConfig()

        self._buffers: Dict[str, List[BufferedMessage]] = {}
        self._timers: Dict[str, asyncio.Task] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._last_message_time: Dict[str, float] = {}

        self._lock = asyncio.Lock()

    async def add_message(
        self,
        session_id: str,
        content: str,
        sender_id: str,
        message_id: Optional[str] = None,
        callback: Optional[Callable] = None,
    ) -> bool:
        """
        添加消息到缓冲区

        Args:
            session_id: 会话ID
            content: 消息内容
            sender_id: 发送者ID
            message_id: 消息ID（可选）
            callback: 计时器到期时的回调函数

        Returns:
            是否成功添加
        """
        if not self.config.enabled:
            if callback:
                asyncio.create_task(callback(session_id, [content]))
            return False

        async with self._lock:
            now = time.time()

            if session_id not in self._buffers:
                self._buffers[session_id] = []

            buffer = self._buffers[session_id]

            if len(buffer) >= self.config.max_buffer_size:
                logger.warning(f"[MessageBuffer] 缓冲区已满，清空旧消息: {session_id}")
                buffer.clear()

            buffered_msg = BufferedMessage(content=content, timestamp=now, sender_id=sender_id, message_id=message_id)
            buffer.append(buffered_msg)
            self._last_message_time[session_id] = now

            if callback:
                self._callbacks[session_id] = callback

            if session_id in self._timers and not self._timers[session_id].done():
                logger.debug(f"[MessageBuffer] 重置计时器: {session_id}")
                self._timers[session_id].cancel()

            patience = self._calculate_patience(session_id)
            logger.debug(f"[MessageBuffer] 设置计时器: {session_id}, {patience:.1f}秒")
            self._timers[session_id] = asyncio.create_task(self._wait_and_process(session_id, patience))

            return True

    def _calculate_patience(self, session_id: str) -> float:
        """
        计算耐心时间

        根据消息频率动态调整：
        - 消息来得越快，耐心时间越短
        - 消息来得越慢，耐心时间越长
        """
        buffer = self._buffers.get(session_id, [])

        if len(buffer) <= 1:
            return self.config.patience_seconds

        if len(buffer) >= 3:
            return min(self.config.patience_seconds * 0.5, self.config.max_patience_seconds)

        return self.config.patience_seconds

    async def _wait_and_process(self, session_id: str, patience: float):
        """等待耐心时间，然后处理消息"""
        try:
            await asyncio.sleep(patience)

            async with self._lock:
                if session_id not in self._buffers:
                    return

                buffer = self._buffers.pop(session_id, [])
                callback = self._callbacks.pop(session_id, None)

                if session_id in self._timers:
                    del self._timers[session_id]

            if buffer and callback:
                aggregated = self._aggregate_messages(buffer)
                logger.info(f"[MessageBuffer] 处理聚合消息: {session_id}, {len(buffer)}条")

                try:
                    await callback(session_id, aggregated)
                except (OSError, RuntimeError) as e:
                    logger.error(f"[MessageBuffer] 回调执行失败: {e}")

        except asyncio.CancelledError:
            logger.debug(f"[MessageBuffer] 计时器被取消: {session_id}")
        except (OSError, RuntimeError) as e:
            logger.error(f"[MessageBuffer] 处理失败: {e}")

    def _aggregate_messages(self, buffer: List[BufferedMessage]) -> List[str]:
        """
        聚合消息

        支持智能聚合：
        - 如果多条消息看起来是连贯的，合并在一起
        - 否则保持分离
        """
        if not self.config.enable_smart_aggregation or len(buffer) <= 1:
            return [msg.content for msg in buffer]

        contents = [msg.content for msg in buffer]

        if self._should_merge(contents):
            merged = self.config.aggregation_separator.join(contents)
            return [merged]

        return contents

    def _should_merge(self, contents: List[str]) -> bool:
        """判断是否应该合并消息"""
        if len(contents) < 2:
            return False

        last_content = contents[-1].strip()

        continuation_indicators = [
            "，",
            ",",
            "。",
            ".",
            "！",
            "!",
            "？",
            "?",
            "的",
            "了",
            "是",
            "在",
            "有",
            "和",
            "与",
            "然后",
            "接着",
            "还有",
            "另外",
            "而且",
            "that",
            "and",
            "or",
            "but",
            "so",
            "because",
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
        ]

        for indicator in continuation_indicators:
            if last_content.endswith(indicator):
                return True

        if len(last_content) < 10:
            return True

        return False

    async def force_flush(self, session_id: str) -> Optional[List[str]]:
        """
        强制刷新缓冲区（立即处理）

        Args:
            session_id: 会话ID

        Returns:
            聚合后的消息列表，如果没有则返回None
        """
        async with self._lock:
            if session_id not in self._buffers:
                return None

            if session_id in self._timers and not self._timers[session_id].done():
                self._timers[session_id].cancel()

            buffer = self._buffers.pop(session_id, [])
            callback = self._callbacks.pop(session_id, None)

            if session_id in self._timers:
                del self._timers[session_id]

        if buffer:
            aggregated = self._aggregate_messages(buffer)

            if callback:
                try:
                    await callback(session_id, aggregated)
                except (OSError, RuntimeError) as e:
                    logger.error(f"[MessageBuffer] 强制刷新回调执行失败: {e}")

            return aggregated

        return None

    def get_buffer_status(self, session_id: str) -> Optional[Dict]:
        """获取缓冲区状态"""
        if session_id not in self._buffers:
            return None

        buffer = self._buffers[session_id]
        return {
            "count": len(buffer),
            "oldest": datetime.fromtimestamp(buffer[0].timestamp).isoformat() if buffer else None,
            "newest": datetime.fromtimestamp(buffer[-1].timestamp).isoformat() if buffer else None,
            "has_timer": session_id in self._timers and not self._timers[session_id].done(),
        }

    def get_all_status(self) -> Dict[str, Dict]:
        """获取所有缓冲区状态"""
        return {sid: self.get_buffer_status(sid) for sid in self._buffers.keys()}

    async def clear(self, session_id: Optional[str] = None):
        """
        清空缓冲区

        Args:
            session_id: 会话ID，如果为None则清空所有
        """
        async with self._lock:
            if session_id:
                if session_id in self._timers and not self._timers[session_id].done():
                    self._timers[session_id].cancel()
                    del self._timers[session_id]
                self._buffers.pop(session_id, None)
                self._callbacks.pop(session_id, None)
                self._last_message_time.pop(session_id, None)
            else:
                for sid, timer in list(self._timers.items()):
                    if not timer.done():
                        timer.cancel()
                self._timers.clear()
                self._buffers.clear()
                self._callbacks.clear()
                self._last_message_time.clear()

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "enabled": self.config.enabled,
            "active_sessions": len(self._buffers),
            "total_buffered": sum(len(buf) for buf in self._buffers.values()),
            "patience_seconds": self.config.patience_seconds,
        }


_buffer_instance: Optional[MessageBuffer] = None


def get_message_buffer() -> MessageBuffer:
    """获取全局消息缓冲器实例"""
    global _buffer_instance
    if _buffer_instance is None:
        _buffer_instance = MessageBuffer()
    return _buffer_instance


def set_message_buffer(buffer: MessageBuffer):
    """设置全局消息缓冲器实例"""
    global _buffer_instance
    _buffer_instance = buffer
