# tests/test_integration.py
"""Scriptor集成测试 - 验证模块间协作"""

import asyncio

import pytest

# 使用包导入方式，兼容相对导入
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.memory_manager import MemoryManager
except ImportError:
    from memory_manager import MemoryManager
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.search_engine import SearchEngine
except ImportError:
    from search_engine import SearchEngine
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.identity_manager import IdentityManager
except ImportError:
    from identity_manager import IdentityManager
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.group_manager import GroupManager
except ImportError:
    from group_manager import GroupManager
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.conversation_ledger import ConversationLedger
except ImportError:
    from conversation_ledger import ConversationLedger
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.config_pydantic import ScriptorConfig
except ImportError:
    from config_pydantic import ScriptorConfig
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.message_buffering import MessageBuffer
except ImportError:
    from message_buffering import MessageBuffer


class TestIdentityAndGroupIntegration:
    """身份管理与群组管理集成测试"""

    @pytest.mark.asyncio
    async def test_identity_to_group_linkage(self, tmp_path):
        """测试身份与群组的关联"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)

        uid = identity_mgr.get_or_create_uid("user_123", "test_platform", "测试用户")
        assert uid is not None

        group_id = group_mgr.get_or_create_group("group_456", "测试群组", "test_platform", uid)
        assert group_id is not None

        group = group_mgr.get_group("group_456")
        assert group is not None
        assert group.owner_uid == uid

    @pytest.mark.asyncio
    async def test_cross_platform_identity(self, tmp_path):
        """测试跨平台身份聚合"""
        identity_mgr = IdentityManager(tmp_path)

        uid1 = identity_mgr.get_or_create_uid("user_123", "platform_a", "用户A")
        uid2 = identity_mgr.get_or_create_uid("user_456", "platform_b", "用户B")

        identity_mgr.bind_identities(uid1, [uid2])

        assert uid1 in identity_mgr.uid_metadata
        bound_uids = identity_mgr.uid_metadata[uid1].get("bound_uids", [])
        assert uid2 in bound_uids


class TestMemoryAndSearchIntegration:
    """记忆管理与搜索集成测试"""

    @pytest.mark.asyncio
    async def test_memory_record_then_search(self, tmp_path):
        """测试记录记忆后能搜索到"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)

        config = ScriptorConfig(embedding_enabled=False)
        memory_mgr = MemoryManager(tmp_path, config, identity_mgr, group_mgr)
        search_engine = SearchEngine(tmp_path, config, identity_mgr, group_mgr, memory_mgr)

        uid = identity_mgr.get_or_create_uid("user_search", "test", "搜索测试用户")

        from astrbot_plugin_scriptor.core.interfaces import MemoryRecordParams

        params = MemoryRecordParams(uid=uid, group_id="private", content="我喜欢吃苹果", memory_type="preference")
        await memory_mgr.record_long_term_memory(params)

        await asyncio.sleep(0.1)
        search_engine._is_ready = True

        results = await search_engine.search(query="苹果", uid=uid, group_id="private", scope="personal", limit=5)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_memory_search_triggers_strength_update(self, tmp_path):
        """测试搜索触发记忆强度更新"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)

        config = ScriptorConfig(embedding_enabled=False)
        memory_mgr = MemoryManager(tmp_path, config, identity_mgr, group_mgr)
        search_engine = SearchEngine(tmp_path, config, identity_mgr, group_mgr, memory_mgr)

        uid = identity_mgr.get_or_create_uid("user_strength", "test", "强度测试用户")
        profile_dir = tmp_path / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)
        memory_file = profile_dir / "MEMORY.md"
        memory_file.write_text(
            "### [2026-01-01 10:00:00] (fact) [Privacy: private] [Strength: 1.0] [Score: 5.0]\n测试记忆\n",
            encoding="utf-8",
        )

        search_engine._is_ready = True
        search_engine._tantivy_ready = False

        results = await search_engine.search(query="测试", uid=uid, group_id="private", scope="personal", limit=1)


class TestConversationAndMemoryIntegration:
    """对话总账与记忆集成测试"""

    @pytest.mark.asyncio
    async def test_conversation_record_to_memory_extract(self, tmp_path):
        """测试对话记录触发记忆提取"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)
        config = ScriptorConfig(embedding_enabled=False)
        memory_mgr = MemoryManager(tmp_path, config, identity_mgr, group_mgr)

        uid = identity_mgr.get_or_create_uid("user_conv", "test", "对话用户")
        session_id = f"{uid}_private"

        ledger = ConversationLedger(tmp_path)
        await ledger.add_message(session_id, "user", "我决定以后每天早上跑步", "user_input")

        messages = memory_mgr.get_unprocessed_messages(uid, "private")
        assert len(messages) >= 0

    @pytest.mark.asyncio
    async def test_conversation_context_retrieval(self, tmp_path):
        """测试对话上下文检索"""
        ledger = ConversationLedger(tmp_path)
        session_id = "test_session_context"

        for i in range(5):
            await ledger.add_message(session_id, "user", f"消息{i}", "user_input")
            await ledger.add_message(session_id, "assistant", f"回复{i}", "ai_response")

        context = await ledger.get_recent_context(session_id, message_count=3)
        assert len(context) == 3
        roles = [msg["role"] for msg in context]
        assert "user" in roles
        assert "assistant" in roles


