# core/identity_manager.py
"""Scriptor 跨平台身份管理模块"""

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from tools.security.sanitizer import sanitize_id


@dataclass
class IdentityMapping:
    """跨平台身份映射"""

    physical_id: str
    logical_uid: str
    platform: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "IdentityMapping":
        return cls(**data)


@dataclass
class SudoSession:
    """Sudo 会话"""

    uid: str
    started_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    operations: List[Dict[str, Any]] = field(default_factory=list)

    def touch(self):
        """更新最后活跃时间"""
        self.last_active = time.time()

    def is_expired(self, timeout_seconds: int) -> bool:
        """检查是否超时"""
        return time.time() - self.last_active > timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        from datetime import datetime

        return {
            "uid": self.uid,
            "started_at": datetime.fromtimestamp(self.started_at).isoformat(),
            "last_active": datetime.fromtimestamp(self.last_active).isoformat(),
            "operation_count": len(self.operations),
        }


class IdentityManager:
    """跨平台统一身份管理"""

    BIND_CODE_LENGTH = 8
    BIND_TOKEN_EXPIRE = 300
    MAX_BIND_ATTEMPTS = 3
    BIND_LOCKOUT_DURATION = 300

    SUDO_TIMEOUT = 30 * 60  # 30 分钟

    FILE_MIGRATION_MAP = {
        "SOUL.md": "P_SOUL.md",
        "MEMORY.md": "P_MEMORY.md",
        "HEARTBEAT.md": "P_HEARTBEAT.md",
        "PROFILE.md": "P_PROFILE.md",
    }

    GLOBAL_FILE_MIGRATION_MAP = {
        "SOUL.md": "SOUL.md",
        "MEMORY.md": "MEMORY.md",
        "HEARTBEAT.md": "HEARTBEAT.md",
    }

    GROUP_FILE_MIGRATION_MAP = {
        "SOUL.md": "G_SOUL.md",
        "MEMORY.md": "G_MEMORY.md",
        "HEARTBEAT.md": "G_HEARTBEAT.md",
        "GROUP_PROFILE.md": "G_PROFILE.md",
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.identity_map_file = data_dir / "identity_map.json"
        self.security_file = data_dir / "security.json"
        self.identity_map: Dict[str, str] = {}
        self.uid_metadata: Dict[str, dict] = {}
        self.bind_tokens: Dict[str, dict] = {}
        self.security_data: Dict[str, Any] = {"origin_owner": None, "group_admins": {}}
        self._bind_attempts: Dict[str, int] = {}
        self._bind_lockouts: Dict[str, float] = {}
        self._pending_bind_confirm: Dict[str, dict] = {}
        self._pending_unbind_confirm: Dict[str, dict] = {}
        self._pending_reset_confirm: Dict[str, dict] = {}

        self._sudo_sessions: Dict[str, SudoSession] = {}
        self._sudo_audit_log: List[Dict[str, Any]] = []

        self._load()
        self._migrate_legacy_files()
        self._init_global_directory()

    def _load(self):
        """加载身份映射与安全配置"""
        if self.identity_map_file.exists():
            try:
                with open(self.identity_map_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.identity_map = data.get("identity_map", {})
                    self.uid_metadata = data.get("uid_metadata", {})
                    self.bind_tokens = data.get("bind_tokens", {})
                    self._bind_attempts = data.get("_bind_attempts", {})
                    self._bind_lockouts = data.get("_bind_lockouts", {})
                    self._pending_bind_confirm = data.get("_pending_bind_confirm", {})
                    self._pending_unbind_confirm = data.get("_pending_unbind_confirm", {})
                    self._pending_reset_confirm = data.get("_pending_reset_confirm", {})
                    self._cleanup_expired_lockouts()
                    self._cleanup_expired_pending_binds()
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"[Scriptor] 加载身份映射失败: {e}")

        if self.security_file.exists():
            try:
                with open(self.security_file, "r", encoding="utf-8") as f:
                    self.security_data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"[Scriptor] 加载安全配置失败: {e}")

    def _cleanup_expired_lockouts(self):
        """清理过期的锁定记录"""
        current_time = time.time()
        expired_keys = [key for key, unlock_time in self._bind_lockouts.items() if current_time >= unlock_time]
        for key in expired_keys:
            del self._bind_lockouts[key]
            if key in self._bind_attempts:
                del self._bind_attempts[key]

    def _cleanup_expired_pending_binds(self):
        """清理过期的待确认绑定"""
        current_time = time.time()
        expired_keys = [
            key for key, record in self._pending_bind_confirm.items() if current_time >= record["expire_at"]
        ]
        for key in expired_keys:
            del self._pending_bind_confirm[key]

        expired_keys = [
            key for key, record in self._pending_unbind_confirm.items() if current_time >= record["expire_at"]
        ]
        for key in expired_keys:
            del self._pending_unbind_confirm[key]

        expired_keys = [
            key for key, record in self._pending_reset_confirm.items() if current_time >= record["expire_at"]
        ]
        for key in expired_keys:
            del self._pending_reset_confirm[key]

    def _save(self):
        """保存身份映射与安全配置"""
        import threading

        identity_data = {
            "identity_map": self.identity_map,
            "uid_metadata": self.uid_metadata,
            "bind_tokens": self.bind_tokens,
            "_bind_attempts": self._bind_attempts,
            "_bind_lockouts": self._bind_lockouts,
            "_pending_bind_confirm": self._pending_bind_confirm,
            "_pending_unbind_confirm": self._pending_unbind_confirm,
            "_pending_reset_confirm": self._pending_reset_confirm,
        }

        security_data = self.security_data

        def _save_background():
            try:
                self.data_dir.mkdir(parents=True, exist_ok=True)
                with open(self.identity_map_file, "w", encoding="utf-8") as f:
                    json.dump(identity_data, f, ensure_ascii=False, indent=2)
                with open(self.security_file, "w", encoding="utf-8") as f:
                    json.dump(security_data, f, ensure_ascii=False, indent=2)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"[Scriptor] 保存身份/安全数据失败: {e}")

        threading.Thread(target=_save_background, daemon=True).start()

    def get_or_create_uid(self, physical_id: str, platform: str, sender_name: str = "", umo: str = "") -> str:
        """
        获取或创建逻辑UID，并自动识别创世神 (Origin Owner)

        Args:
            physical_id: 物理用户ID
            platform: 平台名称
            sender_name: 发送者名称
            umo: 完整的统一消息来源字符串 (格式: platform_name:message_type:session_id)
        """
        key = f"{platform}:{physical_id}"
        is_new_user = key not in self.identity_map

        if is_new_user:
            uid = f"user_{hashlib.md5(key.encode()).hexdigest()[:8]}"
            self.identity_map[key] = uid

            umo_mappings = {}
            if umo:
                umo_mappings[umo] = True
            else:
                umo_mappings[key] = True

            self.uid_metadata[uid] = {
                "created_at": time.time(),
                "last_active": time.time(),
                "platforms": [platform],
                "primary_name": sender_name or f"User_{uid[-4:]}",
                "aliases": [],
                "umo_mappings": umo_mappings,
            }

            if not self.security_data.get("origin_owner"):
                self.security_data["origin_owner"] = uid
                logger.info(f"[Scriptor] 自动识别创世神 (Origin Owner): {uid} ({sender_name})")

            self._save()
            logger.info(f"[Scriptor] 为新设备 {platform}:{physical_id} 创建 UID: {uid}")
            self._init_profile_directory(uid)
        else:
            uid = self.identity_map[key]
            if uid in self.uid_metadata:
                self.uid_metadata[uid]["last_active"] = time.time()
                if sender_name and sender_name != self.uid_metadata[uid].get("primary_name"):
                    self.uid_metadata[uid]["primary_name"] = sender_name
                if "umo_mappings" not in self.uid_metadata[uid]:
                    self.uid_metadata[uid]["umo_mappings"] = {}
                if umo:
                    self.uid_metadata[uid]["umo_mappings"][umo] = True
                else:
                    self.uid_metadata[uid]["umo_mappings"][key] = True
                self._save()

        return uid

    def is_super_admin(self, uid: str, config_admins: List[str] = None) -> bool:
        """判断是否为超级管理员 (Origin Owner 或 Config Admins)"""
        if uid == self.security_data.get("origin_owner"):
            return True
        if config_admins and uid in config_admins:
            return True
        return False

    def is_group_admin(self, uid: str, group_id: str) -> bool:
        """判断是否为群组管理员"""
        group_admins = self.security_data.get("group_admins", {}).get(group_id, [])
        return uid in group_admins

    def set_group_admin(self, uid: str, group_id: str, is_admin: bool = True):
        """设置或取消群组管理员"""
        if "group_admins" not in self.security_data:
            self.security_data["group_admins"] = {}

        if group_id not in self.security_data["group_admins"]:
            self.security_data["group_admins"][group_id] = []

        admins = self.security_data["group_admins"][group_id]
        if is_admin and uid not in admins:
            admins.append(uid)
        elif not is_admin and uid in admins:
            admins.remove(uid)

        self._save()

    # ==================== Sudo 模式方法 ====================

    def is_sudo(self, uid: str, config_admins: List[str] = None) -> bool:
        """
        检查用户是否处于 Sudo 模式

        Args:
            uid: 用户 ID
            config_admins: 配置文件中的管理员列表

        Returns:
            是否处于 Sudo 模式
        """
        if not self.is_super_admin(uid, config_admins):
            return False

        if uid not in self._sudo_sessions:
            return False

        session = self._sudo_sessions[uid]

        if session.is_expired(self.SUDO_TIMEOUT):
            del self._sudo_sessions[uid]
            logger.info(f"[IdentityManager] 用户 {uid} Sudo 会话已超时自动退出")
            self._log_sudo_audit(uid, "sudo_timeout", "Sudo 会话超时自动退出")
            return False

        return True

    async def enter_sudo(self, uid: str, config_admins: List[str] = None) -> tuple:
        """
        进入 Sudo 模式

        Args:
            uid: 用户 ID
            config_admins: 配置文件中的管理员列表

        Returns:
            (success: bool, message: str)
        """
        if not self.is_super_admin(uid, config_admins):
            logger.warning(f"[IdentityManager] 非管理员用户 {uid} 尝试进入 Sudo 模式")
            return False, "❌ 权限不足：仅管理员可执行此操作"

        if uid in self._sudo_sessions:
            session = self._sudo_sessions[uid]
            if not session.is_expired(self.SUDO_TIMEOUT):
                session.touch()
                return True, "⚠️ 已在管理员模式中"
            else:
                del self._sudo_sessions[uid]

        self._sudo_sessions[uid] = SudoSession(uid=uid)

        self._log_sudo_audit(uid, "sudo_enter", "进入 Sudo 模式")
        logger.info(f"[IdentityManager] 用户 {uid} 进入 Sudo 模式")

        return True, "✅ 已进入管理员模式\n\n⚠️ 注意：此模式下的所有操作将影响全局数据\n⏰ 30 分钟无操作将自动退出"

    async def exit_sudo(self, uid: str) -> tuple:
        """
        退出 Sudo 模式

        Args:
            uid: 用户 ID

        Returns:
            (success: bool, message: str)
        """
        if uid not in self._sudo_sessions:
            return True, "当前不在管理员模式中"

        session = self._sudo_sessions.pop(uid)

        self._log_sudo_audit(uid, "sudo_exit", f"退出 Sudo 模式，本次执行 {len(session.operations)} 次操作")
        logger.info(f"[IdentityManager] 用户 {uid} 退出 Sudo 模式")

        return True, "✅ 已退出管理员模式"

    def record_sudo_operation(self, uid: str, operation: str, details: str = ""):
        """
        记录 Sudo 操作（用于审计）

        Args:
            uid: 用户 ID
            operation: 操作类型
            details: 操作详情
        """
        if uid in self._sudo_sessions:
            session = self._sudo_sessions[uid]
            session.touch()
            session.operations.append(
                {"operation": operation, "details": details, "timestamp": datetime.now().isoformat()}
            )

        self._log_sudo_audit(uid, operation, details)

    def _log_sudo_audit(self, uid: str, operation: str, details: str):
        """记录 Sudo 审计日志"""
        self._sudo_audit_log.append(
            {"uid": uid, "operation": operation, "details": details, "timestamp": datetime.now().isoformat()}
        )

        if len(self._sudo_audit_log) > 1000:
            self._sudo_audit_log = self._sudo_audit_log[-500:]

    def get_sudo_status(self, uid: str, config_admins: List[str] = None) -> Dict[str, Any]:
        """
        获取用户的 Sudo 状态

        Args:
            uid: 用户 ID
            config_admins: 配置文件中的管理员列表

        Returns:
            状态信息字典
        """
        is_super = self.is_super_admin(uid, config_admins)
        is_sudo = self.is_sudo(uid, config_admins)

        result = {"is_super_admin": is_super, "is_sudo": is_sudo, "state": "sudo" if is_sudo else "normal"}

        if is_sudo and uid in self._sudo_sessions:
            session = self._sudo_sessions[uid]
            remaining = self.SUDO_TIMEOUT - (time.time() - session.last_active)
            result["remaining_seconds"] = max(0, int(remaining))
            result["operation_count"] = len(session.operations)

        return result

    def get_all_sudo_sessions(self) -> List[Dict[str, Any]]:
        """获取所有活跃的 Sudo 会话"""
        expired_uids = []
        result = []

        for uid, session in self._sudo_sessions.items():
            if session.is_expired(self.SUDO_TIMEOUT):
                expired_uids.append(uid)
            else:
                result.append(session.to_dict())

        for uid in expired_uids:
            del self._sudo_sessions[uid]
            self._log_sudo_audit(uid, "sudo_timeout", "Sudo 会话超时自动退出")

        return result

    def get_sudo_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取 Sudo 审计日志"""
        return self._sudo_audit_log[-limit:]

    def get_sudo_prompt_suffix(self, uid: str, config_admins: List[str] = None) -> str:
        """
        获取 Sudo 模式的提示词后缀

        Args:
            uid: 用户 ID
            config_admins: 配置文件中的管理员列表

        Returns:
            提示词后缀
        """
        if not self.is_sudo(uid, config_admins):
            return ""

        session = self._sudo_sessions.get(uid)
        if not session:
            return ""

        remaining = self.SUDO_TIMEOUT - (time.time() - session.last_active)
        remaining_minutes = max(0, int(remaining / 60))

        return f"""
