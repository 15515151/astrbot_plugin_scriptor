# tests/test_performance.py
"""性能测试 - 测试大数据集和响应时间"""

import asyncio
import hashlib
import shutil
import tempfile
import time
from pathlib import Path

import pytest

# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.memory_manager import MemoryManager
except ImportError:
    from memory_manager import MemoryManager
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.search_engine import SearchEngine, SearchResult
except ImportError:
    from search_engine import SearchEngine
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.knowledge_base import KnowledgeBase, KnowledgeItem, KnowledgeType
except ImportError:
    from knowledge_base import KnowledgeBase, KnowledgeItem, KnowledgeType
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.knowledge_graph import Entity, KnowledgeGraph, Relation
except ImportError:
    from knowledge_graph import KnowledgeGraph
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.config_pydantic import ScriptorConfig
except ImportError:
    from config_pydantic import ScriptorConfig


class MockIdentityManager:
    def __init__(self):
        self._groups = {}
        self.uid_metadata = {}

    def get_user_groups(self, uid):
        return self._groups.get(uid, [])

    def get_or_create_uid(self, physical_id, platform, name):
        uid = f"user_{physical_id}"
        if uid not in self.uid_metadata:
            self.uid_metadata[uid] = {"primary_name": name}
        return uid


class MockGroupManager:
    def __init__(self):
        pass

    def get_group(self, group_id):
        return None

    def get_group_context(self, group_id, uid):
        return {}

    def get_user_joined_groups(self, uid):
        return []


@pytest.fixture
def temp_data_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_config():
    config = ScriptorConfig()
    config.embedding_enabled = False
    config.rerank_enabled = False
    config.search_top_k = 5
    return config


@pytest.fixture
def memory_manager(temp_data_dir, mock_config):
    identity_manager = MockIdentityManager()
    group_manager = MockGroupManager()
    return MemoryManager(temp_data_dir, mock_config, identity_manager, group_manager)


@pytest.fixture
def search_engine(temp_data_dir, mock_config, memory_manager):
    identity_manager = MockIdentityManager()
    group_manager = MockGroupManager()
    engine = SearchEngine(temp_data_dir, mock_config, identity_manager, group_manager, memory_manager)
    engine._is_ready = True
    engine._tantivy_ready = False
    return engine


@pytest.fixture
def knowledge_base(temp_data_dir):
    return KnowledgeBase(temp_data_dir)


@pytest.fixture
def knowledge_graph(temp_data_dir):
    return KnowledgeGraph(temp_data_dir)


class TestSearchPerformance:
    """搜索性能测试"""

    @pytest.mark.asyncio
    async def test_search_response_time(self, search_engine, temp_data_dir, memory_manager):
        """测试搜索响应时间"""
        uid = "test_user_search_perf"
        profile_dir = temp_data_dir / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)

        memory_dir = profile_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        for i in range(10):
            memory_file = memory_dir / f"2026-03-{20+i:02d}.md"
            memory_file.write_text(
                f"### [2026-03-{20+i:02d} 10:00:00] (fact)\n测试记忆内容 {i}，包含关键词搜索测试\n", encoding="utf-8"
            )

        start_time = time.time()
        results = await search_engine.search(query="搜索测试", uid=uid, group_id="private", scope="personal", limit=5)
        search_time = time.time() - start_time

        assert search_time < 1.0, f"搜索耗时 {search_time:.2f}s，超过 1s 阈值"
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_large_memory_search(self, search_engine, temp_data_dir):
        """测试大量记忆下的搜索"""
        uid = "test_user_large_search"
        profile_dir = temp_data_dir / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)

        memory_file = profile_dir / "MEMORY.md"
        large_content = []
        for i in range(100):
            large_content.append(f"### [2026-03-{i+1:02d} 10:00:00] (fact)\n记忆条目 {i}：用户喜欢苹果和香蕉\n")
        memory_file.write_text("\n".join(large_content), encoding="utf-8")

        start_time = time.time()
        results = await search_engine.search(query="苹果", uid=uid, group_id="private", scope="personal", limit=10)
        search_time = time.time() - start_time

        assert search_time < 2.0, f"大规模搜索耗时 {search_time:.2f}s，超过 2s 阈值"


