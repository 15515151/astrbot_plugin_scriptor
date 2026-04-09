# tools/performance/monitor.py
"""性能监控工具 - 用于监控NAS环境下的资源使用情况"""

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    """性能快照"""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float


@dataclass
class OperationMetric:
    """操作指标"""

    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None


class PerformanceMonitor:
    """
    性能监控器 - 专为NAS环境优化

    功能：
    - CPU/内存/磁盘/网络实时监控
    - 操作耗时追踪
    - 性能基线建立
    - 资源告警
    """

    def __init__(self, data_dir: Path, sample_interval: float = 5.0, history_size: int = 288):
        """
        Args:
            data_dir: 数据目录
            sample_interval: 采样间隔（秒），默认5秒
            history_size: 历史记录数量，默认288（24小时采样）
        """
        self.data_dir = data_dir
        self.sample_interval = sample_interval
        self.history_size = history_size

        self._snapshots: deque = deque(maxlen=history_size)
        self._operation_metrics: Dict[str, List[OperationMetric]] = {}
        self._is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()

        self._baseline_cpu: float = 0.0
        self._baseline_memory: float = 0.0
        self._baseline_disk_io: float = 0.0

        self._alert_callbacks: List[Callable[[str, Dict], None]] = []

        self._process = psutil.Process()

        try:
            self._initial_disk_io = psutil.disk_io_counters()
            self._initial_net_io = psutil.net_io_counters()
        except Exception as e:
            logger.debug(f"[PerformanceMonitor] 获取初始IO计数失败: {e}")
            self._initial_disk_io = None
            self._initial_net_io = None

    def add_alert_callback(self, callback: Callable[[str, Dict], None]):
        """添加告警回调"""
        self._alert_callbacks.append(callback)

    def _take_snapshot(self) -> PerformanceSnapshot:
        """获取当前性能快照"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)

            mem = psutil.virtual_memory()
            memory_percent = mem.percent
            memory_used_mb = mem.used / (1024 * 1024)
            memory_available_mb = mem.available / (1024 * 1024)

            disk = psutil.disk_usage("/")
            disk_usage_percent = disk.percent

            disk_io_read_mb = 0.0
            disk_io_write_mb = 0.0
            try:
                disk_io = psutil.disk_io_counters()
                if self._initial_disk_io and disk_io:
                    disk_io_read_mb = (disk_io.read_bytes - self._initial_disk_io.read_bytes) / (1024 * 1024)
                    disk_io_write_mb = (disk_io.write_bytes - self._initial_disk_io.write_bytes) / (1024 * 1024)
                    self._initial_disk_io = disk_io
            except Exception as e:
                logger.debug(f"[PerformanceMonitor] 获取磁盘IO失败: {e}")

            network_sent_mb = 0.0
            network_recv_mb = 0.0
            try:
                net_io = psutil.net_io_counters()
                if self._initial_net_io and net_io:
                    network_sent_mb = (net_io.bytes_sent - self._initial_net_io.bytes_sent) / (1024 * 1024)
                    network_recv_mb = (net_io.bytes_recv - self._initial_net_io.bytes_recv) / (1024 * 1024)
                    self._initial_net_io = net_io
            except Exception as e:
                logger.debug(f"[PerformanceMonitor] 获取网络IO失败: {e}")

            snapshot = PerformanceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_io_read_mb=disk_io_read_mb,
                disk_io_write_mb=disk_io_write_mb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
            )

            return snapshot

        except Exception:
            return PerformanceSnapshot(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                disk_io_read_mb=0.0,
                disk_io_write_mb=0.0,
                network_sent_mb=0.0,
                network_recv_mb=0.0,
            )

    async def _monitor_loop(self):
        """监控循环"""
        while self._is_monitoring:
            try:
                snapshot = self._take_snapshot()

                with self._lock:
                    self._snapshots.append(snapshot)

                    self._check_thresholds(snapshot)

                await asyncio.sleep(self.sample_interval)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(self.sample_interval)

    def _check_thresholds(self, snapshot: PerformanceSnapshot):
        """检查阈值并触发告警"""
        alerts = []

        if snapshot.cpu_percent > 90:
            alerts.append(
                (
                    "HIGH_CPU",
                    {"cpu_percent": snapshot.cpu_percent, "message": f"CPU使用率过高: {snapshot.cpu_percent:.1f}%"},
                )
            )

        if snapshot.memory_percent > 85:
            alerts.append(
                (
                    "HIGH_MEMORY",
                    {
                        "memory_percent": snapshot.memory_percent,
                        "memory_used_mb": snapshot.memory_used_mb,
                        "message": f"内存使用率过高: {snapshot.memory_percent:.1f}%",
                    },
                )
            )

        if snapshot.disk_usage_percent > 90:
            alerts.append(
                (
                    "HIGH_DISK",
                    {
                        "disk_usage_percent": snapshot.disk_usage_percent,
                        "message": f"磁盘使用率过高: {snapshot.disk_usage_percent:.1f}%",
                    },
                )
            )

        for alert_type, alert_data in alerts:
            for callback in self._alert_callbacks:
                try:
                    callback(alert_type, alert_data)
                except Exception as e:
                    logger.debug(f"[PerformanceMonitor] 告警回调执行失败: {e}")

    def start(self):
        """启动监控"""
        if self._is_monitoring:
            return

        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """停止监控"""
        self._is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        snapshot = self._take_snapshot()

        return {
            "timestamp": datetime.fromtimestamp(snapshot.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "cpu_percent": snapshot.cpu_percent,
            "memory_percent": snapshot.memory_percent,
            "memory_used_mb": snapshot.memory_used_mb,
            "memory_available_mb": snapshot.memory_available_mb,
            "disk_usage_percent": snapshot.disk_usage_percent,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            if not self._snapshots:
                return {}

            cpu_values = [s.cpu_percent for s in self._snapshots]
            mem_values = [s.memory_percent for s in self._snapshots]
            disk_values = [s.disk_usage_percent for s in self._snapshots]

            return {
                "sample_count": len(self._snapshots),
                "period_start": (
                    datetime.fromtimestamp(self._snapshots[0].timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    if self._snapshots
                    else None
                ),
                "period_end": (
                    datetime.fromtimestamp(self._snapshots[-1].timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    if self._snapshots
                    else None
                ),
                "cpu": {
                    "avg": sum(cpu_values) / len(cpu_values),
                    "max": max(cpu_values),
                    "min": min(cpu_values),
                },
                "memory": {
                    "avg": sum(mem_values) / len(mem_values),
                    "max": max(mem_values),
                    "min": min(mem_values),
                },
                "disk": {
                    "avg": sum(disk_values) / len(disk_values),
                    "max": max(disk_values),
                    "min": min(disk_values),
                },
            }

    def get_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []

        stats = self.get_statistics()
        if not stats:
            return recommendations

        if stats.get("cpu", {}).get("avg", 0) > 70:
            recommendations.append("CPU平均使用率较高，建议检查后台进程或优化计算密集型操作")

        if stats.get("memory", {}).get("avg", 0) > 75:
            recommendations.append("内存平均使用率较高，建议增加缓存清理频率或优化内存使用")

        if stats.get("disk", {}).get("avg", 0) > 80:
            recommendations.append("磁盘使用率较高，建议清理不必要的文件或扩展存储")

        return recommendations


class OperationTimer:
    """操作计时器 - 用于追踪特定操作的耗时"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._metrics: Dict[str, List[OperationMetric]] = {}
        self._active_operations: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._enabled = True
        self._initialized = True

    def enable(self):
        """启用计时器"""
        self._enabled = True

    def disable(self):
        """禁用计时器"""
        self._enabled = False

    def start(self, operation_name: str) -> str:
        """开始计时"""
        if not self._enabled:
            return operation_name

        operation_id = f"{operation_name}_{time.time()}"
        self._active_operations[operation_id] = time.time()
        return operation_id

    def end(self, operation_id: str, success: bool = True, error: Optional[str] = None):
        """结束计时"""
        if not self._enabled or operation_id not in self._active_operations:
            return

        start_time = self._active_operations.pop(operation_id)
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        parts = operation_id.rsplit("_", 1)
        operation_name = parts[0] if parts else operation_id

        metric = OperationMetric(
            name=operation_name,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            success=success,
            error_message=error,
        )

        with self._lock:
            if operation_name not in self._metrics:
                self._metrics[operation_name] = []
            self._metrics[operation_name].append(metric)

            if len(self._metrics[operation_name]) > 1000:
                self._metrics[operation_name] = self._metrics[operation_name][-1000:]

    def get_metrics(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """获取指标"""
        with self._lock:
            if operation_name:
                metrics = self._metrics.get(operation_name, [])
            else:
                all_metrics = {}
                for name, metric_list in self._metrics.items():
                    all_metrics[name] = self._summarize_metrics(metric_list)
                return all_metrics

            if not metrics:
                return {}

            return self._summarize_metrics(metrics)

    def _summarize_metrics(self, metrics: List[OperationMetric]) -> Dict[str, Any]:
        """汇总指标"""
        durations = [m.duration_ms for m in metrics if m.duration_ms is not None]
        success_count = sum(1 for m in metrics if m.success)
        failure_count = len(metrics) - success_count

        return {
            "count": len(metrics),
            "success_count": success_count,
            "failure_count": failure_count,
            "duration_ms": {
                "avg": sum(durations) / len(durations) if durations else 0,
                "max": max(durations) if durations else 0,
                "min": min(durations) if durations else 0,
                "p95": (
                    sorted(durations)[int(len(durations) * 0.95)]
                    if durations and len(durations) > 1
                    else (durations[0] if durations else 0)
                ),
                "p99": (
                    sorted(durations)[int(len(durations) * 0.99)]
                    if durations and len(durations) > 1
                    else (durations[0] if durations else 0)
                ),
            },
        }

    def clear(self, operation_name: Optional[str] = None):
        """清除指标"""
        with self._lock:
            if operation_name:
                self._metrics.pop(operation_name, None)
            else:
                self._metrics.clear()

    def get_slow_operations(self, threshold_ms: float = 1000) -> List[Dict[str, Any]]:
        """获取慢操作"""
        slow_ops = []
        with self._lock:
            for name, metrics in self._metrics.items():
                for metric in metrics:
                    if metric.duration_ms and metric.duration_ms > threshold_ms:
                        slow_ops.append(
                            {
                                "operation": name,
                                "duration_ms": metric.duration_ms,
                                "timestamp": datetime.fromtimestamp(metric.start_time).strftime("%Y-%m-%d %H:%M:%S"),
                                "success": metric.success,
                                "error": metric.error_message,
                            }
                        )

        return sorted(slow_ops, key=lambda x: x["duration_ms"], reverse=True)


class PerformanceTracker:
    """性能追踪上下文管理器"""

    def __init__(self, operation_name: str, timer: Optional[OperationTimer] = None):
        self.operation_name = operation_name
        self.timer = timer or OperationTimer()
        self.operation_id: Optional[str] = None

    def __enter__(self):
        self.operation_id = self.timer.start(self.operation_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.operation_id:
            success = exc_type is None
            error = str(exc_val) if exc_val else None
            self.timer.end(self.operation_id, success=success, error=error)
        return False


def get_operation_timer() -> OperationTimer:
    """获取全局操作计时器实例"""
    return OperationTimer()


def track_operation(operation_name: str):
    """装饰器：追踪函数执行时间"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            timer = get_operation_timer()
            operation_id = timer.start(operation_name)
            try:
                result = await func(*args, **kwargs)
                timer.end(operation_id, success=True)
                return result
            except Exception as e:
                timer.end(operation_id, success=False, error=str(e))
                raise

        def sync_wrapper(*args, **kwargs):
            timer = get_operation_timer()
            operation_id = timer.start(operation_name)
            try:
                result = func(*args, **kwargs)
                timer.end(operation_id, success=True)
                return result
            except Exception as e:
                timer.end(operation_id, success=False, error=str(e))
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
