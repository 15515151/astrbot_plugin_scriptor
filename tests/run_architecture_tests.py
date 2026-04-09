# tests/run_architecture_tests.py
"""
架构增强组件独立测试运行器

由于项目结构复杂，此脚本提供独立的测试环境，
避免 pytest 模块收集时的相对导入问题。
"""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, Mock


def setup_test_environment():
    """设置测试环境"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    plugin_dir = os.path.dirname(script_dir)
    core_dir = os.path.join(plugin_dir, "core")

    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)

    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)


def test_slash_command_router():
    """测试斜杠命令路由器"""
    print("\n" + "=" * 60)
    print("🧪 测试: 斜杠命令路由器 (SlashCommandRouter)")
    print("=" * 60)

    setup_test_environment()

    import importlib.util

    def load_module_from_file(module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    core_dir = os.path.join(base_dir, "core")

    slash_cmd_router = load_module_from_file(
        "core.slash_command_router", os.path.join(core_dir, "slash_command_router.py")
    )

    SlashCommandRouter = slash_cmd_router.SlashCommandRouter
    CommandMetadata = slash_cmd_router.CommandMetadata
    CommandPermission = slash_cmd_router.CommandPermission
    get_slash_command_router = slash_cmd_router.get_slash_command_router

    router = get_slash_command_router()
    router._commands.clear()
    router._alias_map.clear()
    router._category_map.clear()

    # 测试 1: 注册和路由命令
    print("\n✅ 测试 1: 注册和路由命令")

    async def mock_handler(event, **kwargs):
        return "Hello from command"

    cmd = CommandMetadata(name="test_cmd", description="Test command", handler=mock_handler, category="general")

    assert router.register(cmd) is True
    assert "test_cmd" in router.get_command_list()
    print("   ✓ 命令注册成功")

    is_command, result = asyncio.run(router.route("/test_cmd"))
    assert is_command is True
    assert result == "Hello from command"
    print("   ✓ 命令路由成功")

    # 测试 2: 非命令输入
    print("\n✅ 测试 2: 非命令输入处理")
    is_command, result = asyncio.run(router.route("hello world"))
    assert is_command is False
    assert result is None
    print("   ✓ 非命令输入正确识别")

    # 测试 3: 命令别名
    print("\n✅ 测试 3: 命令别名支持")

    async def alias_handler(event, **kwargs):
        return "alias works"

    cmd_with_alias = CommandMetadata(
        name="help", description="Help command", handler=alias_handler, aliases=["h", "?"], category="general"
    )

    router.register(cmd_with_alias)

    _, result = asyncio.run(router.route("/help"))
    assert result == "alias works"
    _, result = asyncio.run(router.route("/h"))
    assert result == "alias works"
    _, result = asyncio.run(router.route("/?"))
    assert result == "alias works"
    print("   ✓ 别名路由正常工作")

    # 测试 4: 禁用命令
    print("\n✅ 测试 4: 禁用命令")
    disabled_cmd = CommandMetadata(
        name="secret", description="Secret command", handler=lambda e: "should not execute", enabled=False
    )

    router.register(disabled_cmd)
    is_command, result = asyncio.run(router.route("/secret"))
    assert is_command is True
    assert "未找到" in result or "已禁用" in result
    print("   ✓ 禁用命令正确拦截")

    # 测试 5: 帮助信息生成
    print("\n✅ 测试 5: 帮助信息生成")
    help_text = router.get_help()
    assert "命令指南" in help_text
    print(f"   ✓ 帮助信息生成成功 ({len(help_text)} 字符)")

    # 测试 6: 统计信息
    print("\n✅ 测试 6: 统计信息")
    stats = router.get_stats()
    assert stats["total_commands"] > 0
    assert stats["enabled_commands"] > 0
    print(f"   ✓ 统计信息: {stats['total_commands']} 个命令")

    print("\n🎉 斜杠命令路由器所有测试通过！\n")


def test_tool_health_manager():
    """测试工具健康管理系统"""
    print("\n" + "=" * 60)
    print("🏥 测试: 工具健康管理系统 (ToolHealthManager)")
    print("=" * 60)

    setup_test_environment()

    import importlib.util

    def load_module_from_file(module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    core_dir = os.path.join(base_dir, "core")

    health_mgr = load_module_from_file("core.tool_health_manager", os.path.join(core_dir, "tool_health_manager.py"))

    ToolHealthManager = health_mgr.ToolHealthManager
    ToolHealthStatus = health_mgr.ToolHealthStatus
    ToolHealthConfig = health_mgr.ToolHealthConfig
    get_tool_health_manager = health_mgr.get_tool_health_manager

    manager = get_tool_health_manager()
    manager._health_records.clear()
    manager._health_checks.clear()
    manager._degraded_tools.clear()

    # 测试 1: 工具注册
    print("\n✅ 测试 1: 工具注册")
    assert manager.register_tool("test_tool") is True
    assert "test_tool" in manager._health_records
    record = manager._health_records["test_tool"]
    assert record.tool_name == "test_tool"
    print("   ✓ 工具注册成功")

    # 测试 2: 工具可用性检查
    print("\n✅ 测试 2: 工具可用性检查")
    manager.register_tool("healthy_tool", initial_status=ToolHealthStatus.HEALTHY)
    manager.register_tool("degraded_tool", initial_status=ToolHealthStatus.UNHEALTHY)
    manager._degraded_tools.add("degraded_tool")

    assert manager.is_tool_available("healthy_tool") is True
    assert manager.is_tool_available("degraded_tool") is False
    assert manager.is_tool_available("unknown_tool") is True
    print("   ✓ 可用性检查正常")

    # 测试 3: 报告执行结果（成功）
    print("\n✅ 测试 3: 报告成功执行结果")
    manager.register_tool("tool_a")
    asyncio.run(manager.report_execution_result("tool_a", success=True))

    record = manager._health_records["tool_a"]
    assert record.success_count == 1
    assert record.failure_count == 0
    assert record.consecutive_failures == 0
    assert record.status == ToolHealthStatus.HEALTHY
    print("   ✓ 成功报告记录正确")

    # 测试 4: 报告执行结果（失败并触发降级）
    print("\n✅ 测试 4: 失败触发降级")
    config = ToolHealthConfig(max_consecutive_failures=3)
    manager.configure(config)
    manager.register_tool("tool_b", initial_status=ToolHealthStatus.HEALTHY)

    for i in range(3):
        asyncio.run(manager.report_execution_result("tool_b", success=False, error_message=f"Error {i}"))

    record = manager._health_records["tool_b"]
    assert record.failure_count == 3
    assert record.consecutive_failures == 3
    assert record.status == ToolHealthStatus.UNHEALTHY
    assert "tool_b" in manager._degraded_tools
    print("   ✓ 降级机制正常工作")

    # 测试 5: 过滤可用工具
    print("\n✅ 测试 5: 过滤可用工具列表")
    all_tools = ["tool_1", "tool_2", "tool_3", "tool_4"]
    for tool in all_tools:
        manager.register_tool(tool)
    manager._degraded_tools.update(["tool_2", "tool_4"])

    available = manager.get_available_tools(all_tools)
    assert "tool_1" in available
    assert "tool_3" in available
    assert "tool_2" not in available
    assert len(available) == 2
    print(f"   ✓ 过滤后剩余 {len(available)} 个可用工具")

    # 测试 6: 健康报告
    print("\n✅ 测试 6: 健康报告生成")
    manager.register_tool("tool_x", initial_status=ToolHealthStatus.HEALTHY)
    manager.register_tool("tool_y", initial_status=ToolHealthStatus.UNHEALTHY)
    manager._degraded_tools.add("tool_y")

    report = manager.get_health_report()
    assert "summary" in report
    assert report["summary"]["total_tools"] >= 2
    assert "tool_y" in report["degraded_tools"]
    print(f"   ✓ 报告生成成功: {report['summary']['total_tools']} 个工具")

    # 测试 7: 强制恢复
    print("\n✅ 测试 7: 强制恢复降级工具")
    manager.register_tool("tool_z")
    manager._degraded_tools.add("tool_z")
    record = manager._health_records["tool_z"]
    record.status = ToolHealthStatus.UNHEALTHY
    record.consecutive_failures = 5

    result = asyncio.run(manager.force_recover("tool_z"))
    assert result is True
    assert "tool_z" not in manager._degraded_tools
    assert record.status == ToolHealthStatus.HEALTHY
    print("   ✓ 强制恢复功能正常")

    print("\n🎉 工具健康管理系统所有测试通过！\n")


def test_permission_engine():
    """测试权限规则引擎"""
    print("\n" + "=" * 60)
    print("🛡️ 测试: 权限规则引擎 (ToolPermissionEngine)")
    print("=" * 60)

    setup_test_environment()

    import importlib.util

    def load_module_from_file(module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    core_dir = os.path.join(base_dir, "core")

    perm_engine = load_module_from_file(
        "core.tool_permission_engine", os.path.join(core_dir, "tool_permission_engine.py")
    )

    ToolPermissionEngine = perm_engine.ToolPermissionEngine
    PermissionRule = perm_engine.PermissionRule
    PermissionAction = perm_engine.PermissionAction
    PermissionCheckResult = perm_engine.PermissionCheckResult
    ToolCallContext = perm_engine.ToolCallContext
    get_tool_permission_engine = perm_engine.get_tool_permission_engine

    engine = get_tool_permission_engine()
    engine._rules.clear()
    engine._audit_log.clear()

    # 测试 1: 规则添加
    print("\n✅ 测试 1: 规则添加")
    rule = PermissionRule(
        rule_id="rule_1",
        tool_pattern="file_*",
        action=PermissionAction.ASK,
        description="File operations need confirmation",
    )

    assert engine.add_rule(rule) is True
    assert len(engine.get_all_rules()) >= 1
    print("   ✓ 规则添加成功")

    # 测试 2: 精确匹配
    print("\n✅ 测试 2: 精确匹配")
    rule_exact = PermissionRule(rule_id="exact_match", tool_pattern="web_search_tool", action=PermissionAction.DENY)
    engine.add_rule(rule_exact)

    rules = engine.get_rules_for_tool("web_search_tool")
    assert len(rules) >= 1
    assert any(r.action == PermissionAction.DENY for r in rules)
    print("   ✓ 精确匹配正常")

    # 测试 3: 通配符匹配
    print("\n✅ 测试 3: 通配符匹配")
    rule_wildcard = PermissionRule(rule_id="wildcard", tool_pattern="file_*", action=PermissionAction.ASK)
    engine.add_rule(rule_wildcard)

    assert rule_wildcard.matches("file_read_tool") is True
    assert rule_wildcard.matches("file_write_tool") is True
    assert rule_wildcard.matches("web_search_tool") is False
    print("   ✓ 通配符匹配正常")

    # 测试 4: 权限检查 - 允许
    print("\n✅ 测试 4: 权限检查 - 允许")
    rule_allow = PermissionRule(rule_id="allow_all", tool_pattern="*", action=PermissionAction.ALLOW)
    engine.add_rule(rule_allow)

    context = ToolCallContext(tool_name="safe_tool", uid="user_123", group_id="group_456", args={})

    result = asyncio.run(engine.check_permission(context))
    assert result.is_allowed is True
    assert result.action == PermissionAction.ALLOW
    print("   ✓ 允许检查通过")

    # 测试 5: 权限检查 - 拒绝
    print("\n✅ 测试 5: 权限检查 - 拒绝")
    rule_deny = PermissionRule(
        rule_id="deny_danger", tool_pattern="delete_*", action=PermissionAction.DENY, priority=100  # 高优先级
    )
    engine.add_rule(rule_deny)

    context_deny = ToolCallContext(tool_name="delete_everything", uid="user_123", group_id="group_456", args={})

    result = asyncio.run(engine.check_permission(context_deny))
    assert result.is_denied is True
    assert result.action == PermissionAction.DENY
    print("   ✓ 拒绝检查通过")

    # 测试 6: 审计日志
    print("\n✅ 测试 6: 审计日志记录")
    context_audit = ToolCallContext(tool_name="audited_tool", uid="user_789", group_id="group_000", args={})

    asyncio.run(engine.check_permission(context_audit))

    logs = engine.get_audit_log(tool_name="audited_tool")
    assert len(logs) >= 1
    assert logs[0]["tool_name"] == "audited_tool"
    assert logs[0]["uid"] == "user_789"
    print(f"   ✓ 审计日志记录成功 ({len(logs)} 条)")

    # 测试 7: 启用/禁用规则
    print("\n✅ 测试 7: 启用/禁用规则")
    rule_toggle = PermissionRule(
        rule_id="toggle_test_unique", tool_pattern="toggle_tool_unique_xyz", action=PermissionAction.DENY
    )
    engine.add_rule(rule_toggle)

    assert engine.disable_rule("toggle_test_unique") is True
    rules_for_tool = engine.get_rules_for_tool("toggle_tool_unique_xyz")
    toggle_matched = [r for r in rules_for_tool if r.rule_id == "toggle_test_unique"]
    assert len(toggle_matched) == 0

    assert engine.enable_rule("toggle_test_unique") is True
    rules_for_tool = engine.get_rules_for_tool("toggle_tool_unique_xyz")
    toggle_matched = [r for r in rules_for_tool if r.rule_id == "toggle_test_unique"]
    assert len(toggle_matched) >= 1
    print("   ✓ 启用/禁用功能正常")

    # 测试 8: 统计信息
    print("\n✅ 测试 8: 统计信息")
    for i in range(5):
        rule_stat = PermissionRule(
            rule_id=f"stat_{i}",
            tool_pattern=f"stat_{i}_*",
            action=PermissionAction.ALLOW if i % 2 == 0 else PermissionAction.DENY,
        )
        engine.add_rule(rule_stat)

    stats = engine.get_stats()
    assert stats["total_rules"] >= 5
    print(f"   ✓ 统计信息: {stats['total_rules']} 条规则")

    print("\n🎉 权限规则引擎所有测试通过！\n")


def test_integration_manager():
    """测试集成管理器"""
    print("\n" + "=" * 60)
    print("🔗 测试: 架构增强集成管理器 (ArchitectureEnhancementManager)")
    print("=" * 60)

    setup_test_environment()

    import importlib.util

    def load_module_from_file(module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    core_dir = os.path.join(base_dir, "core")

    arch_mgr = load_module_from_file(
        "core.architecture_enhancements", os.path.join(core_dir, "architecture_enhancements.py")
    )

    ArchitectureEnhancementManager = arch_mgr.ArchitectureEnhancementManager
    get_architecture_manager = arch_mgr.get_architecture_manager
    PermissionCheckResult = arch_mgr.PermissionCheckResult

    manager = get_architecture_manager()

    # 测试 1: 初始化
    print("\n✅ 测试 1: 初始化")
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

    asyncio.run(manager.initialize(plugin_instance=mock_plugin))

    assert manager.command_router is not None
    assert manager.health_manager is not None
    assert manager.permission_engine is not None
    print("   ✓ 初始化成功")

    # 测试 2: 命令注册
    print("\n✅ 测试 2: 增强命令注册")
    manager.register_enhanced_commands()

    stats = manager.command_router.get_stats()
    assert stats["total_commands"] > 0
    assert "sc_help" in manager.command_router.get_command_list()
    print(f"   ✓ 已注册 {stats['total_commands']} 个增强命令")

    # 测试 3: 综合状态
    print("\n✅ 测试 3: 综合状态报告")
    status = manager.get_comprehensive_status()

    assert "timestamp" in status
    assert "components" in status
    assert "command_router" in status["components"]
    assert "health_manager" in status["components"]
    assert "permission_engine" in status["components"]
    print("   ✓ 状态报告生成成功")

    # 测试 4: 工具过滤
    print("\n✅ 测试 4: 工具可用性过滤")
    all_tools = ["tool_a", "tool_b", "tool_c"]
    filtered = manager.filter_available_tools(all_tools)
    print(f"   ✓ 工具过滤正常 ({len(filtered)}/{len(all_tools)}) 可用")
    assert isinstance(filtered, list)  # 确保返回的是列表

    # 测试 5: 权限检查集成
    print("\n✅ 测试 5: 权限检查集成")
    perm_result = asyncio.run(
        manager.check_tool_permission(tool_name="safe_operation", uid="user_001", group_id="group_001", args={})
    )
    assert isinstance(perm_result, PermissionCheckResult)
    print("   ✓ 权限检查集成正常")

    print("\n🎉 集成管理器所有测试通过！\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("[TEST] Scriptor Architecture Enhancement - Full Test Suite")
    print("=" * 70)
    print(f"\n[TIME] Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        test_slash_command_router()
        test_tool_health_manager()
        test_permission_engine()
        test_integration_manager()

        print("\n" + "=" * 70)
        print("[SUCCESS] All tests passed! Architecture enhancements working correctly.")
        print("=" * 70)
        print(f"\n[TIME] End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return 0

    except Exception as e:
        print("\n" + "=" * 70)
        print("[FAILED] Tests failed!")
        print("=" * 70)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
