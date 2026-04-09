"""
Scriptor v2.0 综合增强 - 集成测试
测试核心组件的协同工作能力
"""

import asyncio
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent


@pytest.mark.asyncio
async def test_concurrency_guard():
    """测试并发控制器"""
    print("\n" + "=" * 60)
    print("⚡ 测试 2: ConcurrencyGuard")
    print("=" * 60)

    from core.concurrency_guard import ConcurrencyGuard, Priority, get_concurrency_guard

    guard = ConcurrencyGuard(max_concurrent=3)

    session1 = await guard.acquire("user_1_private", Priority.PRIVATE)
    session2 = await guard.acquire("user_2_private", Priority.PRIVATE)
    stats = guard.get_stats()

    assert session1 == True, "session1 应获取成功"
    assert session2 == True, "session2 应获取成功"
    assert stats["active"] == 2, f"活跃数应为 2，实际{stats['active']}"

    guard.release("user_1_private")
    guard.release("user_2_private")

    # 等待异步释放操作完成
    await asyncio.sleep(0.1)

    stats = guard.get_stats()
    assert stats["active"] == 0, f"释放后活跃数应为 0，实际{stats['active']}"

    print("  ✅ 基本获取/释放正常")

    global_guard = get_concurrency_guard()
    assert global_guard is not None, "全局实例应存在"
    print("  ✅ 全局单例模式正常")

    print("\n结果：通过 ✅")


@pytest.mark.asyncio
async def test_web_fetcher():
    """测试 WebFetcher"""
    print("\n" + "=" * 60)
    print("🌐 测试 3: WebFetcher")
    print("=" * 60)

    from tools.web_fetch_tool import TokenBucketLimiter, WebFetchConfig, WebFetcher

    config = WebFetchConfig()
    fetcher = WebFetcher(config)

    url_validation_tests = [
        ("http://example.com", True),
        ("https://example.com/path", True),
        ("http://localhost", False),
        ("http://127.0.0.1", False),
        ("ftp://example.com", False),
    ]

    passed = 0
    for url, should_pass in url_validation_tests:
        try:
            if should_pass:
                fetcher._validate_url(url)
                print(f"  ✅ {url} (允许)")
            else:
                try:
                    fetcher._validate_url(url)
                    print(f"  ❌ {url} (应被阻止但未阻止)")
                    continue
                except ValueError:
                    print(f"  ✅ {url} (已阻止)")
            passed += 1
        except Exception as e:
            print(f"  ❌ {url}: {e}")

    limiter = TokenBucketLimiter(10)
    for _ in range(5):
        result = await limiter.acquire()
        assert result == True, "应成功获取令牌"

    print("  ✅ 速率限制器正常 (5/10)")

    stats = fetcher.get_stats()
    assert "cache_size" in stats, "统计信息应包含 cache_size"
    print(f"  ✅ 统计信息正常：{stats}")

    print(f"\n结果：{passed}/{len(url_validation_tests)} 通过")
    assert passed == len(url_validation_tests), f"WebFetcher URL 验证测试失败：{passed}/{len(url_validation_tests)}"


@pytest.mark.asyncio
async def test_tool_search_engine():
    """测试工具搜索引擎"""
    print("\n" + "=" * 60)
    print("🔍 测试 4: ToolSearchEngine")
    print("=" * 60)

    from tools.tool_search import (
        ToolCategory,
        ToolIndexEntry,
        ToolSearchEngine,
        get_tool_search_engine,
    )

    engine = ToolSearchEngine()

    entry1 = ToolIndexEntry(
        name="file_read_tool",
        display_name="File Read",
        description="读取文件内容",
        parameters=[],
        tags={"文件", "读取", "read"},
        category=ToolCategory.FILE,
    )

    entry2 = ToolIndexEntry(
        name="memory_search",
        display_name="Memory Search",
        description="搜索记忆系统",
        parameters=[],
        tags={"记忆", "搜索", "search"},
        category=ToolCategory.MEMORY,
    )

    engine._index["file_read_tool"] = entry1
    engine._index["memory_search"] = entry2
    engine._built = True

    results = await engine.search("读取文件")
    assert len(results) > 0, "搜索'读取文件'应有结果"
    assert results[0].tool_name == "file_read_tool", "第一个结果应为 file_read_tool"
    print(f"  ✅ 搜索'读取文件': 找到 {len(results)} 个结果")

    results = await engine.search("搜索记忆")
    assert len(results) > 0, "搜索'搜索记忆'应有结果"
    print(f"  ✅ 搜索'搜索记忆': 找到 {len(results)} 个结果")

    results = await engine.search("不存在的功能 xyz")
    assert len(results) == 0, "搜索不存在功能应返回空"
    print("  ✅ 搜索不存在的功能：返回空结果")

    global_engine = get_tool_search_engine()
    assert global_engine is not None, "全局实例应存在"
    print("  ✅ 全局单例模式正常")

    stats = engine.get_stats()
    assert stats["total_tools"] == 2, f"工具数应为 2，实际{stats['total_tools']}"
    print(f"  ✅ 统计信息：{stats}")

    print("\n结果：通过 ✅")


