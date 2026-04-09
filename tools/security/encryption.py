# tools/security/encryption.py
"""
Scriptor 加密工具模块

提供记忆内容加密功能，保护用户隐私数据
"""

import base64
from typing import Optional

try:
    from cryptography.fernet import Fernet

    FERNET_AVAILABLE = True
except ImportError:
    FERNET_AVAILABLE = False
    Fernet = None

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class MemoryEncryption:
    """
    记忆内容加密器

    使用 Fernet 对称加密算法，保护记忆内容隐私
    """

    _instance: Optional["MemoryEncryption"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._cipher: Optional[Fernet] = None
        self._enabled: bool = False
        self._initialized = True

    def initialize(self, encryption_key: Optional[str] = None, enabled: bool = False):
        """
        初始化加密器

        Args:
            encryption_key: 加密密钥（Base64 编码的 Fernet 密钥）
            enabled: 是否启用加密
        """
        if not FERNET_AVAILABLE:
            logger.warning("[Scriptor] cryptography 库未安装，记忆加密功能不可用")
            self._enabled = False
            return

        self._enabled = enabled

        if not enabled:
            logger.info("[Scriptor] 记忆加密功能已禁用")
            return

        if not encryption_key:
            logger.warning("[Scriptor] 未提供加密密钥，记忆加密功能已禁用")
            self._enabled = False
            return

        try:
            self._cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
            logger.info("[Scriptor] 记忆加密功能已启用")
        except Exception as e:
            logger.error(f"[Scriptor] 初始化加密器失败: {e}")
            self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """检查加密功能是否启用"""
        return self._enabled and self._cipher is not None

    def encrypt(self, content: str) -> str:
        """
        加密内容

        Args:
            content: 原文内容

        Returns:
            加密后的内容（Base64 编码）
        """
        if not self.is_enabled:
            return content

        try:
            encrypted = self._cipher.encrypt(content.encode("utf-8"))
            return base64.b64encode(encrypted).decode("utf-8")
        except Exception as e:
            logger.error(f"[Scriptor] 加密内容失败: {e}")
            return content

    def decrypt(self, encrypted_content: str) -> str:
        """
        解密内容

        Args:
            encrypted_content: 加密后的内容（Base64 编码）

        Returns:
            解密后的原文内容
        """
        if not self.is_enabled:
            return encrypted_content

        try:
            encrypted_bytes = base64.b64decode(encrypted_content.encode("utf-8"))
            decrypted = self._cipher.decrypt(encrypted_bytes)
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"[Scriptor] 解密内容失败: {e}")
            return encrypted_content

    @staticmethod
    def generate_key() -> str:
        """
        生成新的加密密钥

        Returns:
            Base64 编码的 Fernet 密钥
        """
        if not FERNET_AVAILABLE:
            raise RuntimeError("cryptography 库未安装，无法生成加密密钥")

        return Fernet.generate_key().decode("utf-8")

    @staticmethod
    def is_available() -> bool:
        """检查加密功能是否可用"""
        return FERNET_AVAILABLE


_encryption_instance: Optional[MemoryEncryption] = None


def get_memory_encryption() -> MemoryEncryption:
    """获取加密器单例"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = MemoryEncryption()
    return _encryption_instance


def initialize_encryption(encryption_key: Optional[str] = None, enabled: bool = False):
    """初始化加密器"""
    encryption = get_memory_encryption()
    encryption.initialize(encryption_key, enabled)
    return encryption
