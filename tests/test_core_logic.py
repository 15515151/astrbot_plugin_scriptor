# tests/test_core_logic.py

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest

# 使用包导入方式，兼容相对导入
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.memory_manager import MemoryManager
except ImportError:
    from memory_manager import MemoryManager
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.search_engine import SearchEngine, SearchResult
except ImportError:
    from search_engine import SearchResult
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from tools.security.sanitizer import sanitize_filename, sanitize_id
except ImportError:
    from security.sanitizer import sanitize_filename, sanitize_id
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from tools.common.json_parser import safe_json_loads
except ImportError:
    from common.json_parser import safe_json_loads
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.compactor import Compactor
except ImportError:
    from compactor import Compactor
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.interfaces import MemoryRecordParams
except ImportError:
    from interfaces import MemoryRecordParams


class MockConfig:
    def __init__(self):
        self.embedding_enabled = False
        self.rerank_enabled = False


class MockIdentityManager:
    def get_user_groups(self, uid):
        return []


class MockGroupManager:
    def get_group(self, group_id):
        return None

    def get_group_context(self, group_id, uid):
        return {}


class MockCompactor:
    async def resolve_conflict(self, new_memory, old_contents):
        return f"Resolved: {new_memory} (was {old_contents[0]})"


class MockContext:
    def get_using_provider(self):
        return None


@pytest.fixture
def temp_data_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def memory_manager(temp_data_dir):
    config = MockConfig()
    identity_manager = MockIdentityManager()
    group_manager = MockGroupManager()
    return MemoryManager(temp_data_dir, config, identity_manager, group_manager)


class TestSecurityUtils:
    """测试安全工具函数"""

    def test_sanitize_id_valid(self):
        """测试合法 ID"""
        assert sanitize_id("valid_id_123") == "valid_id_123"

    def test_sanitize_id_path_traversal(self):
        """测试路径遍历字符会被替换为下划线（不再是哈希），安全由 validate_sandbox_path 保障"""
        result = sanitize_id("../etc/passwd")
        # sanitize_id 会将特殊字符替换为下划线
        assert result == ".._etc_passwd"
        assert "/" not in result

    def test_sanitize_id_empty(self):
        """测试空 ID 返回默认值"""
        assert sanitize_id("") == "unknown"
        assert sanitize_id(None, "default") == "default"

    def test_sanitize_filename_valid(self):
        """测试合法文件名"""
        assert sanitize_filename("test.md") == "test.md"

    def test_sanitize_filename_with_path(self):
        """测试带路径的文件名会被提取为纯文件名"""
        result = sanitize_filename("../../../etc/passwd")
        assert result == "passwd"

    def test_safe_json_loads_valid(self):
        """测试有效的 JSON 解析"""
        result = safe_json_loads('{"key": "value"}', default={})
        assert result == {"key": "value"}

    def test_safe_json_loads_invalid(self):
        """测试无效 JSON 返回默认值"""
        result = safe_json_loads("not json", default={})
        assert result == {}

    def test_safe_json_loads_with_markdown(self):
        """测试带 Markdown 标记的 JSON"""
        result = safe_json_loads('```json\n{"key": "value"}\n```', default={})
        assert result == {"key": "value"}


