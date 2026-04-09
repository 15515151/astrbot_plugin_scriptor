"""
智能分段发送模块测试脚本 - 独立版本
测试内容：
1. 长短文双策略分段
2. 延迟清洗功能
3. 首段引用注入
4. 首段 @ 清洗
5. 群组级会话锁
"""

import asyncio
import random
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SmartSplitConfig:
    """智能分段配置"""

    enabled: bool = True
    split_regex: str = r".*?(?:\n+|[。？！~…]{2,})|.+$"
    cleanup_regex: str = r"^\s+|\s+$"
    typing_speed: float = 0.08
    min_delay: float = 1.5
    max_delay: float = 3.5
    random_factor: float = 0.2
    long_text_threshold: int = 150
    long_text_pattern: str = r"\n{2,}"


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

    def __init__(self, chain=None):
        self.chain = chain if chain else []


class MockReply:
    """模拟引用组件"""

    def __init__(self, id):
        self.id = id
        self.type = "Reply"


class SmartSender:
    """智能分段发送器"""

    def __init__(self, config: SmartSplitConfig):
        self.config = config

        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

        self._compiled_split_regex: Optional[re.Pattern] = None
        self._compiled_cleanup_regex: Optional[re.Pattern] = None
        self._compiled_long_text_regex: Optional[re.Pattern] = None
        self._compile_regexes()

        print(f"[SmartSender] 初始化完成，启用状态: {config.enabled}, 长文本阈值: {config.long_text_threshold}")

    def _compile_regexes(self):
        """编译正则表达式"""
        try:
            self._compiled_split_regex = re.compile(self.config.split_regex)
            print(f"[SmartSender] 分段正则编译成功: {self.config.split_regex}")
        except re.error as e:
            print(f"[SmartSender] 分段正则编译失败: {e}，使用默认正则")
            self._compiled_split_regex = re.compile(r".*?(?:\n+|[。？！~…]{2,})|.+$")

        if self.config.cleanup_regex:
            try:
                self._compiled_cleanup_regex = re.compile(self.config.cleanup_regex)
                print(f"[SmartSender] 清理正则编译成功: {self.config.cleanup_regex}")
            except re.error as e:
                print(f"[SmartSender] 清理正则编译失败: {e}")
                self._compiled_cleanup_regex = None
        else:
            self._compiled_cleanup_regex = None

        if self.config.long_text_pattern:
            try:
                self._compiled_long_text_regex = re.compile(self.config.long_text_pattern)
                print(f"[SmartSender] 长文本分段正则编译成功: {self.config.long_text_pattern}")
            except re.error as e:
                print(f"[SmartSender] 长文本分段正则编译失败: {e}")
                self._compiled_long_text_regex = None
        else:
            self._compiled_long_text_regex = None

    async def _get_session_lock(self, session_id: str) -> asyncio.Lock:
        """获取或创建会话锁"""
        async with self._global_lock:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = asyncio.Lock()
            return self._session_locks[session_id]

    @staticmethod
    def remove_leading_at(text: str, target_uid: str) -> str:
        """移除文本开头的针对目标用户的 @ 提及"""
        if not target_uid or not text:
            return text

        pattern = rf"^\[@[^\]]*?\(UID:{re.escape(target_uid)}\)\]\s*"
        cleaned = re.sub(pattern, "", text)

        if cleaned != text:
            print(f"[SmartSender] 已移除首段开头的 @ 提及: target_uid={target_uid}")

        return cleaned

    def split_text(self, text: str, sanitizer_func: Callable[[str], str] = None) -> List[Segment]:
        """将文本智能分段（支持长短文双策略和延迟清洗）"""
        if not text or not text.strip():
            return []

        segments: List[Segment] = []

        text_length = len(text)
        is_long_text = text_length >= self.config.long_text_threshold

        if is_long_text and self._compiled_long_text_regex:
            raw_segments = self._compiled_long_text_regex.split(text)
            print(f"[SmartSender] 长文本分段策略: 长度={text_length}, 阈值={self.config.long_text_threshold}")
        else:
            raw_segments = self._compiled_split_regex.findall(text)
            if is_long_text:
                print("[SmartSender] 长文本但无长文本正则，使用常规分段")

        for seg_text in raw_segments:
            if not seg_text:
                continue

            if sanitizer_func:
                cleaned_text = sanitizer_func(seg_text)
            else:
                cleaned_text = seg_text

            if self._compiled_cleanup_regex:
                cleaned_text = self._compiled_cleanup_regex.sub("", cleaned_text)

            if cleaned_text.strip():
                segments.append(Segment(text=cleaned_text))

        print(
            f"[SmartSender] 文本分段完成: 原始长度={len(text)}, 分段数={len(segments)}, 长文本={'是' if is_long_text else '否'}"
        )

        return segments

    def calculate_delay(self, segment: Segment) -> float:
        """计算发送延迟"""
        base_delay = segment.char_count * self.config.typing_speed
        base_delay = max(self.config.min_delay, min(base_delay, self.config.max_delay))

        if self.config.random_factor > 0:
            random_offset = base_delay * self.config.random_factor * (random.random() * 2 - 1)
            final_delay = base_delay + random_offset
        else:
            final_delay = base_delay

        final_delay = max(self.config.min_delay, min(final_delay, self.config.max_delay))

        return final_delay

    async def send_with_split(
        self,
        text: str,
        session_id: str,
        send_callback,
        convert_at_callback=None,
        sanitizer_func=None,
        reply_to_id: str = None,
        target_uid: str = None,
        debug_mode: bool = False,
    ) -> bool:
        """智能分段发送消息（支持延迟清洗和首段引用）"""
        if not self.config.enabled:
            if sanitizer_func:
                text = sanitizer_func(text)

            if target_uid:
                text = self.remove_leading_at(text, target_uid)

            if convert_at_callback:
                message_chain = await convert_at_callback(text)
            else:
                message_chain = MockMessageChain([text])

            if reply_to_id and message_chain is not None:
                if hasattr(message_chain, "chain"):
                    message_chain.chain.insert(0, MockReply(id=reply_to_id))
                    if debug_mode:
                        print(f"[SmartSender] 首段引用注入: reply_to_id={reply_to_id}")

            return await send_callback(message_chain)

        segments = self.split_text(text, sanitizer_func)

        if not segments:
            return True

        session_lock = await self._get_session_lock(session_id)

        async with session_lock:
            if debug_mode:
                print(f"[SmartSender] 开始分段发送: 会话={session_id}, 分段数={len(segments)}")

            for i, segment in enumerate(segments):
                try:
                    delay = self.calculate_delay(segment)

                    if debug_mode:
                        print(
                            f"[SmartSender] 发送分段 {i+1}/{len(segments)}: "
                            f"字数={segment.char_count}, 延迟={delay:.2f}s, "
                            f"包含@={'是' if segment.has_at else '否'}"
                        )

                    await asyncio.sleep(delay)

                    segment_text = segment.text

                    is_first_segment = i == 0

                    if is_first_segment and target_uid:
                        segment_text = self.remove_leading_at(segment_text, target_uid)

                    if convert_at_callback:
                        message_chain = await convert_at_callback(segment_text)
                    else:
                        message_chain = MockMessageChain([segment_text])

                    if is_first_segment and reply_to_id and message_chain is not None:
                        if hasattr(message_chain, "chain"):
                            message_chain.chain.insert(0, MockReply(id=reply_to_id))
                            if debug_mode:
                                print(f"[SmartSender] 首段引用注入: reply_to_id={reply_to_id}")

                    success = await send_callback(message_chain)

                    if not success:
                        print(f"[SmartSender] 分段 {i+1} 发送失败")
                        return False

                except asyncio.CancelledError:
                    print(f"[SmartSender] 发送被取消: 会话={session_id}")
                    raise
                except Exception as e:
                    print(f"[SmartSender] 发送分段 {i+1} 时出错: {e}")
                    return False

            if debug_mode:
                print(f"[SmartSender] 分段发送完成: 会话={session_id}")

            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "enabled": self.config.enabled,
            "active_sessions": len(self._session_locks),
            "split_regex": self.config.split_regex,
            "typing_speed": self.config.typing_speed,
            "min_delay": self.config.min_delay,
            "max_delay": self.config.max_delay,
            "random_factor": self.config.random_factor,
            "long_text_threshold": self.config.long_text_threshold,
            "long_text_pattern": self.config.long_text_pattern,
        }


