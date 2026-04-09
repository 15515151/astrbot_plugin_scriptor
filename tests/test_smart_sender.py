"""
智能分段发送模块测试脚本
"""

import asyncio

# 使用包导入方式，兼容相对导入
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.smart_sender import Segment, SmartSender, SmartSplitConfig
except ImportError:
    from smart_sender import Segment, SmartSender, SmartSplitConfig


def test_split_text():
    """测试文本分段功能"""
    config = SmartSplitConfig(
        enabled=True,
        split_regex=r".*?(?:\n+|[。？！~…]{2,})|.+$",
        cleanup_regex=r"^\s+|\s+$",
        typing_speed=0.08,
        min_delay=1.5,
        max_delay=3.5,
        random_factor=0.2,
        long_text_threshold=150,
        long_text_pattern=r"\n{2,}",
    )

    sender = SmartSender(config)

    # 测试用例 1: 普通分段（短文本）
    text1 = "你好！我是AI助手。有什么可以帮助你的吗？"
    segments1 = sender.split_text(text1)
    print("测试用例 1: 普通分段（短文本）")
    print(f"  输入: {text1}")
    print(f"  分段数: {len(segments1)}")
    for i, seg in enumerate(segments1):
        print(f"    分段 {i+1}: {seg.text} (字数: {seg.char_count})")
    print()

    # 测试用例 2: 包含 @ 提及
    text2 = "你好 [@张三(UID:user_123)]！这个问题我来回答。[@李四(UID:user_456)] 也来看看吧。"
    segments2 = sender.split_text(text2)
    print("测试用例 2: 包含 @ 提及")
    print(f"  输入: {text2}")
    print(f"  分段数: {len(segments2)}")
    for i, seg in enumerate(segments2):
        print(f"    分段 {i+1}: {seg.text} (字数: {seg.char_count}, 包含@: {seg.has_at})")
    print()

    # 测试用例 3: 长文本（按双换行分段）
    text3 = "这是第一段内容，它比较长，包含了多个句子。这是第一段的继续。\n\n这是第二段内容，同样比较长。它也应该被正确分段。\n\n这是第三段。"
    segments3 = sender.split_text(text3)
    print("测试用例 3: 长文本（按双换行分段）")
    print(f"  输入长度: {len(text3)}")
    print(f"  分段数: {len(segments3)}")
    for i, seg in enumerate(segments3):
        print(f"    分段 {i+1}: {seg.text[:50]!r}... (字数: {seg.char_count})")
    print()

    # 测试用例 4: 长文本但无双换行（不分段）
    text4 = "这是一段很长的文本。" * 20
    segments4 = sender.split_text(text4)
    print("测试用例 4: 长文本但无双换行（应不分段）")
    print(f"  输入长度: {len(text4)}")
    print(f"  分段数: {len(segments4)}")
    print()

    # 测试用例 5: 短文本包含换行（按标点分段）
    text5 = "第一行\n第二行内容。\n第三行！"
    segments5 = sender.split_text(text5)
    print("测试用例 5: 短文本包含换行")
    print(f"  输入: {text5!r}")
    print(f"  输入长度: {len(text5)}")
    print(f"  分段数: {len(segments5)}")
    for i, seg in enumerate(segments5):
        print(f"    分段 {i+1}: {seg.text!r}")
    print()

    print("✅ 所有分段测试通过!")


def test_long_text_strategy():
    """测试长短文双策略"""
    config = SmartSplitConfig(
        enabled=True,
        split_regex=r".*?(?:\n+|[。？！~…]{2,})|.+$",
        cleanup_regex=r"^\s+|\s+$",
        long_text_threshold=150,
        long_text_pattern=r"\n{2,}",
    )

    sender = SmartSender(config)

    print("\n测试长短文双策略:")

    # 短文本（< 150字）
    short_text = "这是一个短文本。只有几十个字。"
    short_segments = sender.split_text(short_text)
    print(f"  短文本 ({len(short_text)}字): 分段数={len(short_segments)}")

    # 长文本（>= 150字）带双换行
    long_text_with_breaks = "段落一内容。" * 30 + "\n\n" + "段落二内容。" * 30
    long_segments = sender.split_text(long_text_with_breaks)
    print(f"  长文本带双换行 ({len(long_text_with_breaks)}字): 分段数={len(long_segments)}")

    # 长文本（>= 150字）无双换行
    long_text_no_breaks = "连续内容。" * 50
    long_segments_no_breaks = sender.split_text(long_text_no_breaks)
    print(f"  长文本无双换行 ({len(long_text_no_breaks)}字): 分段数={len(long_segments_no_breaks)}")

    print("✅ 长短文策略测试通过!")


