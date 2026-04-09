# core/slash_command_router.py
"""
Scriptor 斜杠命令路由器

提供统一的命令管理和路由机制，支持：
- 命令注册与发现
- 参数解析与验证
- 命令别名映射
- 权限前置检查
- 帮助信息自动生成
"""

import asyncio
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class CommandPermission(Enum):
    """命令权限级别"""

    PUBLIC = "public"  # 所有人可用
    USER = "user"  # 已绑定用户
    MEMBER = "member"  # 群组成员
    ADMIN = "admin"  # 管理员
    SUPER_ADMIN = "super_admin"  # 超级管理员


@dataclass
class CommandMetadata:
    """命令元数据"""

    name: str
    description: str
    handler: Callable
    permission: CommandPermission = CommandPermission.PUBLIC
    aliases: List[str] = field(default_factory=list)
    parameters: List[Dict] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    category: str = "general"
    enabled: bool = True
    rate_limit: Optional[int] = None  # 秒数，None 表示无限制

    def __post_init__(self):
        if not self.aliases:
            self.aliases = []


class SlashCommandRouter:
    """
    统一的斜杠命令路由器

    功能：
    - 集中管理所有斜杠命令
    - 支持命令别名
    - 内置权限检查
    - 自动生成帮助信息
    - 速率限制
    """

    _instance: Optional["SlashCommandRouter"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._commands: Dict[str, CommandMetadata] = {}
        self._alias_map: Dict[str, str] = {}  # alias -> command name
        self._category_map: Dict[str, List[str]] = {}  # category -> [command names]
        self._rate_limit_cache: Dict[str, float] = {}  # session_id -> last_exec_time
        self._initialized = True

        logger.info("[SlashCommandRouter] 初始化完成")

    def register(self, metadata: CommandMetadata) -> bool:
        """
        注册一个命令

        Args:
            metadata: 命令元数据

        Returns:
            是否注册成功
        """
        if not metadata.name or not metadata.handler:
            logger.error(f"[SlashCommandRouter] 无效的命令注册：name={metadata.name}")
            return False

        if metadata.name in self._commands:
            logger.warning(f"[SlashCommandRouter] 命令已存在，将被覆盖：{metadata.name}")

        self._commands[metadata.name] = metadata

        for alias in metadata.aliases:
            self._alias_map[alias.lower()] = metadata.name

        if metadata.category not in self._category_map:
            self._category_map[metadata.category] = []

        if metadata.name not in self._category_map[metadata.category]:
            self._category_map[metadata.category].append(metadata.name)

        logger.debug(f"[SlashCommandRouter] 已注册命令：{metadata.name} (类别: {metadata.category})")
        return True

    def unregister(self, name: str) -> bool:
        """注销一个命令"""
        if name not in self._commands:
            return False

        metadata = self._commands.pop(name)

        for alias in metadata.aliases:
            self._alias_map.pop(alias.lower(), None)

        if metadata.category in self._category_map:
            if name in self._category_map[metadata.category]:
                self._category_map[metadata.category].remove(name)

        logger.info(f"[SlashCommandRouter] 已注销命令：{name}")
        return True

    async def route(
        self, input_text: str, event=None, context: Any = None, permission_checker: Optional[Callable] = None
    ) -> Tuple[bool, Any]:
        """
        路由并执行命令

        Args:
            input_text: 用户输入文本
            event: AstrBot 事件对象
            context: 额外上下文（如 plugin 实例）
            permission_checker: 权限检查函数 (uid, permission_level) -> bool

        Returns:
            (是否是命令, 执行结果)
        """
        if not input_text or not input_text.strip().startswith("/"):
            return False, None

        parsed = self._parse_input(input_text.strip())
        if not parsed:
            return False, None

        command_name, args_str = parsed

        resolved_name = self._resolve_command(command_name)
        if not resolved_name:
            return False, None

        metadata = self._commands.get(resolved_name)
        if not metadata or not metadata.enabled:
            logger.warning(f"[SlashCommandRouter] 命令未找到或已禁用：{command_name}")
            return True, f"❌ 未找到命令：`/{command_name}`"

        uid = getattr(event, "get_sender_id", lambda: None)() if event else None

        if not self._check_rate_limit(uid, metadata):
            return True, "⏰ 命令执行过于频繁，请稍后再试"

        if permission_checker and not await self._check_permission(metadata, uid, event, permission_checker):
            return True, "❌ 权限不足，无法执行此命令"

        try:
            result = await self._execute_handler(metadata, args_str, event, context)
            return True, result
        except Exception as e:
            logger.error(f"[SlashCommandRouter] 命令执行失败：{command_name}, 错误：{e}", exc_info=True)
            return True, f"❌ 命令执行出错：{e!s}"

    def _parse_input(self, input_text: str) -> Optional[Tuple[str, str]]:
        """解析用户输入"""
        text = input_text[1:].strip()  # 移除开头的 /

        parts = text.split(None, 1)
        if not parts:
            return None

        command_name = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ""

        return command_name, args_str

    def _resolve_command(self, name: str) -> Optional[str]:
        """解析命令名（支持别名）"""
        name_lower = name.lower()

        if name_lower in self._commands:
            return name_lower

        if name_lower in self._alias_map:
            return self._alias_map[name_lower]

        for cmd_name in self._commands:
            if cmd_name.startswith(name_lower) or name_lower in cmd_name.lower():
                return cmd_name

        return None

    async def _check_permission(
        self, metadata: CommandMetadata, uid: Optional[str], event: Any, checker: Callable
    ) -> bool:
        """检查权限"""
        if metadata.permission == CommandPermission.PUBLIC:
            return True

        if not uid and event:
            uid = getattr(event, "get_sender_id", lambda: None)()

        if not uid:
            return False

        try:
            if asyncio.iscoroutinefunction(checker):
                return await checker(uid, metadata.permission, event)
            else:
                return checker(uid, metadata.permission, event)
        except Exception as e:
            logger.error(f"[SlashCommandRouter] 权限检查异常：{e}")
            return False

    def _check_rate_limit(self, uid: Optional[str], metadata: CommandMetadata) -> bool:
        """检查速率限制"""
        if not metadata.rate_limit or not uid:
            return True

        session_key = f"{uid}:{metadata.name}"
        current_time = (
            asyncio.get_event_loop().time() if hasattr(asyncio, "get_event_loop") else __import__("time").time()
        )

        last_time = self._rate_limit_cache.get(session_key, 0)
        if current_time - last_time < metadata.rate_limit:
            return False

        self._rate_limit_cache[session_key] = current_time
        return True

    async def _execute_handler(self, metadata: CommandMetadata, args_str: str, event: Any, context: Any) -> Any:
        """执行命令处理器"""
        handler = metadata.handler

        if len(args_str) > 0:
            args = self._parse_args(args_str, metadata.parameters)
            if asyncio.iscoroutinefunction(handler):
                return await handler(event, *args, **{"plugin": context})
            else:
                return handler(event, *args, **{"plugin": context})
        else:
            if asyncio.iscoroutinefunction(handler):
                return await handler(event, plugin=context)
            else:
                return handler(event, plugin=context)

    def _parse_args(self, args_str: str, param_definitions: List[Dict]) -> list:
        """解析命令参数"""
        if not param_definitions:
            return [args_str] if args_str.strip() else []

        args = []
        remaining = args_str

        for param_def in param_definitions:
            if not remaining.strip():
                args.append(param_def.get("default"))
                continue

            if remaining.strip().startswith('"') or remaining.strip().startswith("'"):
                match = re.match(r'^["\'](.*?)["\']\s*(.*)', remaining, re.DOTALL)
                if match:
                    args.append(match.group(1))
                    remaining = match.group(2)
                    continue

            parts = remaining.split(None, 1)
            if parts:
                args.append(parts[0])
                remaining = parts[1] if len(parts) > 1 else ""
            else:
                args.append(param_def.get("default"))

        if remaining.strip():
            args.append(remaining.strip())

        return args

    def get_help(
        self, category: Optional[str] = None, user_permission: CommandPermission = CommandPermission.PUBLIC
    ) -> str:
        """
        生成帮助信息

        Args:
            category: 可选的分类过滤
            user_permission: 用户权限级别

        Returns:
            格式化的帮助文本
        """
        sections = []

        categories_to_show = [category] if category else sorted(self._category_map.keys())

        for cat in categories_to_show:
            commands_in_cat = self._category_map.get(cat, [])
            visible_commands = []

            for cmd_name in commands_in_cat:
                metadata = self._commands.get(cmd_name)
                if metadata and metadata.enabled and self._is_permission_visible(metadata.permission, user_permission):
                    visible_commands.append(metadata)

            if not visible_commands:
                continue

            category_names = {
                "identity": "👤 身份管理",
                "memory": "🧠 记忆系统",
                "knowledge": "📚 知识库",
                "learning": "🎓 学习模式",
                "system": "⚙️ 系统状态",
                "admin": "🔐 管理员",
                "general": "💬 通用命令",
            }

            section_title = category_names.get(cat, cat.title())
            section_lines = [f"\n### {section_title}\n"]

            for meta in visible_commands:
                aliases_str = f" (别名: {', '.join(f'/{a}' for a in meta.aliases)})" if meta.aliases else ""
                section_lines.append(f"- `/{meta.name}`{aliases_str}: {meta.description}")

                if meta.examples:
                    for example in meta.examples[:1]:
                        section_lines.append(f"  示例: {example}")

            sections.append("\n".join(section_lines))

        if not sections:
            return "暂无可用命令"

        header = "# 📜 Scriptor 命令指南\n\n💡 输入 `/命令名 参数` 来使用命令。使用 `/help 分类` 查看特定分类。\n"
        footer = "\n---\n💡 使用 `/sc_admin` 查看管理员专属命令"

        return header + "\n".join(sections) + footer

    def _is_permission_visible(self, cmd_perm: CommandPermission, user_perm: CommandPermission) -> bool:
        """判断命令是否对用户可见"""
        perm_order = [
            CommandPermission.PUBLIC,
            CommandPermission.USER,
            CommandPermission.MEMBER,
            CommandPermission.ADMIN,
            CommandPermission.SUPER_ADMIN,
        ]

        try:
            cmd_idx = perm_order.index(cmd_perm)
            user_idx = perm_order.index(user_perm)
            return user_idx >= cmd_idx
        except ValueError:
            return False

    def get_command_list(self) -> List[str]:
        """获取所有已注册的命令名称列表"""
        return list(self._commands.keys())

    def get_metadata(self, name: str) -> Optional[CommandMetadata]:
        """获取命令元数据"""
        resolved = self._resolve_command(name)
        return self._commands.get(resolved) if resolved else None

    def enable_command(self, name: str) -> bool:
        """启用命令"""
        metadata = self._commands.get(name)
        if metadata:
            metadata.enabled = True
            return True
        return False

    def disable_command(self, name: str) -> bool:
        """禁用命令"""
        metadata = self._commands.get(name)
        if metadata:
            metadata.enabled = False
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取路由器统计信息"""
        total = len(self._commands)
        enabled = sum(1 for cmd in self._commands.values() if cmd.enabled)
        categories = len(self._category_map)
        aliases = len(self._alias_map)

        return {
            "total_commands": total,
            "enabled_commands": enabled,
            "disabled_commands": total - enabled,
            "categories": categories,
            "aliases": aliases,
            "rate_limited_sessions": len(self._rate_limit_cache),
        }


_slash_command_router: Optional[SlashCommandRouter] = None


def get_slash_command_router() -> SlashCommandRouter:
    """获取 SlashCommandRouter 单例"""
    global _slash_command_router
    if _slash_command_router is None:
        _slash_command_router = SlashCommandRouter()
    return _slash_command_router