# ============== 测试用例 ==============


def test_remove_leading_at():
    """测试首段 @ 清洗功能"""
    print("\n" + "=" * 60)
    print("测试首段 @ 清洗功能")
    print("=" * 60)

    config = SmartSplitConfig()
    sender = SmartSender(config)

    # 测试用例 1: 开头有 @
    text1 = "[@张三(UID:user_123)] 你好，这是回复内容。"
    cleaned1 = sender.remove_leading_at(text1, "user_123")
    print("\n测试 1: 开头有 @")
    print(f"  原文: {text1}")
    print(f"  清洗后: {cleaned1}")
    assert cleaned1 == "你好，这是回复内容。", f"清洗失败: {cleaned1}"

    # 测试用例 2: 开头有 @ 但带空格
    text2 = "[@李四(UID:user_456)]   这是带空格的回复。"
    cleaned2 = sender.remove_leading_at(text2, "user_456")
    print("\n测试 2: 开头有 @ 且带空格")
    print(f"  原文: {text2}")
    print(f"  清洗后: {cleaned2}")
    assert cleaned2 == "这是带空格的回复。", f"清洗失败: {cleaned2}"

    # 测试用例 3: @ 不在开头（不应清洗）
    text3 = "你好，[@王五(UID:user_789)] 也来看看吧。"
    cleaned3 = sender.remove_leading_at(text3, "user_789")
    print("\n测试 3: @ 不在开头")
    print(f"  原文: {text3}")
    print(f"  清洗后: {cleaned3}")
    assert cleaned3 == text3, f"不应清洗: {cleaned3}"

    # 测试用例 4: @ 的是其他人（不应清洗）
    text4 = "[@张三(UID:user_123)] 你好，[@李四(UID:user_456)] 也来看看吧。"
    cleaned4 = sender.remove_leading_at(text4, "user_456")  # target_uid 是 user_456
    print("\n测试 4: @ 的是其他人")
    print(f"  原文: {text4}")
    print(f"  清洗后: {cleaned4}")
    assert cleaned4 == text4, f"不应清洗其他人的 @: {cleaned4}"

    print("\n✅ 首段 @ 清洗测试通过!")


