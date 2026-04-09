# core/architecture_enhancements.py
"""
Scriptor 架构增强集成模块

将以下高级特性无缝集成到现有 Scriptor 架构中：
- 斜杠命令路由器增强
- 工具降级模式
- 统一权限规则引擎

提供统一的初始化、配置和管理接口。
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from .slash_command_router import CommandMetadata, CommandPermission, SlashCommandRouter, get_slash_command_router
from .tool_health_manager import ToolHealthConfig, ToolHealthManager, ToolHealthStatus, get_tool_health_manager
from .tool_permission_engine import (
    PermissionAction,
    PermissionCheckResult,
    ToolCallContext,
    ToolPermissionEngine,
    get_tool_permission_engine,
)


class ArchitectureEnhancementManager:
    """
    架构增强管理器

    负责协调和初始化所有架构增强组件，
    提供统一的管理接口。
    """

    _instance: Optional["ArchitectureEnhancementManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.command_router: Optional[SlashCommandRouter] = None
        self.health_manager: Optional[ToolHealthManager] = None
        self.permission_engine: Optional[ToolPermissionEngine] = None

        self._plugin_instance = None
        self._initialized = True

        logger.info("[ArchitectureEnhancement] 管理器已初始化")

    async def initialize(self, plugin_instance=None):
        """
        初始化所有增强组件

        Args:
            plugin_instance: Scriptor 插件实例引用
        """
        self._plugin_instance = plugin_instance

        self.command_router = get_slash_command_router()
        self.health_manager = get_tool_health_manager()
        self.permission_engine = get_tool_permission_engine()

        await self._configure_health_manager()
        await self._register_builtin_tools_to_health_monitor()

        logger.info("[ArchitectureEnhancement] 所有增强组件已初始化")

    async def _configure_health_manager(self):
        """配置工具健康检查参数"""
        config = ToolHealthConfig(
            max_consecutive_failures=3,
            check_interval_seconds=300.0,
            auto_recovery_interval=600.0,
            enable_degradation=True,
            log_health_changes=True,
        )

        self.health_manager.configure(config)

    async def _register_builtin_tools_to_health_monitor(self):
        """注册内置工具到健康监控系统"""
        builtin_tools = [
            "web_search_tool",
            "web_fetch_tool",
            "memory_search",
            "file_read_tool",
            "file_write_tool",
            "file_edit_tool",
            "skill_call_tool",
            "query_archives",
            "usage_docs_search",
        ]

        for tool_name in builtin_tools:
            self.health_manager.register_tool(tool_name, initial_status=ToolHealthStatus.UNKNOWN)

        logger.info(f"[ArchitectureEnhancement] 已注册 {len(builtin_tools)} 个内置工具到健康监控")

    async def start_background_services(self):
        """启动后台服务"""
        if self.health_manager:
            await self.health_manager.start_monitoring()
            logger.info("[ArchitectureEnhancement] 后台服务已启动")

    async def stop_background_services(self):
        """停止后台服务"""
        if self.health_manager:
            await self.health_manager.stop_monitoring()
            logger.info("[ArchitectureEnhancement] 后台服务已停止")

    def register_enhanced_commands(self):
        """
        注册增强的斜杠命令

        将现有的 CommandsMixin 命令注册到新的路由系统中，
        添加别名、权限控制和帮助信息。
        """
        if not self._plugin_instance:
            logger.warning("[ArchitectureEnhancement] 无法注册命令：插件实例未设置")
            return

        enhanced_commands = [
            CommandMetadata(
                name="sc_help",
                description="查看 Scriptor 帮助信息",
                handler=self._plugin_instance.cmd_sc_help,
                permission=CommandPermission.PUBLIC,
                aliases=["help", "h"],
                category="general",
                examples=["/sc_help", "/help"],
            ),
            CommandMetadata(
                name="sc_admin",
                description="查看管理员工具（需管理员权限）",
                handler=self._plugin_instance.cmd_sc_admin,
                permission=CommandPermission.ADMIN,
                category="admin",
                examples=["/sc_admin"],
            ),
            CommandMetadata(
                name="whoami",
                description="查看当前身份信息",
                handler=self._plugin_instance.cmd_whoami,
                permission=CommandPermission.USER,
                aliases=["identity", "me"],
                category="identity",
                examples=["/whoami"],
            ),
            CommandMetadata(
                name="mem_status",
                description="查看记忆系统状态",
                handler=self._plugin_instance.cmd_status,
                permission=CommandPermission.USER,
                aliases=["memory_status", "ms"],
                category="memory",
                examples=["/mem_status"],
            ),
            CommandMetadata(
                name="kb_status",
                description="查看知识库状态",
                handler=self._plugin_instance.cmd_kb_status,
                permission=CommandPermission.USER,
                category="knowledge",
                examples=["/kb_status"],
            ),
            CommandMetadata(
                name="learning_status",
                description="查看学习模式状态",
                handler=self._plugin_instance.cmd_learning_status,
                permission=CommandPermission.MEMBER,
                category="learning",
                examples=["/学习状态"],
            ),
            CommandMetadata(
                name="search",
                description="搜索长期记忆",
                handler=self._plugin_instance.cmd_search,
                permission=CommandPermission.USER,
                category="memory",
                examples=["/search Python教程"],
            ),
            CommandMetadata(
                name="buffer_status",
                description="查看消息缓冲器状态",
                handler=self._plugin_instance.cmd_buffer_status,
                permission=CommandPermission.ADMIN,
                category="system",
                examples=["/buffer_status"],
            ),
            CommandMetadata(
                name="lock_status",
                description="查看会话锁状态",
                handler=self._plugin_instance.cmd_lock_status,
                permission=CommandPermission.ADMIN,
                category="system",
                examples=["/lock_status"],
            ),
            CommandMetadata(
                name="sc_concurrency",
                description="查看并发控制状态",
                handler=self._plugin_instance.cmd_sc_concurrency,
                permission=CommandPermission.ADMIN,
                category="system",
                examples=["/sc_concurrency"],
            ),
            CommandMetadata(
                name="smart_split_status",
                description="查看智能分段发送器状态",
                handler=self._plugin_instance.cmd_smart_split_status,
                permission=CommandPermission.ADMIN,
                category="system",
                examples=["/smart_split_status"],
            ),
            CommandMetadata(
                name="webui",
                description="启动 Web 管理界面",
                handler=self._plugin_instance.cmd_webui,
                permission=CommandPermission.ADMIN,
                category="admin",
                examples=["/webui"],
            ),
            CommandMetadata(
                name="arch_health",
                description="查看架构增强状态（新增）",
                handler=self._cmd_arch_health,
                permission=CommandPermission.SUPER_ADMIN,
                category="admin",
                examples=["/arch_health"],
            ),
        ]

        registered_count = 0
        for cmd_meta in enhanced_commands:
            if self.command_router.register(cmd_meta):
                registered_count += 1

        logger.info(f"[ArchitectureEnhancement] 已注册 {registered_count} 个增强命令")

    async def _cmd_arch_health(self, event, **kwargs):
        """查看架构增强状态命令"""
        health_report = self.health_manager.get_health_report() if self.health_manager else {}
        perm_stats = self.permission_engine.get_stats() if self.permission_engine else {}
        router_stats = self.command_router.get_stats() if self.command_router else {}

        lines = [
            "## 🔧 架构增强状态\n",
            "### 📊 斜杠命令路由器",
            f"- 总命令数：{router_stats.get('total_commands', 0)}",
            f"- 启用命令：{router_stats.get('enabled_commands', 0)}",
            f"- 分类数：{router_stats.get('categories', 0)}\n",
            "### 🏥 工具健康监控",
        ]

        if health_report and "summary" in health_report:
            summary = health_report["summary"]
            lines.extend(
                [
                    f"- 总工具数：{summary.get('total_tools', 0)}",
                    f"- 健康：{summary.get('healthy', 0)} ✅",
                    f"- 降级：{summary.get('degraded', 0)} ⚠️",
                    f"- 不健康：{summary.get('unhealthy', 0)} ❌",
                    f"- 可用率：{summary.get('availability_rate', 100):.1f}%",
                ]
            )

            degraded = health_report.get("degraded_tools", [])
            if degraded:
                lines.append(f"\n**降级中的工具**：{', '.join(degraded)}")

        lines.extend(
            [
                "\n### 🛡️ 权限规则引擎",
                f"- 总规则数：{perm_stats.get('total_rules', 0)}",
                f"- 允许规则：{perm_stats.get('allow_rules', 0)} ✅",
                f"- 拒绝规则：{perm_stats.get('deny_rules', 0)} ❌",
                f"- 询问规则：{perm_stats.get('ask_rules', 0)} ❓",
                f"- 最近拒绝次数（100条内）：{perm_stats.get('recent_denials_100', 0)}",
            ]
        )

        event.plain_result("\n".join(lines))

    async def route_command(
        self, input_text: str, event=None, context=None, permission_checker: Optional[Callable] = None
    ) -> tuple:
        """
        路由命令（统一入口）

        Args:
            input_text: 用户输入
            event: 事件对象
            context: 额外上下文
            permission_checker: 权限检查函数

        Returns:
            (是否是命令, 结果)
        """
        if not self.command_router:
            return False, None

        return await self.command_router.route(input_text, event, context, permission_checker)

    async def check_tool_permission(
        self,
        tool_name: str,
        uid: str,
        group_id: str,
        args: Dict[str, Any],
        event=None,
        is_admin: bool = False,
        is_sudo: bool = False,
    ) -> PermissionCheckResult:
        """
        检查工具权限（统一入口）

        Args:
            tool_name: 工具名称
            uid: 用户 ID
            group_id: 群组 ID
            args: 工具参数
            event: 事件对象
            is_admin: 是否管理员
            is_sudo: 是否 sudo 模式

        Returns:
            权限检查结果
        """
        if not self.permission_engine:
            return PermissionCheckResult(action=PermissionAction.ALLOW)

        context = ToolCallContext(
            tool_name=tool_name,
            uid=uid,
            group_id=group_id,
            args=args,
            event=event,
            is_admin=is_admin,
            is_sudo=is_sudo,
            session_id=f"{uid}_{group_id}",
        )

        return await self.permission_engine.check_permission(context)

    def report_tool_execution(self, tool_name: str, success: bool, error_message: Optional[str] = None):
        """
        报告工具执行结果（用于健康监控）

        Args:
            tool_name: 工具名称
            success: 是否成功
            error_message: 错误信息
        """
        if self.health_manager:
            asyncio.create_task(self.health_manager.report_execution_result(tool_name, success, error_message))

    def is_tool_available(self, tool_name: str) -> bool:
        """检查工具是否可用"""
        if self.health_manager:
            return self.health_manager.is_tool_available(tool_name)
        return True

    def filter_available_tools(self, tool_list: List[str]) -> List[str]:
        """过滤出可用工具列表"""
        if self.health_manager:
            return self.health_manager.get_available_tools(tool_list)
        return tool_list

    def get_enhanced_help(self, user_permission: CommandPermission = CommandPermission.PUBLIC) -> str:
        """获取增强的帮助信息"""
        if self.command_router:
            return self.command_router.get_help(user_permission=user_permission)
        return ""

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """获取综合状态报告"""
        status = {
            "timestamp": time.time(),
            "components": {
                "command_router": self.command_router.get_stats() if self.command_router else {},
                "health_manager": self.health_manager.get_health_report() if self.health_manager else {},
                "permission_engine": self.permission_engine.get_stats() if self.permission_engine else {},
            },
        }

        return status


_architecture_manager: Optional[ArchitectureEnhancementManager] = None


def get_architecture_manager() -> ArchitectureEnhancementManager:
    """获取架构增强管理器单例"""
    global _architecture_manager
    if _architecture_manager is None:
        _architecture_manager = ArchitectureEnhancementManager()
    return _architecture_manager