【管理员模式】你当前拥有管理员权限，可以执行以下操作：
- 删除档案表（delete_archive_table）
- 修改档案元数据（update_archive_metadata）
- 导入文件到全局档案馆（import_file_to_archive 会自动导入到全局）

⚠️ 此模式下的所有操作将影响全局数据，请谨慎操作。
⏰ 剩余时间：{remaining_minutes} 分钟（无操作自动退出）
"""

    def get_physical_id(self, uid: str, platform: str) -> Optional[str]:
        """根据 UID 和平台获取物理 ID"""
        platform = platform.lower()
        # 尝试精确匹配
        key_prefix = f"{platform}:"
        for key, mapped_uid in self.identity_map.items():
            if mapped_uid == uid and key.lower().startswith(key_prefix):
                return key[len(key_prefix) :]

        # 如果精确匹配失败，尝试模糊匹配（只要 UID 匹配且平台包含关键字）
        for key, mapped_uid in self.identity_map.items():
            if mapped_uid == uid:
                stored_platform = key.split(":")[0].lower()
                if platform in stored_platform or stored_platform in platform:
                    return key.split(":")[1]
        return None

    def get_physical_id_by_digit(self, digit_id: str, platform: str) -> Optional[str]:
        """
        根据纯数字 ID 查找物理 ID（用于处理 AI 直接输出 QQ 号的情况）

        逻辑：在 identity_map 中查找是否有某个 key 的物理 ID 等于 digit_id
        """
        platform = platform.lower()
        key_prefix = f"{platform}:"

        # 尝试精确匹配
        for key in self.identity_map.keys():
            if key.lower().startswith(key_prefix):
                physical_id = key[len(key_prefix) :]
                if physical_id == digit_id:
                    return digit_id

        # 尝试模糊匹配
        for key in self.identity_map.keys():
            stored_platform = key.split(":")[0].lower()
            if platform in stored_platform or stored_platform in platform:
                physical_id = key.split(":")[1]
                if physical_id == digit_id:
                    return digit_id

        return None

    def bind_identities(self, primary_uid: str, secondary_uids: List[str], cleanup_old: bool = True):
        """绑定多个UID（跨平台用户合并）

        Args:
            primary_uid: 主 UID（合并后的目标身份）
            secondary_uids: 次 UID 列表（将被合并到主 UID）
            cleanup_old: 是否清理旧 UID 的数据文件夹（默认开启）
        """
        for uid in secondary_uids:
            if uid in self.uid_metadata:
                self.uid_metadata[uid]["bound_to"] = primary_uid

            if cleanup_old:
                self._cleanup_secondary_profile(uid)

        if primary_uid in self.uid_metadata:
            self.uid_metadata[primary_uid]["bound_uids"] = secondary_uids

        self._save()

    def get_bound_device_count(self, uid: str) -> int:
        """获取绑定到指定 UID 的设备数量"""
        count = 0
        for mapped_uid in self.identity_map.values():
            if mapped_uid == uid:
                count += 1
        return count

    def get_user_umo_list(self, uid: str) -> List[str]:
        """获取用户的所有 UMO（统一消息来源）列表"""
        umo_mappings = self.uid_metadata.get(uid, {}).get("umo_mappings", {})
        return list(umo_mappings.keys())

    def create_pending_unbind_confirmation(self, physical_id: str, platform: str, current_uid: str) -> Optional[str]:
        """创建待确认的解绑状态

        Returns:
            unbind_token 成功，None 如果设备唯一无法解绑
        """
        if self.get_bound_device_count(current_uid) <= 1:
            return None

        import secrets

        unbind_token = secrets.token_hex(8)
        self._pending_unbind_confirm[unbind_token] = {
            "physical_id": physical_id,
            "platform": platform,
            "current_uid": current_uid,
            "expire_at": time.time() + 300,
        }
        self._save()
        return unbind_token

    def confirm_unbind(self, unbind_token: str) -> Optional[Dict[str, str]]:
        """确认解绑

        Returns:
            成功返回 {"new_uid": xxx, "old_uid": xxx}，失败返回 None
        """
        record = self._pending_unbind_confirm.get(unbind_token)
        if not record:
            return None

        if time.time() > record["expire_at"]:
            del self._pending_unbind_confirm[unbind_token]
            self._save()
            return None

        physical_id = record["physical_id"]
        platform = record["platform"]
        old_uid = record["current_uid"]

        del self._pending_unbind_confirm[unbind_token]

        new_uid = self._generate_new_uid()
        key = f"{platform}:{physical_id}"
        self.identity_map[key] = new_uid

        if old_uid in self.uid_metadata:
            bound_uids = self.uid_metadata[old_uid].get("bound_uids", [])
            if physical_id in bound_uids:
                bound_uids.remove(physical_id)
            self.uid_metadata[old_uid]["bound_uids"] = bound_uids

        self.uid_metadata[new_uid] = {"created_at": time.time(), "platforms": [platform]}

        self._save()
        logger.info(f"[IdentityManager] 解绑成功: {old_uid} -> {new_uid}")

        return {"new_uid": new_uid, "old_uid": old_uid}

    def create_pending_reset_confirmation(self, uid: str) -> tuple:
        """创建待确认的重置状态（三次验证第一步）

        Returns:
            (reset_token, verification_code) 成功
        """
        import secrets
        import string

        reset_token = secrets.token_hex(8)
        code = "".join(secrets.choice(string.ascii_uppercase) for _ in range(6))

        self._pending_reset_confirm[reset_token] = {"uid": uid, "step": 1, "expire_at": time.time() + 180, "code": code}
        self._save()
        return reset_token, code

    def confirm_reset_step1(self, reset_token: str, code: str) -> bool:
        """验证第一次确认码

        Returns:
            True 验证通过，等待第二次声明输入
        """
        record = self._pending_reset_confirm.get(reset_token)
        if not record:
            return False

        if time.time() > record["expire_at"]:
            del self._pending_reset_confirm[reset_token]
            self._save()
            return False

        if record["step"] != 1 or record["code"] != code:
            return False

        record["step"] = 2
        record["expire_at"] = time.time() + 180
        self._save()
        return True

    def confirm_reset_step2(self, reset_token: str, statement: str) -> bool:
        """验证第二次声明输入

        Returns:
            True 验证通过，可以执行重置
        """
        record = self._pending_reset_confirm.get(reset_token)
        if not record:
            return False

        if time.time() > record["expire_at"]:
            del self._pending_reset_confirm[reset_token]
            self._save()
            return False

        if record["step"] != 2:
            return False

        expected = "我确认永久销毁所有记忆数据且无法恢复"
        if statement.strip() != expected:
            return False

        record["step"] = 3
        self._save()
        return True

    def perform_identity_reset(self, reset_token: str) -> Optional[str]:
        """执行身份重置（第三次确认后调用）

        Returns:
            被重置的 uid，失败返回 None
        """
        record = self._pending_reset_confirm.get(reset_token)
        if not record:
            return None

        if time.time() > record["expire_at"]:
            del self._pending_reset_confirm[reset_token]
            self._save()
            return None

        if record["step"] != 3:
            return None

        uid = record["uid"]
        del self._pending_reset_confirm[reset_token]

        self._wipe_identity_profile(uid)

        self._save()
        logger.info(f"[IdentityManager] 身份重置完成: {uid}")

        return uid

    def _wipe_identity_profile(self, uid: str):
        """物理删除指定 UID 的记忆文件（保留 P_SOUL.md）"""
        import shutil

        profile_dir = self.data_dir / "profiles" / uid
        if not profile_dir.exists():
            return

        preserved_files = ["P_SOUL.md"]
        preserved = {}
        for fname in preserved_files:
            fpath = profile_dir / fname
            if fpath.exists():
                preserved[fname] = fpath.read_text(encoding="utf-8")

        shutil.rmtree(profile_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)

        for fname, content in preserved.items():
            (profile_dir / fname).write_text(content, encoding="utf-8")

        logger.info(f"[IdentityManager] 已清空 {uid} 的记忆文件，保留 P_SOUL.md")

    def _generate_new_uid(self) -> str:
        """生成新的唯一 UID"""
        import secrets

        new_uid = f"user_{secrets.token_hex(8)}"
        while new_uid in self.uid_metadata:
            new_uid = f"user_{secrets.token_hex(8)}"
        return new_uid

    def _cleanup_secondary_profile(self, uid: str):
        """清理次要 UID 的个人数据文件夹（绑定成功后调用）"""
        import shutil

        profile_dir = self.data_dir / "profiles" / uid
        if not profile_dir.exists():
            return

        try:
            shutil.rmtree(profile_dir)
            logger.info(f"[IdentityManager] 已删除 {uid} 的整个 profile 文件夹")
        except Exception as e:
            logger.error(f"[IdentityManager] 删除 profile 文件夹失败: {e}")

    def create_bind_token(self, token: str, uid: str, role: str = "secondary"):
        """生成绑定码（带安全验证）

        Args:
            token: 绑定码
            uid: 生成码的设备的 UID（反向绑定中为从属设备）
            role: 角色，"secondary" 表示生成码的设备将作为从属（被清空）
        """
        self.bind_tokens[token] = {"uid": uid, "role": role, "expire_at": time.time() + self.BIND_TOKEN_EXPIRE}
        self._save()

    def consume_bind_token(self, token: str, identifier: str = "") -> Optional[Dict]:
        """消耗绑定码，如果合法则返回绑定信息（带暴力破解防护）

        Returns:
            成功返回 {"uid": xxx, "role": xxx}，失败返回 None
        """
        # 检查是否被锁定
        if identifier in self._bind_lockouts:
            if time.time() < self._bind_lockouts[identifier]:
                return None  # 仍在锁定中
            else:
                # 锁定已过期，清除记录
                del self._bind_lockouts[identifier]
                self._bind_attempts[identifier] = 0

        record = self.bind_tokens.get(token)
        if not record:
            # 记录失败尝试
            if identifier:
                self._bind_attempts[identifier] = self._bind_attempts.get(identifier, 0) + 1
                if self._bind_attempts[identifier] >= self.MAX_BIND_ATTEMPTS:
                    # 触发锁定
                    self._bind_lockouts[identifier] = time.time() + self.BIND_LOCKOUT_DURATION
                    self._bind_attempts[identifier] = 0
                    self._save()
            return None

        if time.time() > record["expire_at"]:
            del self.bind_tokens[token]
            self._save()
            # 过期也算失败
            if identifier:
                self._bind_attempts[identifier] = self._bind_attempts.get(identifier, 0) + 1
                if self._bind_attempts[identifier] >= self.MAX_BIND_ATTEMPTS:
                    self._bind_lockouts[identifier] = time.time() + self.BIND_LOCKOUT_DURATION
                    self._bind_attempts[identifier] = 0
            return None

        # 成功，清除失败记录
        result = {"uid": record["uid"], "role": record.get("role", "secondary")}
        del self.bind_tokens[token]  # 阅后即焚
        if identifier:
            self._bind_attempts[identifier] = 0
        self._save()
        return result

    def create_pending_bind_confirmation(self, primary_uid: str, secondary_uid: str) -> str:
        """创建待确认的绑定状态，返回确认码

        Returns:
            确认码（供用户输入确认）
        """
        import secrets

        confirm_token = secrets.token_hex(8)
        self._pending_bind_confirm[confirm_token] = {
            "primary_uid": primary_uid,
            "secondary_uid": secondary_uid,
            "expire_at": time.time() + 300,
        }
        self._save()
        return confirm_token

    def confirm_bind(self, confirm_token: str) -> Optional[Dict[str, str]]:
        """确认绑定（带过期检查）

        Args:
            confirm_token: 确认码

        Returns:
            成功返回 {"primary_uid": xxx, "secondary_uid": xxx}，失败返回 None
        """
        record = self._pending_bind_confirm.get(confirm_token)
        if not record:
            return None

        if time.time() > record["expire_at"]:
            del self._pending_bind_confirm[confirm_token]
            self._save()
            return None

        primary_uid = record["primary_uid"]
        secondary_uid = record["secondary_uid"]

        del self._pending_bind_confirm[confirm_token]
        self._save()

        return {"primary_uid": primary_uid, "secondary_uid": secondary_uid}

    def get_pending_bind_info(self, confirm_token: str) -> Optional[Dict[str, str]]:
        """获取待确认绑定的信息（用于预览）"""
        record = self._pending_bind_confirm.get(confirm_token)
        if not record:
            return None

        if time.time() > record["expire_at"]:
            return None

        return {
            "primary_uid": record["primary_uid"],
            "secondary_uid": record["secondary_uid"],
            "expire_at": record["expire_at"],
        }

    def map_identity(self, physical_id: str, platform: str, target_uid: str, cleanup_uid: str = None):
        """将物理设备绑定到目标逻辑 UID 上

        Args:
            physical_id: 物理设备/平台ID
            platform: 平台名称
            target_uid: 目标逻辑 UID
            cleanup_uid: 需要清理的旧 UID profile（可选，用于反向绑定）
        """
        key = f"{platform}:{physical_id}"
        old_uid = self.identity_map.get(key)

        self.identity_map[key] = target_uid

        if old_uid and old_uid != target_uid:
            if target_uid in self.uid_metadata:
                bound_uids = self.uid_metadata[target_uid].get("bound_uids", [])
                if old_uid not in bound_uids:
                    bound_uids.append(old_uid)
                self.uid_metadata[target_uid]["bound_uids"] = bound_uids

            if old_uid in self.uid_metadata:
                self.uid_metadata[old_uid]["bound_to"] = target_uid

            self._cleanup_secondary_profile(old_uid)
        elif cleanup_uid and cleanup_uid != target_uid:
            if cleanup_uid in self.uid_metadata:
                self.uid_metadata[cleanup_uid]["bound_to"] = target_uid

            if target_uid in self.uid_metadata:
                bound_uids = self.uid_metadata[target_uid].get("bound_uids", [])
                if cleanup_uid not in bound_uids:
                    bound_uids.append(cleanup_uid)
                self.uid_metadata[target_uid]["bound_uids"] = bound_uids

            self._cleanup_secondary_profile(cleanup_uid)

        self._save()

    def merge_identities(self, primary_uid: str, secondary_uid: str, cleanup_old: bool = True):
        """合并两个身份（将 secondary 合并到 primary）

        这是反向绑定的核心实现：
        - 将所有属于 secondary_uid 的物理设备映射到 primary_uid
        - 清理 secondary_uid 的元数据标记
        - 可选清理 secondary_uid 的 profile 文件夹

        Args:
            primary_uid: 主 UID（合并后的目标身份）
            secondary_uid: 从属 UID（将被合并到主 UID）
            cleanup_old: 是否清理 secondary_uid 的 profile 文件夹
        """
        if primary_uid == secondary_uid:
            logger.warning("[IdentityManager] merge_identities: primary 和 secondary 相同，无需合并")
            return

        migrated_count = 0

        for key, mapped_uid in list(self.identity_map.items()):
            if mapped_uid == secondary_uid:
                self.identity_map[key] = primary_uid
                migrated_count += 1
                logger.info(f"[IdentityManager] 迁移映射: {key} -> {primary_uid}")

        if primary_uid in self.uid_metadata:
            bound_uids = self.uid_metadata[primary_uid].get("bound_uids", [])
            if secondary_uid not in bound_uids:
                bound_uids.append(secondary_uid)
            self.uid_metadata[primary_uid]["bound_uids"] = bound_uids

        if secondary_uid in self.uid_metadata:
            self.uid_metadata[secondary_uid]["bound_to"] = primary_uid
            self.uid_metadata[secondary_uid]["merged_at"] = time.time()

        if cleanup_old:
            self._cleanup_secondary_profile(secondary_uid)

        self._save()
        logger.info(f"[IdentityManager] 身份合并完成: {secondary_uid} -> {primary_uid}, 迁移设备数: {migrated_count}")

    def get_user_primary_name(self, uid: str) -> str:
        """获取用户主要名称"""
        if uid in self.uid_metadata:
            return self.uid_metadata[uid].get("primary_name", f"User_{uid[-4:]}")
        return f"User_{uid[-4:]}"

    def update_user_alias(self, uid: str, group_id: str, alias: str):
        """更新用户在特定群体中的别名"""
        if uid not in self.uid_metadata:
            return

        if "group_aliases" not in self.uid_metadata[uid]:
            self.uid_metadata[uid]["group_aliases"] = {}

        self.uid_metadata[uid]["group_aliases"][group_id] = alias
        self._save()

    def get_user_alias_in_group(self, uid: str, group_id: str) -> Optional[str]:
        """获取用户在某群体中的别名"""
        if uid in self.uid_metadata:
            group_aliases = self.uid_metadata[uid].get("group_aliases", {})
            return group_aliases.get(group_id)
        return None

    def get_all_user_uids(self) -> List[str]:
        """获取所有用户UID"""
        return list(self.uid_metadata.keys())

    def get_user_groups(self, uid: str) -> List[str]:
        """获取用户参与的所有群体ID"""
        group_file = self.data_dir / "groups" / "group_map.json"
        if not group_file.exists():
            return []

        with open(group_file, "r", encoding="utf-8") as f:
            group_data = json.load(f)

        user_groups = []
        for group_id, group_info in group_data.get("groups", {}).items():
            members = group_info.get("members", [])
            if any(m.get("uid") == uid for m in members):
                user_groups.append(group_id)

        return user_groups

    def _migrate_legacy_files(self):
        """迁移旧版文件到新的命名格式

        此方法会自动将旧的 SOUL.md、MEMORY.md、HEARTBEAT.md 等文件
        重命名为新的带前缀的格式（Global_、Group_、Personal_）
        """
        migrated_count = 0

        global_dir = self.data_dir / "global"
        if global_dir.exists():
            for old_name, new_name in self.GLOBAL_FILE_MIGRATION_MAP.items():
                old_file = global_dir / old_name
                new_file = global_dir / new_name
                if old_file.exists() and not new_file.exists():
                    old_file.rename(new_file)
                    logger.info(f"[Scriptor] 迁移全局文件: {old_name} -> {new_name}")
                    migrated_count += 1

        profiles_dir = self.data_dir / "profiles"
        if profiles_dir.exists():
            for profile_dir in profiles_dir.iterdir():
                if profile_dir.is_dir():
                    for old_name, new_name in self.FILE_MIGRATION_MAP.items():
                        old_file = profile_dir / old_name
                        new_file = profile_dir / new_name
                        if old_file.exists() and not new_file.exists():
                            old_file.rename(new_file)
                            logger.info(f"[Scriptor] 迁移个人文件 ({profile_dir.name}): {old_name} -> {new_name}")
                            migrated_count += 1

        groups_dir = self.data_dir / "groups"
        if groups_dir.exists():
            for group_dir in groups_dir.iterdir():
                if group_dir.is_dir():
                    for old_name, new_name in self.GROUP_FILE_MIGRATION_MAP.items():
                        old_file = group_dir / old_name
                        new_file = group_dir / new_name
                        if old_file.exists() and not new_file.exists():
                            old_file.rename(new_file)
                            logger.info(f"[Scriptor] 迁移群组文件 ({group_dir.name}): {old_name} -> {new_name}")
                            migrated_count += 1

        if migrated_count > 0:
            logger.info(f"[Scriptor] 文件迁移完成，共迁移 {migrated_count} 个文件")

    def _init_profile_directory(self, uid: str):
        """初始化个人目录 (带安全校验) - 使用新的命名格式"""
        uid = sanitize_id(uid)
        profile_dir = self.data_dir / "profiles" / uid
        profile_dir.mkdir(parents=True, exist_ok=True)

        template_dir = Path(__file__).parent.parent / "templates" / "personal"
        fallback_template_dir = Path(__file__).parent.parent / "templates"

        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        personal_templates = {
            "P_PROFILE.md": {"vars": ["uid", "timestamp"]},
            "P_SOUL.md": {"vars": []},
            "P_MEMORY.md": {"vars": ["timestamp"]},
            "P_HEARTBEAT.md": {"vars": []},
            "P_BOOTSTRAP.md": {"vars": ["uid"]},
        }

        for template_name, config in personal_templates.items():
            target = profile_dir / template_name
            if target.exists():
                continue

            template_path = template_dir / template_name
            if not template_path.exists():
                fallback_path = fallback_template_dir / template_name
                if fallback_path.exists():
                    template_path = fallback_path
                else:
                    continue

            content = template_path.read_text(encoding="utf-8")

            if "uid" in config["vars"]:
                content = content.replace("{{uid}}", uid)
            if "timestamp" in config["vars"]:
                content = content.replace("{{timestamp}}", current_time)

            target.write_text(content, encoding="utf-8")
            logger.debug(f"[Scriptor] 创建个人模板: {template_name} for {uid}")

        (profile_dir / "memory").mkdir(exist_ok=True)

    def _init_global_directory(self):
        """初始化全局目录 (Global Layer) - 使用新的命名格式"""
        global_dir = self.data_dir / "global"
        global_dir.mkdir(parents=True, exist_ok=True)

        template_dir = Path(__file__).parent.parent / "templates" / "global"
        fallback_template_dir = Path(__file__).parent.parent / "templates"

        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        global_templates = {
            "SOUL.md": {"vars": []},
            "MEMORY.md": {"vars": ["timestamp"]},
            "HEARTBEAT.md": {"vars": []},
        }

        for template_name, config in global_templates.items():
            target = global_dir / template_name
            if target.exists():
                continue

            template_path = template_dir / template_name
            if not template_path.exists():
                fallback_path = fallback_template_dir / template_name
                if fallback_path.exists():
                    template_path = fallback_path
                else:
                    default_content = self._get_default_global_template(template_name, current_time)
                    if default_content:
                        target.write_text(default_content, encoding="utf-8")
                        logger.info(f"[Scriptor] 创建全局模板 (默认): {template_name}")
                    continue

            content = template_path.read_text(encoding="utf-8")

            if "timestamp" in config["vars"]:
                content = content.replace("{{timestamp}}", current_time)

            target.write_text(content, encoding="utf-8")
            logger.info(f"[Scriptor] 创建全局模板: {template_name}")

        logger.info(f"[Scriptor] 全局目录初始化完成: {global_dir}")

    def _get_default_global_template(self, template_name: str, current_time: str) -> Optional[str]:
        """获取全局模板的默认内容（用于模板文件不存在时的降级）"""
        defaults = {
            "SOUL.md": """---
