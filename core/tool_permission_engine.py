# core/tool_permission_engine.py
"""
Scriptor 工具权限规则引擎

提供细粒度的工具级权限控制：
- 基于规则的权限检查 (Allow/Deny/Ask)
- 支持正则表达式和通配符匹配
- 工具调用前拦截（PreToolUse Hook）
- 权限规则动态管理
- 审计日志记录
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class PermissionAction(Enum):
    """权限动作"""

    ALLOW = "allow"  # 允许执行
    DENY = "deny"  # 拒绝执行
    ASK = "ask"  # 询问用户


@dataclass
class PermissionRule:
    """权限规则"""

    rule_id: str
    tool_pattern: str  # 工具名称模式（支持通配符 * 和正则）
    action: PermissionAction
    description: str = ""
    priority: int = 0  # 优先级，数值越高优先级越高
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)  # 额外条件
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def matches(self, tool_name: str) -> bool:
        """
        检查工具名是否匹配此规则

        Args:
            tool_name: 工具名称

        Returns:
            是否匹配
        """
        pattern = self.tool_pattern

        if pattern == "*":
            return True

        if pattern == tool_name:
            return True

        if "*" in pattern or "?" in pattern:
            regex_pattern = pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
            try:
                if re.fullmatch(regex_pattern, tool_name):
                    return True
            except re.error:
                pass

        if pattern.startswith("regex:"):
            regex_str = pattern[6:]
            try:
                if re.search(regex_str, tool_name):
                    return True
            except re.error:
                pass

        return False


@dataclass
class PermissionCheckResult:
    """权限检查结果"""

    action: PermissionAction
    matched_rule: Optional[PermissionRule] = None
    reason: str = ""
    requires_confirmation: bool = False

    @property
    def is_allowed(self) -> bool:
        return self.action == PermissionAction.ALLOW

    @property
    def is_denied(self) -> bool:
        return self.action == PermissionAction.DENY

    @property
    def should_ask(self) -> bool:
        return self.action == PermissionAction.ASK


@dataclass
class ToolCallContext:
    """工具调用上下文"""

    tool_name: str
    uid: str
    group_id: str
    args: Dict[str, Any]
    event: Any = None
    is_admin: bool = False
    is_sudo: bool = False
    session_id: str = ""


class ToolPermissionEngine:
    """
    工具权限引擎

    功能：
    - 管理权限规则（Allow/Deny/Ask）
    - 执行权限检查
    - 支持优先级和条件判断
    - 提供审计日志
    - 动态规则管理
    """

    _instance: Optional["ToolPermissionEngine"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._rules: List[PermissionRule] = []
        self._audit_log: List[Dict[str, Any]] = []
        self._max_audit_log_size: int = 1000
        self._default_action: PermissionAction = PermissionAction.ALLOW
        self._initialized = True

        self._load_default_rules()

        logger.info("[ToolPermissionEngine] 初始化完成")

    def _load_default_rules(self):
        """加载默认安全规则"""
        default_deny_patterns = [
            ("file_write_tool*", "文件写入操作", 50),
            ("file_edit_tool*", "文件编辑操作", 50),
            ("file_append_tool*", "文件追加操作", 50),
            ("delete_archive_table", "删除档案表", 100),
            ("update_archive_metadata", "修改档案元数据", 80),
            ("set_group_admin_tool", "设置群管理员", 100),
            ("import_file_to_archive", "导入文件到档案馆", 60),
        ]

        for pattern, desc, priority in default_deny_patterns:
            self.add_rule(
                PermissionRule(
                    rule_id=f"default_deny_{pattern.replace('*', '_')}",
                    tool_pattern=pattern,
                    action=PermissionAction.ASK,
                    description=f"默认规则：{desc}需要确认",
                    priority=priority,
                )
            )

        logger.info(f"[ToolPermissionEngine] 已加载 {len(default_deny_patterns)} 条默认安全规则")

    def add_rule(self, rule: PermissionRule) -> bool:
        """
        添加权限规则

        Args:
            rule: 权限规则

        Returns:
            是否添加成功
        """
        existing = next((r for r in self._rules if r.rule_id == rule.rule_id), None)

        if existing:
            idx = self._rules.index(existing)
            self._rules[idx] = rule
            logger.debug(f"[ToolPermissionEngine] 规则已更新：{rule.rule_id}")
        else:
            self._rules.append(rule)
            self._rules.sort(key=lambda r: r.priority, reverse=True)
            logger.debug(f"[ToolPermissionEngine] 规则已添加：{rule.rule_id}")

        return True

    def remove_rule(self, rule_id: str) -> bool:
        """移除权限规则"""
        original_len = len(self._rules)
        self._rules = [r for r in self._rules if r.rule_id != rule_id]

        removed = len(self._rules) < original_len
        if removed:
            logger.info(f"[ToolPermissionEngine] 规则已移除：{rule_id}")

        return removed

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        rule = next((r for r in self._rules if r.rule_id == rule_id), None)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        rule = next((r for r in self._rules if r.rule_id == rule_id), None)
        if rule:
            rule.enabled = False
            return True
        return False

    async def check_permission(
        self,
        context: ToolCallContext,
        confirmation_callback: Optional[Callable[[ToolCallContext], asyncio.Future]] = None,
    ) -> PermissionCheckResult:
        """
        检查工具调用权限

        Args:
            context: 工具调用上下文
            confirmation_callback: 当需要确认时的回调函数

        Returns:
            权限检查结果
        """
        matched_rule = None

        for rule in self._rules:
            if not rule.enabled:
                continue

            if rule.matches(context.tool_name):
                if self._check_conditions(rule.conditions, context):
                    matched_rule = rule
                    break

        action = self._default_action
        reason = ""

        if matched_rule:
            action = matched_rule.action
            reason = f"命中规则 [{matched_rule.rule_id}]: {matched_rule.description}"

            if action == PermissionAction.ASK and confirmation_callback and context.event:
                result = await self._request_confirmation(context, confirmation_callback, matched_rule)
                if result:
                    action = result
                    reason += " → 用户确认后允许"
                else:
                    action = PermissionAction.DENY
                    reason += " → 用户拒绝或超时"

        check_result = PermissionCheckResult(
            action=action,
            matched_rule=matched_rule,
            reason=reason,
            requires_confirmation=(action == PermissionAction.ASK and matched_rule is not None),
        )

        self._log_audit(context, check_result)

        return check_result

    def _check_conditions(self, conditions: Dict[str, Any], context: ToolCallContext) -> bool:
        """检查额外条件"""
        if not conditions:
            return True

        for key, expected_value in conditions.items():
            actual_value = getattr(context, key, None)

            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    return False
            elif callable(expected_value):
                try:
                    if not expected_value(context):
                        return False
                except Exception as e:
                    logger.warning(f"[ToolPermissionEngine] 条件函数执行失败：{e}")
                    return False
            else:
                if actual_value != expected_value:
                    return False

        return True

    async def _request_confirmation(
        self, context: ToolCallContext, callback: Callable, rule: PermissionRule
    ) -> Optional[PermissionAction]:
        """请求用户确认"""
        try:
            future = callback(context)

            if asyncio.isfuture(future) or asyncio.iscoroutine(future):
                result = await asyncio.wait_for(
                    asyncio.ensure_future(future) if not asyncio.isfuture(future) else future, timeout=30.0
                )
                return result

            return None

        except asyncio.TimeoutError:
            logger.warning(f"[ToolPermissionEngine] 确认请求超时：{context.tool_name}")
            return None
        except Exception as e:
            logger.error(f"[ToolPermissionEngine] 确认请求异常：{e}")
            return None

    def _log_audit(self, context: ToolCallContext, result: PermissionCheckResult):
        """记录审计日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": context.tool_name,
            "uid": context.uid,
            "group_id": context.group_id,
            "action": result.action.value,
            "rule_id": result.matched_rule.rule_id if result.matched_rule else None,
            "reason": result.reason,
            "is_admin": context.is_admin,
            "is_sudo": context.is_sudo,
        }

        self._audit_log.append(log_entry)

        if len(self._audit_log) > self._max_audit_log_size:
            self._audit_log = self._audit_log[-self._max_audit_log_size :]

    def get_audit_log(
        self,
        limit: int = 100,
        tool_name: Optional[str] = None,
        uid: Optional[str] = None,
        action: Optional[PermissionAction] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取审计日志

        Args:
            limit: 返回条数限制
            tool_name: 可选的工具名称过滤
            uid: 可选的用户 ID 过滤
            action: 可选的动作过滤

        Returns:
            审计日志列表
        """
        logs = self._audit_log.copy()

        if tool_name:
            logs = [l for l in logs if l.get("tool_name") == tool_name]

        if uid:
            logs = [l for l in logs if l.get("uid") == uid]

        if action:
            logs = [l for l in logs if l.get("action") == action.value]

        return logs[-limit:] if limit > 0 else logs

    def get_rules_for_tool(self, tool_name: str) -> List[PermissionRule]:
        """获取适用于某个工具的所有规则"""
        return [r for r in self._rules if r.enabled and r.matches(tool_name)]

    def get_all_rules(self) -> List[PermissionRule]:
        """获取所有规则"""
        return self._rules.copy()

    def set_default_action(self, action: PermissionAction):
        """设置默认动作"""
        self._default_action = action
        logger.info(f"[ToolPermissionEngine] 默认动作已设置为：{action.value}")

    def clear_custom_rules(self):
        """清除所有自定义规则（保留以 'default_' 开头的默认规则）"""
        custom_count = len([r for r in self._rules if not r.rule_id.startswith("default_")])
        self._rules = [r for r in self._rules if r.rule_id.startswith("default_")]
        logger.info(f"[ToolPermissionEngine] 已清除 {custom_count} 条自定义规则")

    def export_rules(self) -> List[Dict[str, Any]]:
        """导出所有规则为字典列表"""
        return [
            {
                "rule_id": r.rule_id,
                "tool_pattern": r.tool_pattern,
                "action": r.action.value,
                "description": r.description,
                "priority": r.priority,
                "enabled": r.enabled,
                "conditions": r.conditions,
            }
            for r in self._rules
        ]

    def import_rules(self, rules_data: List[Dict[str, Any]]) -> int:
        """
        导入规则

        Args:
            rules_data: 规则数据列表

        Returns:
            成功导入的规则数量
        """
        imported_count = 0

        for data in rules_data:
            try:
                rule = PermissionRule(
                    rule_id=data["rule_id"],
                    tool_pattern=data["tool_pattern"],
                    action=PermissionAction(data["action"]),
                    description=data.get("description", ""),
                    priority=data.get("priority", 0),
                    enabled=data.get("enabled", True),
                    conditions=data.get("conditions", {}),
                )

                if self.add_rule(rule):
                    imported_count += 1

            except Exception as e:
                logger.error(f"[ToolPermissionEngine] 导入规则失败：{data}, 错误：{e}")

        logger.info(f"[ToolPermissionEngine] 成功导入 {imported_count}/{len(rules_data)} 条规则")
        return imported_count

    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        total_rules = len(self._rules)
        enabled_rules = sum(1 for r in self._rules if r.enabled)
        allow_rules = sum(1 for r in self._rules if r.enabled and r.action == PermissionAction.ALLOW)
        deny_rules = sum(1 for r in self._rules if r.enabled and r.action == PermissionAction.DENY)
        ask_rules = sum(1 for r in self._rules if r.enabled and r.action == PermissionAction.ASK)

        recent_denials = sum(1 for l in self._audit_log[-100:] if l.get("action") == "deny")

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "allow_rules": allow_rules,
            "deny_rules": deny_rules,
            "ask_rules": ask_rules,
            "default_action": self._default_action.value,
            "audit_log_size": len(self._audit_log),
            "recent_denials_100": recent_denials,
        }


_tool_permission_engine: Optional[ToolPermissionEngine] = None


def get_tool_permission_engine() -> ToolPermissionEngine:
    """获取 ToolPermissionEngine 单例"""
    global _tool_permission_engine
    if _tool_permission_engine is None:
        _tool_permission_engine = ToolPermissionEngine()
    return _tool_permission_engine
