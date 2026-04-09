# hooks/llm/__init__.py
"""LLM交互钩子模块"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMHook(ABC):
    """LLM钩子基类"""

    @abstractmethod
    async def on_before_request(self, event: Any, req: Any) -> Any:
        """
        LLM请求前调用

        Args:
            event: 消息事件
            req: LLM请求对象

        Returns:
            修改后的请求对象
        """
        return req

    @abstractmethod
    async def on_after_response(self, event: Any, resp: Any):
        """
        LLM响应后调用

        Args:
            event: 消息事件
            resp: LLM响应对象
        """
        pass

    @abstractmethod
    async def on_tool_call(self, tool_name: str, tool_args: Dict, result: str):
        """
        工具调用时调用

        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            result: 工具执行结果
        """
        pass


class RequestHook(LLMHook):
    """请求钩子 - 可继承自定义请求处理"""

    async def on_before_request(self, event: Any, req: Any) -> Any:
        return req

    async def on_after_response(self, event: Any, resp: Any):
        pass

    async def on_tool_call(self, tool_name: str, tool_args: Dict, result: str):
        pass


class ResponseHook(LLMHook):
    """响应钩子 - 可继承自定义响应处理"""

    async def on_before_request(self, event: Any, req: Any) -> Any:
        return req

    async def on_after_response(self, event: Any, resp: Any):
        pass

    async def on_tool_call(self, tool_name: str, tool_args: Dict, result: str):
        pass
