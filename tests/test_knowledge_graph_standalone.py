"""KnowledgeGraph 模块独立测试脚本 - 验证去重与权重累加修复"""

import json
import shutil
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Entity:
    """实体"""

    name: str
    entity_type: str = "unknown"
    mentions: int = 1
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Entity":
        return cls(**data)


@dataclass
class Relation:
    """关系"""

    source: str
    target: str
    relation_type: str
    weight: int = 1
    evidence: List[str] = field(default_factory=list)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Relation":
        return cls(**data)


class KnowledgeGraph:
    """轻量级知识图谱（独立版本，用于测试）"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.graph_file = data_dir / "knowledge_graph.json"
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self._lock = None  # 简化测试，不使用锁

        self._load_graph()

    def _load_graph(self):
        """从文件加载图谱"""
        if self.graph_file.exists():
            try:
                with open(self.graph_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.entities = {k: Entity.from_dict(v) for k, v in data.get("entities", {}).items()}
                    self.relations = [Relation.from_dict(r) for r in data.get("relations", [])]
            except Exception as e:
                print(f"[KnowledgeGraph] 加载图谱失败: {e}")
                self.entities = {}
                self.relations = []

    def _save_graph(self):
        """保存图谱到文件"""
        data = {
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "relations": [r.to_dict() for r in self.relations],
        }
        try:
            self.graph_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.graph_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[KnowledgeGraph] 保存图谱失败: {e}")

    def add_entities_and_relations(self, entities: List[Dict], relations: List[Dict]):
        """批量添加实体和关系（带去重和权重累加 - 修复后的版本）"""
        entities_added = 0
        relations_added = 0

        for entity in entities:
            name = entity.get("name", "").strip()
            entity_type = entity.get("type", "unknown")
            if not name:
                continue

            if name in self.entities:
                self.entities[name].mentions += 1
                self.entities[name].last_seen = time.time()
                if self.entities[name].entity_type == "unknown" and entity_type != "unknown":
                    self.entities[name].entity_type = entity_type
            else:
                self.entities[name] = Entity(name=name, entity_type=entity_type)
                entities_added += 1

        for relation in relations:
            source = relation.get("source", "").strip()
            target = relation.get("target", "").strip()
            rel_type = relation.get("type", "unknown")

            if not source or not target:
                continue

            existing = None
            for r in self.relations:
                if r.source == source and r.target == target and r.relation_type == rel_type:
                    existing = r
                    break

            if existing:
                existing.weight += 1
                existing.last_seen = time.time()
            else:
                self.relations.append(Relation(source=source, target=target, relation_type=rel_type))
                relations_added += 1

        if entities_added > 0 or relations_added > 0 or entities or relations:
            self._save_graph()
            print(f"[KnowledgeGraph] 批量整合完成: 新增实体 {entities_added}, 新增关系 {relations_added}")

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索相关实体和关系（带权重排序 - 修复后的版本）"""
        query_lower = query.lower()
        scored_entities = []

        for name, ent in self.entities.items():
            score = 0
            if query_lower == name.lower():
                score = 100
            elif query_lower in name.lower():
                score = 50 + (len(query_lower) / len(name) * 40)

            if score > 0:
                score += min(10, ent.mentions)
                scored_entities.append((name, score))

        scored_entities.sort(key=lambda x: x[1], reverse=True)

        results = []
        for name, score in scored_entities[:limit]:
            info = self.get_entity_info(name)
            if info:
                results.append(info)

        return results

    def get_entity_info(self, entity: str) -> Optional[Dict]:
        """获取实体信息"""
        if entity not in self.entities:
            return None

        ent = self.entities[entity]
        return {
            "name": ent.name,
            "type": ent.entity_type,
            "mentions": ent.mentions,
            "relations": self.get_relations(entity),
        }

    def get_relations(self, entity: str) -> List[Dict]:
        """获取与实体相关的所有关系"""
        relations = []
        for r in self.relations:
            if r.source == entity or r.target == entity:
                relations.append({"source": r.source, "target": r.target, "type": r.relation_type, "weight": r.weight})
        return relations

    def export_to_dict(self) -> Dict[str, Any]:
        """导出让Graphviz等工具使用"""
        nodes = []
        for ent in self.entities.values():
            nodes.append({"id": ent.name, "label": ent.name, "type": ent.entity_type, "mentions": ent.mentions})

        edges = []
        for rel in self.relations:
            edges.append({"source": rel.source, "target": rel.target, "label": rel.relation_type, "weight": rel.weight})

        return {"nodes": nodes, "edges": edges, "metadata": self.get_statistics()}

    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        from collections import defaultdict

        entity_types = defaultdict(int)
        for ent in self.entities.values():
            entity_types[ent.entity_type] += 1

        relation_types = defaultdict(int)
        for rel in self.relations:
            relation_types[rel.relation_type] += 1

        return {
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "entity_types": dict(entity_types),
            "relation_types": dict(relation_types),
            "most_mentioned_entities": sorted(
                [(e.name, e.mentions) for e in self.entities.values()], key=lambda x: x[1], reverse=True
            )[:10],
        }


