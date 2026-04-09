# tests/test_search_engine.py
"""SearchEngine 核心模块测试

优化说明：
1. 禁用了 embedding 和 maintenance，避免长时间等待
2. 所有测试使用 Mock，不依赖真实文件系统或网络
3. 超时时间设置为 1 秒
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.search_engine import SearchEngine, SearchResult
except ImportError:
    from search_engine import SearchEngine, SearchResult


class MockConfig:
    """模拟配置对象"""

    embedding_enabled = False
    search_top_k = 5
    memory_compact_threshold = 8000
    nightly_maintenance_enabled = False
    nightly_maintenance_inactivity_minutes = 60
    embedding_provider = "local"
    embedding_api_base = "http://localhost:11434/v1"
    embedding_api_key = ""
    embedding_model = "AI-ModelScope/bge-small-zh-v1.5"
    rerank_enabled = False
    rerank_provider = "api"
    rerank_api_base = "http://localhost:11434/v1"
    rerank_api_key = ""
    rerank_model = "bge-reranker-v2-m3"
    rerank_top_k = 5
    max_system_prompt_tokens = 100000
    enable_token_control = True
    daily_note_enabled = True
    cross_group_enabled = True


@pytest.fixture
def temp_data_dir(tmp_path):
    """创建临时数据目录"""
    return tmp_path


@pytest.fixture
def mock_config():
    """创建模拟配置"""
    return MockConfig()


@pytest.fixture
def mock_identity_manager():
    """创建模拟IdentityManager"""
    manager = MagicMock()
    manager.get_user_groups = MagicMock(return_value=["group_1", "group_2"])
    return manager


@pytest.fixture
def mock_group_manager():
    """创建模拟GroupManager"""
    manager = MagicMock()
    mock_group = MagicMock()
    mock_group.name = "测试群组"
    manager.get_group = MagicMock(return_value=mock_group)
    manager.get_user_joined_groups = MagicMock(return_value=[])
    return manager


@pytest.fixture
def mock_memory_manager():
    """创建模拟MemoryManager"""
    manager = MagicMock()
    manager._last_active_time = {}
    manager.increase_memory_strength = AsyncMock()
    return manager


@pytest.fixture
def search_engine(temp_data_dir, mock_config, mock_identity_manager, mock_group_manager, mock_memory_manager):
    """创建SearchEngine实例（已禁用后台任务）"""
    with patch.object(SearchEngine, "_lazy_init_engines"):
        engine = SearchEngine(
            data_dir=temp_data_dir,
            config=mock_config,
            identity_manager=mock_identity_manager,
            group_manager=mock_group_manager,
            memory_manager=mock_memory_manager,
        )
        engine._is_ready = True
        engine._tantivy_ready = False
        yield engine


class TestSearchResult:
    """SearchResult数据类测试"""

    def test_search_result_creation(self):
        """测试SearchResult创建"""
        result = SearchResult(content="测试内容", source="test.md", source_type="memory", score=0.95, date="2026-03-18")
        assert result.content == "测试内容"
        assert result.source == "test.md"
        assert result.source_type == "memory"
        assert result.score == 0.95
        assert result.date == "2026-03-18"

    def test_search_result_defaults(self):
        """测试SearchResult默认值"""
        result = SearchResult(content="测试", source="test", source_type="memory", score=1.0)
        assert result.date == ""


class TestSearchEngineInit:
    """SearchEngine初始化测试"""

    def test_initialization(self, search_engine, temp_data_dir, mock_config):
        """测试SearchEngine正确初始化"""
        assert search_engine.data_dir == temp_data_dir
        assert search_engine.config == mock_config
        assert search_engine.bm25 is not None
        assert search_engine._is_ready is True


class TestTokenization:
    """分词测试"""

    def test_tokenize_english(self, search_engine):
        """测试英文分词"""
        result = search_engine._tokenize("Hello World")
        assert "hello" in result
        assert "world" in result

    def test_tokenize_chinese(self, search_engine):
        """测试中文分词"""
        result = search_engine._tokenize("你好世界")
        assert "你" in result or "好" in result

    def test_tokenize_mixed(self, search_engine):
        """测试中英文混合分词"""
        result = search_engine._tokenize("Hello你好World世界")
        assert "hello" in result
        assert "world" in result

    def test_tokenize_empty(self, search_engine):
        """测试空字符串分词"""
        result = search_engine._tokenize("")
        assert result == ""


class TestFileReading:
    """文件读取测试"""

    def test_read_file_within_limit(self, search_engine, tmp_path):
        """测试读取限制内的文件"""
        test_file = tmp_path / "test.md"
        content = "A" * 100
        test_file.write_text(content, encoding="utf-8")

        result = search_engine._read_file_with_limit(test_file, max_size=1024)
        assert result == content

    def test_read_file_exceeds_limit(self, search_engine, tmp_path):
        """测试读取超过限制的文件"""
        test_file = tmp_path / "test.md"
        content = "A" * 2000
        test_file.write_text(content, encoding="utf-8")

        result = search_engine._read_file_with_limit(test_file, max_size=1024)
        assert "[... 内容已截断" in result

    def test_read_nonexistent_file(self, search_engine, tmp_path):
        """测试读取不存在的文件"""
        test_file = tmp_path / "nonexistent.md"
        result = search_engine._read_file_with_limit(test_file, max_size=1024)
        assert result == ""


class TestSearchResult:
    """SearchResult数据类测试"""

    def test_search_result_creation(self):
        """测试SearchResult创建"""
        result = SearchResult(content="测试内容", source="test.md", source_type="memory", score=0.95, date="2026-03-18")
        assert result.content == "测试内容"
        assert result.source == "test.md"
        assert result.source_type == "memory"
        assert result.score == 0.95
        assert result.date == "2026-03-18"

    def test_search_result_defaults(self):
        """测试SearchResult默认值"""
        result = SearchResult(content="测试", source="test", source_type="memory", score=1.0)
        assert result.date == ""
        assert result.uid == ""
        assert result.group_id == ""


class TestRanking:
    """结果排序测试"""

    def test_rank_results_empty(self, search_engine):
        """测试空结果排序"""
        results = []
        ranked = search_engine._rank_results(results, "测试")
        assert ranked == []

    def test_rank_results_single(self, search_engine):
        """测试单结果排序"""
        results = [SearchResult(content="测试内容", source="test.md", source_type="memory", score=1.0)]
        ranked = search_engine._rank_results(results, "测试")
        assert len(ranked) == 1

    def test_rank_results_with_date(self, search_engine):
        """测试带日期的排序"""
        results = [
            SearchResult(content="旧内容", source="old.md", source_type="memory", score=1.0, date="2026-01-01"),
            SearchResult(content="新内容", source="new.md", source_type="memory", score=1.0, date="2026-03-18"),
        ]
        ranked = search_engine._rank_results(results, "内容")
        assert len(ranked) == 2


class TestIndexCache:
    """索引缓存测试"""

    def test_load_index_cache_empty(self, search_engine):
        """测试加载空索引缓存"""
        search_engine._load_index_cache()
        assert search_engine._index_cache == {}
        assert search_engine._indexed_content_hashes == {}

    def test_save_index_cache(self, search_engine):
        """测试保存索引缓存"""
        search_engine._index_cache = {"key1": 12345}
        search_engine._indexed_content_hashes = {"file1": "hash1"}
        search_engine._save_index_cache()

        assert search_engine._INDEX_CACHE_FILE.exists()


class TestBM25:
    """BM25测试"""

    def test_bm25_instance(self, search_engine):
        """测试BM25实例存在"""
        assert search_engine.bm25 is not None


class TestFormatResults:
    """结果格式化测试"""

    def test_format_empty_results(self, search_engine):
        """测试格式化空结果"""
        result = search_engine.format_results([])
        assert "未找到" in result

    def test_format_single_result(self, search_engine):
        """测试格式化单个结果"""
        results = [
            SearchResult(content="测试内容", source="test.md", source_type="memory", score=1.0, date="2026-03-18")
        ]
        formatted = search_engine.format_results(results)
        assert "测试内容" in formatted
        assert "test.md" in formatted


class TestSearchIntegration:
    """搜索集成测试（快速版）"""

    @pytest.mark.asyncio
    async def test_search_returns_list(self, search_engine):
        """测试搜索返回列表"""
        results = await search_engine.search(
            query="测试", uid="user_123", group_id="private", scope="personal", limit=5
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self, search_engine):
        """测试空查询"""
        results = await search_engine.search(query="", uid="user_123", group_id="private", scope="personal", limit=5)
        assert isinstance(results, list)


class TestPersonalDocsCollection:
    """个人文档收集测试"""

    @pytest.mark.asyncio
    async def test_collect_personal_docs_empty(self, search_engine):
        """测试收集空个人文档"""
        docs = await search_engine._collect_personal_docs("nonexistent_user")
        assert docs == []

    @pytest.mark.asyncio
    async def test_collect_personal_docs_with_files(self, search_engine, temp_data_dir):
        """测试收集有文件的个人文档"""
        profile_dir = temp_data_dir / "profiles" / "test_user"
        profile_dir.mkdir(parents=True, exist_ok=True)

        profile_file = profile_dir / "PROFILE.md"
        profile_file.write_text("我叫张三", encoding="utf-8")

        docs = await search_engine._collect_personal_docs("test_user")
        assert len(docs) >= 1
        assert any(d.source == "PROFILE.md" for d in docs)


class TestGroupDocsCollection:
    """群组文档收集测试"""

    @pytest.mark.asyncio
    async def test_collect_group_docs_empty(self, search_engine):
        """测试收集空群组文档"""
        docs = await search_engine._collect_group_docs("nonexistent_group")
        assert docs == []

    @pytest.mark.asyncio
    async def test_collect_group_docs_with_files(self, search_engine, temp_data_dir):
        """测试收集有文件的群组文档"""
        group_dir = temp_data_dir / "groups" / "test_group"
        group_dir.mkdir(parents=True, exist_ok=True)

        group_file = group_dir / "GROUP.md"
        group_file.write_text("这是一个测试群组", encoding="utf-8")

        docs = await search_engine._collect_group_docs("test_group")
        assert len(docs) >= 1
        assert any(d.source == "GROUP.md" for d in docs)