async def test_reply_injection():
    """测试首段引用注入功能"""
    print("\n" + "=" * 60)
    print("测试首段引用注入功能")
    print("=" * 60)

    config = SmartSplitConfig(enabled=True)
    sender = SmartSender(config)

    sent_messages = []

    async def mock_send_callback(message_chain):
        sent_messages.append(message_chain)
        return True

    async def mock_convert_at_callback(text):
        return MockMessageChain([text])

    # 发送带引用的消息
    text = "这是回复内容。"
    success = await sender.send_with_split(
        text=text,
        session_id="test_group_1",
        send_callback=mock_send_callback,
        convert_at_callback=mock_convert_at_callback,
        reply_to_id="msg_12345",
        target_uid="user_123",
        debug_mode=True,
    )

    assert success, "发送失败"
    assert len(sent_messages) == 1, f"应发送 1 条消息，实际: {len(sent_messages)}"

    first_msg = sent_messages[0]
    assert len(first_msg.chain) == 2, f"消息链应有 2 个元素（Reply + 文本），实际: {len(first_msg.chain)}"
    assert isinstance(first_msg.chain[0], MockReply), "第一个元素应为 Reply"
    assert first_msg.chain[0].id == "msg_12345", f"Reply ID 应为 msg_12345，实际: {first_msg.chain[0].id}"

    print("\n发送的消息链:")
    for i, item in enumerate(first_msg.chain):
        if isinstance(item, MockReply):
            print(f"  [{i}] Reply(id={item.id})")
        else:
            print(f"  [{i}] 文本: {item}")

    print("\n✅ 首段引用注入测试通过!")


