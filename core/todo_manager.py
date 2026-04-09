from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from astrbot.api import logger


@dataclass
class TodoItem:
    """待办事项数据类"""

    id: int
    content: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "pending"


class TodoManager:
    """
    待办事项管理器

    核心职责：
    1. 解析结构化 Markdown TODO 文件
    2. 提供增删改查 (CRUD) 接口
    3. 维护排序规则（未完成正序，已完成倒序）
    4. 自动归档已完成项
    """

    def __init__(self, data_dir: Path, scope: str = "personal"):
        self.data_dir = data_dir
        self.scope = scope
        self._next_id = 1
        self._cache: Optional[Dict[str, List[TodoItem]]] = None

    def _get_todo_file_path(self, uid: str, is_archive: bool = False) -> Path:
        """获取 TODO 文件路径"""
        if self.scope == "personal":
            base_dir = self.data_dir / "profiles" / uid
            if is_archive:
                return base_dir / "todo_archive"
            return base_dir / "Personal_TODO.md"
        else:
            group_id = uid.replace("group_", "")
            base_dir = self.data_dir / "groups" / group_id
            if is_archive:
                return base_dir / "todo_archive"
            return base_dir / "Group_TODO.md"

    def _parse_todo_file(self, file_path: Path) -> Tuple[List[TodoItem], List[TodoItem]]:
        """解析 TODO Markdown 文件

        Returns:
            (pending_items, completed_items)
        """
        if not file_path.exists():
            return [], []

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"[TodoManager] 读取 TODO 文件失败: {e}")
            return [], []

        pending_items = []
        completed_items = []
        current_id = 1

        lines = content.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("## 未完成"):
                current_section = "pending"
                continue
            elif line.startswith("## 已完成"):
                current_section = "completed"
                continue

            if current_section is None:
                continue

            match = re.match(r"^\s*-\s*\[(x| )\]\s*\[([^\]]+)\]\s*(.+?)(?:\s*\(完成于:\s*([^\)]+)\))?$", line)
            if not match:
                continue

            checkbox = match.group(1).strip()
            timestamp_str = match.group(2).strip() if match.group(2) else None
            content = match.group(3).strip() if match.group(3) else ""

            if not content:
                continue

            try:
                created_at = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                created_at = datetime.now()

            completed_at = None
            if match.group(2):
                completed_match = re.search(r"完成于:\s*(.+)", match.group(2))
                if completed_match:
                    try:
                        completed_at = datetime.strptime(completed_match.group(1).strip(), "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        completed_at = datetime.now()

            if checkbox == "x":
                completed_items.append(
                    TodoItem(
                        id=current_id,
                        content=content,
                        created_at=created_at,
                        completed_at=completed_at,
                        status="completed",
                    )
                )
            else:
                pending_items.append(
                    TodoItem(id=current_id, content=content, created_at=created_at, completed_at=None, status="pending")
                )

            current_id += 1

        return pending_items, completed_items

    def _generate_markdown(self, pending_items: List[TodoItem], completed_items: List[TodoItem]) -> str:
        """生成结构化 Markdown 内容"""
        lines = ["# 个人待办清单" if self.scope == "personal" else "# 群组待办清单"]
        lines.append("")

        lines.append("## 未完成 (Pending)")
        lines.append("<!-- 待办事项将在此处显示 -->")
        lines.append("")

        for item in sorted(pending_items, key=lambda x: x.created_at):
            timestamp = item.created_at.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"- [ ] [{timestamp}] {item.content}")

        lines.append("")
        lines.append("## 已完成 (Completed)")
        lines.append("<!-- 已完成的待办事项将在此处显示 -->")
        lines.append("")

        for item in sorted(completed_items, key=lambda x: (x.completed_at or datetime.min), reverse=True):
            timestamp = item.created_at.strftime("%Y-%m-%d %H:%M:%S")
            completed_str = f" (完成于: {item.completed_at.strftime('%Y-%m-%d %H:%M:%S')})" if item.completed_at else ""
            lines.append(f"- [x] [{timestamp}] {item.content}{completed_str}")

        return "\n".join(lines)

    def get_hot_memory(self, uid: str) -> str:
        """获取热记忆内容（未完成 + 最近3天已完成）

        Returns:
            格式化的待办摘要文本
        """
        todo_file = self._get_todo_file_path(uid, is_archive=False)
        pending_items, completed_items = self._parse_todo_file(todo_file)

        three_days_ago = datetime.now() - timedelta(days=3)
        recent_completed = [
            item for item in completed_items if item.completed_at and item.completed_at > three_days_ago
        ]

        lines = ["【当前待办状态】"]
        lines.append("")

        if pending_items:
            lines.append("**未完成：**")
            for i, item in enumerate(sorted(pending_items, key=lambda x: x.created_at), 1):
                lines.append(f"{i+1}. {item.content[:50]}{'...' if len(item.content) > 50 else ''}")
        else:
            lines.append("**无未完成待办**")

        lines.append("")

        if recent_completed:
            lines.append("**最近完成（3天内）：**")
            for i, item in enumerate(sorted(recent_completed, key=lambda x: x.completed_at, reverse=True), 1):
                lines.append(f"{i+1}. {item.content[:50]}{'...' if len(item.content) > 50 else ''}")
        else:
            lines.append("**无最近完成记录**")

        return "\n".join(lines)

    def add_todo(self, uid: str, content: str) -> TodoItem:
        """添加新待办"""
        todo_file = self._get_todo_file_path(uid, is_archive=False)
        pending_items, completed_items = self._parse_todo_file(todo_file)

        new_item = TodoItem(
            id=self._next_id, content=content, created_at=datetime.now(), completed_at=None, status="pending"
        )
        self._next_id += 1

        pending_items.append(new_item)
        markdown_content = self._generate_markdown(pending_items, completed_items)

        try:
            todo_file.write_text(markdown_content, encoding="utf-8")
            logger.info(f"[TodoManager] 已添加待办: {content[:30]}... (ID: {new_item.id})")
        except Exception as e:
            logger.error(f"[TodoManager] 写入 TODO 文件失败: {e}")
            raise

        return new_item

    def complete_todo(self, uid: str, task_id: int) -> bool:
        """标记待办为已完成"""
        todo_file = self._get_todo_file_path(uid, is_archive=False)
        pending_items, completed_items = self._parse_todo_file(todo_file)

        target_item = None
        for item in pending_items:
            if item.id == task_id:
                target_item = item
                break

        if not target_item:
            logger.warning(f"[TodoManager] 未找到待办 ID: {task_id}")
            return False

        target_item.completed_at = datetime.now()
        target_item.status = "completed"

        completed_items.insert(0, target_item)
        markdown_content = self._generate_markdown(pending_items, completed_items)

        try:
            todo_file.write_text(markdown_content, encoding="utf-8")
            logger.info(f"[TodoManager] 已完成待办: {target_item.content[:30]}... (ID: {task_id})")
            return True
        except Exception as e:
            logger.error(f"[TodoManager] 写入 TODO 文件失败: {e}")
            return False

    def update_todo(self, uid: str, task_id: int, new_content: str) -> bool:
        """更新待办内容"""
        todo_file = self._get_todo_file_path(uid, is_archive=False)
        pending_items, completed_items = self._parse_todo_file(todo_file)

        target_item = None
        for item in pending_items:
            if item.id == task_id:
                target_item = item
                break

        if not target_item:
            logger.warning(f"[TodoManager] 未找到待办 ID: {task_id}")
            return False

        target_item.content = new_content

        markdown_content = self._generate_markdown(pending_items, completed_items)

        try:
            todo_file.write_text(markdown_content, encoding="utf-8")
            logger.info(f"[TodoManager] 已更新待办: {new_content[:30]}... (ID: {task_id})")
            return True
        except Exception as e:
            logger.error(f"[TodoManager] 写入 TODO 文件失败: {e}")
            return False

    def delete_todo(self, uid: str, task_id: int) -> bool:
        """删除待办"""
        todo_file = self._get_todo_file_path(uid, is_archive=False)
        pending_items, completed_items = self._parse_todo_file(todo_file)

        pending_items = [item for item in pending_items if item.id != task_id]
        completed_items = [item for item in completed_items if item.id != task_id]

        markdown_content = self._generate_markdown(pending_items, completed_items)

        try:
            todo_file.write_text(markdown_content, encoding="utf-8")
            logger.info(f"[TodoManager] 已删除待办 ID: {task_id}")
            return True
        except Exception as e:
            logger.error(f"[TodoManager] 写入 TODO 文件失败: {e}")
            return False

    def query_history(
        self,
        uid: str,
        time_range: Optional[str] = None,
        specific_date: Optional[str] = None,
        keyword: Optional[str] = None,
        status: str = "all",
        limit: int = 20,
    ) -> List[TodoItem]:
        """查询历史待办

        Args:
            uid: 用户 ID
            time_range: 时间范围，如 "2026-03" (某月), "2026" (某年)
            specific_date: 具体日期，如 "2026-03-05"
            keyword: 关键词搜索
            status: 状态过滤："completed", "pending", "all"
            limit: 返回条数限制

        Returns:
            匹配的待办列表
        """
        todo_file = self._get_todo_file_path(uid, is_archive=False)
        pending_items, completed_items = self._parse_todo_file(todo_file)

        all_items = pending_items + completed_items
        filtered_items = []

        for item in all_items:
            if status == "pending" and item.status != "pending":
                continue
            if status == "completed" and item.status != "completed":
                continue

            if keyword and keyword.lower() not in item.content.lower():
                continue

            if specific_date:
                item_date = item.created_at.strftime("%Y-%m-%d")
                if item_date != specific_date:
                    continue
            elif time_range:
                if time_range == item.created_at.strftime("%Y-%m") or time_range == item.created_at.strftime("%Y"):
                    pass
                else:
                    continue

            filtered_items.append(item)

            if len(filtered_items) >= limit:
                break

        filtered_items.sort(key=lambda x: (x.completed_at or x.created_at), reverse=True)
        return filtered_items[:limit]

    def archive_old_completed(self, uid: str) -> int:
        """归档旧已完成项

        将上个月及以前的已完成项移动到归档文件

        Returns:
            归档的条目数量
        """
        todo_file = self._get_todo_file_path(uid, is_archive=False)
        pending_items, completed_items = self._parse_todo_file(todo_file)

        if not completed_items:
            return 0

        current_month = datetime.now().strftime("%Y-%m")
        to_archive = []
        remaining_completed = []

        for item in completed_items:
            if not item.completed_at:
                continue

            item_month = item.completed_at.strftime("%Y-%m")
            if item_month < current_month:
                to_archive.append(item)
            else:
                remaining_completed.append(item)

        if not to_archive:
            return 0

        archive_dir = self._get_todo_file_path(uid, is_archive=True)
        archive_dir.mkdir(parents=True, exist_ok=True)

        archive_file = archive_dir / f"{to_archive[0].completed_at.strftime('%Y-%m')}.md"

        try:
            if archive_file.exists():
                existing_content = archive_file.read_text(encoding="utf-8")
                lines = existing_content.split("\n")
                for item in to_archive:
                    timestamp = item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    completed_str = (
                        f" (完成于: {item.completed_at.strftime('%Y-%m-%d %H:%M:%S')})" if item.completed_at else ""
                    )
                    lines.append(f"- [x] [{timestamp}] {item.content}{completed_str}")
                existing_content = "\n".join(lines)
            else:
                archive_lines = ["# 归档待办 - {to_archive[0].completed_at.strftime('%Y-%m')}"]
                for item in sorted(to_archive, key=lambda x: x.completed_at):
                    timestamp = item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    completed_str = (
                        f" (完成于: {item.completed_at.strftime('%Y-%m-%d %H:%M:%S')})" if item.completed_at else ""
                    )
                    archive_lines.append(f"- [x] [{timestamp}] {item.content}{completed_str}")
                existing_content = "\n".join(archive_lines)

            archive_file.write_text(existing_content, encoding="utf-8")
            logger.info(f"[TodoManager] 已归档 {len(to_archive)} 条待办到: {archive_file.name}")
        except Exception as e:
            logger.error(f"[TodoManager] 归档失败: {e}")
            return 0

        markdown_content = self._generate_markdown(pending_items, remaining_completed)

        try:
            todo_file.write_text(markdown_content, encoding="utf-8")
            logger.info(f"[TodoManager] 主文件已更新，归档 {len(to_archive)} 条")
            return len(to_archive)
        except Exception as e:
            logger.error(f"[TodoManager] 更新主文件失败: {e}")
            return 0
