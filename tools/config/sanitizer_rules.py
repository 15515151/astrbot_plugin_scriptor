# tools/config/sanitizer_rules.py
"""消息清洗规则配置 - 平台规则与错误模式"""

from enum import Enum


class Platform(Enum):
    DEFAULT = "default"
    QQ = "qq"
    WECHAT = "wechat"
    TELEGRAM = "telegram"
    DISCORD = "discord"


PLATFORM_RULES = {
    Platform.QQ: {
        "bold": False,
        "italic": False,
        "strikethrough": False,
        "code": False,
        "links": False,
        "headers": False,
        "lists": False,
        "quotes": False,
    },
    Platform.WECHAT: {
        "bold": False,
        "italic": False,
        "strikethrough": False,
        "code": False,
        "links": True,
        "headers": False,
        "lists": True,
        "quotes": True,
    },
    Platform.TELEGRAM: {
        "bold": True,
        "italic": True,
        "strikethrough": True,
        "code": True,
        "links": True,
        "headers": True,
        "lists": True,
        "quotes": True,
    },
    Platform.DISCORD: {
        "bold": True,
        "italic": True,
        "strikethrough": True,
        "code": True,
        "links": True,
        "headers": True,
        "lists": True,
        "quotes": True,
    },
    Platform.DEFAULT: {
        "bold": True,
        "italic": True,
        "strikethrough": True,
        "code": True,
        "links": True,
        "headers": True,
        "lists": True,
        "quotes": True,
    },
}


ERROR_PATTERNS = [
    r"Traceback \(most recent call last\)",
    r"File \".*\", line \d+",
    r"Exception:",
    r"Error:",
    r"AttributeError:",
    r"TypeError:",
    r"ValueError:",
    r"KeyError:",
    r"IndexError:",
    r"NameError:",
    r"SyntaxError:",
    r"RuntimeError:",
    r"ImportError:",
    r"ModuleNotFoundError:",
    r"OSError:",
    r"IOError:",
    r"UnicodeDecodeError:",
    r"UnicodeEncodeError:",
    r"ConnectionError:",
    r"TimeoutError:",
    r"RequestException:",
    r"HTTPError:",
    r"Internal Server Error",
    r"500 Internal Server Error",
    r"404 Not Found",
    r"403 Forbidden",
    r"401 Unauthorized",
    r"400 Bad Request",
    r"NoneType",
    r"'NoneType' object has no attribute",
    r"cannot unpack non-iterable",
    r"division by zero",
    r"list index out of range",
    r"string index out of range",
    r"dictionary update sequence element",
    r"missing \d+ required positional argument",
    r"unexpected keyword argument",
    r"positional argument follows keyword argument",
    r"invalid syntax",
    r"indentation error",
    r"tab error",
    r"__thought__",
    r"<think>",
    r"<\/think>",
    r"\[Scriptor-Debug\]",
]