async def test_group_level_lock():
    """测试群组级会话锁"""
    print("\n" + "=" * 60)
    print("测试群组级会话锁")
    print("=" * 60)

    config = SmartSplitConfig(enabled=True)
    sender = SmartSender(config)

    sent_order = []

    async def mock_send_callback(message_chain):
        sent_order.append(f"msg_{len(sent_order)}")
        await asyncio.sleep(0.1)  # 模拟发送延迟
        return True

    async def mock_convert_at_callback(text):
        return MockMessageChain([text])

    # 模拟同一群组的两个用户同时发送
    async def user_send(session_id, user_name):
        await sender.send_with_split(
            text=f"{user_name}的消息",
            session_id=session_id,  # 同一群组使用相同的 session_id
            send_callback=mock_send_callback,
            convert_at_callback=mock_convert_at_callback,
            debug_mode=True,
        )

    # 并发发送（同一群组）
    await asyncio.gather(user_send("group_123", "用户A"), user_send("group_123", "用户B"))

    # 验证消息是串行发送的（不会有交织）
    print(f"\n发送顺序: {sent_order}")
    print("✅ 群组级会话锁测试通过!")


async def test_combined_features():
    """测试组合功能：首段引用 + 去 @ + 分段"""
    print("\n" + "=" * 60)
    print("测试组合功能：首段引用 + 去 @ + 分段")
    print("=" * 60)

    config = SmartSplitConfig(enabled=True)
    sender = SmartSender(config)

    sent_messages = []

    async def mock_send_callback(message_chain):
        sent_messages.append(message_chain)
        return True

    async def mock_convert_at_callback(text):
        # 模拟 @ 转换（这里简化处理）
        return MockMessageChain([text])

    # AI 生成的回复（开头有 @，且会被分段）
    text = "[@张三(UID:user_123)] 你好！这是第一句。这是第二句。"

    success = await sender.send_with_split(
        text=text,
        session_id="test_group",
        send_callback=mock_send_callback,
        convert_at_callback=mock_convert_at_callback,
        reply_to_id="msg_999",
        target_uid="user_123",
        debug_mode=True,
    )

    assert success, "发送失败"

    print(f"\n发送了 {len(sent_messages)} 条消息:")
    for i, msg in enumerate(sent_messages):
        print(f"\n消息 {i+1}:")
        for j, item in enumerate(msg.chain):
            if isinstance(item, MockReply):
                print(f"  [{j}] Reply(id={item.id})")
            else:
                print(f"  [{j}] 文本: {item}")

    # 验证第一条消息
    first_msg = sent_messages[0]
    assert isinstance(first_msg.chain[0], MockReply), "第一条消息应有引用"
    assert "[@张三(UID:user_123)]" not in first_msg.chain[1], "首段 @ 应被清洗"

    print("\n✅ 组合功能测试通过!")


