# mixins/admin_mixin.py
"""
管理员模式 Mixin

包含：
- /sudo_state_up 命令
- /sudo_state_down 命令
- /sudo_status 命令

使用 IdentityManager 的 sudo 功能
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from astrbot.api import logger
from astrbot.api.event import filter

from .base import BaseMixin

if TYPE_CHECKING:
    from astrbot.api.event import AstrMessageEvent


class AdminMixin(BaseMixin):
    """
    管理员模式 Mixin

    包含：
    - Sudo 模式命令
    - 管理员状态查询
    """

    @filter.command("sudo_state_up")
    async def cmd_sudo_state_up(self, event: AstrMessageEvent):
        """进入管理员模式"""
        uid, group_id, _ = self._get_identity(event)

        success, message = await self.identity_manager.enter_sudo(uid, self.config.admin_uids)

        if success:
            logger.info(f"[Scriptor] 用户 {uid} 进入管理员模式")

        yield event.plain_result(message)

    @filter.command("sudo_state_down")
    async def cmd_sudo_state_down(self, event: AstrMessageEvent):
        """退出管理员模式"""
        uid, group_id, _ = self._get_identity(event)

        success, message = await self.identity_manager.exit_sudo(uid)

        if success:
            logger.info(f"[Scriptor] 用户 {uid} 退出管理员模式")

        yield event.plain_result(message)

    @filter.command("sudo_status")
    async def cmd_sudo_status(self, event: AstrMessageEvent):
        """查看管理员状态"""
        uid, group_id, _ = self._get_identity(event)

        status = self.identity_manager.get_sudo_status(uid, self.config.admin_uids)

        state_icons = {"sudo": "🔴", "normal": "🟢"}

        icon = state_icons.get(status["state"], "⚪")

        msg_lines = [
            "## 🔐 管理员状态",
            "",
            f"**当前状态**: {icon} {status['state'].upper()}",
            f"**是否超级管理员**: {'✅ 是' if status['is_super_admin'] else '❌ 否'}",
        ]

        if status["is_sudo"]:
            msg_lines.extend(
                [
                    f"**剩余时间**: {status.get('remaining_seconds', 0) // 60} 分钟",
                    f"**本次操作数**: {status.get('operation_count', 0)} 次",
                ]
            )

        if status["is_super_admin"] and not status["is_sudo"]:
            msg_lines.extend(
                [
                    "",
                    "💡 使用 `/sudo_state_up` 进入管理员模式",
                ]
            )

        if status["is_sudo"]:
            msg_lines.extend(
                [
                    "",
                    "💡 使用 `/sudo_state_down` 退出管理员模式",
                ]
            )

        yield event.plain_result("\n".join(msg_lines))

    @filter.command("sudo_sessions")
    async def cmd_sudo_sessions(self, event: AstrMessageEvent):
        """查看所有活跃的 sudo 会话（仅管理员）"""
        uid, group_id, _ = self._get_identity(event)

        if not self.identity_manager.is_super_admin(uid, self.config.admin_uids):
            yield event.plain_result("❌ 权限不足：仅管理员可查看此信息")
            return

        sessions = self.identity_manager.get_all_sudo_sessions()

        if not sessions:
            yield event.plain_result("当前没有活跃的管理员会话")
            return

        msg_lines = ["## 📋 活跃的管理员会话", ""]

        for session in sessions:
            msg_lines.append(f"- **用户**: {session['uid']}")
            msg_lines.append(f"  - 开始时间: {session['started_at']}")
            msg_lines.append(f"  - 最后活跃: {session['last_active']}")
            msg_lines.append(f"  - 操作次数: {session['operation_count']}")
            msg_lines.append("")

        yield event.plain_result("\n".join(msg_lines))

    @filter.command("sudo_audit")
    async def cmd_sudo_audit(self, event: AstrMessageEvent):
        """查看管理员操作审计日志（仅管理员）"""
        uid, group_id, _ = self._get_identity(event)

        if not self.identity_manager.is_super_admin(uid, self.config.admin_uids):
            yield event.plain_result("❌ 权限不足：仅管理员可查看此信息")
            return

        audit_log = self.identity_manager.get_sudo_audit_log(limit=20)

        if not audit_log:
            yield event.plain_result("暂无操作记录")
            return

        msg_lines = ["## 📜 管理员操作审计日志", ""]

        for entry in audit_log[-20:]:
            msg_lines.append(f"- **{entry['timestamp']}**")
            msg_lines.append(f"  - 用户: {entry['uid']}")
            msg_lines.append(f"  - 操作: {entry['operation']}")
            msg_lines.append(f"  - 详情: {entry['details']}")
            msg_lines.append("")

        yield event.plain_result("\n".join(msg_lines))
