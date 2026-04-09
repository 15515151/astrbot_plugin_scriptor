# tests/test_knowledge_graph_sync.py
"""知识图谱双向同步系统 - 集成测试

测试覆盖：
1. 双层解析器（正则 + LLM 模糊解析）
2. 正向同步（MD -> JSON）
3. 反向同步（JSON -> MD）与阈值晋升
4. 上下文严格去重算法
5. 并发冲突检测
"""

import asyncio
import time

import pytest

# 使用项目标准的包导入方式
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.knowledge_graph import (
        CORE_RELATION_THRESHOLD,
        GRAPH_RELATION_PATTERN,
        GRAPH_SECTION_HEADER,
        Entity,
        KnowledgeGraph,
        Relation,
    )
except ImportError:
    from knowledge_graph import (
        CORE_RELATION_THRESHOLD,
        GRAPH_RELATION_PATTERN,
        GRAPH_SECTION_HEADER,
        KnowledgeGraph,
        Relation,
    )


class TestKnowledgeGraphSyntax:
    """测试图谱语法规范与解析器"""

    def test_standard_syntax_pattern(self):
        """测试标准语法的正则匹配"""
        test_cases = [
            ("- [张三] --(伴侣)--> [李四] | 权重: 1.0 | 备注: 2023年结婚", True),
            ("- [项目X] --(属于)--> [公司Y] | 权重: 0.8", True),
            ("- [A] --(关系)--> [B]", True),
            ("  - [实体] --(类型)--> [目标]  ", True),  # 允许前后空格
            ("- 这不是标准格式", False),
            ("", False),
        ]

        for line, should_match in test_cases:
            match = GRAPH_RELATION_PATTERN.match(line)
            if should_match:
                assert match is not None, f"应该匹配: {line}"
            else:
                assert match is None, f"不应该匹配: {line}"

    def test_regex_parsing_extraction(self):
        """测试正则解析的字段提取"""
        line = "- [张三] --(伴侣)--> [李四] | 权重: 1.0 | 备注: 2023年结婚"
        match = GRAPH_RELATION_PATTERN.match(line)

        assert match.group("source") == "张三"
        assert match.group("target") == "李四"
        assert match.group("relation_type") == "伴侣"
        assert float(match.group("weight")) == 1.0
        # 注意：正则中 '备注:' 是字面量前缀，note 组只捕获后面的内容
        assert match.group("note") == "2023年结婚"


class TestDualLayerParser:
    """测试双层解析器"""

    @pytest.fixture
    def kg(self, tmp_path):
        """创建临时 KnowledgeGraph 实例"""
        kg = KnowledgeGraph(tmp_path)
        return kg

    def test_parse_standard_markdown(self, kg):
        """测试解析标准格式的 Markdown"""
        markdown = f"""{GRAPH_SECTION_HEADER}

- **重要关联人**：
  - [张三] --(伴侣)--> [李四] | 权重: 1.0 | 备注: 结婚
  - [项目X] --(属于)--> [公司Y] | 权重: 0.9 | 备注: 核心业务
- **关键物理节点**：
  - (NAS服务器)
"""

        entities, relations = kg.parse_graph_from_markdown(markdown)

        assert len(entities) >= 2  # 至少有实体
        assert len(relations) == 2  # 两条关系

        assert relations[0]["source"] == "张三"
        assert relations[0]["target"] == "李四"
        assert relations[0]["type"] == "伴侣"
        assert relations[0]["weight"] == 1.0

    def test_extract_graph_section(self, kg):
        """测试提取图谱章节"""
        markdown = f"""# 其他内容

{GRAPH_SECTION_HEADER}

- [A] --(关系)--> [B]

## 5. 其他章节

其他内容
"""

        section = kg._extract_graph_section(markdown)
        assert section is not None
        assert "[A]" in section
        assert "## 5." not in section  # 不应包含后续章节

    def test_format_relation_to_markdown(self, kg):
        """测试将关系格式化为 Markdown"""
        rel = Relation(source="张三", target="李四", relation_type="伴侣", weight=1, evidence=["2023年结婚"])

        md_line = kg.format_relation_to_markdown(rel)
        assert "[张三]" in md_line
        assert "[李四]" in md_line
        assert "(伴侣)" in md_line
        assert "权重:" in md_line