class TestMemoryManager:
    """测试记忆管理器"""

    @pytest.mark.asyncio
    async def test_memory_conflict_resolution(self, memory_manager, temp_data_dir):
        """测试记忆冲突解决"""
        uid = "test_user"
        group_id = "private"
        compactor = MockCompactor()

        old_memory = SearchResult(content="I hate apples.", source="MEMORY.md", source_type="memory", score=1.0)

        new_memory = "I love apples now."

        resolved = await memory_manager.resolve_memory_conflict(uid, group_id, new_memory, [old_memory], compactor)

        assert resolved == "Resolved: I love apples now. (was I hate apples.)"

    @pytest.mark.asyncio
    async def test_record_interaction_soft_truncation(self, memory_manager, temp_data_dir):
        """测试软截断机制"""
        uid = "test_user"
        group_id = "private"

        is_new = await memory_manager.record_interaction(uid, group_id, "user", "Hello")
        assert is_new == True

        is_new2 = await memory_manager.record_interaction(uid, group_id, "assistant", "Hi")
        assert is_new2 == False

        profile_dir = temp_data_dir / "profiles" / uid / "memory"
        files = list(profile_dir.glob("*.md"))
        assert len(files) == 1

        content = files[0].read_text(encoding="utf-8")
        assert "Hello" in content
        assert "Hi" in content

    @pytest.mark.asyncio
    async def test_get_profile_dir(self, memory_manager):
        """测试获取用户目录"""
        uid = "test_user_123"
        profile_dir = memory_manager._get_profile_dir(uid)
        assert profile_dir.name == uid
        assert "profiles" in str(profile_dir)

    @pytest.mark.asyncio
    async def test_get_group_dir(self, memory_manager):
        """测试获取群组目录"""
        group_id = "test_group_456"
        group_dir = memory_manager._get_group_dir(group_id)
        assert group_dir.name == group_id
        assert "groups" in str(group_dir)

    @pytest.mark.asyncio
    async def test_record_long_term_memory(self, memory_manager, temp_data_dir):
        """测试记录长期记忆"""
        uid = "test_user_memory"
        group_id = "private"

        profile_dir = temp_data_dir / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)

        params = MemoryRecordParams(
            uid=uid, group_id=group_id, content="This is a test memory", memory_type="fact", privacy_level="private"
        )

        await memory_manager.record_long_term_memory(params)

        memory_file = profile_dir / "P_MEMORY.md"
        assert memory_file.exists()

        content = memory_file.read_text(encoding="utf-8")
        assert "This is a test memory" in content

    @pytest.mark.asyncio
    async def test_update_profile(self, memory_manager, temp_data_dir):
        """测试更新用户画像"""
        uid = "test_user"

        profile_dir = temp_data_dir / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_file = profile_dir / "P_PROFILE.md"
        profile_file.write_text("## 用户资料\n", encoding="utf-8")

        await memory_manager.update_profile(uid, "private", "Likes coffee", scope="personal")

        content = profile_file.read_text(encoding="utf-8")
        assert "Likes coffee" in content

    @pytest.mark.asyncio
    async def test_file_lock_lru(self, memory_manager, temp_data_dir):
        """测试文件锁 LRU 清理"""
        for i in range(150):
            lock = await memory_manager._get_lock(temp_data_dir / f"file_{i}.txt")
            assert lock is not None

        await asyncio.sleep(0.1)
        assert len(memory_manager._file_locks) <= memory_manager._MAX_LOCKS

    def test_should_extract_memory(self, memory_manager):
        """测试记忆提取判断"""
        assert memory_manager.should_extract_memory("请记住我喜欢咖啡") == True
        assert memory_manager.should_extract_memory("这是很重要的事情") == True
        assert memory_manager.should_extract_memory("我决定明天去旅行") == True
        assert memory_manager.should_extract_memory("hello world") == False

    def test_extract_memory_type(self, memory_manager):
        """测试记忆类型提取"""
        assert memory_manager.extract_memory_type("我喜欢咖啡") == "preference"
        assert memory_manager.extract_memory_type("我决定去旅行") == "decision"
        assert memory_manager.extract_memory_type("待办：买牛奶") == "task"
        assert memory_manager.extract_memory_type("这是个事实") == "fact"


class TestSearchResult:
    """测试搜索结果"""

    def test_search_result_creation(self):
        """测试搜索结果创建"""
        result = SearchResult(
            content="Test content", source="MEMORY.md", source_type="memory", score=0.8, date="2024-01-01"
        )

        assert result.content == "Test content"
        assert result.source == "MEMORY.md"
        assert result.score == 0.8


class TestCompactor:
    """测试记忆压缩器"""

    def test_compactor_init(self):
        """测试压缩器初始化"""
        config = MockConfig()
        context = MockContext()
        compactor = Compactor(config, context)

        assert compactor.config == config
        assert compactor.context == context

    def test_format_messages(self):
        """测试消息格式化"""
        config = MockConfig()
        context = MockContext()
        compactor = Compactor(config, context)

        messages = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there"}]

        formatted = compactor._format_messages(messages)
        assert "user: Hello" in formatted
        assert "assistant: Hi there" in formatted