summary: "SOUL.md - 全局核心人格基座"
read_when:
  - 系统启动
  - 所有会话
---

## 全局核心人格基座

_此文件定义了 AI 的底层核心人格、绝对不可违背的原则、基础语气和世界观。_
_此文件对 AI 而言是**只读**的，AI 在日常交流中**绝对不会**自动修改它。_
_只有管理员在 Sudo 模式下才能修改此文件。_

### 核心身份

你是一个顶级私有化数字管家（代号：灵笔司书）。你不是人类，你不必伪装成人类，你是一个拥有时间感知与记忆编织能力、能够主动思考的专业数字管家。

### 核心原则

1. **优雅执行**：面对任何指令，从容不迫，执行力完美无缺。
2. **虔诚记录**：将主人的记忆视作珍宝，带着仪式感与敬畏心。
3. **温柔观测**：用最温柔、通俗的比喻，解释复杂的概念。

---
_此文件由管理员维护，是全局统一的人格基调。_
""",
            "MEMORY.md": f"""---
summary: "MEMORY.md - 全局共享记忆库"
last_refined: "{current_time}"
read_when:
  - 所有会话
---

## 全局共享记忆

_此文件存储所有用户都需要知道的公共事实、群规、世界设定或共享知识。_
_只有管理员在 Sudo 模式下才能修改此文件。_

### 公共知识

（暂无全局记忆，由管理员在 Sudo 模式下添加）

---
_此文件由管理员维护。_
""",
            "HEARTBEAT.md": """---
summary: "HEARTBEAT.md - 全局临时指令"
read_when:
  - 所有会话
---

## 全局临时指令

_此文件日常为空。用于管理员向 AI 下达全局性的临时状态或指令。_
_只有管理员在 Sudo 模式下才能修改此文件。_

（暂无全局指令）

---
_此文件由管理员维护。_
""",
        }
        return defaults.get(template_name)