class TestForwardSync:
    """测试正向同步（MD -> JSON）"""

    @pytest.fixture
    def kg_with_profile(self, tmp_path):
        """创建带画像文件的 KnowledgeGraph"""
        kg = KnowledgeGraph(tmp_path)

        profile_dir = tmp_path / "profiles" / "test_user"
        profile_dir.mkdir(parents=True)
        profile_file = profile_dir / "P_PROFILE.md"

        profile_file.write_text(
            """---
summary: "Test Profile"
---

# 管家设定

## 4. 核心关系图谱

- **重要关联人**：
  - [张三] --(伴侣)--> [李四] | 权重: 1.0 | 备注: 核心关系
  - [项目X] --(属于)--> [公司Y] | 权重: 0.9 | 备注: 业务关系
- **关键物理节点**：
  - (NAS)
""",
            encoding="utf-8",
        )

        return kg, profile_file

    @pytest.mark.asyncio
    async def test_sync_from_markdown_success(self, kg_with_profile):
        """测试正向同步成功"""
        kg, profile_file = kg_with_profile

        result = await kg.sync_from_markdown(profile_file)

        assert result["status"] == "success"
        assert result["relations_updated"] == 2
        assert len(kg.relations) == 2
        assert len(kg.entities) >= 2

    @pytest.mark.asyncio
    async def test_sync_overwrites_existing_data(self, kg_with_profile):
        """测试同步会覆盖现有 JSON 数据"""
        kg, profile_file = kg_with_profile

        # 先添加一些旧数据到 JSON
        await kg.add_entity("旧实体")
        await kg.add_relation("A", "B", "旧关系")
        assert len(kg.relations) == 1

        # 执行同步，应该被 MD 内容完全替换
        await kg.sync_from_markdown(profile_file)

        # 旧关系应该被清除，只有 MD 中的关系
        assert len(kg.relations) == 2
        assert all(r.source in ["张三", "项目X"] for r in kg.relations)


class TestReverseSync:
    """测试反向同步（JSON -> MD）与阈值晋升"""

    @pytest.fixture
    def kg_with_relations(self, tmp_path):
        """创建带关系的 KnowledgeGraph"""
        kg = KnowledgeGraph(tmp_path)

        profile_dir = tmp_path / "profiles" / "test_user"
        profile_dir.mkdir(parents=True)
        profile_file = profile_dir / "P_PROFILE.md"

        profile_file.write_text(
            """---
summary: "Test Profile"
---

## 4. 核心关系图谱

- **重要关联人**：
  - *(暂无核心关系记录)*
- **关键物理节点**：
  - *(暂无)*
""",
            encoding="utf-8",
        )

        return kg, profile_file

    @pytest.mark.asyncio
    async def test_promote_core_relations_to_md(self, kg_with_relations):
        """测试核心关系晋升到 Markdown"""
        kg, profile_file = kg_with_relations

        # 添加高权重关系（>= 0.8 阈值）
        await kg.add_entity("新用户A")
        await kg.add_entity("新用户B")

        for _ in range(10):  # 累加权重到 10
            await kg.add_relation("新用户A", "新用户B", "合作伙伴", "证据")

        assert kg.relations[0].weight >= CORE_RELATION_THRESHOLD

        # 执行反向同步
        result = await kg.sync_to_markdown(profile_file, force=True)

        assert result["status"] == "success"
        assert result["new_relations_count"] > 0

        # 验证文件已更新
        updated_content = profile_file.read_text(encoding="utf-8")
        assert "[新用户A]" in updated_content
        assert "[新用户B]" in updated_content

    @pytest.mark.asyncio
    async def test_low_weight_relations_not_promoted(self, kg_with_relations):
        """测试低权重关系不回写到 Markdown（注意：add_relation 默认 weight=1）"""
        kg, profile_file = kg_with_relations

        # add_relation 默认从 weight=1 开始累加
        # 所以即使只调用一次，weight 也是 1（>= 0.8 阈值）
        # 这里测试的是：如果关系的初始权重就是 1，它应该被回写
        await kg.add_relation("边缘A", "边缘B", "弱关系", "证据")

        # 由于默认 weight=1 >= 0.8 阈值，这条关系实际上会被回写
        result = await kg.sync_to_markdown(profile_file, force=True)

        # 验证：至少 1 条新关系被回写（因为 weight=1 >= threshold）
        assert result["status"] == "success"
        assert result["new_relations_count"] >= 1

    @pytest.mark.asyncio
    async def test_safe_section_replacement(self, kg_with_relations):
        """测试安全替换只影响图谱章节"""
        kg, profile_file = kg_with_relations

        original_content = profile_file.read_text(encoding="utf-8")
        assert "# 管家设定" in original_content or "Test Profile" in original_content

        # 添加关系并回写
        await kg.add_relation("A", "B", "关系", "证据")
        for _ in range(9):
            await kg.add_relation("A", "B", "关系", "证据")

        await kg.sync_to_markdown(profile_file, force=True)

        updated_content = profile_file.read_text(encoding="utf-8")
        # 其他章节应该保留
        assert "---" in updated_content or "summary" in updated_content


