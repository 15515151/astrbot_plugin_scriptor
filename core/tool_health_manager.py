# core/tool_health_manager.py
"""
Scriptor 工具健康管理与降级模式

提供工具的健康检查、降级模式和状态监控功能：
- 工具健康检查接口
- 自动降级机制（工具不可用时从可用列表移除）
- 健康状态监控与日志
- 优雅恢复机制
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class ToolHealthStatus(Enum):
    """工具健康状态"""

    HEALTHY = "healthy"  # 正常可用
    DEGRADED = "degraded"  # 降级运行（部分功能不可用）
    UNHEALTHY = "unhealthy"  # 不健康（可能失败）
    DISABLED = "disabled"  # 已禁用
    UNKNOWN = "unknown"  # 状态未知


@dataclass
class ToolHealthRecord:
    """工具健康记录"""

    tool_name: str
    status: ToolHealthStatus = ToolHealthStatus.UNKNOWN
    last_check_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    error_message: Optional[str] = None
    recovery_attempt: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "last_check": datetime.fromtimestamp(self.last_check_time).isoformat() if self.last_check_time else None,
            "last_success": (
                datetime.fromtimestamp(self.last_success_time).isoformat() if self.last_success_time else None
            ),
            "last_failure": (
                datetime.fromtimestamp(self.last_failure_time).isoformat() if self.last_failure_time else None
            ),
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "consecutive_failures": self.consecutive_failures,
            "error_message": self.error_message,
        }


@dataclass
class ToolHealthConfig:
    """工具健康检查配置"""

    max_consecutive_failures: int = 3  # 连续失败多少次后标记为不健康
    check_interval_seconds: float = 300.0  # 检查间隔（秒）
    auto_recovery_interval: float = 600.0  # 自动恢复尝试间隔（秒）
    enable_degradation: bool = True  # 是否启用自动降级
    log_health_changes: bool = True  # 是否记录健康状态变化


class ToolHealthManager:
    """
    工具健康管理器

    功能：
    - 注册工具并提供健康检查回调
    - 监控工具执行状态
    - 自动降级不健康的工具
    - 定期尝试恢复已降级的工具
    - 提供健康状态查询和报告
    """

    _instance: Optional["ToolHealthManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._health_records: Dict[str, ToolHealthRecord] = {}
        self._health_checks: Dict[str, Callable] = {}  # tool_name -> async health_check()
        self._config: ToolHealthConfig = ToolHealthConfig()
        self._degraded_tools: Set[str] = set()  # 当前被降级的工具集合
        self._background_task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self._initialized = True

        logger.info("[ToolHealthManager] 初始化完成")

    def configure(self, config: ToolHealthConfig):
        """配置健康检查参数"""
        self._config = config
        logger.info(
            f"[ToolHealthManager] 配置已更新：max_failures={config.max_consecutive_failures}, "
            f"check_interval={config.check_interval_seconds}s"
        )

    def register_tool(
        self,
        tool_name: str,
        health_check: Optional[Callable[[], Any]] = None,
        initial_status: ToolHealthStatus = ToolHealthStatus.UNKNOWN,
    ) -> bool:
        """
        注册一个工具

        Args:
            tool_name: 工具名称
            health_check: 健康检查函数，返回 (is_healthy: bool, message: str)
            initial_status: 初始状态

        Returns:
            是否注册成功
        """
        if not tool_name:
            logger.error("[ToolHealthManager] 无法注册空名称的工具")
            return False

        record = ToolHealthRecord(tool_name=tool_name, status=initial_status, last_check_time=time.time())

        self._health_records[tool_name] = record

        if health_check:
            self._health_checks[tool_name] = health_check

        logger.debug(f"[ToolHealthManager] 已注册工具：{tool_name} (初始状态: {initial_status.value})")
        return True

    def unregister_tool(self, tool_name: str) -> bool:
        """注销一个工具"""
        if tool_name in self._health_records:
            del self._health_records[tool_name]
            self._health_checks.pop(tool_name, None)
            self._degraded_tools.discard(tool_name)
            logger.info(f"[ToolHealthManager] 已注销工具：{tool_name}")
            return True
        return False

    async def report_execution_result(self, tool_name: str, success: bool, error_message: Optional[str] = None):
        """
        报告工具执行结果

        Args:
            tool_name: 工具名称
            success: 是否成功
            error_message: 错误信息（如果失败）
        """
        if tool_name not in self._health_records:
            self.register_tool(tool_name)

        record = self._health_records[tool_name]
        current_time = time.time()

        record.last_check_time = current_time

        if success:
            record.success_count += 1
            record.last_success_time = current_time
            record.consecutive_failures = 0
            record.error_message = None

            old_status = record.status
            if record.status in [ToolHealthStatus.UNHEALTHY, ToolHealthStatus.DEGRADED]:
                record.status = ToolHealthStatus.HEALTHY
                self._degraded_tools.discard(tool_name)

                if self._config.log_health_changes and old_status != record.status:
                    logger.info(f"[ToolHealthManager] ✅ 工具恢复健康：{tool_name}")

            if record.status == ToolHealthStatus.UNKNOWN:
                record.status = ToolHealthStatus.HEALTHY

        else:
            record.failure_count += 1
            record.last_failure_time = current_time
            record.consecutive_failures += 1
            record.error_message = error_message or "未知错误"

            should_degrade = (
                self._config.enable_degradation
                and record.consecutive_failures >= self._config.max_consecutive_failures
                and record.status == ToolHealthStatus.HEALTHY
            )

            if should_degrade:
                old_status = record.status
                record.status = ToolHealthStatus.UNHEALTHY
                self._degraded_tools.add(tool_name)

                if self._config.log_health_changes:
                    logger.warning(
                        f"[ToolHealthManager] ⚠️ 工具已降级：{tool_name} "
                        f"(连续失败 {record.consecutive_failures} 次, 错误: {error_message})"
                    )

    async def run_health_check(self, tool_name: Optional[str] = None) -> Dict[str, ToolHealthRecord]:
        """
        运行健康检查

        Args:
            tool_name: 可选，指定要检查的工具。None 表示检查所有

        Returns:
            检查结果字典
        """
        results = {}

        tools_to_check = [tool_name] if tool_name else list(self._health_records.keys())

        for name in tools_to_check:
            if name not in self._health_records:
                continue

            record = self._health_records[name]
            check_func = self._health_checks.get(name)

            try:
                if check_func:
                    is_healthy, message = await self._execute_check(check_func)

                    if is_healthy:
                        await self.report_execution_result(name, True)
                    else:
                        await self.report_execution_result(name, False, message)

                results[name] = record

            except Exception as e:
                logger.error(f"[ToolHealthManager] 健康检查异常：{name}, 错误：{e}")
                await self.report_execution_result(name, False, str(e))
                results[name] = record

        return results

    async def _execute_check(self, check_func: Callable) -> tuple:
        """执行健康检查函数"""
        result = check_func()

        if asyncio.iscoroutine(result):
            result = await result

        if isinstance(result, tuple) and len(result) >= 2:
            return result[0], result[1]
        elif isinstance(result, bool):
            return result, "" if result else "健康检查返回 False"
        else:
            return bool(result), ""

    def is_tool_available(self, tool_name: str) -> bool:
        """
        检查工具是否可用（未降级）

        Args:
            tool_name: 工具名称

        Returns:
            是否可用
        """
        if tool_name in self._degraded_tools:
            return False

        record = self._health_records.get(tool_name)
        if not record:
            return True  # 未注册的工具默认可用

        if record.status == ToolHealthStatus.DISABLED:
            return False

        return True

    def get_degraded_tools(self) -> Set[str]:
        """获取当前被降级的工具集合"""
        return self._degraded_tools.copy()

    def get_available_tools(self, all_tools: List[str]) -> List[str]:
        """
        过滤出可用的工具列表

        Args:
            all_tools: 所有工具名称列表

        Returns:
            过滤后的可用工具列表
        """
        return [t for t in all_tools if self.is_tool_available(t)]

    def get_tool_status(self, tool_name: str) -> Optional[ToolHealthStatus]:
        """获取工具状态"""
        record = self._health_records.get(tool_name)
        return record.status if record else None

    def get_health_report(self) -> Dict[str, Any]:
        """
        生成健康报告

        Returns:
            包含统计信息的字典
        """
        total = len(self._health_records)
        healthy = sum(1 for r in self._health_records.values() if r.status == ToolHealthStatus.HEALTHY)
        degraded = len(self._degraded_tools)
        unhealthy = sum(1 for r in self._health_records.values() if r.status == ToolHealthStatus.UNHEALTHY)
        disabled = sum(1 for r in self._health_records.values() if r.status == ToolHealthStatus.DISABLED)
        unknown = total - healthy - degraded - unhealthy - disabled

        records_detail = {name: record.to_dict() for name, record in self._health_records.items()}

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tools": total,
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
                "disabled": disabled,
                "unknown": unknown,
                "availability_rate": (healthy / total * 100) if total > 0 else 100,
            },
            "degraded_tools": list(self._degraded_tools),
            "records": records_detail,
            "config": {
                "max_consecutive_failures": self._config.max_consecutive_failures,
                "auto_recovery_enabled": self._config.auto_recovery_interval > 0,
                "degradation_enabled": self._config.enable_degradation,
            },
        }

    async def start_monitoring(self):
        """启动后台监控任务"""
        if self._is_running:
            logger.warning("[ToolHealthManager] 监控已在运行中")
            return

        if self._config.check_interval_seconds <= 0:
            logger.info("[ToolHealthManager] 健康检查间隔配置为 0，跳过后台监控")
            return

        self._is_running = True
        self._background_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"[ToolHealthManager] 后台监控已启动 (间隔: {self._config.check_interval_seconds}s)")

    async def stop_monitoring(self):
        """停止后台监控任务"""
        self._is_running = False

        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        self._background_task = None
        logger.info("[ToolHealthManager] 后台监控已停止")

    async def _monitoring_loop(self):
        """后台监控循环"""
        while self._is_running:
            try:
                await asyncio.sleep(self._config.check_interval_seconds)

                if not self._is_running:
                    break

                await self._try_recovery()

                results = await self.run_health_check()

                if results:
                    degraded_now = [
                        name
                        for name, rec in results.items()
                        if rec.status in [ToolHealthStatus.UNHEALTHY, ToolHealthStatus.DEGRADED]
                    ]
                    if degraded_now:
                        logger.debug(f"[ToolHealthMonitor] 发现 {len(degraded_now)} 个不健康工具")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[ToolHealthMonitor] 监控循环出错：{e}", exc_info=True)
                await asyncio.sleep(60)

    async def _try_recovery(self):
        """尝试恢复已降级的工具"""
        if not self._degraded_tools or self._config.auto_recovery_interval <= 0:
            return

        current_time = time.time()
        tools_to_recover = []

        for tool_name in list(self._degraded_tools):
            record = self._health_records.get(tool_name)
            if not record:
                continue

            time_since_failure = current_time - (record.last_failure_time or 0)

            if time_since_failure >= self._config.auto_recovery_interval:
                tools_to_recover.append(tool_name)

        for tool_name in tools_to_recover:
            record = self._health_records.get(tool_name)
            if record:
                record.recovery_attempt += 1
                record.consecutive_failures = max(0, record.consecutive_failures - 1)

                if record.consecutive_failures < self._config.max_consecutive_failures:
                    self._degraded_tools.discard(tool_name)
                    record.status = ToolHealthStatus.DEGRADED
                    logger.info(
                        f"[ToolHealthManager] 🔄 尝试恢复工具：{tool_name} " f"(第 {record.recovery_attempt} 次尝试)"
                    )

    async def force_recover(self, tool_name: str) -> bool:
        """
        强制恢复一个被降级的工具

        Args:
            tool_name: 工具名称

        Returns:
            是否成功恢复
        """
        if tool_name not in self._degraded_tools:
            return False

        record = self._health_records.get(tool_name)
        if record:
            record.consecutive_failures = 0
            record.status = ToolHealthStatus.HEALTHY
            record.error_message = None
            self._degraded_tools.discard(tool_name)

            logger.info(f"[ToolHealthManager] ✅ 强制恢复工具：{tool_name}")
            return True

        return False


_tool_health_manager: Optional[ToolHealthManager] = None


def get_tool_health_manager() -> ToolHealthManager:
    """获取 ToolHealthManager 单例"""
    global _tool_health_manager
    if _tool_health_manager is None:
        _tool_health_manager = ToolHealthManager()
    return _tool_health_manager
