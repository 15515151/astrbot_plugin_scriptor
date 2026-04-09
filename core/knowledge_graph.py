# core/knowledge_graph.py
"""轻量级知识图谱模块 - 支持声明式 Markdown 双向同步

功能特性：
1. 双层解析器：正则快速解析 + LLM 模糊解析与自修复
2. 双向同步：MD <-> JSON 双向同步，支持阈值晋升
3. 上下文去重：避免 MD 和 JSON 数据重复注入 Prompt
4. 声明式干预：用户通过 Markdown 直接编辑知识图谱
"""

import asyncio
import json
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from tools.common.json_parser import safe_json_loads

# ========== 知识图谱 Markdown 语法规范 ==========
# 标准格式：- [实体A] --(关系类型)--> [实体B] | 权重: 0.9 | 备注: 补充说明
# 示例：
#   - [张三] --(伴侣)--> [李四] | 权重: 1.0 | 备注: 2023年结婚
#   - [项目X] --(属于)--> [公司Y] | 权重: 0.8 | 备注: 核心业务

GRAPH_SECTION_HEADER = "## 4. 核心关系图谱"
GRAPH_RELATION_PATTERN = re.compile(
    r"^\s*-\s*\[(?P<source>[^\]]+)\]\s*--\((?P<relation_type>[^)]+)\)-->\s*\[(?P<target>[^\]]+)\]"
    r"(?:\s*\|\s*权重:\s*(?P<weight>[\d.]+))?"
    r"(?:\s*\|\s*备注:\s*(?P<note>.*))?",
    re.UNICODE,
)