class TestMemoryPerformance:
    """记忆性能测试"""

    @pytest.mark.asyncio
    async def test_batch_record_performance(self, memory_manager, temp_data_dir):
        """测试批量记录性能"""
        uid = "test_user_batch"

        start_time = time.time()
        for i in range(100):
            await memory_manager.record_interaction(uid, "private", "user", f"测试消息 {i}")
        batch_time = time.time() - start_time

        assert batch_time < 5.0, f"批量记录100条消息耗时 {batch_time:.2f}s，超过 5s 阈值"

    @pytest.mark.asyncio
    async def test_concurrent_record_performance(self, memory_manager, temp_data_dir):
        """测试并发记录性能"""
        uid = "test_user_concurrent_perf"

        async def record_message(i):
            return await memory_manager.record_interaction(uid, "private", "user", f"并发消息 {i}")

        start_time = time.time()
        await asyncio.gather(*[record_message(i) for i in range(50)])
        concurrent_time = time.time() - start_time

        assert concurrent_time < 3.0, f"并发记录50条消息耗时 {concurrent_time:.2f}s，超过 3s 阈值"


class TestKnowledgeBasePerformance:
    """知识库性能测试"""

    def test_large_knowledge_search(self, knowledge_base, temp_data_dir):
        """测试大规模知识库搜索"""
        for i in range(100):
            item = KnowledgeItem.create(
                title=f"知识条目 {i}",
                content=f"这是知识条目 {i} 的内容，包含测试关键词和描述信息",
                knowledge_type=KnowledgeType.FACT,
                tags=["测试", f"标签{i % 10}"],
            )
            knowledge_base.add_item(item)

        start_time = time.time()
        results = knowledge_base.search("测试关键词", limit=10)
        search_time = time.time() - start_time

        assert search_time < 0.5, f"知识库搜索耗时 {search_time:.2f}s，超过 0.5s 阈值"
        assert len(results) > 0

    def test_category_query_performance(self, knowledge_base, temp_data_dir):
        """测试分类查询性能"""
        for i in range(50):
            item = KnowledgeItem.create(
                title=f"分类测试 {i}",
                content=f"分类测试内容 {i}",
                knowledge_type=KnowledgeType.FACT if i % 2 == 0 else KnowledgeType.SKILL,
                category=f"类别{i % 5}",
            )
            knowledge_base.add_item(item)

        start_time = time.time()
        items = knowledge_base.get_all_items()
        query_time = time.time() - start_time

        assert query_time < 0.3, f"分类查询耗时 {query_time:.2f}s，超过 0.3s 阈值"
        assert len(items) >= 50


class TestKnowledgeGraphPerformance:
    """知识图谱性能测试"""

    def test_large_graph_operations(self, knowledge_graph):
        """测试大规模图谱操作"""
        entities = []
        relations = []

        for i in range(100):
            entities.append({"name": f"实体{i}", "type": "人物"})

        for i in range(50):
            relations.append({"source": f"实体{i}", "target": f"实体{i+50}", "type": "关联"})

        start_time = time.time()
        knowledge_graph.add_entities_and_relations(entities, relations)
        add_time = time.time() - start_time

        assert add_time < 2.0, f"添加100个实体和50个关系耗时 {add_time:.2f}s，超过 2s 阈值"
        assert len(knowledge_graph.entities) >= 100

    def test_graph_search_performance(self, knowledge_graph):
        """测试图谱搜索性能"""
        entities = []
        for i in range(50):
            entities.append({"name": f"用户{i}", "type": "人物"})

        knowledge_graph.add_entities_and_relations(entities, [])

        start_time = time.time()
        for _ in range(20):
            knowledge_graph.search("用户")
        search_time = time.time() - start_time

        assert search_time < 0.5, f"搜索耗时 {search_time:.2f}s，超过 0.5s 阈值"

    def test_graph_retention(self, knowledge_graph):
        """测试图谱持久化"""
        entities = [
            {"name": "张三", "type": "人物"},
            {"name": "李四", "type": "人物"},
            {"name": "北京", "type": "地点"},
        ]
        relations = [
            {"source": "张三", "target": "北京", "type": "去过"},
            {"source": "李四", "target": "北京", "type": "住在"},
        ]

        knowledge_graph.add_entities_and_relations(entities, relations)

        result = knowledge_graph.export_to_dict()
        assert "nodes" in result


