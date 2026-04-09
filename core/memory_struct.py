# core/memory_struct.py
"""
增强的记忆结构模块 - 支持记忆三元组 (judgment + reasoning + tags)
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StructuredMemory:
    """结构化记忆数据类 - 记忆三元组结构"""

    # 核心三元组
    judgment: str = ""  # 论断 - 核心内容
    reasoning: str = ""  # 理由 - 为什么记住这个
    tags: List[str] = field(default_factory=list)  # 标签

    # 元数据
    memory_type: str = "fact"  # 记忆类型
    timestamp: str = ""  # 时间戳
    status: str = "active"  # 状态
    privacy_level: str = "private"  # 隐私级别
    strength: float = 1.0  # 强度
    useful_score: float = 5.0  # 有用性评分

    # 主动记忆标记
    is_active: bool = False  # 是否为主动记忆（永不衰减）

    # 原始内容（向后兼容）
    raw_content: str = ""

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = []

        # 标题行
        status_tag = f" [Status: {self.status}]" if self.status else ""
        active_tag = " [Active: true]" if self.is_active else ""

        header = (
            f"### [{self.timestamp}] ({self.memory_type})"
            f"{status_tag}"
            f"{active_tag}"
            f" [Privacy: {self.privacy_level}]"
            f" [Strength: {self.strength:.1f}]"
            f" [Score: {self.useful_score:.1f}]"
        )
        lines.append(header)

        # 三元组内容
        if self.judgment:
            lines.append(f"**论断**: {self.judgment}")
        if self.reasoning:
            lines.append(f"**理由**: {self.reasoning}")
        if self.tags:
            tag_str = ", ".join(f"[{tag}]" for tag in self.tags)
            lines.append(f"**标签**: {tag_str}")

        # 原始内容（向后兼容）
        if self.raw_content and not self.judgment:
            lines.append(self.raw_content)

        return "\n".join(lines) + "\n"

    @classmethod
    def from_markdown(cls, block: str) -> Optional["StructuredMemory"]:
        """从 Markdown 块解析结构化记忆"""
        if not block.strip():
            return None

        memory = cls()
        lines = block.strip().split("\n")

        if not lines:
            return None

        # 解析标题行
        header_line = lines[0]
        memory._parse_header(header_line)

        # 解析内容行
        content_lines = lines[1:] if len(lines) > 1 else []
        memory._parse_content(content_lines)

        return memory

    def _parse_header(self, header: str):
        """解析标题行"""
        # 提取时间戳
        ts_match = re.search(r"\[(.*?)\]", header)
        if ts_match:
            self.timestamp = ts_match.group(1)

        # 提取记忆类型
        type_match = re.search(r"\((.*?)\)", header)
        if type_match:
            self.memory_type = type_match.group(1)

        # 提取状态
        status_match = re.search(r"\[Status:\s*(\w+)\]", header)
        if status_match:
            self.status = status_match.group(1)

        # 提取主动记忆标记
        active_match = re.search(r"\[Active:\s*(\w+)\]", header)
        if active_match:
            self.is_active = active_match.group(1).lower() == "true"

        # 提取隐私级别
        privacy_match = re.search(r"\[Privacy:\s*(\w+)\]", header)
        if privacy_match:
            self.privacy_level = privacy_match.group(1)

        # 提取强度
        strength_match = re.search(r"\[Strength:\s*([\d.]+)\]", header)
        if strength_match:
            try:
                self.strength = float(strength_match.group(1))
            except (ValueError, TypeError, AttributeError):
                pass

        # 提取有用性评分
        score_match = re.search(r"\[Score:\s*([\d.]+)\]", header)
        if score_match:
            try:
                self.useful_score = float(score_match.group(1))
            except (ValueError, TypeError, AttributeError):
                pass

    def _parse_content(self, lines: List[str]):
        """解析内容行"""
        raw_parts = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 解析论断
            if line.startswith("**论断**:"):
                self.judgment = line[len("**论断**:") :].strip()
            # 解析理由
            elif line.startswith("**理由**:"):
                self.reasoning = line[len("**理由**:") :].strip()
            # 解析标签
            elif line.startswith("**标签**:"):
                tag_str = line[len("**标签**:") :].strip()
                # 提取 [tag] 格式的标签
                self.tags = re.findall(r"\[(.*?)\]", tag_str)
                if not self.tags:
                    # 如果没有 [tag] 格式，尝试逗号分隔
                    self.tags = [t.strip() for t in tag_str.split(",") if t.strip()]
            else:
                raw_parts.append(line)

        # 保存原始内容
        if raw_parts:
            self.raw_content = "\n".join(raw_parts)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "judgment": self.judgment,
            "reasoning": self.reasoning,
            "tags": self.tags,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp,
            "status": self.status,
            "privacy_level": self.privacy_level,
            "strength": self.strength,
            "useful_score": self.useful_score,
            "is_active": self.is_active,
            "raw_content": self.raw_content,
        }

    @classmethod
    def create_simple(
        cls,
        content: str,
        memory_type: str = "fact",
        privacy_level: str = "private",
        strength: float = 1.0,
        useful_score: float = 5.0,
        status: str = "active",
        is_active: bool = False,
    ) -> "StructuredMemory":
        """创建简单的结构化记忆（向后兼容）"""

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return cls(
            raw_content=content,
            memory_type=memory_type,
            timestamp=timestamp,
            status=status,
            privacy_level=privacy_level,
            strength=strength,
            useful_score=useful_score,
            is_active=is_active,
        )

    @classmethod
    def create_triple(
        cls,
        judgment: str,
        reasoning: str = "",
        tags: List[str] = None,
        memory_type: str = "fact",
        privacy_level: str = "private",
        strength: float = 1.0,
        useful_score: float = 5.0,
        status: str = "active",
        is_active: bool = False,
    ) -> "StructuredMemory":
        """创建三元组结构化记忆"""

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return cls(
            judgment=judgment,
            reasoning=reasoning,
            tags=tags or [],
            memory_type=memory_type,
            timestamp=timestamp,
            status=status,
            privacy_level=privacy_level,
            strength=strength,
            useful_score=useful_score,
            is_active=is_active,
        )
