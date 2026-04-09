# tools/security/sanitizer.py
"""安全工具模块 - 分层防御架构

三层安全机制：
1. 存储层 (Storage): sanitize_id(), sanitize_filename() - ID/文件名合法化，防目录穿越
2. 工具层 (Tool): validate_sandbox_path() - 沙盒隔离，允许复杂路径
3. 网络层 (Network): validate_url() - URL 白名单，防 SSRF 攻击

设计原则：
- ID 由平台官方生成，用户无法篡改，无注入风险。只做字符过滤（替换非法文件系统字符），不做安全拦截。
- 用户名/昵称等用户可控输入的防注入，在上层 Prompt 层面处理。
"""

import hashlib
import re
from pathlib import Path
from typing import Tuple

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-.*]+$")


# =============================================================================
# 第一层：存储层 - ID 和文件名脱敏（用于目录名、数据库键）
# =============================================================================


def sanitize_log_message(message: str, max_content_length: int = 100) -> str:
    """
    对日志消息进行脱敏处理，防止敏感信息泄露

    Args:
        message: 原始日志消息
        max_content_length: 内容最大显示长度

    Returns:
        脱敏后的消息
    """
    if not message:
        return ""

    sensitive_patterns = [
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]+)', r"api_key=***"),
        (r'token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]+)', r"token=***"),
        (r'password["\']?\s*[:=]\s*["\']?([^\s"\']+)', r"password=***"),
        (r"bearer\s+([a-zA-Z0-9_\-\.]+)", r"bearer ***"),
    ]

    result = message
    for pattern, replacement in sensitive_patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    if len(result) > max_content_length:
        result = result[:max_content_length] + "..."

    return result


ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_id(identifier: str, default: str = "unknown") -> str:
    """
    将 ID 转换为合法的文件/目录名字符串。

    设计原则：只做字符过滤，不做安全拦截。
    - ID 由平台官方生成，用户无法篡改，无注入风险。
    - 唯一需要处理的是操作系统不允许出现在文件名中的字符。

    适用场景：生成目录名、数据库 Collection 名称、文件名前缀

    Args:
        identifier: 原始 ID
        default: 非法输入时的默认值

    Returns:
        合法的文件名安全的 ID
    """
    if not identifier or not isinstance(identifier, str):
        return default

    if identifier in ("*", "unknown", "all"):
        return identifier

    sanitized = ILLEGAL_FILENAME_CHARS.sub("_", identifier)

    if not sanitized or not sanitized.strip():
        return default

    return sanitized


def sanitize_filename(filename: str, default: str = "unknown") -> str:
    """
    安全清洗文件名，保留扩展名用于识别文件类型

    适用场景：用户上传的文件名、AI 生成的文件名

    Args:
        filename: 原始文件名
        default: 校验失败时的默认值

    Returns:
        安全的文件名（去除路径分隔符，保留扩展名）
    """
    if not filename or not isinstance(filename, str):
        return default

    if ".." in filename or "/" in filename or "\\" in filename:
        filename = Path(filename).name

    if SAFE_FILENAME_PATTERN.match(filename):
        return filename

    sanitized = f"sanitized_{hashlib.md5(filename.encode()).hexdigest()[:8]}.txt"
    logger.warning(f"[Scriptor] 检测到非法文件名 '{filename}'，已清洗为 '{sanitized}'")
    return sanitized


# =============================================================================
# 第二层：工具层 - 沙盒路径验证（允许复杂路径，但防止越权）
# =============================================================================


class SandboxEscapeError(PermissionError):
    """沙盒越权异常"""

    pass


def validate_sandbox_path(requested_path: str, sandbox_root: Path) -> Path:
    """
    验证路径是否在沙盒范围内（核心安全函数）

    允许 AI 传入包含斜杠、子目录的复杂路径，但通过 Path.resolve()
    解析后验证是否仍在沙盒根目录内。

    适用场景：file_read, file_write, file_edit, glob_search 等文件操作工具

    Args:
        requested_path: AI 传入的路径（可以是相对路径或包含 ../ 的路径）
        sandbox_root: 沙盒根目录（如 profiles/uid/working 或 groups/gid/working）

    Returns:
        解析后的安全绝对路径

    Raises:
        SandboxEscapeError: 当路径试图越权访问沙盒外文件时
    """
    if not requested_path:
        raise SandboxEscapeError("路径不能为空")

    sandbox_root = Path(sandbox_root).resolve()

    requested = Path(requested_path).expanduser()

    if requested.is_absolute():
        final_path = requested.resolve()
    else:
        final_path = (sandbox_root / requested).resolve()

    sandbox_root_str = str(sandbox_root)
    final_path_str = str(final_path)

    if not final_path_str.startswith(sandbox_root_str):
        logger.warning(
            f"[Scriptor] 安全拦截：路径越权访问。" f"请求: {requested_path}, 沙盒: {sandbox_root}, 解析后: {final_path}"
        )
        raise SandboxEscapeError(
            f"安全限制：无法访问沙盒外文件 '{requested_path}'。" f"只允许在 '{sandbox_root.name}' 目录内操作。"
        )

    return final_path


# =============================================================================
# 第三层：网络层 - URL 验证（防止 SSRF 攻击）
# =============================================================================

DANGEROUS_URL_PATTERNS = [
    r"^(https?|ftps?)://[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+",  # IP 地址（防止内网攻击）
    r"^(https?|ftps?)://localhost",  # localhost
    r"^(https?|ftps?)://127\.",  # 127.x.x.x
    r"^(https?|ftps?)://10\.",  # 10.x.x.x (内网 A 类)
    r"^(https?|ftps?)://172\.(1[6-9]|2[0-9]|3[0-1])\.",  # 172.16-31.x.x (内网 B 类)
    r"^(https?|ftps?)://192\.168\.",  # 192.168.x.x (内网 C 类)
    r"^(https?|ftps?)://0\.",  # 0.0.0.0
    r"@",  # URL 中的认证信息可能是钓鱼尝试
]

ALLOWED_PROTOCOL = frozenset({"http", "https", "ftp", "ftps"})


def validate_url(url: str, allow_internal: bool = False) -> Tuple[bool, str]:
    """
    验证 URL 是否安全（不清洗，只验证）

    适用场景：OpenClaw 网络工具、WebSearch 工具

    Args:
        url: 待验证的 URL
        allow_internal: 是否允许访问内网地址（默认 False，仅允许公网）

    Returns:
        (is_safe, reason) - is_safe 为 True 表示安全，reason 为原因说明
    """
    if not url or not isinstance(url, str):
        return False, "URL 不能为空"

    url_lower = url.lower().strip()

    for pattern in DANGEROUS_URL_PATTERNS:
        if re.match(pattern, url_lower):
            if not allow_internal:
                return False, f"安全限制：不允许访问内网地址 '{url}'"
            return False, f"警告：检测到内网地址 '{url}'"

    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)

        if not parsed.scheme:
            return False, "URL 缺少协议（如 https://）"

        if parsed.scheme not in ALLOWED_PROTOCOL:
            return False, f"安全限制：仅允许 http/https/ftp/ftps 协议，不支持 '{parsed.scheme}'"

        if not parsed.netloc:
            return False, "URL 缺少域名（如 google.com）"

        return True, "URL 验证通过"

    except Exception as e:
        return False, f"URL 解析失败: {e!s}"


# =============================================================================
# 导出汇总
# =============================================================================

__all__ = [
    "SandboxEscapeError",
    "sanitize_filename",
    "sanitize_id",
    "sanitize_log_message",
    "validate_sandbox_path",
    "validate_url",
]
