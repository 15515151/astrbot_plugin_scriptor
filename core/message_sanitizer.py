# core/message_sanitizer.py
"""
消息清洗与错误拦截模块
功能：
1. Markdown 清洗（支持不同平台）
2. 错误检测与拦截（防止底层报错暴露给用户）
3. 文本格式降级

配置已迁移至 tools/config/sanitizer_rules.py
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from tools.config.sanitizer_rules import ERROR_PATTERNS, PLATFORM_RULES, Platform


@dataclass
class SanitizerConfig:
    """清洗器配置"""

    enabled: bool = True

    strip_markdown: bool = True

    intercept_errors: bool = True

    friendly_error_message: str = "抱歉，刚才出了点小问题，请再试一次吧～"

    platform_rules: Dict[Platform, Dict] = field(default_factory=lambda: PLATFORM_RULES)

    error_patterns: List[str] = field(default_factory=lambda: ERROR_PATTERNS.copy())


class MessageSanitizer:
    """消息清洗器"""

    def __init__(self, config: Optional[SanitizerConfig] = None):
        self.config = config or SanitizerConfig()
        self._error_count = 0

    def sanitize(self, text: str, platform: Platform = Platform.DEFAULT) -> Tuple[bool, str]:
        """
        清洗消息

        Args:
            text: 原始文本
            platform: 平台类型

        Returns:
            (is_error, sanitized_text)
            - is_error: 是否检测到错误
            - sanitized_text: 清洗后的文本
        """
        if not self.config.enabled:
            return False, text

        is_error, intercepted = self._detect_and_intercept_error(text)
        if is_error:
            return True, intercepted

        if self.config.strip_markdown:
            text = self._strip_markdown(text, platform)

        return False, text

    def _detect_and_intercept_error(self, text: str) -> Tuple[bool, str]:
        """
        检测并拦截错误

        Returns:
            (is_error, friendly_message)
        """
        if not self.config.intercept_errors:
            return False, text

        for pattern in self.config.error_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self._error_count += 1
                logger.warning(f"[MessageSanitizer] 检测到潜在错误，已拦截 (总数: {self._error_count})")
                logger.debug(f"[MessageSanitizer] 原始内容: {text[:200]}...")
                return True, self.config.friendly_error_message

        return False, text

    def _strip_markdown(self, text: str, platform: Platform) -> str:
        """
        根据平台清洗 Markdown

        Args:
            text: 原始文本
            platform: 平台类型

        Returns:
            清洗后的文本
        """
        rules = self.config.platform_rules.get(platform, self.config.platform_rules[Platform.DEFAULT])

        result = text

        if not rules.get("headers", True):
            result = self._remove_headers(result)

        if not rules.get("bold", True):
            result = self._remove_bold(result)

        if not rules.get("italic", True):
            result = self._remove_italic(result)

        if not rules.get("strikethrough", True):
            result = self._remove_strikethrough(result)

        if not rules.get("code", True):
            result = self._remove_code(result)

        if not rules.get("links", True):
            result = self._remove_links(result)

        if not rules.get("lists", True):
            result = self._remove_lists(result)

        if not rules.get("quotes", True):
            result = self._remove_quotes(result)

        result = self._cleanup_whitespace(result)

        if platform in (Platform.QQ, Platform.WECHAT):
            result = self._remove_extra_blank_lines(result)

        return result

    def _remove_extra_blank_lines(self, text: str) -> str:
        """移除多余的空行（仅用于 QQ/微信）"""
        text = re.sub(r"\n{3,}", "\n", text)
        text = re.sub(r"\n\n+", "\n", text)
        return text.strip()

    def _remove_headers(self, text: str) -> str:
        """移除标题"""
        return re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    def _remove_bold(self, text: str) -> str:
        """移除粗体"""
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"__(.*?)__", r"\1", text)
        return text

    def _remove_italic(self, text: str) -> str:
        """移除斜体"""
        text = re.sub(r"\*(.*?)\*", r"\1", text)
        text = re.sub(r"_(.*?)_", r"\1", text)
        return text

    def _remove_strikethrough(self, text: str) -> str:
        """移除删除线"""
        return re.sub(r"~~(.*?)~~", r"\1", text)

    def _remove_code(self, text: str) -> str:
        """移除代码块和行内代码"""
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`(.*?)`", r"\1", text)
        return text

    def _remove_links(self, text: str) -> str:
        """移除链接，保留链接文本"""
        return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    def _remove_lists(self, text: str) -> str:
        """移除列表标记"""
        text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)
        return text

    def _remove_quotes(self, text: str) -> str:
        """移除引用标记"""
        return re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

    def _remove_hr(self, text: str) -> str:
        """
        移除分割线及其后的换行符

        处理场景：
        - 正文\\n\\n---\\n\\n下文 → 正文\\n\\n下文
        - 正文\\n---\\n下文 → 正文\\n下文
        - ---\\n开头正文 → 开头正文
        - 正文\\n- - -\\n下文 → 正文\\n下文（带空格的分割线）
        """
        text = re.sub(r"(\n)[ \t]*[-*_](?:[ \t]*[-*_]){2,}[ \t]*\n+", r"\1", text)
        text = re.sub(r"^[ \t]*[-*_](?:[ \t]*[-*_]){2,}[ \t]*\n+", "", text)
        return text

    def pre_sanitize(self, text: str, platform: Platform = Platform.DEFAULT) -> str:
        """
        预清洗：在分段前执行，去除 Markdown 标记但保留换行结构

        仅对 QQ 和微信平台执行，其他平台直接返回原文

        Args:
            text: 原始文本
            platform: 平台类型

        Returns:
            清洗后的文本（保留换行符）
        """
        if platform not in (Platform.QQ, Platform.WECHAT):
            return text

        if not self.config.enabled or not self.config.strip_markdown:
            return text

        result = text

        rules = self.config.platform_rules.get(platform, self.config.platform_rules[Platform.DEFAULT])

        if not rules.get("code", True):
            result = self._remove_code(result)

        if not rules.get("headers", True):
            result = self._remove_headers(result)

        result = self._remove_hr(result)

        if not rules.get("bold", True):
            result = self._remove_bold(result)

        if not rules.get("italic", True):
            result = self._remove_italic(result)

        if not rules.get("strikethrough", True):
            result = self._remove_strikethrough(result)

        if not rules.get("links", True):
            result = self._remove_links(result)

        if not rules.get("lists", True):
            result = self._remove_lists(result)

        if not rules.get("quotes", True):
            result = self._remove_quotes(result)

        return result

    def post_sanitize(self, text: str, platform: Platform = Platform.DEFAULT) -> str:
        """
        后清洗：在分段后执行，检查并清理碎片

        如果清洗后只剩孤立的 Markdown 符号，返回空字符串

        Args:
            text: 清洗后的文本
            platform: 平台类型

        Returns:
            清理后的文本，如果是碎片则返回空字符串
        """
        if platform not in (Platform.QQ, Platform.WECHAT):
            return text

        stripped = text.strip()

        if not stripped:
            return ""

        markdown_only_pattern = r"^[*_~>`#\-\s]+$"
        if re.match(markdown_only_pattern, stripped):
            logger.debug(f"[MessageSanitizer] 检测到碎片，已丢弃: {stripped!r}")
            return ""

        return text

    def _cleanup_whitespace(self, text: str) -> str:
        """清理空白字符"""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "error_count": self._error_count,
            "enabled": self.config.enabled,
            "strip_markdown": self.config.strip_markdown,
            "intercept_errors": self.config.intercept_errors,
        }


_sanitizer_instance: Optional[MessageSanitizer] = None


def get_sanitizer() -> MessageSanitizer:
    """获取全局清洗器实例"""
    global _sanitizer_instance
    if _sanitizer_instance is None:
        _sanitizer_instance = MessageSanitizer()
    return _sanitizer_instance


def set_sanitizer(sanitizer: MessageSanitizer):
    """设置全局清洗器实例"""
    global _sanitizer_instance
    _sanitizer_instance = sanitizer