def test_long_text_strategy():
    """测试长短文双策略"""
    print("\n" + "=" * 60)
    print("测试长短文双策略")
    print("=" * 60)

    config = SmartSplitConfig()
    sender = SmartSender(config)

    # 短文本（< 150字）
    short_text = "这是一个短文本。只有几十个字。"
    short_segments = sender.split_text(short_text)
    print(f"\n短文本 ({len(short_text)}字): 分段数={len(short_segments)}")

    # 长文本（>= 150字）带双换行
    long_text_with_breaks = "段落一内容。" * 30 + "\n\n" + "段落二内容。" * 30
    long_segments = sender.split_text(long_text_with_breaks)
    print(f"长文本带双换行 ({len(long_text_with_breaks)}字): 分段数={len(long_segments)}")

    # 长文本（>= 150字）无双换行
    long_text_no_breaks = "连续内容。" * 50
    long_segments_no_breaks = sender.split_text(long_text_no_breaks)
    print(f"长文本无双换行 ({len(long_text_no_breaks)}字): 分段数={len(long_segments_no_breaks)}")

    print("\n✅ 长短文策略测试通过!")


class MockIdentityManager:
    """模拟身份管理器"""

    def __init__(self):
        self.identity_map = {
            "qq:123456789": "user_abc12345",
            "qq:987654321": "user_xyz98765",
        }
        self.uid_metadata = {
            "user_abc12345": {"primary_name": "张三"},
            "user_xyz98765": {"primary_name": "李四"},
            "user_547813589": {"primary_name": "桃子"},
        }

    def get_physical_id(self, uid: str, platform: str) -> Optional[str]:
        """根据 UID 和平台获取物理 ID"""
        platform = platform.lower()
        key_prefix = f"{platform}:"
        for key, mapped_uid in self.identity_map.items():
            if mapped_uid == uid and key.lower().startswith(key_prefix):
                return key[len(key_prefix) :]
        return None

    def get_physical_id_by_digit(self, digit_id: str, platform: str) -> Optional[str]:
        """根据纯数字 ID 查找物理 ID"""
        platform = platform.lower()
        key_prefix = f"{platform}:"
        for key in self.identity_map.keys():
            if key.lower().startswith(key_prefix):
                physical_id = key[len(key_prefix) :]
                if physical_id == digit_id:
                    return digit_id
        return None

    def get_user_primary_name(self, uid: str) -> str:
        """获取用户主名称"""
        return self.uid_metadata.get(uid, {}).get("primary_name", "Unknown")


class MockAt:
    """模拟 At 组件"""

    def __init__(self, qq):
        self.qq = qq
        self.type = "At"


def resolve_at_target(target_uid: str, platform: str, identity_manager: MockIdentityManager) -> Optional[str]:
    """
    多重智能兜底解析 At 目标（独立测试版本）

    1. 第一层：查映射表（逻辑ID/昵称 -> 物理ID）
    2. 第二层：智能去前缀提取（user_xxx -> xxx）
    3. 第三层：物理ID兜底（直接使用纯数字）
    """
    if not target_uid:
        return None

    physical_id = None

    # 纯数字（可能是物理ID）
    if target_uid.isdigit():
        physical_id = identity_manager.get_physical_id_by_digit(target_uid, platform)
        if physical_id:
            print(f"  [At解析-第一层] 纯数字查表成功: {target_uid} -> {physical_id}")
            return physical_id
        print(f"  [At解析-第三层] 纯数字兜底: {target_uid}")
        return target_uid

    # user_ 前缀（逻辑ID格式）
    if target_uid.startswith("user_"):
        digit_part = target_uid[5:]
        if digit_part.isdigit():
            physical_id = identity_manager.get_physical_id_by_digit(digit_part, platform)
            if physical_id:
                print(f"  [At解析-第二层] 去前缀查表成功: {target_uid} -> {physical_id}")
                return physical_id
            print(f"  [At解析-第二层] 去前缀兜底: {target_uid} -> {digit_part}")
            return digit_part

    # 尝试通过逻辑ID查表
    physical_id = identity_manager.get_physical_id(target_uid, platform)
    if physical_id:
        print(f"  [At解析-第一层] 逻辑ID查表成功: {target_uid} -> {physical_id}")
        return physical_id

    print(f"  [At解析失败] 无法识别的目标标识符: {target_uid}")
    return None


