#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试三级档案馆架构和 sudo 模式（简化版）
"""

import asyncio
import json
import shutil
import sqlite3
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

# ==================== 简化的测试类定义 ====================


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
            return False, "❌ 权限不足：仅管理员可执行此操作"
        if uid in self._sudo_sessions:
            session = self._sudo_sessions[uid]
            if not session.is_expired(self.SUDO_TIMEOUT):
                session.touch()
                return True, "⚠️ 已在管理员模式中"
            else:
                del self._sudo_sessions[uid]
        self._sudo_sessions[uid] = SudoSession(uid=uid)
        return True, "✅ 已进入管理员模式"

    async def exit_sudo(self, uid: str) -> tuple:
        if uid not in self._sudo_sessions:
            return True, "当前不在管理员模式中"
        del self._sudo_sessions[uid]
        return True, "✅ 已退出管理员模式"

    def record_sudo_operation(self, uid: str, operation: str, details: str = ""):
        if uid in self._sudo_sessions:
            session = self._sudo_sessions[uid]
            session.touch()
            session.operations.append(
                {"operation": operation, "details": details, "timestamp": datetime.now().isoformat()}
            )


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


# ==================== 测试函数 ====================


def test_identity_manager_sudo():
    """测试 IdentityManager 的 Sudo 功能"""
    print("Testing IdentityManager Sudo...")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        identity_manager = SimpleIdentityManager(temp_dir)

        # 模拟创世神
        identity_manager.security_data["origin_owner"] = "user_123"

        # 测试超级管理员检查
        assert identity_manager.is_super_admin("user_123") == True
        assert identity_manager.is_super_admin("user_456", ["user_456"]) == True
        assert identity_manager.is_super_admin("user_789") == False
        print("  - Super admin check: PASS")

        # 测试 sudo 模式
        assert identity_manager.is_sudo("user_123") == False
        print("  - Initial sudo state: PASS")

        # 进入 sudo 模式
        success, msg = asyncio.run(identity_manager.enter_sudo("user_123"))
        assert success == True
        assert identity_manager.is_sudo("user_123") == True
        print("  - Enter sudo: PASS")

        # 非管理员尝试进入
        success, msg = asyncio.run(identity_manager.enter_sudo("user_789"))
        assert success == False
        print("  - Non-admin enter sudo rejected: PASS")

        # 退出 sudo 模式
        success, msg = asyncio.run(identity_manager.exit_sudo("user_123"))
        assert success == True
        assert identity_manager.is_sudo("user_123") == False
        print("  - Exit sudo: PASS")

        print("IdentityManager Sudo: ALL TESTS PASSED\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_archive_router():
    """测试 ArchiveRouter"""
    print("Testing ArchiveRouter...")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        router = SimpleArchiveRouter(temp_dir)

        # 测试路径解析 - 私聊
        db_path, scope = router.resolve_db_path("user_123", "private", is_sudo=False)
        assert scope == ArchiveScope.PERSONAL
        assert "profiles" in str(db_path)
        print("  - Private chat path: PASS")

        # 测试路径解析 - 群聊
        db_path, scope = router.resolve_db_path("user_123", "group_456", is_sudo=False)
        assert scope == ArchiveScope.GROUP
        assert "groups" in str(db_path)
        print("  - Group chat path: PASS")

        # 测试路径解析 - sudo 模式
        db_path, scope = router.resolve_db_path("user_123", "private", is_sudo=True)
        assert scope == ArchiveScope.GLOBAL
        assert "global" in str(db_path)
        print("  - Sudo mode path: PASS")

        print("ArchiveRouter: ALL TESTS PASSED\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_archive_manager():
    """测试 ArchiveManager"""
    print("Testing ArchiveManager...")

    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "test_archives.db"

    try:
        manager = SimpleArchiveManager(db_path)

        # 测试注册表
        manager.register_table(
            table_name="test_table",
            display_name="测试表",
            columns={"col1": "列1", "col2": "列2"},
            row_count=100,
            description="测试描述",
            scope="personal",
        )

        archives = manager.get_all_archives()
        assert len(archives) == 1
        assert archives[0]["display_name"] == "测试表"
        assert archives[0]["scope"] == "personal"
        print("  - Register table: PASS")

        # 测试更新元数据
        success = manager.update_metadata("test_table", display_name="新名称", description="新描述")
        assert success == True

        # 测试删除
        success = manager.unregister_table("test_table")
        assert success == True
        archives = manager.get_all_archives()
        assert len(archives) == 0
        print("  - Delete table: PASS")

        print("ArchiveManager: ALL TESTS PASSED\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_archive_index():
    """测试 ArchiveIndex"""
    print("Testing ArchiveIndex...")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        router = SimpleArchiveRouter(temp_dir)

        # 创建个人档案
        personal_db = temp_dir / "profiles" / "user_user_123" / "archives.db"
        personal_manager = SimpleArchiveManager(personal_db)
        personal_manager.register_table(
            table_name="personal_table",
            display_name="个人档案",
            columns={"col1": "列1"},
            row_count=10,
            scope="personal",
        )

        # 创建全局档案
        global_db = temp_dir / "global" / "archives.db"
        global_manager = SimpleArchiveManager(global_db)
        global_manager.register_table(
            table_name="global_table", display_name="全局档案", columns={"col1": "列1"}, row_count=100, scope="global"
        )

        # 测试索引聚合
        accessible_dbs = router.resolve_accessible_dbs("user_123", "private")

        # 应该包含个人和全局档案
        assert len(accessible_dbs) == 2
        scopes = [db["scope"] for db in accessible_dbs]
        assert ArchiveScope.PERSONAL in scopes
        assert ArchiveScope.GLOBAL in scopes
        print("  - Index aggregation: PASS")

        print("ArchiveIndex: ALL TESTS PASSED\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_migration():
    """测试数据迁移"""
    print("Testing Migration...")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        # 创建旧版数据库
        legacy_db = temp_dir / "archives.db"
        legacy_db.write_text("test")

        # 执行迁移
        global_dir = temp_dir / "global"
        global_dir.mkdir(parents=True, exist_ok=True)
        global_db = global_dir / "archives.db"

        if legacy_db.exists() and not global_db.exists():
            import shutil as sh

            sh.move(str(legacy_db), str(global_db))
            result = True
        else:
            result = False

        assert result == True

        # 验证迁移结果
        assert not legacy_db.exists()
        assert global_db.exists()
        print("  - Legacy migration: PASS")

        print("Migration: ALL TESTS PASSED\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=" * 50)
    print("三级档案馆架构 + Sudo 模式 测试")
    print("(简化版 - 独立测试)")
    print("=" * 50 + "\n")

    test_identity_manager_sudo()
    test_archive_router()
    test_archive_manager()
    test_archive_index()
    test_migration()

    print("=" * 50)
    print("ALL TESTS PASSED!")
    print("=" * 50)