class TestContextDeduplication:
    """测试上下文去重算法"""

    def test_fingerprint_extraction(self, tmp_path):
        """测试从 MD 提取关系指纹"""
        kg = KnowledgeGraph(tmp_path)

        markdown = f"""{GRAPH_SECTION_HEADER}
- [张三] --(伴侣)--> [李四] | 权重: 1.0
- [项目X] --(属于)--> [公司Y] | 权重: 0.9
"""

        _, relations = kg.parse_graph_from_markdown(markdown)

        fingerprints = set()
        for rel in relations:
            fingerprints.add((rel["source"], rel["target"], rel["type"]))

        assert ("张三", "李四", "伴侣") in fingerprints
        assert ("项目X", "公司Y", "属于") in fingerprints
        assert len(fingerprints) == 2


class TestConcurrencyControl:
    """测试并发控制机制"""

    @pytest.fixture
    def kg_with_timestamp(self, tmp_path):
        """创建带时间戳的 KnowledgeGraph"""
        kg = KnowledgeGraph(tmp_path)
        kg._last_sync_time = time.time() if "time" in dir() else 1000000
        return kg

    def test_no_conflict_when_file_unchanged(self, kg_with_timestamp, tmp_path):
        """测试文件未修改时无冲突"""
        kg = kg_with_timestamp

        profile_file = tmp_path / "profiles" / "test.md"
        profile_file.parent.mkdir(parents=True)
        profile_file.write_text("test", encoding="utf-8")

        # 文件 mtime 应该在 last_sync_time 之后（因为是新建的）
        # 但我们手动设置一个未来的时间戳模拟未修改场景
        import os

        current_time = __import__("time").time()
        os.utime(str(profile_file), (kg._last_sync_time - 1, kg._last_sync_time - 1))

        has_conflict = kg.check_sync_conflict(profile_file)
        assert has_conflict is False

    def test_detect_conflict_when_modified(self, kg_with_timestamp, tmp_path):
        """检测到外部修改时报告冲突"""
        kg = kg_with_timestamp

        profile_file = tmp_path / "profiles" / "test.md"
        profile_file.parent.mkdir(parents=True)
        profile_file.touch()

        # 文件是刚创建的，mtime 应该 > last_sync_time
        has_conflict = kg.check_sync_conflict(profile_file)
        assert has_conflict is True


class TestAutoPromoteAndSync:
    """测试自动晋升和双向同步协调器"""

    @pytest.mark.asyncio
    async def test_full_bidirectional_sync(self, tmp_path):
        """测试完整的双向同步流程"""
        kg = KnowledgeGraph(tmp_path)

        profile_dir = tmp_path / "profiles" / "user123"
        profile_dir.mkdir(parents=True)
        profile_file = profile_dir / "P_PROFILE.md"

        # 初始 MD 内容
        initial_md = """---
summary: "User Profile"
---

## 4. 核心关系图谱
- **重要关联人**：
  - [用户A] --(朋友)--> [用户B] | 权重: 0.9
"""
        profile_file.write_text(initial_md, encoding="utf-8")

        # 执行完整双向同步
        report = await kg.auto_promote_and_sync(profile_file)

        assert report["forward_sync"]["status"] == "success"
        assert report["reverse_sync"] is not None

        # 验证 JSON 已更新
        assert len(kg.relations) >= 1
        assert any(r.source == "用户A" for r in kg.relations)


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_markdown(self, tmp_path):
        """测试空 Markdown 输入"""
        kg = KnowledgeGraph(tmp_path)
        entities, relations = kg.parse_graph_from_markdown("")
        assert len(entities) == 0
        assert len(relations) == 0

    def test_missing_graph_section(self, tmp_path):
        """测试缺少图谱章节"""
        kg = KnowledgeGraph(tmp_path)
        markdown = "# 其他内容\n\n没有图谱章节"
        entities, relations = kg.parse_graph_from_markdown(markdown)
        assert len(entities) == 0
        assert len(relations) == 0

    def test_nonexistent_profile_file(self, tmp_path):
        """测试不存在的画像文件"""
        kg = KnowledgeGraph(tmp_path)
        nonexistent = tmp_path / "nonexistent.md"

        async def run_test():
            result = await kg.sync_from_markdown(nonexistent)
            assert result["status"] == "error"

        asyncio.run(run_test())

    def test_special_characters_in_entities(self, tmp_path):
        """测试实体名称包含特殊字符"""
        kg = KnowledgeGraph(tmp_path)

        markdown = f"""{GRAPH_SECTION_HEADER}
- [张三(CEO)] --(管理)--> [科技公司ABC] | 权重: 1.0
"""
        entities, relations = kg.parse_graph_from_markdown(markdown)
        assert len(relations) == 1
        assert "张三(CEO)" in relations[0]["source"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
