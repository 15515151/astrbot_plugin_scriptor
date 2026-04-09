# core/permission_manager.py
"""
Scriptor 权限管理模块

提供细粒度的权限控制系统，支持基于角色和功能的权限管理
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限枚举"""

    # 基础权限
    VIEW = "view"
    SEARCH = "search"
    RECORD = "record"

    # 管理权限
    DEBUG = "debug"
    BACKUP = "backup"
    DELETE = "delete"
    EXPORT = "export"

    # 高级权限
    ADMIN = "admin"
    REINDEX = "reindex"
    CONFIG = "config"
    ENCRYPT = "encrypt"


class Role(Enum):
    """角色枚举"""

    GUEST = "guest"
    USER = "user"
    MEMBER = "member"
    MODERATOR = "moderator"
    ADMIN = "admin"
    OWNER = "owner"


@dataclass
class PermissionPolicy:
    """权限策略"""

    allowed_permissions: Set[Permission] = field(default_factory=set)
    denied_permissions: Set[Permission] = field(default_factory=set)
    conditions: Dict[str, any] = field(default_factory=dict)


class PermissionManager:
    """
    细粒度权限管理器

    支持:
    - 基于角色的权限继承
    - 基于用户的权限覆盖
    - 基于群体成员角色的权限
    - 条件权限（如隐私级别、记忆类型）
    """

    _instance: Optional["PermissionManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._role_permissions: Dict[Role, PermissionPolicy] = {}
        self._user_permissions: Dict[str, PermissionPolicy] = {}
        self._admin_uids: Set[str] = set()
        self._initialized = True

        self._init_default_policies()

    def _init_default_policies(self):
        """初始化默认权限策略"""

        # Guest 权限 - 只能查看公开内容
        self._role_permissions[Role.GUEST] = PermissionPolicy(allowed_permissions={Permission.VIEW})

        # User 权限 - 基本操作
        self._role_permissions[Role.USER] = PermissionPolicy(
            allowed_permissions={Permission.VIEW, Permission.SEARCH, Permission.RECORD}
        )

        # Member 权限 - 群组成员
        self._role_permissions[Role.MEMBER] = PermissionPolicy(
            allowed_permissions={Permission.VIEW, Permission.SEARCH, Permission.RECORD}
        )

        # Moderator 权限 - 群组版主
        self._role_permissions[Role.MODERATOR] = PermissionPolicy(
            allowed_permissions={Permission.VIEW, Permission.SEARCH, Permission.RECORD, Permission.DELETE}
        )

        # Admin 权限 - 管理员
        self._role_permissions[Role.ADMIN] = PermissionPolicy(
            allowed_permissions={
                Permission.VIEW,
                Permission.SEARCH,
                Permission.RECORD,
                Permission.DEBUG,
                Permission.BACKUP,
                Permission.DELETE,
                Permission.EXPORT,
                Permission.REINDEX,
            }
        )

        # Owner 权限 - 群体所有者
        self._role_permissions[Role.OWNER] = PermissionPolicy(
            allowed_permissions={
                Permission.VIEW,
                Permission.SEARCH,
                Permission.RECORD,
                Permission.DELETE,
                Permission.CONFIG,
                Permission.ENCRYPT,
            }
        )

    def set_admin_uids(self, admin_uids: List[str]):
        """设置管理员 UID 列表"""
        self._admin_uids = set(admin_uids)
        logger.info(f"[Scriptor] 已设置 {len(admin_uids)} 个管理员")

    def add_admin(self, uid: str):
        """添加管理员"""
        self._admin_uids.add(uid)

    def remove_admin(self, uid: str):
        """移除管理员"""
        self._admin_uids.discard(uid)

    def is_admin(self, uid: str) -> bool:
        """检查用户是否为管理员"""
        return uid in self._admin_uids

    def get_user_role(self, uid: str, group_id: Optional[str] = None, group_role: Optional[str] = None) -> Role:
        """
        获取用户的角色

        Args:
            uid: 用户 ID
            group_id: 群体 ID
            group_role: 用户在群体中的角色

        Returns:
            用户角色
        """
        if uid in self._admin_uids:
            return Role.ADMIN

        if group_role:
            role_map = {
                "owner": Role.OWNER,
                "admin": Role.ADMIN,
                "moderator": Role.MODERATOR,
                "member": Role.MEMBER,
            }
            return role_map.get(group_role.lower(), Role.USER)

        return Role.USER

    def check_permission(
        self,
        uid: str,
        permission: Permission,
        group_id: Optional[str] = None,
        group_role: Optional[str] = None,
        **conditions,
    ) -> bool:
        """
        检查用户是否具有特定权限

        Args:
            uid: 用户 ID
            permission: 要检查的权限
            group_id: 群体 ID（用于群体特定权限检查）
            group_role: 用户在群体中的角色
            **conditions: 额外的条件参数

        Returns:
            是否具有权限
        """
        role = self.get_user_role(uid, group_id, group_role)
        policy = self._role_permissions.get(role)

        if policy is None:
            return False

        if permission in policy.denied_permissions:
            return False

        if permission in policy.allowed_permissions:
            if not self._check_conditions(policy.conditions, conditions):
                return False
            return True

        user_policy = self._user_permissions.get(uid)
        if user_policy:
            if permission in user_policy.denied_permissions:
                return False
            if permission in user_policy.allowed_permissions:
                return True

        return False

    def _check_conditions(self, conditions: Dict, context: Dict) -> bool:
        """检查条件是否满足"""
        for key, expected in conditions.items():
            actual = context.get(key)
            if actual != expected:
                return False
        return True

    def grant_permission(self, uid: str, permission: Permission, conditions: Optional[Dict] = None):
        """
        授予用户特定权限

        Args:
            uid: 用户 ID
            permission: 要授予的权限
            conditions: 权限条件
        """
        if uid not in self._user_permissions:
            self._user_permissions[uid] = PermissionPolicy()

        self._user_permissions[uid].allowed_permissions.add(permission)
        if conditions:
            self._user_permissions[uid].conditions.update(conditions)

    def revoke_permission(self, uid: str, permission: Permission):
        """
        撤销用户特定权限

        Args:
            uid: 用户 ID
            permission: 要撤销的权限
        """
        if uid in self._user_permissions:
            self._user_permissions[uid].allowed_permissions.discard(permission)

    def deny_permission(self, uid: str, permission: Permission):
        """
        拒绝用户特定权限

        Args:
            uid: 用户 ID
            permission: 要拒绝的权限
        """
        if uid not in self._user_permissions:
            self._user_permissions[uid] = PermissionPolicy()

        self._user_permissions[uid].denied_permissions.add(permission)
        self._user_permissions[uid].allowed_permissions.discard(permission)

    def get_user_permissions(
        self, uid: str, group_id: Optional[str] = None, group_role: Optional[str] = None
    ) -> List[Permission]:
        """
        获取用户的所有有效权限

        Args:
            uid: 用户 ID
            group_id: 群体 ID
            group_role: 用户在群体中的角色

        Returns:
            权限列表
        """
        role = self.get_user_role(uid, group_id, group_role)
        permissions = set()

        role_policy = self._role_permissions.get(role)
        if role_policy:
            permissions.update(role_policy.allowed_permissions)

        user_policy = self._user_permissions.get(uid)
        if user_policy:
            permissions.update(user_policy.allowed_permissions)
            permissions -= user_policy.denied_permissions

        return list(permissions)

    def can_access_memory(
        self, uid: str, memory_privacy: str, memory_scope: str, group_id: Optional[str] = None
    ) -> bool:
        """
        检查用户是否可以访问特定记忆

        Args:
            uid: 用户 ID
            memory_privacy: 记忆的隐私级别
            memory_scope: 记忆的范围
            group_id: 群体 ID

        Returns:
            是否可以访问
        """
        if self.is_admin(uid):
            return True

        if memory_privacy == "global":
            return True

        if memory_privacy == "private":
            return uid == memory_scope or uid == memory_scope.replace("private_", "")

        if memory_privacy == "group":
            return group_id is not None and uid == memory_scope

        return False


_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """获取权限管理器单例"""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
