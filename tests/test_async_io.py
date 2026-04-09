# tests/test_async_io.py
"""异步IO工具测试"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.common.async_io import (
    async_append_text,
    async_read_json,
    async_read_text,
    async_write_json,
    async_write_text,
)


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_json_file(temp_dir):
    """创建临时JSON文件"""
    file_path = temp_dir / "test.json"
    data = {"key": "value", "number": 42, "list": [1, 2, 3]}
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return file_path


@pytest.fixture
def temp_text_file(temp_dir):
    """创建临时文本文件"""
    file_path = temp_dir / "test.txt"
    file_path.write_text("Hello, World!", encoding="utf-8")
    return file_path


class TestAsyncJsonIO:
    """异步JSON读写测试"""

    @pytest.mark.asyncio
    async def test_async_read_json_success(self, temp_json_file):
        """测试异步读取JSON - 成功"""
        result = await async_read_json(temp_json_file)

        assert result is not None
        assert result["key"] == "value"
        assert result["number"] == 42
        assert result["list"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_async_read_json_with_default(self):
        """测试异步读取JSON - 文件不存在返回默认值"""
        result = await async_read_json(Path("/nonexistent/file.json"), default={"default": True})

        assert result == {"default": True}

    @pytest.mark.asyncio
    async def test_async_read_json_invalid_file(self):
        """测试异步读取JSON - 无效文件"""
        invalid_file = Path(tempfile.gettempdir()) / "invalid_json_12345.json"
        invalid_file.write_text("{ invalid json", encoding="utf-8")

        try:
            result = await async_read_json(invalid_file, default=None)
            assert result is None
        finally:
            if invalid_file.exists():
                invalid_file.unlink()

    @pytest.mark.asyncio
    async def test_async_write_json_success(self, temp_dir):
        """测试异步写入JSON - 成功"""
        file_path = temp_dir / "output.json"
        data = {"name": "test", "value": 123}

        await async_write_json(file_path, data)

        assert file_path.exists()
        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    @pytest.mark.asyncio
    async def test_async_write_json_nested(self, temp_dir):
        """测试异步写入JSON - 嵌套对象"""
        file_path = temp_dir / "nested.json"
        data = {"level1": {"level2": {"level3": [1, 2, 3]}}, "list": [{"a": 1}, {"b": 2}]}

        await async_write_json(file_path, data)

        result = await async_read_json(file_path)
        assert result == data


class TestAsyncTextIO:
    """异步文本读写测试"""

    @pytest.mark.asyncio
    async def test_async_read_text_success(self, temp_text_file):
        """测试异步读取文本 - 成功"""
        result = await async_read_text(temp_text_file)

        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_async_read_text_default_empty(self):
        """测试异步读取文本 - 文件不存在返回空字符串"""
        result = await async_read_text(Path("/nonexistent/file.txt"), default="")
        assert result == ""

    @pytest.mark.asyncio
    async def test_async_read_text_custom_default(self):
        """测试异步读取文本 - 自定义默认值"""
        result = await async_read_text(Path("/nonexistent/file.txt"), default="custom default")
        assert result == "custom default"

    @pytest.mark.asyncio
    async def test_async_write_text_success(self, temp_dir):
        """测试异步写入文本 - 成功"""
        file_path = temp_dir / "output.txt"
        content = "Test content\nLine 2\nLine 3"

        await async_write_text(file_path, content)

        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content

    @pytest.mark.asyncio
    async def test_async_write_text_creates_parent(self, temp_dir):
        """测试异步写入文本 - 自动创建父目录"""
        file_path = temp_dir / "subdir" / "nested" / "file.txt"

        await async_write_text(file_path, "content")

        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == "content"


class TestAsyncFileOperations:
    """异步文件操作测试"""

    @pytest.mark.asyncio
    async def test_async_append_text(self, temp_dir):
        """测试异步追加文本"""
        file_path = temp_dir / "append_test.txt"

        await async_write_text(file_path, "Line 1\n")
        await async_append_text(file_path, "Line 2\n")
        await async_append_text(file_path, "Line 3\n")

        content = file_path.read_text(encoding="utf-8")
        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content

    @pytest.mark.asyncio
    async def test_async_append_creates_file(self, temp_dir):
        """测试异步追加创建文件"""
        file_path = temp_dir / "new_append.txt"

        await async_append_text(file_path, "First line")

        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == "First line"

    @pytest.mark.asyncio
    async def test_async_append_creates_parent(self, temp_dir):
        """测试异步追加自动创建父目录"""
        file_path = temp_dir / "subdir" / "nested" / "file.txt"

        await async_append_text(file_path, "content")

        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == "content"


class TestAsyncIOConcurrency:
    """异步IO并发测试"""

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, temp_json_file):
        """测试并发读取"""
        tasks = [async_read_json(temp_json_file) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        for result in results:
            assert result["key"] == "value"

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, temp_dir):
        """测试并发写入"""

        async def write_file(index):
            file_path = temp_dir / f"concurrent_{index}.json"
            await async_write_json(file_path, {"index": index})
            return file_path

        tasks = [write_file(i) for i in range(10)]
        file_paths = await asyncio.gather(*tasks)

        for i, path in enumerate(file_paths):
            assert path.exists()
            data = await async_read_json(path)
            assert data["index"] == i

    @pytest.mark.asyncio
    async def test_mixed_read_write(self, temp_dir):
        """测试混合读写"""
        file_path = temp_dir / "mixed.json"

        await async_write_json(file_path, {"counter": 0})

        for i in range(5):
            data = await async_read_json(file_path)
            data["counter"] = i + 1
            await async_write_json(file_path, data)

        final_data = await async_read_json(file_path)
        assert final_data["counter"] == 5
