"""
Scriptor 加密功能测试

测试记忆内容加密功能
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.security.encryption import MemoryEncryption, get_memory_encryption


class TestMemoryEncryption:
    """加密器测试"""

    @pytest.fixture
    def encryption(self):
        """创建加密器实例"""
        enc = MemoryEncryption()
        enc._initialized = True
        enc._cipher = None
        enc._enabled = False
        return enc

    def test_initialization_disabled(self, encryption):
        """测试初始化为禁用状态"""
        encryption.initialize(enabled=False)

        assert not encryption.is_enabled

    def test_initialization_without_key(self, encryption):
        """测试没有密钥时初始化"""
        encryption.initialize(encryption_key=None, enabled=True)

        assert not encryption.is_enabled

    @patch("tools.security.encryption.FERNET_AVAILABLE", True)
    @patch("tools.security.encryption.Fernet")
    def test_initialization_with_key(self, mock_fernet, encryption):
        """测试有密钥时初始化"""
        mock_fernet_instance = MagicMock()
        mock_fernet.return_value = mock_fernet_instance

        test_key = "test_encryption_key_12345678901234567890123456789012"
        encryption.initialize(encryption_key=test_key, enabled=True)

        assert encryption.is_enabled

    def test_encrypt_when_disabled(self, encryption):
        """测试禁用时加密返回原文"""
        encryption._enabled = False

        result = encryption.encrypt("test content")

        assert result == "test content"

    @patch("tools.security.encryption.FERNET_AVAILABLE", True)
    @patch("tools.security.encryption.Fernet")
    def test_encrypt_when_enabled(self, mock_fernet, encryption):
        """测试启用时加密"""
        mock_fernet_instance = MagicMock()
        mock_fernet_instance.encrypt.return_value = b"encrypted_content"
        mock_fernet.return_value = mock_fernet_instance

        test_key = "test_key_12345678901234567890123456789012"
        encryption.initialize(encryption_key=test_key, enabled=True)

        result = encryption.encrypt("test content")

        assert result is not None
        assert isinstance(result, str)

    def test_decrypt_when_disabled(self, encryption):
        """测试禁用时解密返回原文"""
        encryption._enabled = False

        result = encryption.decrypt("encrypted content")

        assert result == "encrypted content"

    @patch("tools.security.encryption.FERNET_AVAILABLE", True)
    @patch("tools.security.encryption.Fernet")
    def test_decrypt_when_enabled(self, mock_fernet, encryption):
        """测试启用时解密"""
        mock_fernet_instance = MagicMock()
        mock_fernet_instance.decrypt.return_value = b"decrypted content"
        mock_fernet.return_value = mock_fernet_instance

        test_key = "test_key_12345678901234567890123456789012"
        encryption.initialize(encryption_key=test_key, enabled=True)

        result = encryption.decrypt("encrypted_content")

        assert result == "decrypted content"

    def test_encrypt_decrypt_roundtrip(self, encryption):
        """测试加密解密往返"""
        encryption._enabled = False

        original = "Hello, World!"
        encrypted = encryption.encrypt(original)
        decrypted = encryption.decrypt(encrypted)

        assert encrypted == original
        assert decrypted == original


class TestEncryptionSingleton:
    """加密器单例测试"""

    def test_get_memory_encryption(self):
        """测试获取加密器单例"""
        enc1 = get_memory_encryption()
        enc2 = get_memory_encryption()

        assert enc1 is enc2


class TestEncryptionAvailability:
    """加密功能可用性测试"""

    def test_is_available_without_fernet(self):
        """测试 Fernet 不可用时"""
        with patch("tools.security.encryption.FERNET_AVAILABLE", False):
            result = MemoryEncryption.is_available()
            assert result == False

    def test_generate_key_without_fernet(self):
        """测试 Fernet 不可用时生成密钥"""
        with patch("tools.security.encryption.FERNET_AVAILABLE", False), pytest.raises(RuntimeError):
            MemoryEncryption.generate_key()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