def test_skill_system():
    """测试技能系统"""
    print("\n" + "=" * 60)
    print("🎯 测试 5: SkillTool 系统")
    print("=" * 60)

    from tools.skill_tool import (
        CooldownManager,
        ExecutionMode,
        SkillDefinition,
        SkillRegistry,
        SkillTaskStore,
    )

    registry = SkillRegistry()
    cooldown = CooldownManager(default_cooldown=30)
    store = SkillTaskStore()

    skill = SkillDefinition(
        name="test-skill",
        display_name="Test Skill",
        description="测试技能",
        full_prompt="你是测试技能",
        required_tools=["file_read_tool"],
        execution_mode=ExecutionMode.INLINE,
        cooldown_seconds=30,
    )

    registry._skills["test-skill"] = skill
    registry._triggers_index["测试"] = {"test-skill"}

    retrieved = registry.get_skill("test-skill")
    assert retrieved is not None, "应找到技能"
    assert retrieved.name == "test-skill", "技能名称应匹配"
    print("  ✅ 技能注册/获取正常")

    all_skills = registry.list_skills()
    assert len(all_skills) >= 1, f"至少有 1 个技能，实际{len(all_skills)}"
    print(f"  ✅ 列出技能：{len(all_skills)} 个")

    recommended = registry.recommend_skills("这是一个测试任务")
    print(f"  ✅ 技能推荐：推荐 {len(recommended)} 个")

    can_execute = cooldown.can_execute("test-skill", "session_1")
    assert can_execute == True, "首次执行应通过冷却检查"
    print("  ✅ 冷却检查：首次可通过")

    cooldown.record_execution("test-skill", "session_1")
    can_execute_again = cooldown.can_execute("test-skill", "session_1")
    assert can_execute_again == False, "刚执行过不应通过冷却检查"
    print("  ✅ 冷却机制：执行后正确阻止")

    remaining = cooldown.get_remaining_cooldown("test-skill", "session_1")
    assert remaining > 0, "剩余冷却时间应大于 0"
    print(f"  ✅ 剩余冷却时间：{remaining:.1f}s")

    print("\n结果：通过 ✅")


def test_recurrence_parser():
    """测试循环表达式解析器"""
    print("\n" + "=" * 60)
    print("🔄 测试 6: RecurrenceParser")
    print("=" * 60)

    from tools.recurrence_parser import RecurrenceParser, RecurrenceType

    parser = RecurrenceParser()

    test_cases = [
        ("every day", True, RecurrenceType.DAILY, "每天"),
        ("每天", True, RecurrenceType.DAILY, "每天"),
        ("every monday", True, RecurrenceType.WEEKLY, None),
        ("每周一", True, RecurrenceType.WEEKLY, None),
        ("every week", True, RecurrenceType.WEEKLY, "每周"),
        ("weekdays", True, RecurrenceType.WEEKLY, None),
        ("工作日", True, RecurrenceType.WEEKLY, None),
        ("weekends", True, RecurrenceType.WEEKLY, None),
        ("every 2 days", True, RecurrenceType.DAILY, "每 2 天"),
    ]

    passed = 0
    for expr, should_valid, expected_type, desc in test_cases:
        result = parser.parse(expr)

        if should_valid:
            if result.valid and result.recurrence_type == expected_type:
                print(f"  ✅ '{expr}' → {result.description}")
                passed += 1
            else:
                print(f"  ❌ '{expr}': 预期 valid={should_valid}, type={expected_type}")
                print(f"      实际 valid={result.valid}, type={result.recurrence_type}, error={result.error}")
        else:
            if not result.valid:
                print(f"  ✅ '{expr}' → 正确拒绝 ({result.error[:30]})")
                passed += 1
            else:
                print(f"  ❌ '{expr}': 预期无效，但解析为 {result.description}")

    next_trigger = parser.calculate_next_trigger(parser.parse("every day"))
    assert next_trigger is not None, "应计算出下次触发时间"
    print(f"  ✅ 下次触发时间计算：{next_trigger.strftime('%Y-%m-%d %H:%M')}")
    passed += 1

    total = len(test_cases) + 1
    print(f"\n结果：{passed}/{total} 通过")
    assert passed == total, f"RecurrenceParser 测试失败：{passed}/{total}"


def test_config_completeness():
    """测试配置项完整性"""
    print("\n" + "=" * 60)
    print("⚙️  测试 7: 配置项完整性")
    print("=" * 60)

    from core.config_pydantic import ScriptorConfigPydantic

    config = ScriptorConfigPydantic(
        **{
            "admin_uids": [],
            "data_dir": "/tmp/test",
        }
    )

    required_attrs = [
        "concurrency_control_enabled",
        "max_concurrent_llm",
        "session_timeout_seconds",
        "max_pending_per_session",
        "session_locks_enabled",
        "max_file_locks",
    ]

    passed = 0
    for attr in required_attrs:
        assert hasattr(config, attr), f"缺少配置项：{attr}"
        value = getattr(config, attr)
        print(f"  ✅ {attr} = {value}")
        passed += 1

    assert config.max_concurrent_llm == 5, f"默认值应为 5，实际{config.max_concurrent_llm}"
    print(f"  ✅ 默认值验证：max_concurrent_llm={config.max_concurrent_llm}")

    print(f"\n结果：{passed}/{len(required_attrs)} 通过")
    assert passed == len(required_attrs), f"配置项测试失败：{passed}/{len(required_attrs)}"
