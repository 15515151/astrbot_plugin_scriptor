# core/smart_sender.py
"""
智能分段发送模块
功能：
1. 正则表达式智能分段
2. 拟人化打字延迟
3. 会话级并发锁（防止消息穿插）
4. 保护社交组件（@ 提及不被切断）
"""

import asyncio
import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


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

        logger.info(f"[SmartSender] 初始化完成，启用状态: {config.enabled}, 长文本阈值: {config.long_text_threshold}")

    def _compile_regexes(self):
        """编译正则表达式"""
        try:
            self._compiled_split_regex = re.compile(self.config.split_regex)
            logger.debug(f"[SmartSender] 分段正则编译成功: {self.config.split_regex}")
        except re.error as e:
            logger.error(f"[SmartSender] 分段正则编译失败: {e}，使用默认正则")
            self._compiled_split_regex = re.compile(r".*?[。？！~…\n]+|.+$")

        if self.config.cleanup_regex:
            try:
                self._compiled_cleanup_regex = re.compile(self.config.cleanup_regex)
                logger.debug(f"[SmartSender] 清理正则编译成功: {self.config.cleanup_regex}")
            except re.error as e:
                logger.error(f"[SmartSender] 清理正则编译失败: {e}")
                self._compiled_cleanup_regex = None
        else:
            self._compiled_cleanup_regex = None

        if self.config.long_text_pattern:
            try:
                self._compiled_long_text_regex = re.compile(self.config.long_text_pattern)
                logger.debug(f"[SmartSender] 长文本分段正则编译成功: {self.config.long_text_pattern}")
            except re.error as e:
                logger.error(f"[SmartSender] 长文本分段正则编译失败: {e}")
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
        """
        移除文本开头的针对目标用户的 @ 提及

        Args:
            text: 原始文本
            target_uid: 目标用户的逻辑 ID（如 user_123）

        Returns:
            清洗后的文本
        """
        if not target_uid or not text:
            return text

        # 匹配开头的 [@任意字符(UID:target_uid)] 及其后的空白
        pattern = rf"^\[@[^\]]*?\(UID:{re.escape(target_uid)}\)\]\s*"
        cleaned = re.sub(pattern, "", text)

        if cleaned != text:
            logger.debug(f"[SmartSender] 已移除首段开头的 @ 提及: target_uid={target_uid}")

        return cleaned

    def _contains_table(self, text: str) -> bool:
        """检测文本是否包含 Markdown 表格

        表格特征：
        1. 包含 |---| 或 |:---| 这样的分隔行
        2. 或者多行以 | 开头和结尾
        """
        if "|---" in text or "|:--" in text or "|---|" in text:
            return True

        lines = text.split("\n")
        table_lines = 0
        for line in lines:
            line = line.strip()
            if line.startswith("|") and line.endswith("|"):
                table_lines += 1
                if table_lines >= 2:
                    return True

        return False

    def split_text(self, text: str, sanitizer=None, platform=None) -> List[Segment]:
        """
        将文本智能分段（支持预清洗、长短文双策略和碎片检查）

        Args:
            text: 原始文本
            sanitizer: MessageSanitizer 实例（用于预清洗和碎片检查）
            platform: 平台类型（Platform 枚举）

        Returns:
            分段列表
        """
        if not text or not text.strip():
            return []

        segments: List[Segment] = []

        if sanitizer and platform:
            text = sanitizer.pre_sanitize(text, platform)
            if not text or not text.strip():
                return []

        if self._contains_table(text):
            if sanitizer and platform:
                text = sanitizer.post_sanitize(text, platform)
            segments.append(Segment(text=text))
            if logger.isEnabledFor(10):
                logger.debug(f"[SmartSender] 检测到表格，跳过分段: 长度={len(text)}")
            return segments

        text_length = len(text)
        is_long_text = text_length >= self.config.long_text_threshold

        if is_long_text and self._compiled_long_text_regex:
            raw_segments = self._compiled_long_text_regex.split(text)
            if logger.isEnabledFor(10):
                logger.debug(
                    f"[SmartSender] 长文本分段策略: 长度={text_length}, 阈值={self.config.long_text_threshold}"
                )
        else:
            raw_segments = self._compiled_split_regex.findall(text)
            if is_long_text:
                logger.debug("[SmartSender] 长文本但无长文本正则，使用常规分段")

        for seg_text in raw_segments:
            if not seg_text:
                continue

            cleaned_text = seg_text

            if self._compiled_cleanup_regex:
                cleaned_text = self._compiled_cleanup_regex.sub("", cleaned_text)

            if sanitizer and platform:
                cleaned_text = sanitizer.post_sanitize(cleaned_text, platform)

            if cleaned_text and cleaned_text.strip():
                segments.append(Segment(text=cleaned_text))

        if self.config.enabled and logger.isEnabledFor(10):
            logger.debug(
                f"[SmartSender] 文本分段完成: 原始长度={len(text)}, 分段数={len(segments)}, 长文本={'是' if is_long_text else '否'}"
            )

        return segments

    def calculate_delay(self, segment: Segment) -> float:
        """
        计算发送延迟

        Args:
            segment: 分段数据

        Returns:
            延迟时间（秒）
        """
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
        sanitizer=None,
        platform=None,
        reply_to_id: str = None,
        target_uid: str = None,
        debug_mode: bool = False,
    ) -> bool:
        """
        智能分段发送消息（支持预清洗、碎片检查和首段引用）

        Args:
            text: 要发送的文本（原始 Markdown 文本）
            session_id: 会话ID（用于并发锁）
            send_callback: 发送回调函数，签名为 async def callback(message_chain) -> bool
            convert_at_callback: @ 转换回调函数，签名为 async def callback(text) -> message_chain
            sanitizer: MessageSanitizer 实例（用于预清洗和碎片检查）
            platform: 平台类型（Platform 枚举）
            reply_to_id: 原消息 ID（用于构建 Reply 组件，仅首段生效）
            target_uid: 提问者的逻辑 ID（用于清洗首段开头的 @ 提及）
            debug_mode: 是否输出调试日志

        Returns:
            是否发送成功
        """
        if not self.config.enabled:
            if sanitizer and platform:
                text = sanitizer.pre_sanitize(text, platform)

            if target_uid:
                text = self.remove_leading_at(text, target_uid)

            if convert_at_callback:
                message_chain = await convert_at_callback(text)
            else:
                message_chain = text

            if reply_to_id and message_chain is not None:
                try:
                    from astrbot.api.message_components import Reply

                    if hasattr(message_chain, "chain"):
                        message_chain.chain.insert(0, Reply(id=reply_to_id))
                        if debug_mode:
                            logger.info(f"[SmartSender] 首段引用注入: reply_to_id={reply_to_id}")
                except Exception as e:
                    logger.warning(f"[SmartSender] 引用注入失败: {e}")

            return await send_callback(message_chain)

        segments = self.split_text(text, sanitizer, platform)

        if not segments:
            return True

        session_lock = await self._get_session_lock(session_id)

        async with session_lock:
            if debug_mode:
                logger.info(f"[SmartSender] 开始分段发送: 会话={session_id}, 分段数={len(segments)}")

            for i, segment in enumerate(segments):
                try:
                    delay = self.calculate_delay(segment)

                    if debug_mode:
                        logger.info(
                            f"[SmartSender] 发送分段 {i+1}/{len(segments)}: "
                            f"字数={segment.char_count}, 延迟={delay:.2f}s, "
                            f"包含@={'是' if segment.has_at else '否'}"
                        )

                    await asyncio.sleep(delay)

                    segment_text = segment.text

                    # 首段特殊处理：去 @ + 注入引用
                    is_first_segment = i == 0

                    if is_first_segment and target_uid:
                        # 移除首段开头的 @ 提及
                        segment_text = self.remove_leading_at(segment_text, target_uid)

                    if convert_at_callback:
                        message_chain = await convert_at_callback(segment_text)
                    else:
                        message_chain = segment_text

                    # 首段引用注入
                    if is_first_segment and reply_to_id and message_chain is not None:
                        try:
                            from astrbot.api.message_components import Reply

                            if hasattr(message_chain, "chain"):
                                message_chain.chain.insert(0, Reply(id=reply_to_id))
                                if debug_mode:
                                    logger.info(f"[SmartSender] 首段引用注入: reply_to_id={reply_to_id}")
                        except Exception as e:
                            logger.warning(f"[SmartSender] 引用注入失败: {e}")

                    success = await send_callback(message_chain)

                    if not success:
                        logger.warning(f"[SmartSender] 分段 {i+1} 发送失败")
                        return False

                except asyncio.CancelledError:
                    logger.warning(f"[SmartSender] 发送被取消: 会话={session_id}")
                    raise
                except Exception as e:
                    logger.error(f"[SmartSender] 发送分段 {i+1} 时出错: {e}")
                    return False

            if debug_mode:
                logger.info(f"[SmartSender] 分段发送完成: 会话={session_id}")

            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "enabled": self.config.enabled,
            "only_llm": self.config.only_llm,
            "active_sessions": len(self._session_locks),
            "split_regex": self.config.split_regex,
            "typing_speed": self.config.typing_speed,
            "min_delay": self.config.min_delay,
            "max_delay": self.config.max_delay,
            "random_factor": self.config.random_factor,
            "long_text_threshold": self.config.long_text_threshold,
            "long_text_pattern": self.config.long_text_pattern,
        }

    async def cleanup_idle_sessions(self, max_idle_count: int = 100):
        """清理空闲的会话锁"""
        async with self._global_lock:
            if len(self._session_locks) > max_idle_count:
                idle_sessions = [sid for sid, lock in self._session_locks.items() if not lock.locked()]

                for sid in idle_sessions[: len(idle_sessions) - max_idle_count // 2]:
                    del self._session_locks[sid]

                if idle_sessions:
                    logger.debug(f"[SmartSender] 清理空闲会话锁: {len(idle_sessions)} 个")


def create_smart_sender_from_config(config) -> SmartSender:
    """
    从 ScriptorConfig 创建 SmartSender 实例

    Args:
        config: ScriptorConfigPydantic 实例

    Returns:
        SmartSender 实例
    """
    split_config = SmartSplitConfig(
        enabled=config.smart_split_enabled,
        only_llm=config.smart_split_only_llm,
        split_regex=config.smart_split_regex,
        cleanup_regex=config.smart_split_cleanup_regex,
        typing_speed=config.smart_split_typing_speed,
        min_delay=config.smart_split_min_delay,
        max_delay=config.smart_split_max_delay,
        random_factor=config.smart_split_random_factor,
        long_text_threshold=config.smart_split_long_text_threshold,
        long_text_pattern=config.smart_split_long_text_pattern,
    )

    return SmartSender(split_config)
