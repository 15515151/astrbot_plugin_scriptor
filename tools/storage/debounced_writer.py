# tools/storage/debounced_writer.py
"""防抖写入器模块 - 高频I/O优化核心组件"""

import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class DebouncedWriter:
    """
    防抖写入器 - 高频I/O优化核心组件
    原理：将多次零散的写入请求合并为定期批量写入，大幅减少磁盘IOPS
    适用场景：跨群消息、群组交互记录等高频变更数据
    """

    def __init__(
        self,
        flush_interval: float = 60.0,
        batch_size: int = 100,
        file_path: Optional[Path] = None,
        serializer: Callable[[Any], str] = lambda x: json.dumps(x, ensure_ascii=False, indent=2),
        file_mode: str = "json",
    ):
        """
        初始化防抖写入器

        Args:
            flush_interval: 强制刷盘间隔（秒），默认60秒
            batch_size: 累积多少条变更后立即刷盘
            file_path: 文件路径（json模式必需）
            serializer: 序列化函数
            file_mode: 文件模式 "json" 或 "text"
        """
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.file_path = file_path
        self.serializer = serializer
        self.file_mode = file_mode

        self._data: Any = None
        self._pending_data: Any = None
        self._lock = threading.Lock()
        self._last_flush = time.time()
        self._flush_task: Optional[asyncio.Task] = None
        self._initialized = False

    def set_data(self, data: Any):
        """设置数据（仅更新内存，不立即写盘）"""
        with self._lock:
            self._pending_data = data

    def update(self, updater: Callable[[Any], Any]):
        """原子更新数据"""
        with self._lock:
            if self._pending_data is None and self._data is not None:
                self._pending_data = self._data
            elif self._pending_data is None:
                self._pending_data = {}

            self._pending_data = updater(self._pending_data)
            self._check_flush_conditions()

    def _check_flush_conditions(self):
        """检查是否满足刷盘条件"""
        now = time.time()
        is_batch_full = False

        if isinstance(self._pending_data, dict) or isinstance(self._pending_data, list):
            is_batch_full = len(self._pending_data) >= self.batch_size

        if is_batch_full or (now - self._last_flush) >= self.flush_interval:
            self._flush()

    def _flush(self):
        """执行刷盘（同步，后台线程调用）"""
        if self._pending_data is None:
            return

        self._data = self._pending_data
        self._pending_data = None
        self._last_flush = time.time()

        if not self.file_path:
            return

        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            if self.file_mode == "json":
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.write(self.serializer(self._data))
            else:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.write(str(self._data))

            logger.debug(f"[DebouncedWriter] 刷盘成功: {self.file_path}")
        except Exception as e:
            logger.error(f"[Scriptor] 防抖写入失败 {self.file_path}: {e}")

    async def flush(self):
        """手动触发刷盘（异步）"""
        with self._lock:
            self._flush()

    async def start(self, initial_data: Any):
        """启动后台调度"""
        self._data = initial_data
        self._pending_data = None
        self._initialized = True

        async def _periodic_flush():
            while self._initialized:
                await asyncio.sleep(self.flush_interval)
                with self._lock:
                    if self._pending_data is not None:
                        self._flush()

        self._flush_task = asyncio.create_task(_periodic_flush())

    async def stop(self):
        """停止并确保数据落盘"""
        self._initialized = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()

    def get_data(self) -> Any:
        """获取当前内存数据"""
        with self._lock:
            if self._pending_data is not None:
                return self._pending_data
            return self._data