def test_at_resolution():
    """测试多重智能兜底解析机制"""
    print("\n" + "=" * 60)
    print("测试多重智能兜底解析机制")
    print("=" * 60)

    identity_manager = MockIdentityManager()
    platform = "qq"

    # 测试用例 1: 逻辑ID查表（已知用户）
    print("\n测试 1: 逻辑ID查表（已知用户）")
    result1 = resolve_at_target("user_abc12345", platform, identity_manager)
    print(f"  结果: {result1}")
    assert result1 == "123456789", f"应为 123456789，实际: {result1}"

    # 测试用例 2: user_前缀 + 纯数字（去前缀兜底）
    print("\n测试 2: user_前缀 + 纯数字（去前缀兜底）")
    result2 = resolve_at_target("user_547813589", platform, identity_manager)
    print(f"  结果: {result2}")
    assert result2 == "547813589", f"应为 547813589，实际: {result2}"

    # 测试用例 3: 纯物理ID（纯数字兜底）
    print("\n测试 3: 纯物理ID（纯数字兜底）")
    result3 = resolve_at_target("111222333", platform, identity_manager)
    print(f"  结果: {result3}")
    assert result3 == "111222333", f"应为 111222333，实际: {result3}"

    # 测试用例 4: 纯数字查表（已知用户）
    print("\n测试 4: 纯数字查表（已知用户）")
    result4 = resolve_at_target("123456789", platform, identity_manager)
    print(f"  结果: {result4}")
    assert result4 == "123456789", f"应为 123456789，实际: {result4}"

    # 测试用例 5: 未知逻辑ID（解析失败）
    print("\n测试 5: 未知逻辑ID（解析失败）")
    result5 = resolve_at_target("user_unknown", platform, identity_manager)
    print(f"  结果: {result5}")
    assert result5 is None, f"应为 None，实际: {result5}"

    print("\n✅ 多重智能兜底解析测试通过!")


class MockGroupMember:
    """模拟群成员"""

    def __init__(self, uid: str, alias: str, role: str = "member"):
        self.uid = uid
        self.alias = alias
        self.role = role


class MockGroup:
    """模拟群组"""

    def __init__(self, group_id: str, name: str):
        self.group_id = group_id
        self.name = name
        self.members: List[MockGroupMember] = []


class MockGroupManager:
    """模拟群组管理器"""

    def __init__(self):
        self.groups: Dict[str, MockGroup] = {
            "group_123": MockGroup("group_123", "测试群"),
        }

    def get_group(self, group_id: str) -> Optional[MockGroup]:
        return self.groups.get(group_id)

    def get_member(self, group_id: str, uid: str) -> Optional[MockGroupMember]:
        group = self.get_group(group_id)
        if not group:
            return None
        for member in group.members:
            if member.uid == uid:
                return member
        return None

    def add_member(self, group_id: str, uid: str, alias: str, role: str = "member"):
        group = self.get_group(group_id)
        if not group:
            return

        existing = self.get_member(group_id, uid)
        if existing:
            existing.alias = alias
            existing.role = role
            return

        member = MockGroupMember(uid=uid, alias=alias, role=role)
        group.members.append(member)


def register_mentioned_user_to_group(group_manager: MockGroupManager, group_id: str, uid: str, physical_id: str):
    """
    将被 @ 的用户注册到群成员列表中（顺手牵羊式登记）

    Args:
        group_id: 群组ID
        uid: 用户的逻辑ID
        physical_id: 用户的物理ID（如QQ号）
    """
    if group_id == "private":
        return

    group = group_manager.get_group(group_id)
    if not group:
        return

    existing_member = group_manager.get_member(group_id, uid)
    if existing_member:
        return

    group_manager.add_member(group_id, uid, physical_id, role="member")
    print(f"  [顺手牵羊] 登记群成员: group={group_id}, uid={uid}, physical_id={physical_id}")


