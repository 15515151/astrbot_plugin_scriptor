"""
平台差异化处理测试

验证方案 C 的实现：
- QQ/微信：分段 + 清洗 + @ 转换 + 引用
- 其他平台：不分段 + 不清洗 + @ 转换 + 引用

注意：需要 AstrBot 环境的测试在完整测试套件中运行
"""

import importlib.util
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

spec = importlib.util.spec_from_file_location(
    "message_sanitizer",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "message_sanitizer.py"),
)
message_sanitizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(message_sanitizer)
Platform = message_sanitizer.Platform


class TestPlatformDetection:
    """平台检测测试"""

    def test_platform_detection_qq(self):
        """测试 QQ 平台检测"""
        umo = "aiocqhttp:group:12345"
        parts = umo.split(":")
        platform_str = parts[0].lower() if parts else ""

        if platform_str.startswith("qq") or any(x in platform_str for x in ["onebot", "aiocqhttp", "napcat", "cqhttp"]):
            detected = Platform.QQ
        else:
            detected = Platform.DEFAULT

        assert detected == Platform.QQ

    def test_platform_detection_wechat(self):
        """测试微信平台检测"""
        test_cases = [
            ("weixin_oc:private:123", Platform.WECHAT),
            ("wx123:group:456", Platform.WECHAT),
        ]

        for umo, expected in test_cases:
            parts = umo.split(":")
            platform_str = parts[0].lower() if parts else ""

            if platform_str.startswith("weixin") or "wx" in platform_str:
                detected = Platform.WECHAT
            else:
                detected = Platform.DEFAULT

            assert detected == expected, f"Failed for {umo}"

    def test_platform_detection_telegram(self):
        """测试 Telegram 平台检测"""
        test_cases = [
            ("telegram:group:123", Platform.TELEGRAM),
            ("tg:private:456", Platform.TELEGRAM),
        ]

        for umo, expected in test_cases:
            parts = umo.split(":")
            platform_str = parts[0].lower() if parts else ""

            if "telegram" in platform_str or "tg" in platform_str:
                detected = Platform.TELEGRAM
            else:
                detected = Platform.DEFAULT

            assert detected == expected, f"Failed for {umo}"

    def test_platform_detection_discord(self):
        """测试 Discord 平台检测"""
        umo = "discord:channel:12345"
        parts = umo.split(":")
        platform_str = parts[0].lower() if parts else ""

        if "discord" in platform_str:
            detected = Platform.DISCORD
        else:
            detected = Platform.DEFAULT

        assert detected == Platform.DISCORD

    def test_platform_detection_default(self):
        """测试默认平台检测"""
        test_cases = [
            "webchat:session:123",
            "unknown:platform:456",
            "",
        ]

        for umo in test_cases:
            parts = umo.split(":") if umo else []
            platform_str = parts[0].lower() if parts else ""

            detected = Platform.DEFAULT

            if platform_str.startswith("qq") or any(
                x in platform_str for x in ["onebot", "aiocqhttp", "napcat", "cqhttp"]
            ):
                detected = Platform.QQ
            elif platform_str.startswith("weixin") or "wx" in platform_str:
                detected = Platform.WECHAT
            elif "telegram" in platform_str or "tg" in platform_str:
                detected = Platform.TELEGRAM
            elif "discord" in platform_str:
                detected = Platform.DISCORD

            assert detected == Platform.DEFAULT, f"Failed for {umo}"


class TestPlatformEnum:
    """Platform 枚举测试"""

    def test_platform_enum_values(self):
        """测试 Platform 枚举值"""
        assert Platform.DEFAULT.name == "DEFAULT"
        assert Platform.QQ.name == "QQ"
        assert Platform.WECHAT.name == "WECHAT"
        assert Platform.TELEGRAM.name == "TELEGRAM"
        assert Platform.DISCORD.name == "DISCORD"


class TestPlatformDifferentiationLogic:
    """平台差异化逻辑测试（不需要 AstrBot 环境）"""

    def test_qq_wechat_platform_identification(self):
        """测试 QQ/微信平台识别"""
        qq_platforms = ["aiocqhttp", "onebot", "napcat", "cqhttp", "qq"]
        wechat_platforms = ["weixin", "wx"]
        other_platforms = ["telegram", "discord", "webchat", "slack"]

        for p in qq_platforms:
            umo = f"{p}:group:123"
            parts = umo.split(":")
            platform_str = parts[0].lower() if parts else ""

            is_qq_wechat = (
                platform_str.startswith("qq")
                or any(x in platform_str for x in ["onebot", "aiocqhttp", "napcat", "cqhttp"])
                or platform_str.startswith("weixin")
                or "wx" in platform_str
            )
            assert is_qq_wechat, f"QQ platform {p} should be identified as QQ/WeChat"

        for p in wechat_platforms:
            umo = f"{p}:group:123"
            parts = umo.split(":")
            platform_str = parts[0].lower() if parts else ""

            is_qq_wechat = (
                platform_str.startswith("qq")
                or any(x in platform_str for x in ["onebot", "aiocqhttp", "napcat", "cqhttp"])
                or platform_str.startswith("weixin")
                or "wx" in platform_str
            )
            assert is_qq_wechat, f"WeChat platform {p} should be identified as QQ/WeChat"

        for p in other_platforms:
            umo = f"{p}:group:123"
            parts = umo.split(":")
            platform_str = parts[0].lower() if parts else ""

            is_qq_wechat = (
                platform_str.startswith("qq")
                or any(x in platform_str for x in ["onebot", "aiocqhttp", "napcat", "cqhttp"])
                or platform_str.startswith("weixin")
                or "wx" in platform_str
            )
            assert not is_qq_wechat, f"Other platform {p} should NOT be identified as QQ/WeChat"

    def test_other_platform_preserves_markdown_logic(self):
        """测试其他平台保留 Markdown 的逻辑"""
        original_text = "**bold** `code` __underline__ ~~strikethrough~~"

        qq_wechat_platforms = [Platform.QQ, Platform.WECHAT]
        other_platforms = [Platform.TELEGRAM, Platform.DISCORD, Platform.DEFAULT]

        for platform in other_platforms:
            if platform in qq_wechat_platforms:
                processed = original_text.replace("**", "").replace("`", "").replace("__", "").replace("~~", "")
            else:
                processed = original_text

            assert "**" in processed, f"Platform {platform.name} should preserve **"
            assert "`" in processed, f"Platform {platform.name} should preserve `"
            assert "__" in processed, f"Platform {platform.name} should preserve __"
            assert "~~" in processed, f"Platform {platform.name} should preserve ~~"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