class TestIndexPerformance:
    """索引性能测试"""

    @pytest.mark.asyncio
    async def test_index_rebuild_time(self, search_engine, temp_data_dir):
        """测试索引重建时间"""
        uid = "test_user_rebuild"
        profile_dir = temp_data_dir / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)

        memory_dir = profile_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        for i in range(20):
            memory_file = memory_dir / f"2026-03-{i+1:02d}.md"
            memory_file.write_text(f"### [2026-03-{i+1:02d} 10:00:00] (fact)\n重建测试记忆 {i}\n", encoding="utf-8")

        start_time = time.time()
        all_docs = await search_engine._collect_all_docs_for_indexing(uid, "private", "all")
        collect_time = time.time() - start_time

        assert collect_time < 2.0, f"收集文档耗时 {collect_time:.2f}s，超过 2s 阈值"

    @pytest.mark.asyncio
    async def test_index_incremental_update(self, search_engine, temp_data_dir):
        """测试索引增量更新时间"""
        uid = "test_user_incremental"
        profile_dir = temp_data_dir / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)

        memory_file = profile_dir / "MEMORY.md"
        memory_file.write_text("### [2026-03-29 10:00:00] (fact)\n增量更新测试\n", encoding="utf-8")

        start_time = time.time()
        content_hash = hashlib.md5(memory_file.read_bytes()).hexdigest()
        search_engine._indexed_content_hashes[str(memory_file)] = content_hash
        update_time = time.time() - start_time

        assert update_time < 0.1, f"增量更新耗时 {update_time:.2f}s，超过 0.1s 阈值"


class TestMemoryUsage:
    """内存使用测试"""

    @pytest.mark.asyncio
    async def test_file_lock_memory(self, memory_manager, temp_data_dir):
        """测试文件锁内存占用"""
        initial_lock_count = len(memory_manager._file_locks)

        for i in range(150):
            await memory_manager._get_lock(temp_data_dir / f"file_{i}.txt")

        final_lock_count = len(memory_manager._file_locks)

        assert (
            final_lock_count <= memory_manager._MAX_LOCKS
        ), f"锁数量 {final_lock_count} 超过限制 {memory_manager._MAX_LOCKS}"

    @pytest.mark.asyncio
    async def test_high_concurrency_write(self, memory_manager, temp_data_dir):
        """测试高并发写入"""
        uid = "test_user_stress"

        async def write_task(i):
            await memory_manager.record_interaction(uid, "private", "user", f"压力测试消息 {i}")

        start_time = time.time()
        await asyncio.gather(*[write_task(i) for i in range(100)])
        total_time = time.time() - start_time

        assert total_time < 10.0, f"100次并发写入耗时 {total_time:.2f}s，超过 10s 阈值"

    @pytest.mark.asyncio
    async def test_mixed_operations(self, memory_manager, search_engine, temp_data_dir):
        """测试混合操作性能"""
        uid = "test_user_mixed"

        async def read_operation():
            await search_engine.search("测试", uid, "private", "personal", 5)

        async def write_operation(i):
            await memory_manager.record_interaction(uid, "private", "user", f"混合测试消息 {i}")

        operations = []
        for i in range(25):
            operations.append(write_operation(i))
            operations.append(read_operation())

        start_time = time.time()
        await asyncio.gather(*operations)
        total_time = time.time() - start_time

        assert total_time < 15.0, f"50次混合操作耗时 {total_time:.2f}s，超过 15s 阈值"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
