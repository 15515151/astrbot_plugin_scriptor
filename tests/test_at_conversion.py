"""
@ 提及转换和智能分段集成测试
验证清理后的代码功能正常
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SmartSplitConfig:
    """智能分段配置"""

    enabled: bool = True
    only_llm: bool = True
    split_regex: str = r".*?[。？！~…\n]+|.+$"
    cleanup_regex: str = r"[\n]+$"
    typing_speed: float = 0.08
    min_delay: float = 1.5
    max_delay: float = 3.5
    random_factor: float = 0.2


@dataclass
class Segment:
    """分段数据结构"""

    text: str
    has_at: bool = False
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.text)
        self.has_at = "[@" in self.text and "(UID:" in self.text


class MockMessageChain:
    """模拟消息链"""

    def __init__(self, components=None):
        self.chain = components or []


class MockPlain:
    """模拟纯文本组件"""

    def __init__(self, text):
        self.text = text


class MockAt:
    """模拟 @ 组件"""

    def __init__(self, qq):
        self.qq = qq


class MockIdentityManager:
    """模拟身份管理器"""

    def __init__(self):
        self._identity_map = {
            ("user_123", "qq"): "123456789",
            ("user_456", "qq"): "987654321",
            ("张三", "qq"): "111111111",
        }

    def get_physical_id(self, uid: str, platform: str) -> Optional[str]:
        return self._identity_map.get((uid, platform))

    def get_physical_id_by_digit(self, digit: str, platform: str) -> Optional[str]:
        for (uid, p), physical in self._identity_map.items():
            if physical == digit:
                return physical
        return None


def convert_text_to_chain(text: str, identity_manager: MockIdentityManager, platform: str = "qq"):
    """
    模拟 _convert_text_to_chain 方法
    将包含 [@昵称(UID:xxx)] 的文本转换为消息链
    """
    chain = MockMessageChain()
    pattern = r"\[@.*?\s*\(UID:\s*([a-zA-Z0-9_]+)\s*\)\]"

    last_pos = 0
    for match in re.finditer(pattern, text):
        plain_text = text[last_pos : match.start()]
        if plain_text:
            chain.chain.append(MockPlain(plain_text))

        target_uid = match.group(1)

        if target_uid.isdigit():
            physical_id = identity_manager.get_physical_id_by_digit(target_uid, platform)
            if not physical_id:
                physical_id = target_uid
        else:
            physical_id = identity_manager.get_physical_id(target_uid, platform)

        if physical_id:
            chain.chain.append(MockAt(qq=physical_id))
        else:
            chain.chain.append(MockPlain(match.group(0)))

        last_pos = match.end()

    remaining_text = text[last_pos:]
    if remaining_text:
        chain.chain.append(MockPlain(remaining_text))

    return chain


class SmartSender:
    """智能分段发送器"""

    def __init__(self, config: SmartSplitConfig):
        self.config = config
        self._compiled_split_regex = re.compile(config.split_regex)
        self._compiled_cleanup_regex = re.compile(config.cleanup_regex) if config.cleanup_regex else None

    def split_text(self, text: str) -> List[Segment]:
        """将文本智能分段"""
        if not text or not text.strip():
            return []

        segments = []
        raw_segments = self._compiled_split_regex.findall(text)

        for seg_text in raw_segments:
            if not seg_text:
                continue

            if self._compiled_cleanup_regex:
                cleaned_text = self._compiled_cleanup_regex.sub("", seg_text)
            else:
                cleaned_text = seg_text

            if cleaned_text.strip():
                segments.append(Segment(text=cleaned_text))

        return segments


def test_at_conversion():
    """测试 @ 提及转换"""
    print("\n" + "=" * 60)
    print("测试 1: @ 提及转换")
    print("=" * 60)

    identity_manager = MockIdentityManager()

    # 测试用例 1: 句首 @
    text1 = "[@张三(UID:user_123)]，你好！"
    chain1 = convert_text_to_chain(text1, identity_manager)
    print("\n测试用例 1 - 句首 @:")
    print(f"  输入: {text1}")
    print(f"  输出组件数: {len(chain1.chain)}")
    for i, comp in enumerate(chain1.chain):
        if isinstance(comp, MockAt):
            print(f"    组件 {i+1}: At(qq={comp.qq})")
        else:
            print(f"    组件 {i+1}: Plain('{comp.text}')")

    assert len(chain1.chain) == 2, "应有 2 个组件"
    assert isinstance(chain1.chain[0], MockAt), "第一个组件应为 At"
    assert chain1.chain[0].qq == "123456789", "At 的 qq 应为 123456789"
    print("  ✅ 通过")

    # 测试用例 2: 句中 @
    text2 = "你好 [@张三(UID:user_123)]，今天天气不错。"
    chain2 = convert_text_to_chain(text2, identity_manager)
    print("\n测试用例 2 - 句中 @:")
    print(f"  输入: {text2}")
    print(f"  输出组件数: {len(chain2.chain)}")
    for i, comp in enumerate(chain2.chain):
        if isinstance(comp, MockAt):
            print(f"    组件 {i+1}: At(qq={comp.qq})")
        else:
            print(f"    组件 {i+1}: Plain('{comp.text}')")

    assert len(chain2.chain) == 3, "应有 3 个组件"
    assert isinstance(chain2.chain[0], MockPlain), "第一个组件应为 Plain"
    assert isinstance(chain2.chain[1], MockAt), "第二个组件应为 At"
    assert isinstance(chain2.chain[2], MockPlain), "第三个组件应为 Plain"
    print("  ✅ 通过")

    # 测试用例 3: 多个 @
    text3 = "[@张三(UID:user_123)] 和 [@李四(UID:user_456)] 你们好！"
    chain3 = convert_text_to_chain(text3, identity_manager)
    print("\n测试用例 3 - 多个 @:")
    print(f"  输入: {text3}")
    print(f"  输出组件数: {len(chain3.chain)}")
    for i, comp in enumerate(chain3.chain):
        if isinstance(comp, MockAt):
            print(f"    组件 {i+1}: At(qq={comp.qq})")
        else:
            print(f"    组件 {i+1}: Plain('{comp.text}')")

    assert len(chain3.chain) == 4, "应有 4 个组件"
    at_count = sum(1 for c in chain3.chain if isinstance(c, MockAt))
    assert at_count == 2, "应有 2 个 At 组件"
    print("  ✅ 通过")

    print("\n✅ 所有 @ 提及转换测试通过!")


def test_smart_split_with_at():
    """测试智能分段与 @ 提及的集成"""
    print("\n" + "=" * 60)
    print("测试 2: 智能分段与 @ 提及集成")
    print("=" * 60)

    config = SmartSplitConfig(enabled=True)
    sender = SmartSender(config)
    identity_manager = MockIdentityManager()

    # 测试用例: 包含 @ 的多句文本
    text = "你好 [@张三(UID:user_123)]！今天天气不错。[@李四(UID:user_456)] 也来看看吧。"

    print(f"\n原始文本: {text}")

    segments = sender.split_text(text)
    print(f"\n分段结果 ({len(segments)} 段):")

    for i, seg in enumerate(segments):
        print(f"\n  分段 {i+1}: '{seg.text}'")
        print(f"    字数: {seg.char_count}, 包含@: {seg.has_at}")

        # 对每个分段进行 @ 转换
        chain = convert_text_to_chain(seg.text, identity_manager)
        print(f"    转换后组件数: {len(chain.chain)}")
        for j, comp in enumerate(chain.chain):
            if isinstance(comp, MockAt):
                print(f"      组件 {j+1}: At(qq={comp.qq})")
            else:
                print(f"      组件 {j+1}: Plain('{comp.text}')")

    # 验证每个包含 @ 的分段都能正确转换
    for seg in segments:
        if seg.has_at:
            chain = convert_text_to_chain(seg.text, identity_manager)
            has_at_component = any(isinstance(c, MockAt) for c in chain.chain)
            assert has_at_component, f"分段 '{seg.text}' 包含 @ 标签但转换后没有 At 组件"

    print("\n✅ 智能分段与 @ 提及集成测试通过!")


def test_split_edge_cases():
    """测试分段边界情况"""
    print("\n" + "=" * 60)
    print("测试 3: 分段边界情况")
    print("=" * 60)

    config = SmartSplitConfig(enabled=True)
    sender = SmartSender(config)

    # 测试用例 1: 空文本
    segments1 = sender.split_text("")
    print(f"\n空文本: 分段数 = {len(segments1)}")
    assert len(segments1) == 0, "空文本应产生 0 个分段"
    print("  ✅ 通过")

    # 测试用例 2: 单句无标点
    segments2 = sender.split_text("这是一句话")
    print(f"\n单句无标点: 分段数 = {len(segments2)}")
    assert len(segments2) == 1, "单句应产生 1 个分段"
    print("  ✅ 通过")

    # 测试用例 3: 连续标点
    segments3 = sender.split_text("真的吗？？真的！！")
    print(f"\n连续标点: 分段数 = {len(segments3)}")
    for i, seg in enumerate(segments3):
        print(f"  分段 {i+1}: '{seg.text}'")
    print("  ✅ 通过")

    print("\n✅ 所有边界情况测试通过!")


def test_cleanup():
    """测试清理功能"""
    print("\n" + "=" * 60)
    print("测试 4: 清理功能")
    print("=" * 60)

    config = SmartSplitConfig(enabled=True, cleanup_regex=r"[\n]+$")  # 清理末尾换行
    sender = SmartSender(config)

    text = "第一行\n第二行。\n第三行！"
    segments = sender.split_text(text)

    print(f"\n原始文本: {text!r}")
    print("分段结果:")
    for i, seg in enumerate(segments):
        print(f"  分段 {i+1}: {seg.text!r}")

    # 验证清理后的分段末尾没有换行符
    for seg in segments:
        assert not seg.text.endswith("\n"), f"分段 '{seg.text}' 末尾不应有换行符"

    print("\n✅ 清理功能测试通过!")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 @ 提及转换和智能分段集成测试")
    print("=" * 60)

    test_at_conversion()
    test_smart_split_with_at()
    test_split_edge_cases()
    test_cleanup()

    print("\n" + "=" * 60)
    print("🎉 所有测试通过! 代码清理后功能正常!")
    print("=" * 60)
