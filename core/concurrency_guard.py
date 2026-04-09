# core/concurrency_guard.py
"""
全局并发控制模块

功能：
1. 全局信号量限制最大并发 LLM 请求数
2. 优先级队列调度（admin > private > group > background）
3. 并发状态监控与统计
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class Priority(Enum):
    """优先级枚举"""

    ADMIN = 100
    PRIVATE = 50
    GROUP = 10
    BACKGROUND = 0


@dataclass
class WaitingRequest:
    """等待中的请求"""

    session_id: str
    priority: Priority
    arrived_at: float
    future: asyncio.Future = None


class ConcurrencyGuard:
    """
    全局并发控制器

    通过 asyncio.Semaphore 实现全局并发限制，
    配合优先级队列实现智能调度。
    """

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count: int = 0
        self._waiting_queue: deque[WaitingRequest] = deque()
        self._active_sessions: Dict[str, float] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._total_acquired: int = 0
        self._total_released: int = 0
        self._total_wait_time: float = 0.0
        self._wait_count: int = 0

    async def acquire(
        self, session_id: str, priority: Priority = Priority.GROUP, timeout: Optional[float] = None
    ) -> bool:
        """
        获取全局并发槽位

        Args:
            session_id: 会话 ID
            priority: 优先级
            timeout: 超时时间（秒），None 表示无限等待

        Returns:
            是否成功获取
        """
        arrived_at = time.time()

        async with self._lock:
            if self._semaphore._value > 0:
                await self._semaphore.acquire()
                self._active_count += 1
                self._active_sessions[session_id] = time.time()
                self._total_acquired += 1
                return True

            waiting_req = WaitingRequest(
                session_id=session_id,
                priority=priority,
                arrived_at=arrived_at,
                future=asyncio.get_event_loop().create_future(),
            )
            self._waiting_queue.append(waiting_req)

        try:
            if timeout is not None:
                try:
                    await asyncio.wait_for(waiting_req.future, timeout=timeout)
                except asyncio.TimeoutError:
                    async with self._lock:
                        if waiting_req in self._waiting_queue:
                            self._waiting_queue.remove(waiting_req)
                            waiting_req.future.set_result(False)
                    return False
            else:
                await waiting_req.future

            return waiting_req.future.result()

        except Exception as e:
            logger.error(f"[ConcurrencyGuard] 获取锁异常: {e}")
            async with self._lock:
                if waiting_req in self._waiting_queue:
                    self._waiting_queue.remove(waiting_req)
            return False

    def release(self, session_id: str):
        """
        释放全局并发槽位

        Args:
            session_id: 会话 ID
        """
        try:
            self._semaphore.release()
            self._total_released += 1

            async def _async_release():
                async with self._lock:
                    self._active_count -= 1
                    if session_id in self._active_sessions:
                        del self._active_sessions[session_id]

                    self._schedule_next()

            task = asyncio.create_task(_async_release())

        except Exception as e:
            logger.error(f"[ConcurrencyGuard] 释放锁异常: {e}")

    async def _schedule_next(self):
        """调度下一个等待的请求"""
        if not self._waiting_queue:
            return

        if self._semaphore._value <= 0:
            return

        sorted_waiting = sorted(self._waiting_queue, key=lambda x: (-x.priority.value, x.arrived_at))

        next_req = sorted_waiting[0]
        self._waiting_queue.remove(next_req)

        wait_time = time.time() - next_req.arrived_at
        self._total_wait_time += wait_time
        self._wait_count += 1

        try:
            await self._semaphore.acquire()
            self._active_count += 1
            self._active_sessions[next_req.session_id] = time.time()
            self._total_acquired += 1
            next_req.future.set_result(True)
        except Exception as e:
            logger.error(f"[ConcurrencyGuard] 调度下一个请求失败: {e}")
            if not next_req.future.done():
                next_req.future.set_result(False)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "max_concurrent": self.max_concurrent,
            "active": self._active_count,
            "waiting": len(self._waiting_queue),
            "active_sessions": list(self._active_sessions.keys()),
            "waiting_details": [
                {
                    "session_id": w.session_id,
                    "priority": w.priority.name,
                    "wait_seconds": round(time.time() - w.arrived_at, 1),
                }
                for w in list(self._waiting_queue)[:10]
            ],
            "total_acquired": self._total_acquired,
            "total_released": self._total_released,
            "avg_wait_time": round(self._total_wait_time / max(1, self._wait_count), 2) if self._wait_count > 0 else 0,
        }

    def update_max_concurrent(self, new_max: int):
        """动态调整最大并发数（需谨慎使用）"""
        if new_max < 1:
            new_max = 1

        old_max = self.max_concurrent
        diff = new_max - old_max

        if diff > 0:
            for _ in range(diff):
                self._semaphore.release()
        elif diff < 0:
            pass

        self.max_concurrent = new_max
        logger.info(f"[ConcurrencyGuard] 最大并发数调整: {old_max} → {new_max}")


def compute_priority_from_event(event, admin_uids: set = None) -> Priority:
    """
    从事件计算优先级

    Args:
        event: AstrBot 消息事件
        admin_uids: 管理员 UID 集合

    Returns:
        优先级枚举值
    """
    if admin_uids is None:
        admin_uids = set()

    uid = getattr(event, "get_sender_id", lambda: None)()
    gid = getattr(event, "get_group_id", lambda: None)()

    if uid and uid in admin_uids:
        return Priority.ADMIN

    if gid and gid != "private":
        return Priority.GROUP

    return Priority.PRIVATE


_guard_instance: Optional[ConcurrencyGuard] = None


def get_concurrency_guard() -> ConcurrencyGuard:
    """获取全局并发控制器实例"""
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = ConcurrencyGuard(max_concurrent=5)
    return _guard_instance


def set_concurrency_guard(guard: ConcurrencyGuard):
    """设置全局并发控制器实例"""
    global _guard_instance
    _guard_instance = guard
