# tests/test_architecture_enhancements.py
"""
架构增强组件测试

验证以下功能：
- 斜杠命令路由器
- 工具健康管理系统
- 权限规则引擎
- 集成管理器
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.architecture_enhancements import get_architecture_manager
from core.slash_command_router import CommandMetadata, get_slash_command_router
from core.tool_health_manager import (
    ToolHealthConfig,
    ToolHealthStatus,
    get_tool_health_manager,
)
from core.tool_permission_engine import (
    PermissionAction,
    PermissionRule,
    ToolCallContext,
    get_tool_permission_engine,
)


class TestSlashCommandRouter:
    """斜杠命令路由器测试"""

    @pytest.fixture
    def router(self):
        """每个测试前重置路由器"""
        router = get_slash_command_router()
        router._commands.clear()
        router._alias_map.clear()
        router._category_map.clear()
        router._rate_limit_cache.clear()
        yield router

    @pytest.mark.asyncio
    async def test_register_and_route_command(self, router):
        """测试命令注册和路由"""

        async def mock_handler(event, **kwargs):
            return "Hello from command"

        cmd = CommandMetadata(name="test_cmd", description="Test command", handler=mock_handler, category="general")

        assert router.register(cmd) is True
        assert "test_cmd" in router.get_command_list()

        is_command, result = await router.route("/test_cmd")
        assert is_command is True
        assert result == "Hello from command"

    @pytest.mark.asyncio
    async def test_non_command_input(self, router):
        """测试非命令输入"""
        is_command, result = await router.route("hello world")
        assert is_command is False
        assert result is None

        is_command, result = await router.route("")
        assert is_command is False

    @pytest.mark.asyncio
    async def test_command_with_alias(self, router):
        """测试命令别名"""

        async def handler(event, **kwargs):
            return "alias works"

        cmd = CommandMetadata(
            name="help", description="Help command", handler=handler, aliases=["h", "?"], category="general"
        )

        router.register(cmd)

        _, result = await router.route("/help")
        assert result == "alias works"

        _, result = await router.route("/h")
        assert result == "alias works"

        _, result = await router.route("/?")
        assert result == "alias works"

    @pytest.mark.asyncio
    async def test_disabled_command(self, router):
        """测试禁用命令"""

        async def handler(event, **kwargs):
            return "should not execute"

        cmd = CommandMetadata(name="secret", description="Secret command", handler=handler, enabled=False)

        router.register(cmd)

        is_command, result = await router.route("/secret")
        assert is_command is True
        assert "未找到" in result or "已禁用" in result

    def test_get_help(self, router):
        """测试帮助信息生成"""
        cmd1 = CommandMetadata(name="cmd1", description="First command", handler=lambda e: None, category="identity")

        cmd2 = CommandMetadata(name="cmd2", description="Second command", handler=lambda e: None, category="memory")

        router.register(cmd1)
        router.register(cmd2)

        help_text = router.get_help()
        assert "命令指南" in help_text
        assert "cmd1" in help_text or "cmd2" in help_text

    def test_stats(self, router):
        """测试统计信息"""
        for i in range(3):
            cmd = CommandMetadata(name=f"cmd_{i}", description=f"Command {i}", handler=lambda e: None)
            router.register(cmd)

        stats = router.get_stats()
        assert stats["total_commands"] == 3
        assert stats["enabled_commands"] == 3


class TestToolHealthManager:
    """工具健康管理系统测试"""

    @pytest.fixture
    def manager(self):
        """每个测试前重置管理器"""
        manager = get_tool_health_manager()
        manager._health_records.clear()
        manager._health_checks.clear()
        manager._degraded_tools.clear()
        yield manager

    def test_register_tool(self, manager):
        """测试工具注册"""
        assert manager.register_tool("test_tool") is True
        assert "test_tool" in manager._health_records

        record = manager._health_records["test_tool"]
        assert record.tool_name == "test_tool"

    def test_tool_availability(self, manager):
        """测试工具可用性检查"""
        manager.register_tool("healthy_tool", initial_status=ToolHealthStatus.HEALTHY)
        manager.register_tool("degraded_tool", initial_status=ToolHealthStatus.UNHEALTHY)

        # 手动添加到降级集合
        manager._degraded_tools.add("degraded_tool")

        assert manager.is_tool_available("healthy_tool") is True
        assert manager.is_tool_available("degraded_tool") is False
        assert manager.is_tool_available("unknown_tool") is True  # 未注册的默认可用

    @pytest.mark.asyncio
    async def test_report_execution_result_success(self, manager):
        """测试报告成功执行结果"""
        manager.register_tool("tool_a")

        await manager.report_execution_result("tool_a", success=True)

        record = manager._health_records["tool_a"]
        assert record.success_count == 1
        assert record.failure_count == 0
        assert record.consecutive_failures == 0
        assert record.status == ToolHealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_report_execution_result_failure(self, manager):
        """测试报告失败执行结果"""
        config = ToolHealthConfig(max_consecutive_failures=3)
        manager.configure(config)
        manager.register_tool("tool_b", initial_status=ToolHealthStatus.HEALTHY)

        # 模拟连续失败
        for i in range(3):
            await manager.report_execution_result("tool_b", success=False, error_message=f"Error {i}")

        record = manager._health_records["tool_b"]
        assert record.failure_count == 3
        assert record.consecutive_failures == 3
        assert record.status == ToolHealthStatus.UNHEALTHY
        assert "tool_b" in manager._degraded_tools

    @pytest.mark.asyncio
    async def test_auto_recovery_after_degradation(self, manager):
        """测试降级后的自动恢复"""
        config = ToolHealthConfig(max_consecutive_failures=2, auto_recovery_interval=0.1)  # 很短的间隔用于测试
        manager.configure(config)
        manager.register_tool("tool_c", initial_status=ToolHealthStatus.HEALTHY)

        # 触发降级
        await manager.report_execution_result("tool_c", success=False)
        await manager.report_execution_result("tool_c", success=False)

        assert "tool_c" in manager._degraded_tools

        # 等待恢复尝试
        await asyncio.sleep(0.15)

        # 尝试恢复（减少连续失败次数）
        await manager._try_recovery()

        if "tool_c" not in manager._degraded_tools:
            record = manager._health_records["tool_c"]
            assert record.status != ToolHealthStatus.UNHEALTHY

    def test_filter_available_tools(self, manager):
        """测试过滤可用工具"""
        all_tools = ["tool_1", "tool_2", "tool_3", "tool_4"]

        for tool in all_tools:
            manager.register_tool(tool)

        # 标记部分工具为降级
        manager._degraded_tools.update(["tool_2", "tool_4"])

        available = manager.get_available_tools(all_tools)
        assert "tool_1" in available
        assert "tool_3" in available
        assert "tool_2" not in available
        assert "tool_4" not in available
        assert len(available) == 2

    def test_health_report(self, manager):
        """测试健康报告生成"""
        manager.register_tool("tool_x", initial_status=ToolHealthStatus.HEALTHY)
        manager.register_tool("tool_y", initial_status=ToolHealthStatus.UNHEALTHY)
        manager._degraded_tools.add("tool_y")

        report = manager.get_health_report()

        assert "summary" in report
        assert report["summary"]["total_tools"] == 2
        assert report["summary"]["healthy"] >= 1
        assert "tool_y" in report["degraded_tools"]

    @pytest.mark.asyncio
    async def test_force_recover(self, manager):
        """测试强制恢复"""
        manager.register_tool("tool_z", initial_status=ToolHealthStatus.UNHEALTHY)
        manager._degraded_tools.add("tool_z")

        record = manager._health_records["tool_z"]
        record.consecutive_failures = 5

        assert await manager.force_recover("tool_z") is True
        assert "tool_z" not in manager._degraded_tools
        assert record.status == ToolHealthStatus.HEALTHY
        assert record.consecutive_failures == 0


class TestToolPermissionEngine:
    """工具权限规则引擎测试"""

    @pytest.fixture
    def engine(self):
        """每个测试前重置引擎"""
        engine = get_tool_permission_engine()
        engine._rules.clear()
        engine._audit_log.clear()
        yield engine

    def test_add_rule(self, engine):
        """测试添加规则"""
        rule = PermissionRule(
            rule_id="rule_1",
            tool_pattern="file_*",
            action=PermissionAction.ASK,
            description="File operations need confirmation",
        )

        assert engine.add_rule(rule) is True
        assert len(engine.get_all_rules()) == 1

    def test_rule_matching_exact(self, engine):
        """测试精确匹配"""
        rule = PermissionRule(rule_id="exact_match", tool_pattern="web_search_tool", action=PermissionAction.DENY)
        engine.add_rule(rule)

        rules = engine.get_rules_for_tool("web_search_tool")
        assert len(rules) == 1
        assert rules[0].action == PermissionAction.DENY

    def test_rule_matching_wildcard(self, engine):
        """测试通配符匹配"""
        rule = PermissionRule(rule_id="wildcard", tool_pattern="file_*", action=PermissionAction.ASK)
        engine.add_rule(rule)

        assert rule.matches("file_read_tool") is True
        assert rule.matches("file_write_tool") is True
        assert rule.matches("web_search_tool") is False

    def test_rule_priority(self, engine):
        """测试规则优先级"""
        low_priority = PermissionRule(rule_id="low", tool_pattern="*", action=PermissionAction.ALLOW, priority=1)
        high_priority = PermissionRule(
            rule_id="high", tool_pattern="dangerous_*", action=PermissionAction.DENY, priority=100
        )

        engine.add_rule(low_priority)
        engine.add_rule(high_priority)

        rules = engine.get_rules_for_tool("dangerous_delete")
        assert len(rules) > 0
        assert rules[0].priority > rules[-1].priority

    @pytest.mark.asyncio
    async def test_check_permission_allow(self, engine):
        """测试权限检查 - 允许"""
        rule = PermissionRule(rule_id="allow_all", tool_pattern="*", action=PermissionAction.ALLOW)
        engine.add_rule(rule)

        context = ToolCallContext(tool_name="safe_tool", uid="user_123", group_id="group_456", args={})

        result = await engine.check_permission(context)
        assert result.is_allowed is True
        assert result.action == PermissionAction.ALLOW

    @pytest.mark.asyncio
    async def test_check_permission_deny(self, engine):
        """测试权限检查 - 拒绝"""
        rule = PermissionRule(rule_id="deny_danger", tool_pattern="delete_*", action=PermissionAction.DENY)
        engine.add_rule(rule)

        context = ToolCallContext(tool_name="delete_everything", uid="user_123", group_id="group_456", args={})

        result = await engine.check_permission(context)
        assert result.is_denied is True
        assert result.action == PermissionAction.DENY

    @pytest.mark.asyncio
    async def test_audit_logging(self, engine):
        """测试审计日志记录"""
        rule = PermissionRule(rule_id="audit_test", tool_pattern="*", action=PermissionAction.ALLOW)
        engine.add_rule(rule)

        context = ToolCallContext(tool_name="audited_tool", uid="user_789", group_id="group_000", args={})

        await engine.check_permission(context)

        logs = engine.get_audit_log(tool_name="audited_tool")
        assert len(logs) >= 1
        assert logs[0]["tool_name"] == "audited_tool"
        assert logs[0]["uid"] == "user_789"

    def test_enable_disable_rule(self, engine):
        """测试启用/禁用规则"""
        rule = PermissionRule(rule_id="toggle", tool_pattern="toggle_tool", action=PermissionAction.DENY)
        engine.add_rule(rule)

        assert engine.disable_rule("toggle") is True
        rules_for_tool = engine.get_rules_for_tool("toggle_tool")
        assert len(rules_for_tool) == 0  # 被禁用的规则不应匹配

        assert engine.enable_rule("toggle") is True
        rules_for_tool = engine.get_rules_for_tool("toggle_tool")
        assert len(rules_for_tool) == 1

    def test_export_import_rules(self, engine):
        """测试规则导出/导入"""
        original_rules = [
            {"rule_id": "exp_1", "tool_pattern": "exp_*", "action": "allow", "priority": 10},
            {"rule_id": "exp_2", "tool_pattern": "imp_*", "action": "deny", "priority": 20},
        ]

        imported = engine.import_rules(original_rules)
        assert imported == 2

        exported = engine.export_rules()
        assert len(exported) >= 2

    def test_stats(self, engine):
        """测试统计信息"""
        for i in range(5):
            rule = PermissionRule(
                rule_id=f"stat_{i}",
                tool_pattern=f"stat_{i}_*",
                action=PermissionAction.ALLOW if i % 2 == 0 else PermissionAction.DENY,
            )
            engine.add_rule(rule)

        stats = engine.get_stats()
        assert stats["total_rules"] == 5
        assert stats["allow_rules"] == 3
        assert stats["deny_rules"] == 2


class TestArchitectureEnhancementManager:
    """集成管理器测试"""

    @pytest.fixture
    def manager(self):
        """每个测试前重置管理器"""
        manager = get_architecture_manager()
        yield manager

    @pytest.mark.asyncio
    async def test_initialization(self, manager):
        """测试初始化"""
        mock_plugin = Mock()
        mock_plugin.cmd_sc_help = AsyncMock(return_value=None)
        mock_plugin.cmd_sc_admin = AsyncMock(return_value=None)
        mock_plugin.cmd_whoami = AsyncMock(return_value=None)
        mock_plugin.cmd_status = AsyncMock(return_value=None)
        mock_plugin.cmd_kb_status = AsyncMock(return_value=None)
        mock_plugin.cmd_learning_status = AsyncMock(return_value=None)
        mock_plugin.cmd_search = AsyncMock(return_value=None)
        mock_plugin.cmd_buffer_status = AsyncMock(return_value=None)
        mock_plugin.cmd_lock_status = AsyncMock(return_value=None)
        mock_plugin.cmd_sc_concurrency = AsyncMock(return_value=None)
        mock_plugin.cmd_smart_split_status = AsyncMock(return_value=None)
        mock_plugin.cmd_webui = AsyncMock(return_value=None)

        await manager.initialize(plugin_instance=mock_plugin)

        assert manager.command_router is not None
        assert manager.health_manager is not None
        assert manager.permission_engine is not None

    @pytest.mark.asyncio
    async def test_register_commands(self, manager):
        """测试命令注册"""
        mock_plugin = Mock()
        mock_plugin.cmd_sc_help = AsyncMock(return_value=None)
        mock_plugin.cmd_sc_admin = AsyncMock(return_value=None)
        mock_plugin.cmd_whoami = AsyncMock(return_value=None)

        await manager.initialize(plugin_instance=mock_plugin)
        manager.register_enhanced_commands()

        stats = manager.command_router.get_stats()
        assert stats["total_commands"] > 0
        assert "sc_help" in manager.command_router.get_command_list()

    @pytest.mark.asyncio
    async def test_comprehensive_status(self, manager):
        """测试综合状态报告"""
        await manager.initialize()

        status = manager.get_comprehensive_status()

        assert "timestamp" in status
        assert "components" in status
        assert "command_router" in status["components"]
        assert "health_manager" in status["components"]
        assert "permission_engine" in status["components"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