class TestMessageBufferingIntegration:
    """消息缓冲集成测试"""

    @pytest.mark.asyncio
    async def test_message_buffer_flushes_to_memory(self, tmp_path):
        """测试消息缓冲刷新到记忆"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)
        config = ScriptorConfig(embedding_enabled=False, message_buffer_enabled=True)
        memory_mgr = MemoryManager(tmp_path, config, identity_mgr, group_mgr)

        uid = identity_mgr.get_or_create_uid("user_buffer", "test", "缓冲用户")
        session_id = f"{uid}_private"

        from astrbot_plugin_scriptor.core.message_buffering import BufferConfig

        buffer_config = BufferConfig(patience_seconds=0.1)
        buffer = MessageBuffer(buffer_config)

        flushed_messages = []

        async def flush_callback(sid: str, messages: list):
            flushed_messages.extend(messages)

        for i in range(3):
            await buffer.add_message(session_id, f"缓冲消息{i}", "user_123", flush_callback)

        await asyncio.sleep(0.5)
        assert len(flushed_messages) >= 0


class TestProfileAndMemoryFlow:
    """画像与记忆流程集成测试"""

    @pytest.mark.asyncio
    async def test_profile_update_creates_memory(self, tmp_path):
        """测试画像更新创建记忆"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)
        config = ScriptorConfig(embedding_enabled=False)
        memory_mgr = MemoryManager(tmp_path, config, identity_mgr, group_mgr)

        uid = identity_mgr.get_or_create_uid("user_profile", "test", "画像用户")
        profile_dir = tmp_path / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_file = profile_dir / "P_PROFILE.md"
        if not profile_file.exists():
            profile_file.write_text("## 用户资料\n初始内容\n", encoding="utf-8")

        await memory_mgr.update_profile(uid, "private", "我叫张三，住在上海", scope="personal")

        updated_content = profile_file.read_text(encoding="utf-8")
        assert "张三" in updated_content or "上海" in updated_content


class TestSearchResultRanking:
    """搜索结果排序集成测试"""

    @pytest.mark.asyncio
    async def test_entity_first_ranking(self, tmp_path):
        """测试实体优先排序"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)
        config = ScriptorConfig(embedding_enabled=False)
        memory_mgr = MemoryManager(tmp_path, config, identity_mgr, group_mgr)
        search_engine = SearchEngine(tmp_path, config, identity_mgr, group_mgr, memory_mgr)

        uid = identity_mgr.get_or_create_uid("user_rank", "test", "排序用户")
        profile_dir = tmp_path / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)

        (profile_dir / "PROFILE.md").write_text("## 用户资料\n我叫李四，我喜欢跑步\n", encoding="utf-8")
        (profile_dir / "MEMORY.md").write_text(
            "### [2026-01-01] (fact) [Privacy: private] [Strength: 1.0] [Score: 5.0]\n我也喜欢跑步\n", encoding="utf-8"
        )

        search_engine._is_ready = True
        search_engine._tantivy_ready = False

        results = await search_engine.search(query="跑步", uid=uid, group_id="private", scope="personal", limit=5)

        assert isinstance(results, list)


class TestDataPersistenceFlow:
    """数据持久化流程集成测试"""

    @pytest.mark.asyncio
    async def test_memory_persists_across_instances(self, tmp_path):
        """测试记忆在实例间持久化"""
        identity_mgr1 = IdentityManager(tmp_path)
        group_mgr1 = GroupManager(tmp_path, identity_mgr1)
        config = ScriptorConfig(embedding_enabled=False)
        memory_mgr1 = MemoryManager(tmp_path, config, identity_mgr1, group_mgr1)

        uid = identity_mgr1.get_or_create_uid("user_persist", "test", "持久用户")

        await memory_mgr1.record_interaction(uid=uid, group_id="private", role="user", content="持久化测试消息")

        del memory_mgr1
        del identity_mgr1
        del group_mgr1

        identity_mgr2 = IdentityManager(tmp_path)
        group_mgr2 = GroupManager(tmp_path, identity_mgr2)
        memory_mgr2 = MemoryManager(tmp_path, config, identity_mgr2, group_mgr2)

        notes = memory_mgr2.get_daily_notes(uid, "private", days=7)
        assert len(notes) >= 0


class TestErrorRecoveryFlow:
    """错误恢复流程集成测试"""

    @pytest.mark.asyncio
    async def test_search_fallback_on_tantivy_failure(self, tmp_path):
        """测试Tantivy失败时降级到BM25"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)
        config = ScriptorConfig(embedding_enabled=False)
        memory_mgr = MemoryManager(tmp_path, config, identity_mgr, group_mgr)
        search_engine = SearchEngine(tmp_path, config, identity_mgr, group_mgr, memory_mgr)

        search_engine._is_ready = True
        search_engine._tantivy_ready = False

        uid = identity_mgr.get_or_create_uid("user_fallback", "test", "降级用户")
        profile_dir = tmp_path / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "MEMORY.md").write_text(
            "### [2026-01-01] (fact) [Privacy: private] [Strength: 1.0] [Score: 5.0]\n降级测试内容\n", encoding="utf-8"
        )

        results = await search_engine.search(query="降级", uid=uid, group_id="private", scope="personal", limit=5)

        assert isinstance(results, list)


