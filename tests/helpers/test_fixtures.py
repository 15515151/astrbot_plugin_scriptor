#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
共享测试工具类

提供简化版的测试用 IdentityManager、ArchiveRouter、ArchiveManager 等
供多个测试文件复用
"""

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ArchiveScope(Enum):
    """档案层级"""

    PERSONAL = "personal"
    GROUP = "group"
    GLOBAL = "global"


@dataclass
class SudoSession:
    """Sudo 会话"""

    uid: str
    started_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    operations: List[Dict[str, Any]] = field(default_factory=list)

    def touch(self):
        self.last_active = time.time()

    def is_expired(self, timeout_seconds: int) -> bool:
        return time.time() - self.last_active > timeout_seconds


class SimpleIdentityManager:
    """简化的身份管理器（用于测试）"""

    SUDO_TIMEOUT = 30 * 60

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.security_data: Dict[str, Any] = {"origin_owner": None, "group_admins": {}}
        self._sudo_sessions: Dict[str, SudoSession] = {}
        self._sudo_audit_log: List[Dict[str, Any]] = []

    def is_super_admin(self, uid: str, config_admins: List[str] = None) -> bool:
        if uid == self.security_data.get("origin_owner"):
            return True
        if config_admins and uid in config_admins:
            return True
        return False

    def is_sudo(self, uid: str, config_admins: List[str] = None) -> bool:
        if not self.is_super_admin(uid, config_admins):
            return False
        if uid not in self._sudo_sessions:
            return False
        session = self._sudo_sessions[uid]
        if session.is_expired(self.SUDO_TIMEOUT):
            del self._sudo_sessions[uid]
            return False
        return True

    async def enter_sudo(self, uid: str, config_admins: List[str] = None) -> tuple:
        if not self.is_super_admin(uid, config_admins):
            return False, "\u274c \u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7ba1\u7406\u5458\u53ef\u6267\u884c\u64cd\u4f5c"
        if uid in self._sudo_sessions:
            session = self._sudo_sessions[uid]
            if not session.is_expired(self.SUDO_TIMEOUT):
                session.touch()
                return True, "\u26a0\ufe0f \u5df2\u5728\u7ba1\u7406\u5458\u6a21\u5f0f\u4e2d"
            else:
                del self._sudo_sessions[uid]
        self._sudo_sessions[uid] = SudoSession(uid=uid)
        return True, "\u2705 \u5df2\u8fdb\u5165\u7ba1\u7406\u5458\u6a21\u5f0f"

    async def exit_sudo(self, uid: str) -> tuple:
        if uid not in self._sudo_sessions:
            return True, "\u5f53\u524d\u4e0d\u5728\u7ba1\u7406\u5458\u6a21\u5f0f\u4e2d"
        del self._sudo_sessions[uid]
        return True, "\u2705 \u5df2\u9000\u51fa\u7ba1\u7406\u5458\u6a21\u5f0f"

    def record_sudo_operation(self, uid: str, operation: str, details: str = ""):
        if uid in self._sudo_sessions:
            session = self._sudo_sessions[uid]
            session.touch()
            session.operations.append(
                {"operation": operation, "details": details, "timestamp": datetime.now().isoformat()}
            )

    def get_all_sudo_sessions(self) -> List[Dict[str, Any]]:
        expired_uids = []
        result = []

        for uid, session in self._sudo_sessions.items():
            if session.is_expired(self.SUDO_TIMEOUT):
                expired_uids.append(uid)
            else:
                result.append(session.to_dict())

        for uid in expired_uids:
            del self._sudo_sessions[uid]

        return result

    def get_sudo_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._sudo_audit_log[-limit:]

    def get_sudo_status(self, uid: str, config_admins: List[str] = None) -> Dict[str, Any]:
        is_super = self.is_super_admin(uid, config_admins)
        is_sudo_mode = self.is_sudo(uid, config_admins)

        result = {"is_super_admin": is_super, "is_sudo": is_sudo_mode, "state": "sudo" if is_sudo_mode else "normal"}

        if is_sudo_mode and uid in self._sudo_sessions:
            session = self._sudo_sessions[uid]
            remaining = self.SUDO_TIMEOUT - (time.time() - session.last_active)
            result["remaining_seconds"] = max(0, int(remaining))
            result["operation_count"] = len(session.operations)

        return result


class SimpleArchiveRouter:
    """简化的档案路由器（用于测试）"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        (self.data_dir / "global").mkdir(parents=True, exist_ok=True)

    def resolve_db_path(self, uid: str, group_id: str, is_sudo: bool = False):
        if is_sudo:
            return self.data_dir / "global" / "archives.db", ArchiveScope.GLOBAL
        if group_id == "private":
            profile_dir = self.data_dir / "profiles" / f"user_{uid}"
            profile_dir.mkdir(parents=True, exist_ok=True)
            return profile_dir / "archives.db", ArchiveScope.PERSONAL
        else:
            group_dir = self.data_dir / "groups" / group_id
            group_dir.mkdir(parents=True, exist_ok=True)
            return group_dir / "archives.db", ArchiveScope.GROUP

    def resolve_accessible_dbs(self, uid: str, group_id: str) -> List[Dict[str, Any]]:
        dbs = []
        profile_dir = self.data_dir / "profiles" / f"user_{uid}"
        personal_db = profile_dir / "archives.db"
        if personal_db.exists():
            dbs.append({"scope": ArchiveScope.PERSONAL, "path": personal_db, "priority": 1})
        if group_id != "private":
            group_dir = self.data_dir / "groups" / group_id
            group_db = group_dir / "archives.db"
            if group_db.exists():
                dbs.append({"scope": ArchiveScope.GROUP, "path": group_db, "priority": 2})
        global_db = self.data_dir / "global" / "archives.db"
        if global_db.exists():
            dbs.append({"scope": ArchiveScope.GLOBAL, "path": global_db, "priority": 3})
        return sorted(dbs, key=lambda x: x["priority"])


class SimpleArchiveManager:
    """简化的档案管理器（用于测试）"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
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
        columns: Dict,
        row_count: int,
        description: str = "",
        scope: str = "auto",
    ):
        with sqlite3.connect(str(self.db_path)) as conn:
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

    def get_all_archives(self) -> List[Dict]:
        if not self.db_path.exists():
            return []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM archive_registry ORDER BY import_time DESC")
            return [dict(row) for row in cursor.fetchall()]

    def unregister_table(self, table_name: str) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM archive_registry WHERE table_name = ?", (table_name,))
            if not cursor.fetchone():
                return False
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            cursor.execute("DELETE FROM archive_registry WHERE table_name = ?", (table_name,))
            conn.commit()
            return True

    def update_metadata(self, table_name: str, display_name: str = None, description: str = None) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
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
            return True

    def execute_query(self, sql: str) -> List[Dict]:
        if not self.db_path.exists():
            return []
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(sql)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.debug(f"[TestArchiveManager] 查询失败: {e}")
            return []
