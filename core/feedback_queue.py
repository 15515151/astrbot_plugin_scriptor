# core/feedback_queue.py
"""
反馈队列模块 - 异步处理记忆更新，不阻塞对话
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型"""

    MEMORY_EXTRACTION = "memory_extraction"
    MEMORY_REINFORCE = "memory_reinforce"
    PROFILE_UPDATE = "profile_update"
    SLEEP_CONSOLIDATION = "sleep_consolidation"
    INDEX_REBUILD = "index_rebuild"


@dataclass
class FeedbackTask:
    """反馈任务"""

    task_type: FeedbackType
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1-10, 1最高
    created_at: float = field(default_factory=lambda: __import__("time").time())
    max_retries: int = 3
    retry_count: int = 0


class FeedbackQueue:
    """反馈队列 - 异步处理记忆更新"""

    def __init__(self):
        self._queue: deque = deque()
        self._lock = asyncio.Lock()
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._processors: Dict[FeedbackType, Callable] = {}
        self._stop_event = asyncio.Event()

    def register_processor(self, task_type: FeedbackType, processor: Callable):
        """注册任务处理器"""
        self._processors[task_type] = processor
        logger.debug(f"[FeedbackQueue] 注册处理器: {task_type}")

    async def enqueue(self, task: FeedbackTask) -> bool:
        """将任务加入队列"""
        async with self._lock:
            self._queue.append(task)
            # 按优先级排序
            self._queue = deque(sorted(self._queue, key=lambda x: x.priority))
            logger.debug(f"[FeedbackQueue] 任务入队: {task.task_type}, 队列长度: {len(self._queue)}")
            return True

    async def _process_task(self, task: FeedbackTask) -> bool:
        """处理单个任务"""
        try:
            processor = self._processors.get(task.task_type)
            if not processor:
                logger.warning(f"[FeedbackQueue] 未找到处理器: {task.task_type}")
                return False

            if asyncio.iscoroutinefunction(processor):
                await processor(task.data)
            else:
                processor(task.data)

            logger.debug(f"[FeedbackQueue] 任务处理成功: {task.task_type}")
            return True

        except Exception as e:
            logger.error(f"[FeedbackQueue] 任务处理失败: {task.task_type}, 错误: {e}")
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                # 重试：重新入队，优先级降低
                task.priority = min(10, task.priority + 1)
                await self.enqueue(task)
                logger.info(f"[FeedbackQueue] 任务将重试 ({task.retry_count}/{task.max_retries}): {task.task_type}")
            return False

    async def _worker_loop(self):
        """工作循环"""
        logger.info("[FeedbackQueue] 工作循环启动")

        while not self._stop_event.is_set():
            try:
                task = None

                # 获取任务
                async with self._lock:
                    if self._queue:
                        task = self._queue.popleft()

                if task:
                    await self._process_task(task)
                else:
                    # 队列为空，等待
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                logger.info("[FeedbackQueue] 工作循环被取消")
                break
            except Exception as e:
                logger.error(f"[FeedbackQueue] 工作循环异常: {e}")
                await asyncio.sleep(1)  # 避免错误循环

        logger.info("[FeedbackQueue] 工作循环停止")

    def start(self):
        """启动队列处理"""
        if self._is_running:
            return

        self._is_running = True
        self._stop_event.clear()
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("[FeedbackQueue] 队列已启动")

    async def stop(self):
        """停止队列处理"""
        if not self._is_running:
            return

        self._is_running = False
        self._stop_event.set()

        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("[FeedbackQueue] 队列已停止")

    def queue_size(self) -> int:
        """获取队列大小"""
        return len(self._queue)

    def is_empty(self) -> bool:
        """队列是否为空"""
        return len(self._queue) == 0


# 全局队列实例
_global_queue: Optional[FeedbackQueue] = None


def get_feedback_queue() -> FeedbackQueue:
    """获取全局反馈队列实例"""
    global _global_queue
    if _global_queue is None:
        _global_queue = FeedbackQueue()
    return _global_queue


def init_feedback_queue() -> FeedbackQueue:
    """初始化全局反馈队列"""
    global _global_queue
    _global_queue = FeedbackQueue()
    return _global_queue