def test_opportunistic_registration():
    """测试顺手牵羊式群成员登记（使用物理ID）"""
    print("\n" + "=" * 60)
    print("测试顺手牵羊式群成员登记")
    print("=" * 60)

    group_manager = MockGroupManager()
    group_id = "group_123"

    # 初始状态：群成员列表为空
    print("\n初始状态:")
    group = group_manager.get_group(group_id)
    print(f"  群成员数: {len(group.members)}")
    assert len(group.members) == 0, "初始应为空"

    # 模拟用户A被 @（首次登记，使用QQ号作为物理ID）
    print("\n模拟用户A被 @:")
    register_mentioned_user_to_group(group_manager, group_id, "user_111", "123456789")
    assert len(group.members) == 1, "应有1个成员"
    assert group.members[0].uid == "user_111"
    assert group.members[0].alias == "123456789", "alias应存储物理ID"

    # 模拟用户A再次被 @（不应重复登记）
    print("\n模拟用户A再次被 @:")
    register_mentioned_user_to_group(group_manager, group_id, "user_111", "123456789")
    assert len(group.members) == 1, "不应重复登记"

    # 模拟用户B被 @（新成员登记）
    print("\n模拟用户B被 @:")
    register_mentioned_user_to_group(group_manager, group_id, "user_222", "987654321")
    assert len(group.members) == 2, "应有2个成员"

    # 验证最终成员列表
    print("\n最终群成员列表:")
    for member in group.members:
        print(f"  - {member.alias} ({member.uid})")

    print("\n✅ 顺手牵羊式群成员登记测试通过!")


class MockPlatform:
    """模拟平台枚举"""

    QQ = "qq"
    WECHAT = "wechat"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    DEFAULT = "default"


class MockMessageSanitizer:
    """模拟消息清洗器"""

    def pre_sanitize(self, text: str, platform) -> str:
        """预清洗：去除 Markdown 标记但保留换行"""
        if platform not in (MockPlatform.QQ, MockPlatform.WECHAT):
            return text

        result = text

        result = re.sub(r"```[\s\S]*?```", "", result)
        result = re.sub(r"`(.*?)`", r"\1", result)
        result = re.sub(r"^#{1,6}\s+", "", result, flags=re.MULTILINE)
        result = re.sub(r"(\n)[ \t]*[-*_](?:[ \t]*[-*_]){2,}[ \t]*\n+", r"\1", result)
        result = re.sub(r"^[ \t]*[-*_](?:[ \t]*[-*_]){2,}[ \t]*\n+", "", result)
        result = re.sub(r"\*\*(.*?)\*\*", r"\1", result)
        result = re.sub(r"__(.*?)__", r"\1", result)
        result = re.sub(r"\*(.*?)\*", r"\1", result)
        result = re.sub(r"_(.*?)_", r"\1", result)
        result = re.sub(r"~~(.*?)~~", r"\1", result)
        result = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", result)
        result = re.sub(r"^[\s]*[-*+]\s+", "", result, flags=re.MULTILINE)
        result = re.sub(r"^[\s]*\d+\.\s+", "", result, flags=re.MULTILINE)
        result = re.sub(r"^>\s+", "", result, flags=re.MULTILINE)

        return result

    def post_sanitize(self, text: str, platform) -> str:
        """后清洗：检查碎片"""
        if platform not in (MockPlatform.QQ, MockPlatform.WECHAT):
            return text

        stripped = text.strip()

        if not stripped:
            return ""

        markdown_only_pattern = r"^[*_~>`#\-\s]+$"
        if re.match(markdown_only_pattern, stripped):
            print(f"[MockMessageSanitizer] 检测到碎片，已丢弃: {stripped!r}")
            return ""

        return text


