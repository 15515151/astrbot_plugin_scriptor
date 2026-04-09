# tests/test_backup_manager.py
"""备份管理器测试"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.storage.backup_manager import BackupManager


@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        profiles_dir = data_dir / "profiles"
        groups_dir = data_dir / "groups"
        profiles_dir.mkdir()
        groups_dir.mkdir()

        (profiles_dir / "user1.md").write_text("# User 1 Memory", encoding="utf-8")
        (profiles_dir / "user2.md").write_text("# User 2 Memory", encoding="utf-8")
        (groups_dir / "group1.md").write_text("# Group 1 Memory", encoding="utf-8")

        yield data_dir


@pytest.fixture
def backup_manager(temp_data_dir):
    """创建备份管理器实例"""
    return BackupManager(temp_data_dir, max_backups=3)


class TestBackupCreation:
    """备份创建测试"""

    def test_create_backup_success(self, backup_manager):
        """测试创建备份 - 成功"""
        backup_path = backup_manager.create_backup()

        assert backup_path.exists()
        assert (backup_path / "profiles").exists()
        assert (backup_path / "groups").exists()
        assert (backup_path / "metadata.json").exists()

    def test_create_backup_with_name(self, backup_manager):
        """测试创建备份 - 指定名称"""
        backup_path = backup_manager.create_backup(name="my_backup")

        assert backup_path.name == "my_backup"
        assert backup_path.exists()

    def test_create_backup_different_timestamps(self, backup_manager):
        """测试创建备份 - 不同时间戳"""

        backup1 = backup_manager.create_backup(name="backup_first")
        backup2 = backup_manager.create_backup(name="backup_second")

        assert backup1 != backup2
        assert backup1.name != backup2.name

    def test_create_backup_metadata(self, backup_manager):
        """测试创建备份 - 元数据正确"""
        backup_path = backup_manager.create_backup()

        metadata_file = backup_path / "metadata.json"
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        assert "name" in metadata
        assert "created_at" in metadata
        assert "profiles_count" in metadata
        assert "groups_count" in metadata


class TestBackupRestoration:
    """备份恢复测试"""

    def test_restore_backup_success(self, backup_manager, temp_data_dir):
        """测试恢复备份 - 成功"""
        backup_path = backup_manager.create_backup(name="restore_test")

        original_content = (temp_data_dir / "profiles" / "user1.md").read_text(encoding="utf-8")

        (temp_data_dir / "profiles" / "user1.md").write_text("# Modified", encoding="utf-8")

        result = backup_manager.restore_backup("restore_test")

        assert result is True
        restored_content = (temp_data_dir / "profiles" / "user1.md").read_text(encoding="utf-8")
        assert restored_content == original_content

    def test_restore_backup_not_found(self, backup_manager):
        """测试恢复备份 - 备份不存在"""
        result = backup_manager.restore_backup("nonexistent_backup")
        assert result is False

    def test_restore_backup_preserves_structure(self, backup_manager, temp_data_dir):
        """测试恢复备份 - 保留目录结构"""
        backup_path = backup_manager.create_backup(name="structure_test")

        backup_manager.restore_backup("structure_test")

        assert (temp_data_dir / "profiles").exists()
        assert (temp_data_dir / "groups").exists()


class TestBackupCleanup:
    """备份清理测试"""

    def test_cleanup_old_backups(self, backup_manager):
        """测试清理旧备份"""
        for i in range(5):
            backup_manager.create_backup(name=f"backup_{i}")

        backup_manager._cleanup_old_backups()

        remaining = list(backup_manager.backup_dir.iterdir())
        assert len(remaining) <= 3

    def test_max_backups_respected(self, backup_manager):
        """测试最大备份数量限制"""
        for i in range(6):
            backup_manager.create_backup(name=f"extra_backup_{i}")

        backup_count = len([d for d in backup_manager.backup_dir.iterdir() if d.is_dir()])
        assert backup_count <= 3

    def test_cleanup_preserves_recent(self, backup_manager):
        """测试清理保留最近备份"""
        for i in range(4):
            backup_manager.create_backup(name=f"recent_{i}")

        backup_manager._cleanup_old_backups()

        recent_backup = backup_manager.backup_dir / "recent_3"
        assert recent_backup.exists()


class TestBackupList:
    """备份列表测试"""

    def test_list_backups(self, backup_manager):
        """测试列出备份"""
        backup_manager.create_backup(name="list_test_1")
        backup_manager.create_backup(name="list_test_2")

        backups = backup_manager.list_backups()

        assert len(backups) >= 2
        names = [b["name"] for b in backups]
        assert "list_test_1" in names
        assert "list_test_2" in names

    def test_list_backups_empty(self, backup_manager):
        """测试列出备份 - 无备份"""
        backups = backup_manager.list_backups()
        assert isinstance(backups, list)


class TestBackupMetadata:
    """备份元数据测试"""

    def test_list_backups_contains_info(self, backup_manager):
        """测试列出备份包含信息"""
        backup_manager.create_backup(name="info_test")

        backups = backup_manager.list_backups()
        assert len(backups) >= 1

        info_test = next((b for b in backups if b.get("name") == "info_test"), None)
        assert info_test is not None
        assert "created_at" in info_test
        assert "profiles_count" in info_test

    def test_list_backups_not_found(self, backup_manager):
        """测试列出备份 - 过滤不存在"""
        backup_manager.create_backup(name="test1")

        backups = backup_manager.list_backups()
        not_found = [b for b in backups if b.get("name") == "nonexistent"]
        assert len(not_found) == 0


class TestBackupEdgeCases:
    """备份边界情况测试"""

    def test_create_backup_empty_data_dir(self, backup_manager, temp_data_dir):
        """测试创建备份 - 空数据目录"""
        (temp_data_dir / "profiles" / "user1.md").unlink()
        (temp_data_dir / "groups" / "group1.md").unlink()

        backup_path = backup_manager.create_backup()

        assert backup_path.exists()
        backups = backup_manager.list_backups()
        assert any("profiles_count" in b for b in backups)

    def test_backup_with_special_characters_in_name(self, backup_manager):
        """测试备份名称包含特殊字符"""
        backup_path = backup_manager.create_backup(name="backup_with_special_!@#$")
        assert backup_path.exists()

    def test_concurrent_backup_creation(self, backup_manager):
        """测试并发创建备份"""
        import threading

        results = []

        def create_backup_thread(name):
            path = backup_manager.create_backup(name=name)
            results.append(path)

        threads = [threading.Thread(target=create_backup_thread, args=(f"thread_{i}",)) for i in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 3
