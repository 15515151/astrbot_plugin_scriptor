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

    def _get_todo_file_path(self, uid: str) -> Path:
        """获取 TODO 主文件路径
        
        Args:
            uid: 用户 ID 或群组 ID
            
        Returns:
            文件路径
        """
        if self.scope == "personal":
            base_dir = self.data_dir / "profiles" / uid
            return base_dir / "P_TODO.md"
        else:
            group_id = uid.replace("group_", "")
            base_dir = self.data_dir / "groups" / group_id
            return base_dir / "G_TODO.md"

    def _get_archive_dir(self, uid: str) -> Path:
        """获取归档目录路径
        
        Args:
            uid: 用户 ID 或群组 ID
            
        Returns:
            归档目录路径
        """
        if self.scope == "personal":
            return self.data_dir / "profiles" / uid / "TODOed"
        else:
            group_id = uid.replace("group_", "")
            return self.data_dir / "groups" / group_id / "TODOed"

    def _get_archive_file_path(self, uid: str, year: int, month: int) -> Path:
        """获取按月的归档文件路径
        
        Args:
            uid: 用户 ID 或群组 ID
            year: 年份
            month: 月份
            
        Returns:
            归档文件路径（如 TODOed/P_TODO_2024-03.md）
        """
        archive_dir = self._get_archive_dir(uid)
        if self.scope == "personal":
            filename = f"P_TODO_{year}-{month:02d}.md"
        else:
            filename = f"G_TODO_{year}-{month:02d}.md"
        return archive_dir / filename

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
        todo_file = self._get_todo_file_path(uid)
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
        todo_file = self._get_todo_file_path(uid)
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
            
            self.archive_old_completed(uid)
        except Exception as e:
            logger.error(f"[TodoManager] 写入 TODO 文件失败: {e}")
            raise

        return new_item

    def complete_todo(self, uid: str, task_id: int) -> bool:
        """标记待办为已完成"""
        todo_file = self._get_todo_file_path(uid)
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
            
            self.archive_old_completed(uid)
            return True
        except Exception as e:
            logger.error(f"[TodoManager] 写入 TODO 文件失败: {e}")
            return False

    def update_todo(self, uid: str, task_id: int, new_content: str) -> bool:
        """更新待办内容"""
        todo_file = self._get_todo_file_path(uid)
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
        todo_file = self._get_todo_file_path(uid)
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
        todo_file = self._get_todo_file_path(uid)
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
        """归档旧已完成项（按月切片归档）

        将完成时间超过 3 天的已完成项按月份分组，
        分别写入对应的归档文件（如 TODOed/P_TODO_2024-03.md）

        Returns:
            归档的条目数量
        """
        todo_file = self._get_todo_file_path(uid)
        pending_items, completed_items = self._parse_todo_file(todo_file)

        if not completed_items:
            return 0

        three_days_ago = datetime.now() - timedelta(days=3)
        to_archive = []
        remaining_completed = []

        for item in completed_items:
            if not item.completed_at:
                continue

            if item.completed_at < three_days_ago:
                to_archive.append(item)
            else:
                remaining_completed.append(item)

        if not to_archive:
            return 0

        from collections import defaultdict
        archive_by_month = defaultdict(list)
        for item in to_archive:
            if item.completed_at:
                year_month = (item.completed_at.year, item.completed_at.month)
                archive_by_month[year_month].append(item)

        total_archived = 0
        for (year, month), items in archive_by_month.items():
            archive_file = self._get_archive_file_path(uid, year, month)
            
            try:
                archive_dir = self._get_archive_dir(uid)
                if not archive_dir.exists():
                    archive_dir.mkdir(parents=True, exist_ok=True)

                existing_lines = []
                if archive_file.exists():
                    existing_content = archive_file.read_text(encoding="utf-8")
                    existing_lines = existing_content.split("\n")
                    if existing_lines and not existing_lines[-1]:
                        existing_lines = existing_lines[:-1]
                else:
                    archive_title = f"# {'个人' if self.scope == 'personal' else '群组'}待办归档 - {year}年{month}月"
                    existing_lines = [archive_title, "", "## 已完成（历史）", ""]

                for item in sorted(items, key=lambda x: x.completed_at or x.created_at):
                    timestamp = item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    completed_str = (
                        f" (完成于: {item.completed_at.strftime('%Y-%m-%d %H:%M:%S')})" if item.completed_at else ""
                    )
                    existing_lines.append(f"- [x] [{timestamp}] {item.content}{completed_str}")

                archive_file.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")
                logger.info(f"[TodoManager] 已归档 {len(items)} 条待办到: {archive_file.name}")
                total_archived += len(items)
            except Exception as e:
                logger.error(f"[TodoManager] 归档到 {archive_file.name} 失败: {e}")

        markdown_content = self._generate_markdown(pending_items, remaining_completed)

        try:
            todo_file.write_text(markdown_content, encoding="utf-8")
            logger.info(f"[TodoManager] 主文件已更新，归档 {total_archived} 条")
            return total_archived
        except Exception as e:
            logger.error(f"[TodoManager] 更新主文件失败: {e}")
            return 0
