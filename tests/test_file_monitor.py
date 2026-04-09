# tests/test_file_monitor.py
"""文件监控模块测试"""

from pathlib import Path

import pytest

# 使用包导入方式，兼容相对导入
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.file_monitor import FileChange, FileMonitor
except ImportError:
    from file_monitor import FileChange, FileMonitor


@pytest.fixture
def temp_data_dir(tmp_path):
    """创建临时数据目录"""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    groups_dir = tmp_path / "groups"
    groups_dir.mkdir(exist_ok=True)
    return tmp_path


class TestFileChange:
    """FileChange 数据类测试"""

    def test_create_file_change(self):
        """测试创建文件变更对象"""
        change = FileChange(path=Path("/test/path/file.md"), change_type="created", timestamp=123456789.0)

        assert change.path == Path("/test/path/file.md")
        assert change.change_type == "created"
        assert change.timestamp == 123456789.0

    def test_file_change_equality(self):
        """测试文件变更对象相等性"""
        change1 = FileChange(path=Path("/test/file.md"), change_type="modified", timestamp=1000.0)
        change2 = FileChange(path=Path("/test/file.md"), change_type="modified", timestamp=1000.0)

        assert change1.path == change2.path
        assert change1.change_type == change2.change_type


class TestFileMonitor:
    """FileMonitor 测试"""

    def test_initialization(self, temp_data_dir):
        """测试初始化"""
        changes = []

        def on_change(change):
            changes.append(change)

        monitor = FileMonitor(temp_data_dir, on_change)

        assert monitor.data_dir == temp_data_dir
        assert monitor.on_change == on_change
        assert monitor._is_running is False

    def test_init_file_mtimes(self, temp_data_dir):
        """测试初始化文件时间戳"""
        monitor = FileMonitor(temp_data_dir, lambda x: None)

        test_profile = temp_data_dir / "profiles" / "test_uid"
        test_profile.mkdir()
        test_file = test_profile / "test.md"
        test_file.write_text("test content", encoding="utf-8")

        monitor._init_file_mtimes()

        assert str(test_file) in monitor._file_mtimes