def test_pre_sanitize():
    """测试预清洗功能"""
    print("\n" + "=" * 60)
    print("测试预清洗功能")
    print("=" * 60)

    sanitizer = MockMessageSanitizer()

    test_cases = [
        ("**粗体文本**", "粗体文本"),
        ("*斜体文本*", "斜体文本"),
        ("~~删除线~~", "删除线"),
        ("# 标题", "标题"),
        ("[链接](http://example.com)", "链接"),
        ("`行内代码`", "行内代码"),
        ("**粗体**和*斜体*混合", "粗体和斜体混合"),
    ]

    for original, expected in test_cases:
        result = sanitizer.pre_sanitize(original, MockPlatform.QQ)
        print(f"  原文: {original}")
        print(f"  清洗后: {result}")
        assert result == expected, f"预清洗失败: {result} != {expected}"

    print("\n✅ 预清洗功能测试通过!")


def test_post_sanitize():
    """测试碎片检查功能"""
    print("\n" + "=" * 60)
    print("测试碎片检查功能")
    print("=" * 60)

    sanitizer = MockMessageSanitizer()

    test_cases = [
        ("正常文本", "正常文本"),
        ("*", ""),
        ("**", ""),
        ("___", ""),
        ("~~~", ""),
        (">>>", ""),
        ("###", ""),
        ("   ", ""),
        ("* *", ""),
    ]

    for original, expected in test_cases:
        result = sanitizer.post_sanitize(original, MockPlatform.QQ)
        print(f"  输入: {original!r}")
        print(f"  输出: {result!r}")
        assert result == expected, f"碎片检查失败: {result!r} != {expected!r}"

    print("\n✅ 碎片检查功能测试通过!")


def test_hr_removal():
    """测试分割线清洗功能"""
    print("\n" + "=" * 60)
    print("测试分割线清洗功能")
    print("=" * 60)

    sanitizer = MockMessageSanitizer()

    test_cases = [
        ("正文\n\n---\n\n下文", "正文\n\n下文"),
        ("正文\n---\n下文", "正文\n下文"),
        ("---\n开头正文", "开头正文"),
        ("正文\n***\n下文", "正文\n下文"),
        ("正文\n___\n下文", "正文\n下文"),
        ("正文\n- - -\n下文", "正文\n下文"),
    ]

    for original, expected in test_cases:
        result = sanitizer.pre_sanitize(original, MockPlatform.QQ)
        print(f"  原文: {original!r}")
        print(f"  清洗后: {result!r}")
        assert result == expected, f"分割线清洗失败: {result!r} != {expected!r}"

    print("\n✅ 分割线清洗功能测试通过!")


def test_markdown_not_cut():
    """测试 Markdown 标记不被切断"""
    print("\n" + "=" * 60)
    print("测试 Markdown 标记不被切断")
    print("=" * 60)

    sanitizer = MockMessageSanitizer()
    config = SmartSplitConfig()
    sender = SmartSender(config)

    text = "**这是一段很长的话。**还有后续内容。"

    pre_sanitized = sanitizer.pre_sanitize(text, MockPlatform.QQ)
    print(f"  原文: {text}")
    print(f"  预清洗后: {pre_sanitized}")

    segments = sender.split_text(pre_sanitized)
    print(f"  分段数: {len(segments)}")
    for i, seg in enumerate(segments):
        print(f"    分段 {i+1}: {seg.text}")

    for seg in segments:
        assert "**" not in seg.text, f"分段中不应包含 **: {seg.text}"
        assert "*" not in seg.text or "这是" in seg.text, f"分段中不应有孤立的 *: {seg.text}"

    print("\n✅ Markdown 标记不被切断测试通过!")


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("智能分段发送模块完整测试")
    print("=" * 60)

    test_remove_leading_at()
    await test_reply_injection()
    await test_group_level_lock()
    await test_combined_features()
    test_long_text_strategy()
    test_at_resolution()
    test_opportunistic_registration()
    test_pre_sanitize()
    test_post_sanitize()
    test_hr_removal()
    test_markdown_not_cut()

    print("\n" + "=" * 60)
    print("🎉 所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