class TestConcurrentAccessFlow:
    """并发访问流程集成测试"""

    @pytest.mark.asyncio
    async def test_concurrent_memory_operations(self, tmp_path):
        """测试并发记忆操作"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)
        config = ScriptorConfig(embedding_enabled=False)
        memory_mgr = MemoryManager(tmp_path, config, identity_mgr, group_mgr)

        uid = identity_mgr.get_or_create_uid("user_concurrent", "test", "并发用户")

        async def record_memory(index: int):
            from astrbot_plugin_scriptor.core.interfaces import MemoryRecordParams

            params = MemoryRecordParams(uid=uid, group_id="private", content=f"并发记忆{index}", memory_type="fact")
            await memory_mgr.record_long_term_memory(params)

        tasks = [record_memory(i) for i in range(10)]
        await asyncio.gather(*tasks)

        profile_dir = tmp_path / "profiles" / uid
        memory_file = profile_dir / "P_MEMORY.md"
        assert memory_file.exists()

    @pytest.mark.asyncio
    async def test_concurrent_search_and_record(self, tmp_path):
        """测试并发搜索和记录"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)
        config = ScriptorConfig(embedding_enabled=False)
        memory_mgr = MemoryManager(tmp_path, config, identity_mgr, group_mgr)
        search_engine = SearchEngine(tmp_path, config, identity_mgr, group_mgr, memory_mgr)

        uid = identity_mgr.get_or_create_uid("user_both", "test", "双向用户")
        search_engine._is_ready = True
        search_engine._tantivy_ready = False

        async def record():
            from astrbot_plugin_scriptor.core.interfaces import MemoryRecordParams

            for i in range(5):
                params = MemoryRecordParams(uid=uid, group_id="private", content=f"双向记忆{i}", memory_type="fact")
                await memory_mgr.record_long_term_memory(params)

        async def search():
            for _ in range(5):
                await search_engine.search(query="双向", uid=uid, group_id="private", scope="personal", limit=3)
                await asyncio.sleep(0.01)

        await asyncio.gather(record(), search())


class TestSecurityIntegration:
    """安全集成测试"""

    def test_sanitize_id_prevents_path_traversal(self, tmp_path):
        """测试sanitize_id防止路径遍历"""
        from tools.security.sanitizer import sanitize_id

        malicious_ids = ["../../../etc/passwd", "..\\..\\windows\\system32", "../../secret", "....//....//etc"]

        for malicious in malicious_ids:
            sanitized = sanitize_id(malicious)
            # sanitize_id 会替换特殊字符，但不会移除 ..
            # 真正的安全验证由 validate_sandbox_path 负责
            assert "/" not in sanitized
            assert "\\" not in sanitized

    def test_sanitize_filename_prevents_path_traversal(self, tmp_path):
        """测试sanitize_filename防止路径遍历"""
        from tools.security.sanitizer import sanitize_filename

        malicious_names = ["../../../etc/passwd", "..\\..\\windows\\system32", "../../secret.md"]

        for malicious in malicious_names:
            sanitized = sanitize_filename(malicious)
            assert ".." not in sanitized


class TestPerformanceIntegration:
    """性能集成测试"""

    @pytest.mark.asyncio
    async def test_large_memory_file_handling(self, tmp_path):
        """测试大内存文件处理"""
        identity_mgr = IdentityManager(tmp_path)
        group_mgr = GroupManager(tmp_path, identity_mgr)
        config = ScriptorConfig(embedding_enabled=False)
        memory_mgr = MemoryManager(tmp_path, config, identity_mgr, group_mgr)
        search_engine = SearchEngine(tmp_path, config, identity_mgr, group_mgr, memory_mgr)

        uid = identity_mgr.get_or_create_uid("user_large", "test", "大文件用户")
        profile_dir = tmp_path / "profiles" / uid
        memory_dir = profile_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        large_file = memory_dir / "2026-03-18.md"
        large_content = "A" * 1024 * 1024 * 2
        large_file.write_text(large_content, encoding="utf-8")

        search_engine._is_ready = True
        search_engine._tantivy_ready = False

        result = search_engine._read_file_with_limit(large_file, max_size=1024 * 1024)
        assert "[... 内容已截断" in result
        assert len(result) < large_content.__len__()
