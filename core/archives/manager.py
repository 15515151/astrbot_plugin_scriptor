# core/archives/manager.py
"""
档案管理器 - 单一数据库的 CRUD 操作

功能：
1. 档案表注册与管理
2. 元数据存储
3. 查询执行（只读安全检查）

注意：
- 此类管理单个数据库文件
- 多数据库路由由 ArchiveRouter 处理
"""

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class ArchiveManager:
    """档案管理器 - 管理单个数据库文件"""

    def __init__(self, db_path: str):
        """
        初始化档案管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化元数据表"""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS archive_registry (
                    table_name TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    description TEXT,
                    columns_json TEXT NOT NULL,
                    row_count INTEGER DEFAULT 0,
                    scope TEXT DEFAULT 'auto',
                    import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def register_table(
        self,
        table_name: str,
        display_name: str,
        columns: Dict[str, str],
        row_count: int,
        description: str = "",
        scope: str = "auto",
    ):
        """
        注册一个新档案表

        Args:
            table_name: 表名
            display_name: 显示名称
            columns: 列信息字典
            row_count: 行数
            description: 描述
            scope: 层级 (personal/group/global/auto)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO archive_registry 
                (table_name, display_name, description, columns_json, row_count, scope)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (table_name, display_name, description, json.dumps(columns, ensure_ascii=False), row_count, scope),
            )
            conn.commit()

    def unregister_table(self, table_name: str) -> bool:
        """
        注销并删除一个档案表

        Args:
            table_name: 表名

        Returns:
            是否成功删除
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM archive_registry WHERE table_name = ?", (table_name,))
            if not cursor.fetchone():
                return False

            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            cursor.execute("DELETE FROM archive_registry WHERE table_name = ?", (table_name,))
            conn.commit()

            logger.info(f"[ArchiveManager] 已删除档案表: {table_name}")
            return True

    def update_metadata(self, table_name: str, display_name: str = None, description: str = None) -> bool:
        """
        更新档案元数据

        Args:
            table_name: 表名
            display_name: 新的显示名称（可选）
            description: 新的描述（可选）

        Returns:
            是否成功更新
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM archive_registry WHERE table_name = ?", (table_name,))
            if not cursor.fetchone():
                return False

            updates = []
            params = []

            if display_name is not None:
                updates.append("display_name = ?")
                params.append(display_name)

            if description is not None:
                updates.append("description = ?")
                params.append(description)

            if not updates:
                return True

            params.append(table_name)
            sql = f"UPDATE archive_registry SET {', '.join(updates)} WHERE table_name = ?"
            cursor.execute(sql, params)
            conn.commit()

            logger.info(f"[ArchiveManager] 已更新档案元数据: {table_name}")
            return True

    def get_all_archives(self) -> List[Dict[str, Any]]:
        """获取所有已注册的档案"""
        if not os.path.exists(self.db_path):
            return []

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM archive_registry ORDER BY import_time DESC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"[ArchiveManager] 获取档案列表失败: {e}")
            return []

    def get_archive_list(self) -> List[Dict[str, Any]]:
        """获取所有档案表的简化列表（用于工具调用）"""
        try:
            archives = self.get_all_archives()
            return [
                {
                    "table_name": arc["table_name"],
                    "display_name": arc["display_name"],
                    "description": arc["description"] or "无",
                    "row_count": arc["row_count"],
                    "scope": arc.get("scope", "auto"),
                    "columns": list(json.loads(arc["columns_json"]).keys()),
                }
                for arc in archives
            ]
        except Exception as e:
            logger.error(f"[ArchiveManager] 获取档案列表失败: {e}")
            return []

    def get_archive_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        获取单个档案的详细信息

        Args:
            table_name: 表名

        Returns:
            档案信息字典或 None
        """
        if not os.path.exists(self.db_path):
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM archive_registry WHERE table_name = ?", (table_name,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"[ArchiveManager] 获取档案信息失败: {e}")
            return None

    def database_exists(self) -> bool:
        """检查数据库文件是否存在"""
        return os.path.exists(self.db_path)

    def get_archive_catalog_prompt(self, scope_label: str = "") -> str:
        """
        生成供 AI 使用的档案目录提示词

        Args:
            scope_label: 层级标签（可选）

        Returns:
            档案目录提示词
        """
        archives = self.get_all_archives()
        if not archives:
            return ""

        catalog = []
        for arc in archives:
            cols = json.loads(arc["columns_json"])
            col_desc = ", ".join([f"{k}({v})" for k, v in cols.items()])
            scope_str = f" [{arc.get('scope', 'auto')}]" if arc.get("scope") else ""
            catalog.append(f"- {arc['display_name']} ({arc['table_name']}){scope_str}")
            catalog.append(f"  描述: {arc['description'] or '无'}")
            catalog.append(f"  数据量: {arc['row_count']} 条")
            catalog.append(f"  字段: {col_desc}")

        return "\n".join(catalog)

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        执行 AI 生成的查询语句（只读）

        Args:
            sql: SQL 查询语句

        Returns:
            查询结果列表

        Raises:
            ValueError: 如果 SQL 不是 SELECT 语句
        """
        clean_sql = sql.strip().upper()
        if not clean_sql.startswith("SELECT"):
            raise ValueError("仅允许执行 SELECT 查询语句以保证数据安全。")

        if not os.path.exists(self.db_path):
            raise ValueError(f"数据库不存在: {self.db_path}")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]

    def execute_unsafe(self, sql: str) -> int:
        """
        执行不安全的 SQL 语句（仅限管理员操作）

        Args:
            sql: SQL 语句

        Returns:
            影响的行数
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            return cursor.rowcount

    def get_table_count(self) -> int:
        """获取档案表数量"""
        if not os.path.exists(self.db_path):
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM archive_registry")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.debug(f"[ArchiveManager] 获取表数量失败: {e}")
            return 0