# 核心关系阈值（>= 此值的关系会常驻在 Markdown 中）
CORE_RELATION_THRESHOLD = 0.8


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
    """轻量级知识图谱

    存储路径：global/knowledge_graph.json（全局共享）
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

        # 全局目录路径
        self.global_dir = data_dir / "global"
        self.global_dir.mkdir(parents=True, exist_ok=True)

        # 新路径：global/knowledge_graph.json
        self.graph_file = self.global_dir / "knowledge_graph.json"

        # 迁移旧数据
        self._migrate_from_legacy_path()

        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self._lock = asyncio.Lock()

        self._load_graph()

    def _migrate_from_legacy_path(self):
        """迁移旧路径的数据到 global/ 目录"""
        legacy_file = self.data_dir / "knowledge_graph.json"
        legacy_processed = self.data_dir / "knowledge_graph_processed.json"

        if legacy_file.exists() and not self.graph_file.exists():
            try:
                import shutil

                shutil.move(str(legacy_file), str(self.graph_file))
                logger.info("[KnowledgeGraph] 已迁移图谱数据到 global/ 目录")
            except Exception as e:
                logger.warning(f"[KnowledgeGraph] 迁移图谱数据失败: {e}")

        if legacy_processed.exists():
            new_processed = self.global_dir / "knowledge_graph_processed.json"
            if not new_processed.exists():
                try:
                    import shutil

                    shutil.move(str(legacy_processed), str(new_processed))
                    logger.info("[KnowledgeGraph] 已迁移处理记录到 global/ 目录")
                except Exception as e:
                    logger.warning(f"[KnowledgeGraph] 迁移处理记录失败: {e}")

    def _load_graph(self):
        """从文件加载图谱"""
        if self.graph_file.exists():
            try:
                with open(self.graph_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.entities = {k: Entity.from_dict(v) for k, v in data.get("entities", {}).items()}
                    self.relations = [Relation.from_dict(r) for r in data.get("relations", [])]
                logger.info(f"[KnowledgeGraph] 加载了 {len(self.entities)} 个实体和 {len(self.relations)} 个关系")
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"[KnowledgeGraph] 加载图谱失败: {e}")
                self.entities = {}
                self.relations = []

    def _save_graph(self):
        """保存图谱到文件 (后台线程异步)"""
        import threading

        data = {
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "relations": [r.to_dict() for r in self.relations],
        }

        def _save_background():
            import json

            try:
                self.graph_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.graph_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"[KnowledgeGraph] 保存图谱失败: {e}")

        threading.Thread(target=_save_background, daemon=True).start()

    async def add_entity(self, name: str, entity_type: str = "unknown"):
        """添加或更新实体"""
        async with self._lock:
            if name in self.entities:
                self.entities[name].mentions += 1
                self.entities[name].last_seen = time.time()
            else:
                self.entities[name] = Entity(name=name, entity_type=entity_type)

    async def add_relation(self, source: str, target: str, relation_type: str, evidence: str = ""):
        """添加或更新关系"""
        async with self._lock:
            existing = None
            for r in self.relations:
                if r.source == source and r.target == target and r.relation_type == relation_type:
                    existing = r
                    break

            if existing:
                existing.weight += 1
                existing.last_seen = time.time()
                if evidence and evidence not in existing.evidence:
                    existing.evidence.append(evidence)
            else:
                self.relations.append(
                    Relation(
                        source=source,
                        target=target,
                        relation_type=relation_type,
                        evidence=[evidence] if evidence else [],
                    )
                )

    def get_relations(self, entity: str) -> List[Dict]:
        """获取与实体相关的所有关系"""
        relations = []
        for r in self.relations:
            if r.source == entity or r.target == entity:
                relations.append({"source": r.source, "target": r.target, "type": r.relation_type, "weight": r.weight})
        return relations

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

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        搜索相关实体和关系（带权重排序）

        Args:
            query (str): 搜索关键词
            limit (int): 返回实体数量限制

        Returns:
            List[Dict]: 包含实体及其关系的列表
        """
        query_lower = query.lower()
        scored_entities = []

        for name, ent in self.entities.items():
            score = 0
            if query_lower == name.lower():
                score = 100  # 精确匹配
            elif query_lower in name.lower():
                score = 50 + (len(query_lower) / len(name) * 40)  # 包含匹配，越接近越好

            if score > 0:
                # 结合提及次数进行微调
                score += min(10, ent.mentions)
                scored_entities.append((name, score))

        # 按分数排序
        scored_entities.sort(key=lambda x: x[1], reverse=True)

        results = []
        for name, score in scored_entities[:limit]:
            info = self.get_entity_info(name)
            if info:
                results.append(info)

        return results

    async def consolidate_from_diary(self, diary_content: str, date: str):
        """从日记内容中提取实体和关系并整合（需要外部传入 LLM 调用结果）

        注意：这个方法本身不调用 LLM，需要外部传入 LLM 解析后的结果。
        建议通过 add_entities_and_relations 方法批量添加。
        """
        logger.info(f"[KnowledgeGraph] 准备整合 {date} 的日记内容（图谱整合需要配合 LLM 使用）")
        pass

    def mark_diary_processed(self, uid: str, date: str):
        """标记日记已处理，用于增量更新"""
        processed = self._load_processed_diaries()
        key = f"{uid}:{date}"
        if key not in processed:
            processed.add(key)
            self._save_processed_diaries(processed)

    def is_diary_processed(self, uid: str, date: str) -> bool:
        """检查日记是否已处理"""
        return f"{uid}:{date}" in self._load_processed_diaries()

    def _load_processed_diaries(self) -> set:
        """加载已处理的日记记录"""
        processed_file = self.global_dir / "knowledge_graph_processed.json"
        if processed_file.exists():
            try:
                with open(processed_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def _save_processed_diaries(self, processed: set):
        """保存已处理的日记记录"""
        processed_file = self.global_dir / "knowledge_graph_processed.json"
        try:
            with open(processed_file, "w", encoding="utf-8") as f:
                json.dump(list(processed), f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[KnowledgeGraph] 保存处理记录失败: {e}")

    def add_entities_and_relations(self, entities: List[Dict], relations: List[Dict]):
        """批量添加实体和关系（供外部 LLM 解析结果调用，带去重和权重累加）"""
        entities_added = 0
        relations_added = 0

        # 1. 处理实体
        for entity in entities:
            name = entity.get("name", "").strip()
            entity_type = entity.get("type", "unknown")
            if not name:
                continue

            if name in self.entities:
                # 已存在，增加提及次数
                self.entities[name].mentions += 1
                self.entities[name].last_seen = time.time()
                # 更新类型：如果新类型更具体（不是 unknown），则更新
                if entity_type != "unknown":
                    self.entities[name].entity_type = entity_type
            else:
                # 新实体
                self.entities[name] = Entity(name=name, entity_type=entity_type)
                entities_added += 1

        # 2. 处理关系
        for relation in relations:
            source = relation.get("source", "").strip()
            target = relation.get("target", "").strip()
            rel_type = relation.get("type", "unknown")

            if not source or not target:
                continue

            # 查找是否存在相同关系
            existing = None
            for r in self.relations:
                if r.source == source and r.target == target and r.relation_type == rel_type:
                    existing = r
                    break

            if existing:
                # 已存在，增加权重
                existing.weight += 1
                existing.last_seen = time.time()
            else:
                # 新关系
                self.relations.append(Relation(source=source, target=target, relation_type=rel_type))
                relations_added += 1

        if entities_added > 0 or relations_added > 0 or entities or relations:
            self._save_graph()
            logger.info(f"[KnowledgeGraph] 批量整合完成: 新增实体 {entities_added}, 新增关系 {relations_added}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
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

    def get_neighbors(self, entity: str, max_depth: int = 1) -> Dict[str, Any]:
        """获取实体的邻居节点（带深度）"""
        if entity not in self.entities:
            return {}

        visited = {entity}
        current_level = {entity}
        neighbors = {}

        for _ in range(max_depth):
            next_level = set()
            for rel in self.relations:
                if rel.source in current_level and rel.target not in visited:
                    neighbors[rel.target] = {"type": rel.relation_type, "weight": rel.weight}
                    next_level.add(rel.target)
                    visited.add(rel.target)
                elif rel.target in current_level and rel.source not in visited:
                    neighbors[rel.source] = {"type": rel.relation_type, "weight": rel.weight}
                    next_level.add(rel.source)
                    visited.add(rel.source)
            current_level = next_level
            if not current_level:
                break

        return neighbors

    def export_to_dict(self) -> Dict[str, Any]:
        """导出让Graphviz等工具使用"""
        nodes = []
        for ent in self.entities.values():
            nodes.append({"id": ent.name, "label": ent.name, "type": ent.entity_type, "mentions": ent.mentions})

        edges = []
        for rel in self.relations:
            edges.append({"source": rel.source, "target": rel.target, "label": rel.relation_type, "weight": rel.weight})

        return {"nodes": nodes, "edges": edges, "metadata": self.get_statistics()}

    def merge_similar_entities(self, threshold: float = 0.8):
        """合并相似实体（基于名称相似度）"""
        import difflib

        entity_names = list(self.entities.keys())
        to_merge = []

        for i, name1 in enumerate(entity_names):
            for name2 in entity_names[i + 1 :]:
                similarity = difflib.SequenceMatcher(None, name1, name2).ratio()
                if similarity >= threshold:
                    to_merge.append((name1, name2, similarity))

        for name1, name2, sim in to_merge:
            if name1 in self.entities and name2 in self.entities:
                merged = self.entities[name1]
                merged.mentions += self.entities[name2].mentions
                self.entities[name2] = merged

                for rel in self.relations:
                    if rel.target == name2:
                        rel.target = name1
                    if rel.source == name2:
                        rel.source = name1

                del self.entities[name2]
                logger.info(f"[KnowledgeGraph] 合并相似实体: {name1} <-> {name2} (相似度: {sim:.2f})")

        if to_merge:
            self._save_graph()

    def prune_low_weight_relations(self, min_weight: int = 2):
        """剪枝低权重关系"""
        original_count = len(self.relations)
        self.relations = [r for r in self.relations if r.weight >= min_weight]
        removed = original_count - len(self.relations)

        if removed > 0:
            self._save_graph()
            logger.info(f"[KnowledgeGraph] 剪枝了 {removed} 条低权重关系")

    def get_path(self, source: str, target: str, max_hops: int = 3) -> Optional[List[str]]:
        """查找两个实体之间的最短路径"""
        if source not in self.entities or target not in self.entities:
            return None

        if source == target:
            return [source]

        visited = {source}
        queue = [(source, [source])]

        while queue:
            current, path = queue.pop(0)

            if len(path) > max_hops:
                continue

            for rel in self.relations:
                next_node = None
                if rel.source == current and rel.target not in visited:
                    next_node = rel.target
                elif rel.target == current and rel.source not in visited:
                    next_node = rel.source

                if next_node:
                    new_path = path + [next_node]
                    if next_node == target:
                        return new_path
                    visited.add(next_node)
                    queue.append((next_node, new_path))

        return None

    def clear(self):
        """清空图谱"""
        self.entities.clear()
        self.relations.clear()
        self._save_graph()
        logger.info("[KnowledgeGraph] 图谱已清空")

    # ========== 双层解析引擎（阶段一：声明式 Markdown 解析）==========

    def parse_graph_from_markdown(self, markdown_content: str) -> Tuple[List[Dict], List[Dict]]:
        """
        从 Markdown 内容中解析知识图谱（双层解析器）

        Args:
            markdown_content: 包含图谱章节的 Markdown 文本

        Returns:
            Tuple[实体列表, 关系列表] - 解析出的结构化数据
        """
        entities = []
        relations = []
        seen_entities = set()

        # 提取图谱章节
        graph_section = self._extract_graph_section(markdown_content)
        if not graph_section:
            logger.debug("[KnowledgeGraph] 未找到图谱章节")
            return entities, relations

        # 逐行解析
        for line in graph_section.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("- **"):
                continue

            # 第一层：尝试正则快速解析
            parsed = self._parse_with_regex(line)
            if parsed:
                source, target, rel_type, weight, note = parsed
                entities.extend(self._collect_entities(source, target, seen_entities))
                relations.append({"source": source, "target": target, "type": rel_type, "weight": weight, "note": note})
            else:
                # 第二层：标记为需要 LLM 模糊解析（预留接口）
                logger.debug(f"[KnowledgeGraph] 正则解析失败，需 LLM 模糊解析: {line[:50]}...")

        logger.info(f"[KnowledgeGraph] Markdown 解析完成: {len(entities)} 个实体, {len(relations)} 条关系")
        return entities, relations

    def _extract_graph_section(self, markdown_content: str) -> Optional[str]:
        """从 Markdown 中提取图谱章节内容"""
        lines = markdown_content.split("\n")
        in_graph_section = False
        section_lines = []

        for i, line in enumerate(lines):
            if GRAPH_SECTION_HEADER in line:
                in_graph_section = True
                continue

            if in_graph_section:
                # 遇到下一个同级或更高级标题，结束提取
                if line.startswith("## ") and GRAPH_SECTION_HEADER not in line:
                    break
                section_lines.append(line)

        return "\n".join(section_lines) if section_lines else None

    def _parse_with_regex(self, line: str) -> Optional[Tuple[str, str, str, float, str]]:
        """
        第一层解析器：使用正则快速解析标准格式

        Args:
            line: 单行 Markdown 文本

        Returns:
            Tuple[source, target, relation_type, weight, note] 或 None
        """
        match = GRAPH_RELATION_PATTERN.match(line)
        if match:
            source = match.group("source").strip()
            target = match.group("target").strip()
            rel_type = match.group("relation_type").strip()
            weight = float(match.group("weight")) if match.group("weight") else 1.0
            note = match.group("note").strip() if match.group("note") else ""

            if source and target and rel_type:
                return (source, target, rel_type, weight, note)

        return None

    async def _parse_with_llm(self, line: str, context=None) -> Optional[Tuple[str, str, str, float, str]]:
        """
        第二层解析器：LLM 模糊解析与自修复（容错机制）

        当正则解析失败时调用，用于处理：
        - 用户手滑写错的格式
        - 自然语言描述的关系
        - 非标准但可理解的格式

        Args:
            line: 无法用正则解析的文本行
            context: AstrBot Context 实例（可选）

        Returns:
            标准化的 Tuple 或 None
        """
        if not context:
            logger.warning("[KnowledgeGraph] LLM 模糊解析需要 context，跳过")
            return None

        try:
            prompt = f"""请将以下非标准的知识图谱关系描述转换为标准格式。

标准格式示例：
- [张三] --(伴侣)--> [李四] | 权重: 1.0 | 备注: 2023年结婚

待解析文本：
{line}

请严格按以下 JSON 格式返回（不要包含其他文字）：
{{"source": "实体A", "target": "实体B", "type": "关系类型", "weight": 1.0, "note": "备注"}}"""

            # 调用 LLM（适配多种 Provider 接口）
            response = await self._call_llm(context, prompt)

            if response:
                # 安全解析 JSON
                result = safe_json_loads(response)
                if result and all(k in result for k in ["source", "target", "type"]):
                    source = result.get("source", "").strip()
                    target = result.get("target", "").strip()
                    rel_type = result.get("type", "unknown").strip()
                    weight = float(result.get("weight", 1.0))
                    note = result.get("note", "").strip()

                    if source and target:
                        logger.info(f"[KnowledgeGraph] LLM 模糊解析成功: {line[:30]}... -> 标准格式")
                        return (source, target, rel_type, weight, note)

        except Exception as e:
            logger.error(f"[KnowledgeGraph] LLM 模糊解析失败: {e}")

        return None

    async def _call_llm(self, context, prompt: str) -> Optional[str]:
        """
        调用 LLM（使用 AstrBot v4.x 推荐的 llm_generate 接口）

        Args:
            context: AstrBot Context 实例
            prompt: 提示词

        Returns:
            LLM 响应文本或 None
        """
        try:
            provider_id = await context.get_current_chat_provider_id(None)
            response = await context.llm_generate(chat_provider_id=provider_id, prompt=prompt)
            if response and response.completion_text:
                return response.completion_text.strip()
        except Exception as e:
            logger.debug(f"[KnowledgeGraph] llm_generate 接口调用失败: {e}")

        return None

    def _extract_text_from_response(self, response) -> Optional[str]:
        """从 LLM 响应中提取纯文本"""
        if isinstance(response, str):
            return response.strip()

        if hasattr(response, "completion_text"):
            return response.completion_text.strip()

        if hasattr(response, "text"):
            return response.text.strip()

        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, str):
                return content.strip()

        return None

    def _collect_entities(self, source: str, target: str, seen_entities: Set[str]) -> List[Dict]:
        """收集实体（去重）"""
        entities = []
        for name in [source, target]:
            if name not in seen_entities:
                seen_entities.add(name)
                entities.append({"name": name})
        return entities

    def format_relation_to_markdown(self, relation: Relation) -> str:
        """
        将关系对象格式化为标准 Markdown 语法

        Args:
            relation: Relation 数据类实例

        Returns:
            标准 Markdown 格式的字符串
        """
        weight_str = f"{relation.weight:.1f}" if relation.weight != 1 else "1.0"
        note_str = f" | 备注: {'; '.join(relation.evidence[-3:])}" if relation.evidence else ""
        return (
            f"- [{relation.source}] --({relation.relation_type})--> [{relation.target}] | 权重: {weight_str}{note_str}"
        )

    def get_core_relations_for_markdown(self) -> List[Relation]:
        """
        获取所有核心关系（权重 >= 阈值的关系）

        用于写入 Markdown 文件（常驻上下文）

        Returns:
            核心关系列表（按权重降序排列）
        """
        core_relations = [r for r in self.relations if r.weight >= CORE_RELATION_THRESHOLD]
        core_relations.sort(key=lambda x: x.weight, reverse=True)
        return core_relations

    def generate_markdown_graph_section(self) -> str:
        """
        生成完整的图谱章节 Markdown 内容

        用于回写到 PROFILE.md

        Returns:
            格式化的 Markdown 文本
        """
        core_relations = self.get_core_relations_for_markdown()

        lines = [
            f"{GRAPH_SECTION_HEADER}",
            "",
            "- **重要关联人**：",
        ]

        for rel in core_relations:
            md_line = f"  {self.format_relation_to_markdown(rel)}"
            lines.append(md_line)

        if not core_relations:
            lines.append("  *(暂无核心关系记录)*")

        lines.append("")
        lines.append("- **关键物理节点**：")
        lines.append("  *(暂无物理节点记录)*")
        lines.append("")

        return "\n".join(lines)

    # ========== 正向同步引擎（阶段二：MD -> JSON）==========

    async def sync_from_markdown(self, profile_path: Path, context=None) -> Dict[str, Any]:
        """
        从 Markdown 文件正向同步到知识图谱（MD -> JSON）

        这是声明式干预的核心方法。用户在 Markdown 中编辑的关系
        将无条件覆盖 JSON 中的数据。

        Args:
            profile_path: P_PROFILE.md 或 G_PROFILE.md 的路径
            context: AstrBot Context 实例（用于模糊解析，可选）

        Returns:
            同步统计信息字典
        """
        if not profile_path.exists():
            logger.warning(f"[KnowledgeGraph] 画像文件不存在: {profile_path}")
            return {"status": "error", "message": "文件不存在"}

        try:
            # 读取 Markdown 内容
            markdown_content = profile_path.read_text(encoding="utf-8")

            # 第一层：正则解析所有标准格式的关系
            entities, relations = self.parse_graph_from_markdown(markdown_content)

            # 第二层：尝试 LLM 模糊解析非标准行（如果提供了 Context）
            if context:
                graph_section = self._extract_graph_section(markdown_content)
                if graph_section:
                    for line in graph_section.split("\n"):
                        line = line.strip()
                        if not line or line.startswith("#") or line.startswith("- **"):
                            continue

                        if not self._parse_with_regex(line):
                            parsed = await self._parse_with_llm(line, context)
                            if parsed:
                                source, target, rel_type, weight, note = parsed
                                relations.append(
                                    {
                                        "source": source,
                                        "target": target,
                                        "type": rel_type,
                                        "weight": weight,
                                        "note": note,
                                    }
                                )
                                if not any(e.get("name") == source for e in entities):
                                    entities.append({"name": source})
                                if not any(e.get("name") == target for e in entities):
                                    entities.append({"name": target})

            # 执行同步：以 Markdown 为准，完全重建关系列表
            sync_result = await self._execute_sync(entities, relations)

            # 记录同步时间戳（用于并发控制）
            self._last_sync_time = time.time()
            self._last_sync_source = str(profile_path)

            logger.info(
                f"[KnowledgeGraph] 正向同步完成: "
                f"{sync_result['entities_added']} 实体, "
                f"{sync_result['relations_updated']} 关系更新, "
                f"{sync_result['relations_removed']} 关系移除"
            )

            return {
                "status": "success",
                **sync_result,
                "source_file": str(profile_path.name),
                "sync_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"[KnowledgeGraph] 正向同步失败: {e}")
            return {"status": "error", "message": str(e)}

    async def _execute_sync(self, md_entities: List[Dict], md_relations: List[Dict]) -> Dict[str, int]:
        """
        执行实际的同步操作（以 Markdown 为准）

        策略：
        1. 清空现有关系列表
        2. 将 Markdown 中的关系全部导入
        3. 更新或创建实体

        Args:
            md_entities: 从 MD 解析的实体列表
            md_relations: 从 MD 解析的关系列表

        Returns:
            同步统计信息
        """
        async with self._lock:
            # 记录旧关系数量（用于计算移除数量）
            old_relation_count = len(self.relations)

            # 1. 更新/创建实体
            entities_added = 0
            for entity in md_entities:
                name = entity.get("name", "").strip()
                if not name:
                    continue

                if name in self.entities:
                    self.entities[name].mentions += 1
                    self.entities[name].last_seen = time.time()
                else:
                    entity_type = entity.get("type", "unknown")
                    self.entities[name] = Entity(name=name, entity_type=entity_type)
                    entities_added += 1

            # 2. 以 Markdown 为准，完全重建关系列表
            new_relations = []
            relations_updated = 0

            for rel in md_relations:
                source = rel.get("source", "").strip()
                target = rel.get("target", "").strip()
                rel_type = rel.get("type", "unknown").strip()
                weight = int(rel.get("weight", 1))
                note = rel.get("note", "")

                if not source or not target:
                    continue

                evidence = [note] if note else []

                new_relations.append(
                    Relation(source=source, target=target, relation_type=rel_type, weight=weight, evidence=evidence)
                )
                relations_updated += 1

            # 替换关系列表
            self.relations = new_relations
            relations_removed = (
                old_relation_count - len(new_relations) if old_relation_count > len(new_relations) else 0
            )

            # 3. 保存到文件
            self._save_graph()

            return {
                "entities_added": entities_added,
                "relations_updated": relations_updated,
                "relations_removed": max(0, relations_removed),
                "total_entities": len(self.entities),
                "total_relations": len(self.relations),
            }

    def check_sync_conflict(self, profile_path: Path) -> bool:
        """
        检查是否存在并发冲突（基于文件 mtime）

        Args:
            profile_path: Markdown 文件路径

        Returns:
            True 表示有冲突需要处理，False 表示安全
        """
        if not hasattr(self, "_last_sync_time") or not self._last_sync_time:
            return False

        if not profile_path.exists():
            return True

        file_mtime = profile_path.stat().st_mtime

        if file_mtime > self._last_sync_time:
            logger.info(f"[KnowledgeGraph] 检测到文件更新: " f"{profile_path.name} 在上次同步后被修改")
            return True

        return False

    def get_last_sync_info(self) -> Dict[str, Any]:
        """获取最近一次同步的信息"""
        return {
            "last_sync_time": getattr(self, "_last_sync_time", None),
            "last_sync_source": getattr(self, "_last_sync_source", None),
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
        }

    # ========== 反向同步引擎（阶段三：JSON -> MD + 阈值晋升）==========

    async def sync_to_markdown(self, profile_path: Path, force: bool = False) -> Dict[str, Any]:
        """
        反向同步：将 JSON 中的核心关系回写到 Markdown（JSON -> MD）

        触发条件：
        1. force=True 时强制执行
        2. 检测到有新的核心关系（权重 >= 阈值）且不在 Markdown 中时自动触发

        Args:
            profile_path: P_PROFILE.md 或 G_PROFILE.md 的路径
            force: 是否强制执行（忽略冲突检查）

        Returns:
            回写统计信息字典
        """
        if not profile_path.exists():
            logger.warning(f"[KnowledgeGraph] 画像文件不存在: {profile_path}")
            return {"status": "error", "message": "文件不存在"}

        try:
            # 并发控制：检查文件是否在外部被修改
            if not force and self.check_sync_conflict(profile_path):
                logger.warning(f"[KnowledgeGraph] 跳过反向同步：" f"{profile_path.name} 存在并发冲突")
                return {"status": "skipped", "message": "文件存在并发冲突，跳过回写", "conflict": True}

            # 读取现有 Markdown 内容
            existing_content = profile_path.read_text(encoding="utf-8")

            # 提取现有的核心关系（用于去重）
            existing_entities, existing_relations = self.parse_graph_from_markdown(existing_content)
            existing_relation_keys = {(r["source"], r["target"], r["type"]) for r in existing_relations}

            # 获取需要晋升的核心关系（权重 >= 阈值 且 不在 Markdown 中）
            new_core_relations = []
            for rel in self.relations:
                rel_key = (rel.source, rel.target, rel.relation_type)

                if rel.weight >= CORE_RELATION_THRESHOLD and rel_key not in existing_relation_keys:
                    new_core_relations.append(rel)

            if not new_core_relations and not force:
                logger.debug("[KnowledgeGraph] 无新核心关系需要回写")
                return {"status": "no_action", "message": "无新核心关系需要回写", "new_relations_count": 0}

            # 生成新的图谱章节内容
            all_core_relations = self.get_core_relations_for_markdown()
            new_graph_section = self.generate_markdown_graph_section()

            # 安全替换：只替换图谱章节，保留其他所有内容
            updated_content = self._replace_graph_section(existing_content, new_graph_section)

            # 写入文件
            profile_path.write_text(updated_content, encoding="utf-8")

            # 更新同步时间戳
            self._last_sync_time = time.time()
            self._last_sync_source = str(profile_path)

            logger.info(
                f"[KnowledgeGraph] 反向同步完成: " f"{len(new_core_relations)} 条新核心关系已回写到 {profile_path.name}"
            )

            return {
                "status": "success",
                "new_relations_count": len(new_core_relations),
                "total_core_relations": len(all_core_relations),
                "target_file": str(profile_path.name),
                "sync_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"[KnowledgeGraph] 反向同步失败: {e}")
            return {"status": "error", "message": str(e)}

    def _replace_graph_section(self, content: str, new_section: str) -> str:
        """
        安全地替换 Markdown 中的图谱章节

        只替换 ## 4. 核心关系图谱 章节，保留其他所有内容不变

        Args:
            content: 原始 Markdown 内容
            new_section: 新的图谱章节内容

        Returns:
            替换后的完整 Markdown 内容
        """
        lines = content.split("\n")
        result_lines = []
        in_graph_section = False
        section_replaced = False

        i = 0
        while i < len(lines):
            line = lines[i]

            if GRAPH_SECTION_HEADER in line:
                in_graph_section = True
                if not section_replaced:
                    result_lines.append(new_section)
                    section_replaced = True
                i += 1
                continue

            if in_graph_section:
                if line.startswith("## ") and GRAPH_SECTION_HEADER not in line:
                    in_graph_section = False
                    result_lines.append(line)
                else:
                    i += 1
                    continue

            result_lines.append(line)
            i += 1

        # 如果没有找到原有章节，追加到末尾
        if not section_replaced:
            result_lines.append("")
            result_lines.append(new_section)

        return "\n".join(result_lines)

    def check_for_promotion_candidates(self) -> List[Relation]:
        """
        检查是否有符合晋升条件的关系

        返回所有权重达到阈值但可能尚未在 Markdown 中的关系

        Returns:
            候选关系列表
        """
        candidates = [r for r in self.relations if r.weight >= CORE_RELATION_THRESHOLD]
        candidates.sort(key=lambda x: x.weight, reverse=True)
        return candidates

    async def auto_promote_and_sync(self, profile_path: Path, context=None) -> Dict[str, Any]:
        """
        自动晋升并双向同步（智能协调器）

        完整流程：
        1. 先执行正向同步（MD -> JSON）：确保用户的修改生效
        2. 再执行反向同步（JSON -> MD）：将 AI 学习到的新核心关系回写

        Args:
            profile_path: Markdown 文件路径
            context: AstrBot Context 实例（可选）

        Returns:
            完整的同步报告
        """
        report = {
            "forward_sync": None,
            "reverse_sync": None,
            "promotion_candidates": 0,
            "timestamp": datetime.now().isoformat(),
        }

        # 步骤 1：正向同步（用户优先）
        forward_result = await self.sync_from_markdown(profile_path, context)
        report["forward_sync"] = forward_result

        if forward_result.get("status") != "success":
            report["warning"] = "正向同步失败，跳过反向同步"
            return report

        # 步骤 2：检查晋升候选
        candidates = self.check_for_promotion_candidates()
        report["promotion_candidates"] = len(candidates)

        # 步骤 3：反向同步（AI 学习成果沉淀）
        reverse_result = await self.sync_to_markdown(profile_path, force=True)
        report["reverse_sync"] = reverse_result

        logger.info(
            f"[KnowledgeGraph] 双向同步完成: "
            f"正向={forward_result.get('status')}, "
            f"反向={reverse_result.get('status')}, "
            f"候选晋升={len(candidates)}"
        )

        return report