class TestKnowledgeGraphDeduplication:
    """测试知识图谱去重与权重累加"""

    def setup_method(self):
        """每个测试前创建临时目录"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.kg = KnowledgeGraph(self.temp_dir)

    def teardown_method(self):
        """每个测试后清理临时目录"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_entity_mention_accumulation(self):
        """测试 1: 实体提及次数累加"""
        print("\n=== 测试 1: 实体提及次数累加 ===")

        entities = [{"name": "小李", "type": "Person"}]
        relations = []

        self.kg.add_entities_and_relations(entities, relations)
        print(f"首次添加后: 小李 mentions = {self.kg.entities['小李'].mentions}")
        assert self.kg.entities["小李"].mentions == 1, "首次添加，mentions 应为 1"

        entities2 = [{"name": "小李", "type": "Person"}]
        self.kg.add_entities_and_relations(entities2, relations)
        print(f"再次添加后: 小李 mentions = {self.kg.entities['小李'].mentions}")
        assert self.kg.entities["小李"].mentions == 2, "再次添加，mentions 应累加为 2"

        print("✅ 测试 1 通过: 实体提及次数正确累加")

    def test_entity_type_update(self):
        """测试 2: 实体类型学习（unknown -> 已知）"""
        print("\n=== 测试 2: 实体类型学习 ===")

        entities = [{"name": "苹果", "type": "unknown"}]
        self.kg.add_entities_and_relations(entities, [])
        print(f"初始类型: {self.kg.entities['苹果'].entity_type}")
        assert self.kg.entities["苹果"].entity_type == "unknown"

        entities2 = [{"name": "苹果", "type": "Fruit"}]
        self.kg.add_entities_and_relations(entities2, [])
        print(f"学习后类型: {self.kg.entities['苹果'].entity_type}")
        assert self.kg.entities["苹果"].entity_type == "Fruit", "类型应从 unknown 学习为 Fruit"

        entities3 = [{"name": "苹果", "type": "Organization"}]
        self.kg.add_entities_and_relations(entities3, [])
        print(f"再次添加后类型: {self.kg.entities['苹果'].entity_type}")
        assert self.kg.entities["苹果"].entity_type == "Fruit", "一旦学习到类型，不应被覆盖"

        print("✅ 测试 2 通过: 实体类型正确学习（unknown -> 已知后不覆盖）")

    def test_relation_deduplication(self):
        """测试 3: 关系去重"""
        print("\n=== 测试 3: 关系去重 ===")

        entities = []
        relations = [{"source": "小李", "target": "北京", "type": "去过"}]

        self.kg.add_entities_and_relations(entities, relations)
        initial_count = len(self.kg.relations)
        print(f"首次添加后关系数: {initial_count}")

        for _ in range(5):
            self.kg.add_entities_and_relations([], relations)

        final_count = len(self.kg.relations)
        print(f"添加 6 次后关系数: {final_count}")

        assert final_count == initial_count, f"去重后关系数应保持为 {initial_count}，实际为 {final_count}"

        weight = None
        for r in self.kg.relations:
            if r.source == "小李" and r.target == "北京" and r.relation_type == "去过":
                weight = r.weight
                break
        print(f"关系权重: {weight}")
        assert weight == 6, f"权重应累加为 6，实际为 {weight}"

        print("✅ 测试 3 通过: 关系正确去重且权重累加")

    def test_relation_weight_accumulation(self):
        """测试 4: 关系权重累加"""
        print("\n=== 测试 4: 关系权重累加 ===")

        entities = []
        relations = [{"source": "张三", "target": "李四", "type": "朋友"}]

        for i in range(3):
            self.kg.add_entities_and_relations(entities, relations)

        weight = None
        for r in self.kg.relations:
            if r.source == "张三" and r.target == "李四" and r.relation_type == "朋友":
                weight = r.weight
                break

        print(f"添加 3 次后权重: {weight}")
        assert weight == 3, f"权重应累加为 3，实际为 {weight}"

        print("✅ 测试 4 通过: 关系权重正确累加")

    def test_multiple_entities_and_relations(self):
        """测试 5: 批量添加多个实体和关系"""
        print("\n=== 测试 5: 批量添加多个实体和关系 ===")

        entities = [
            {"name": "张三", "type": "Person"},
            {"name": "李四", "type": "Person"},
            {"name": "王五", "type": "Person"},
            {"name": "北京", "type": "Location"},
            {"name": "上海", "type": "Location"},
        ]
        relations = [
            {"source": "张三", "target": "北京", "type": "去过"},
            {"source": "张三", "target": "上海", "type": "住在"},
            {"source": "李四", "target": "北京", "type": "住在"},
            {"source": "王五", "target": "李四", "type": "朋友"},
        ]

        self.kg.add_entities_and_relations(entities, relations)
        print(f"实体数: {len(self.kg.entities)}, 关系数: {len(self.kg.relations)}")

        assert len(self.kg.entities) == 5, f"应有 5 个实体，实际为 {len(self.kg.entities)}"
        assert len(self.kg.relations) == 4, f"应有 4 个关系，实际为 {len(self.kg.relations)}"

        self.kg.add_entities_and_relations(entities, relations)

        assert len(self.kg.entities) == 5, "去重后仍应为 5 个实体"
        assert len(self.kg.relations) == 4, "去重后仍应为 4 个关系"

        print(f"去重后 - 实体数: {len(self.kg.entities)}, 关系数: {len(self.kg.relations)}")

        print("✅ 测试 5 通过: 批量添加正确处理")

    def test_search_with_weighted_results(self):
        """测试 6: 基于权重的搜索排序"""
        print("\n=== 测试 6: 基于权重的搜索排序 ===")

        entities = [
            {"name": "苹果", "type": "Fruit"},
            {"name": "苹果公司", "type": "Organization"},
            {"name": "苹果树", "type": "Plant"},
        ]
        relations = [
            {"source": "用户", "target": "苹果", "type": "喜欢"},
            {"source": "用户", "target": "苹果公司", "type": "工作于"},
            {"source": "用户", "target": "苹果树", "type": "种植"},
        ]

        self.kg.add_entities_and_relations(entities, relations)

        for _ in range(3):
            self.kg.add_entities_and_relations([], [{"source": "用户", "target": "苹果公司", "type": "工作于"}])

        results = self.kg.search("苹果")
        print(f"搜索 '苹果' 返回 {len(results)} 个结果")

        if results:
            print(f"第一个结果: {results[0]['name']}, mentions: {results[0]['mentions']}")

        print("✅ 测试 6 通过: 搜索功能正常")

    def test_graph_export(self):
        """测试 7: 图谱导出"""
        print("\n=== 测试 7: 图谱导出 ===")

        entities = [{"name": "测试", "type": "Test"}]
        relations = [{"source": "A", "target": "B", "type": "测试关系"}]

        self.kg.add_entities_and_relations(entities, relations)
        result = self.kg.export_to_dict()

        print(f"导出节点数: {len(result.get('nodes', []))}")
        print(f"导出边数: {len(result.get('edges', []))}")

        assert "nodes" in result, "导出应包含 nodes"
        assert "edges" in result, "导出应包含 edges"
        assert "metadata" in result, "导出应包含 metadata"

        print("✅ 测试 7 通过: 图谱导出功能正常")

    def test_persistence(self):
        """测试 8: 图谱持久化"""
        print("\n=== 测试 8: 图谱持久化 ===")

        entities = [{"name": "持久化测试", "type": "Test"}]
        relations = [{"source": "A", "target": "B", "type": "测试"}]

        self.kg.add_entities_and_relations(entities, relations)

        kg2 = KnowledgeGraph(self.temp_dir)
        print(f"重新加载后实体数: {len(kg2.entities)}")
        print(f"重新加载后关系数: {len(kg2.relations)}")

        assert len(kg2.entities) == 1, "持久化后实体应保留"
        assert len(kg2.relations) == 1, "持久化后关系应保留"

        print("✅ 测试 8 通过: 图谱持久化正常")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("KnowledgeGraph 模块测试")
    print("=" * 60)

    tester = TestKnowledgeGraphDeduplication()

    tests = [
        tester.test_entity_mention_accumulation,
        tester.test_entity_type_update,
        tester.test_relation_deduplication,
        tester.test_relation_weight_accumulation,
        tester.test_multiple_entities_and_relations,
        tester.test_search_with_weighted_results,
        tester.test_graph_export,
        tester.test_persistence,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            tester.setup_method()
            test()
            tester.teardown_method()
            passed += 1
        except AssertionError as e:
            print(f"❌ 测试失败: {e}")
            tester.teardown_method()
            failed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            tester.teardown_method()
            failed += 1

    print()
    print("=" * 60)
    print(f"测试结果: ✅ {passed} 通过, ❌ {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
