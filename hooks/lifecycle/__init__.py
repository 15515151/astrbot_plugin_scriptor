# hooks/lifecycle/__init__.py
"""生命周期钩子模块"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class LifecycleHook(ABC):
    """生命周期钩子基类"""

    @abstractmethod
    async def on_startup(self, data_dir: Path):
        """插件启动时调用"""
        pass

    @abstractmethod
    async def on_shutdown(self):
        """插件关闭时调用"""
        pass


class StartupHook(LifecycleHook):
    """启动钩子 - 可继承自定义启动行为"""

    async def on_startup(self, data_dir: Path):
        """插件启动时的初始化逻辑"""
        pass


class ShutdownHook(LifecycleHook):
    """关闭钩子 - 可继承自定义清理逻辑"""

    async def on_shutdown(self):
        """插件关闭时的清理逻辑"""
        pass