def test_delayed_sanitization():
    """测试预清洗功能"""
    config = SmartSplitConfig(
        enabled=True,
        split_regex=r".*?(?:\n+|[。？！~…]{2,})|.+$",
        cleanup_regex=r"^\s+|\s+$",
        long_text_threshold=150,
        long_text_pattern=r"\n{2,}",
    )

    sender = SmartSender(config)

    print("\n测试预清洗功能:")

    class MockSanitizer:
        def pre_sanitize(self, text, platform=None):
            import re

            return re.sub(r"\*\*(.+?)\*\*", r"\1", text)

        def post_sanitize(self, text, platform=None):
            return text

    sanitizer = MockSanitizer()

    md_text = "这是**加粗**文本。这是普通文本。"
    segments = sender.split_text(md_text, sanitizer=sanitizer, platform="qq")

    print(f"  原始文本: {md_text}")
    for i, seg in enumerate(segments):
        print(f"    分段 {i+1}: {seg.text}")

    for seg in segments:
        assert "**" not in seg.text, f"分段中不应包含 ** 标记: {seg.text}"

    print("✅ 预清洗测试通过!")


def test_delay_calculation():
    """测试延迟计算功能"""
    config = SmartSplitConfig(
        enabled=True,
        split_regex=r".*?(?:\n+|[。？！~…]{2,})|.+$",
        cleanup_regex=r"^\s+|\s+$",
        typing_speed=0.08,
        min_delay=1.5,
        max_delay=3.5,
        random_factor=0.2,
    )

    sender = SmartSender(config)

    print("\n测试延迟计算:")

    # 测试短句
    short_seg = Segment(text="你好！")
    short_delay = sender.calculate_delay(short_seg)
    print(f"  短句 (3字): 延迟 = {short_delay:.2f}s (最小限制: {config.min_delay}s)")
    assert short_delay >= config.min_delay, "短句延迟应不小于最小延迟"

    # 测试中等长度
    medium_seg = Segment(text="这是一段中等长度的句子，用于测试打字延迟。")
    medium_delay = sender.calculate_delay(medium_seg)
    print(f"  中句 (20字): 延迟 = {medium_delay:.2f}s")

    # 测试长句
    long_seg = Segment(
        text="这是一段非常长的句子，用于测试最大延迟限制是否生效，如果这个句子很长很长，延迟应该被限制在最大值。" * 5
    )
    long_delay = sender.calculate_delay(long_seg)
    print(f"  长句 ({len(long_seg.text)}字): 延迟 = {long_delay:.2f}s (最大限制: {config.max_delay}s)")
    assert long_delay <= config.max_delay, "长句延迟应不大于最大延迟"

    print("✅ 延迟计算测试通过!")


async def test_session_lock():
    """测试会话锁功能"""
    config = SmartSplitConfig(enabled=True)
    sender = SmartSender(config)

    print("\n测试会话锁:")

    # 获取会话锁
    lock1 = await sender._get_session_lock("session_1")
    lock2 = await sender._get_session_lock("session_2")
    lock1_again = await sender._get_session_lock("session_1")

    print(f"  创建了 {len(sender._session_locks)} 个会话锁")
    print(f"  session_1 锁是否为同一对象: {lock1 is lock1_again}")

    assert lock1 is lock1_again, "同一会话应返回相同的锁对象"
    assert len(sender._session_locks) == 2, "应有 2 个不同的会话锁"

    print("✅ 会话锁测试通过!")


def test_stats():
    """测试统计信息"""
    config = SmartSplitConfig(
        enabled=True,
        split_regex=r".*?(?:\n+|[。？！~…]{2,})|.+$",
        typing_speed=0.08,
        min_delay=1.5,
        max_delay=3.5,
        random_factor=0.2,
        long_text_threshold=150,
        long_text_pattern=r"\n{2,}",
    )

    sender = SmartSender(config)
    stats = sender.get_stats()

    print("\n测试统计信息:")
    print(f"  启用状态: {stats['enabled']}")
    print(f"  活跃会话: {stats['active_sessions']}")
    print(f"  分段正则: {stats['split_regex']}")
    print(f"  打字速度: {stats['typing_speed']}")
    print(f"  最小延迟: {stats['min_delay']}")
    print(f"  最大延迟: {stats['max_delay']}")
    print(f"  随机波动: {stats['random_factor']}")
    print(f"  长文本阈值: {stats['long_text_threshold']}")
    print(f"  长文本正则: {stats['long_text_pattern']}")

    assert stats["enabled"] == True
    assert stats["typing_speed"] == 0.08
    assert stats["long_text_threshold"] == 150

    print("✅ 统计信息测试通过!")


if __name__ == "__main__":
    print("=" * 60)
    print("智能分段发送模块测试")
    print("=" * 60)

    test_split_text()
    test_long_text_strategy()
    test_delayed_sanitization()
    test_delay_calculation()
    asyncio.run(test_session_lock())
    test_stats()

    print("\n" + "=" * 60)
    print("🎉 所有测试通过!")
    print("=" * 60)
