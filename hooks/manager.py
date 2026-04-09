# hooks/manager.py
"""Hook管理器 - 实现完整的插件化扩展机制"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .lifecycle import LifecycleHook, ShutdownHook, StartupHook
from .llm import LLMHook, RequestHook, ResponseHook
from .message import MessageHook, RecordingHook
from .search import IndexHook, RerankHook, SearchHook, SearchQuery, SearchResult
from .storage import BackupHook, StorageHook

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


@dataclass
class HookRegistration:
    """钩子注册信息"""

    name: str
    hook_class: Type
    instance: Any
    enabled: bool = True
    priority: int = 100


class HookManager:
    """
    全局钩子管理器 - 实现插件化扩展机制

    支持的钩子类型：
    - LifecycleHook: 生命周期钩子（启动/关闭）
    - MessageHook: 消息处理钩子
    - LLMHook: LLM交互钩子
    - StorageHook: 存储操作钩子
    - SearchHook: 搜索操作钩子
    """

    _instance: Optional["HookManager"] = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._hooks: Dict[str, List[HookRegistration]] = {
            "lifecycle": [],
            "startup": [],
            "shutdown": [],
            "message": [],
            "recording": [],
            "llm_request": [],
            "llm_response": [],
            "llm_tool": [],
            "storage_save": [],
            "storage_load": [],
            "storage_backup": [],
            "search": [],
            "rerank": [],
            "index": [],
        }

        self._hook_registry: Dict[str, Type] = {
            "lifecycle": LifecycleHook,
            "startup": StartupHook,
            "shutdown": ShutdownHook,
            "message": MessageHook,
            "recording": RecordingHook,
            "llm_request": RequestHook,
            "llm_response": ResponseHook,
            "llm_tool": LLMHook,
            "storage_save": StorageHook,
            "storage_load": StorageHook,
            "storage_backup": BackupHook,
            "search": SearchHook,
            "rerank": RerankHook,
            "index": IndexHook,
        }

        self._initialized = True
        logger.info("[HookManager] 钩子管理器初始化完成")

    def register(self, hook_instance: Any, name: Optional[str] = None, priority: int = 100) -> bool:
        """
        注册一个钩子实例

        Args:
            hook_instance: 钩子实例
            name: 钩子名称（默认使用类名）
            priority: 优先级（越小越先执行）

        Returns:
            是否注册成功
        """
        hook_name = name or hook_instance.__class__.__name__

        hook_type = self._find_hook_type(hook_instance)
        if not hook_type:
            logger.warning(f"[HookManager] 无法识别钩子类型: {hook_name}")
            return False

        registration = HookRegistration(
            name=hook_name, hook_class=type(hook_instance), instance=hook_instance, priority=priority
        )

        if hook_type not in self._hooks:
            self._hooks[hook_type] = []

        self._hooks[hook_type].append(registration)
        self._hooks[hook_type].sort(key=lambda x: x.priority)

        logger.info(f"[HookManager] 注册钩子: {hook_name} (类型: {hook_type}, 优先级: {priority})")
        return True

    def unregister(self, name: str) -> bool:
        """
        注销指定名称的钩子

        Args:
            name: 钩子名称

        Returns:
            是否注销成功
        """
        for hook_list in self._hooks.values():
            for i, reg in enumerate(hook_list):
                if reg.name == name:
                    hook_list.pop(i)
                    logger.info(f"[HookManager] 注销钩子: {name}")
                    return True
        return False

    def enable(self, name: str) -> bool:
        """启用指定钩子"""
        for hook_list in self._hooks.values():
            for reg in hook_list:
                if reg.name == name:
                    reg.enabled = True
                    logger.info(f"[HookManager] 启用钩子: {name}")
                    return True
        return False

    def disable(self, name: str) -> bool:
        """禁用指定钩子"""
        for hook_list in self._hooks.values():
            for reg in hook_list:
                if reg.name == name:
                    reg.enabled = False
                    logger.info(f"[HookManager] 禁用钩子: {name}")
                    return True
        return False

    def get_hooks(self, hook_type: str) -> List[Any]:
        """获取指定类型的所有启用的钩子"""
        return [reg.instance for reg in self._hooks.get(hook_type, []) if reg.enabled]

    def _find_hook_type(self, instance: Any) -> Optional[str]:
        """查找实例对应的钩子类型"""
        for hook_type, hook_class in self._hook_registry.items():
            if isinstance(instance, hook_class):
                return hook_type
        return None

    async def invoke_startup(self, data_dir: Path):
        """调用所有启动钩子"""
        for reg in self._hooks.get("startup", []):
            if reg.enabled:
                try:
                    await reg.instance.on_startup(data_dir)
                    logger.debug(f"[HookManager] 执行启动钩子: {reg.name}")
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 启动钩子执行失败 {reg.name}: {e}")

    async def invoke_shutdown(self):
        """调用所有关闭钩子"""
        for reg in self._hooks.get("shutdown", []):
            if reg.enabled:
                try:
                    await reg.instance.on_shutdown()
                    logger.debug(f"[HookManager] 执行关闭钩子: {reg.name}")
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 关闭钩子执行失败 {reg.name}: {e}")

    async def invoke_message_recording(self, event: Any) -> bool:
        """调用消息记录前钩子，返回是否继续记录"""
        for reg in self._hooks.get("recording", []):
            if reg.enabled:
                try:
                    result = await reg.instance.on_before_recording(event)
                    if result is False:
                        logger.debug(f"[HookManager] 消息记录被钩子拦截: {reg.name}")
                        return False
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 消息记录前钩子执行失败 {reg.name}: {e}")
        return True

    async def invoke_message_recorded(self, event: Any, uid: str, group_id: str):
        """调用消息记录后钩子"""
        for reg in self._hooks.get("recording", []):
            if reg.enabled:
                try:
                    await reg.instance.on_after_recording(event, uid, group_id)
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 消息记录后钩子执行失败 {reg.name}: {e}")

    async def invoke_buffer_flush(self, session_id: str, messages: List[str]):
        """调用缓冲刷新钩子"""
        for reg in self._hooks.get("recording", []):
            if reg.enabled and hasattr(reg.instance, "on_buffer_flush"):
                try:
                    await reg.instance.on_buffer_flush(session_id, messages)
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 缓冲刷新钩子执行失败 {reg.name}: {e}")

    async def invoke_llm_request(self, event: Any, req: Any) -> Any:
        """调用LLM请求前钩子"""
        result = req
        for reg in self._hooks.get("llm_request", []):
            if reg.enabled:
                try:
                    result = await reg.instance.on_before_request(event, result)
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] LLM请求前钩子执行失败 {reg.name}: {e}")
        return result

    async def invoke_llm_response(self, event: Any, resp: Any):
        """调用LLM响应后钩子"""
        for reg in self._hooks.get("llm_response", []):
            if reg.enabled:
                try:
                    await reg.instance.on_after_response(event, resp)
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] LLM响应后钩子执行失败 {reg.name}: {e}")

    async def invoke_tool_call(self, tool_name: str, tool_args: Dict, result: str):
        """调用工具调用钩子"""
        for reg in self._hooks.get("llm_tool", []):
            if reg.enabled and hasattr(reg.instance, "on_tool_call"):
                try:
                    await reg.instance.on_tool_call(tool_name, tool_args, result)
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 工具调用钩子执行失败 {reg.name}: {e}")

    async def invoke_before_save(self, file_path: Path, content: str) -> str:
        """调用文件保存前钩子"""
        result = content
        for reg in self._hooks.get("storage_save", []):
            if reg.enabled:
                try:
                    hook_result = await reg.instance.on_before_save(file_path, result)
                    if hook_result is not None:
                        result = hook_result
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 保存前钩子执行失败 {reg.name}: {e}")
        return result

    async def invoke_after_save(self, file_path: Path, content: str):
        """调用文件保存后钩子"""
        for reg in self._hooks.get("storage_save", []):
            if reg.enabled:
                try:
                    await reg.instance.on_after_save(file_path, content)
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 保存后钩子执行失败 {reg.name}: {e}")

    async def invoke_before_load(self, file_path: Path) -> Optional[bytes]:
        """调用文件加载前钩子"""
        for reg in self._hooks.get("storage_load", []):
            if reg.enabled:
                try:
                    result = await reg.instance.on_before_load(file_path)
                    if result is not None:
                        return result
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 加载前钩子执行失败 {reg.name}: {e}")
        return None

    async def invoke_after_load(self, file_path: Path, content: Any) -> Any:
        """调用文件加载后钩子"""
        result = content
        for reg in self._hooks.get("storage_load", []):
            if reg.enabled:
                try:
                    hook_result = await reg.instance.on_after_load(file_path, result)
                    if hook_result is not None:
                        result = hook_result
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 加载后钩子执行失败 {reg.name}: {e}")
        return result

    async def invoke_before_search(self, query: SearchQuery) -> SearchQuery:
        """调用搜索前钩子"""
        result = query
        for reg in self._hooks.get("search", []):
            if reg.enabled:
                try:
                    hook_result = await reg.instance.on_before_search(result)
                    if hook_result is not None:
                        result = hook_result
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 搜索前钩子执行失败 {reg.name}: {e}")
        return result

    async def invoke_after_search(self, results: List[SearchResult]) -> List[SearchResult]:
        """调用搜索后钩子"""
        result = results
        for reg in self._hooks.get("search", []):
            if reg.enabled:
                try:
                    hook_result = await reg.instance.on_after_search(result)
                    if hook_result is not None:
                        result = hook_result
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 搜索后钩子执行失败 {reg.name}: {e}")
        return result

    async def invoke_before_rerank(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """调用重排前钩子"""
        result = results
        for reg in self._hooks.get("rerank", []):
            if reg.enabled:
                try:
                    hook_result = await reg.instance.on_before_rerank(result, query)
                    if hook_result is not None:
                        result = hook_result
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 重排前钩子执行失败 {reg.name}: {e}")
        return result

    async def invoke_after_rerank(self, results: List[SearchResult]) -> List[SearchResult]:
        """调用重排后钩子"""
        result = results
        for reg in self._hooks.get("rerank", []):
            if reg.enabled:
                try:
                    hook_result = await reg.instance.on_after_rerank(result)
                    if hook_result is not None:
                        result = hook_result
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 重排后钩子执行失败 {reg.name}: {e}")
        return result

    async def invoke_before_index(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """调用索引前钩子"""
        result = document
        for reg in self._hooks.get("index", []):
            if reg.enabled:
                try:
                    hook_result = await reg.instance.on_before_index(result)
                    if hook_result is not None:
                        result = hook_result
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 索引前钩子执行失败 {reg.name}: {e}")
        return result

    async def invoke_after_index(self, document_id: str, document: Dict[str, Any]):
        """调用索引后钩子"""
        for reg in self._hooks.get("index", []):
            if reg.enabled:
                try:
                    await reg.instance.on_after_index(document_id, document)
                except (OSError, RuntimeError) as e:
                    logger.error(f"[HookManager] 索引后钩子执行失败 {reg.name}: {e}")

    def list_hooks(self) -> Dict[str, List[str]]:
        """列出所有已注册的钩子"""
        result = {}
        for hook_type, registrations in self._hooks.items():
            result[hook_type] = [
                f"{reg.name} (enabled={reg.enabled}, priority={reg.priority})" for reg in registrations
            ]
        return result

    def clear_all(self):
        """清除所有钩子注册"""
        for key in self._hooks:
            self._hooks[key].clear()
        logger.info("[HookManager] 已清除所有钩子注册")


def get_hook_manager() -> HookManager:
    """获取全局钩子管理器实例"""
    return HookManager()


class DefaultStartupHook(StartupHook):
    """默认启动钩子实现"""

    async def on_startup(self, data_dir: Path):
        logger.info(f"[DefaultStartupHook] Scriptor 插件启动，数据目录: {data_dir}")


class DefaultShutdownHook(ShutdownHook):
    """默认关闭钩子实现"""

    async def on_shutdown(self):
        logger.info("[DefaultShutdownHook] Scriptor 插件关闭")
