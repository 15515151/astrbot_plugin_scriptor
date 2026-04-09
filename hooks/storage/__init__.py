# hooks/storage/__init__.py
"""存储钩子模块 - 提供存储操作扩展点"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class StorageHook(ABC):
    """存储钩子基类 - 提供存储操作前后的扩展点"""

    @abstractmethod
    async def on_before_save(self, file_path: Path, content: str) -> Optional[str]:
        """
        文件保存前调用

        Args:
            file_path: 文件路径
            content: 要保存的内容

        Returns:
            修改后的内容，如果返回None则使用原始内容
        """
        pass

    @abstractmethod
    async def on_after_save(self, file_path: Path, content: str):
        """
        文件保存后调用

        Args:
            file_path: 文件路径
            content: 已保存的内容
        """
        pass

    @abstractmethod
    async def on_before_load(self, file_path: Path) -> Optional[bytes]:
        """
        文件加载前调用

        Args:
            file_path: 文件路径

        Returns:
            如果返回bytes则使用返回的内容加载
        """
        pass

    @abstractmethod
    async def on_after_load(self, file_path: Path, content: Any) -> Optional[Any]:
        """
        文件加载后调用

        Args:
            file_path: 文件路径
            content: 加载的内容

        Returns:
            修改后的内容，如果返回None则使用原始内容
        """
        pass

    @abstractmethod
    async def on_save_error(self, file_path: Path, content: str, error: Exception):
        """
        文件保存出错时调用

        Args:
            file_path: 文件路径
            content: 要保存的内容
            error: 异常对象
        """
        pass

    @abstractmethod
    async def on_load_error(self, file_path: Path, error: Exception):
        """
        文件加载出错时调用

        Args:
            file_path: 文件路径
            error: 异常对象
        """
        pass


class BackupHook(ABC):
    """备份钩子 - 提供备份操作扩展点"""

    @abstractmethod
    async def on_before_backup(self, backup_name: str) -> Optional[str]:
        """
        备份创建前调用

        Args:
            backup_name: 备份名称

        Returns:
            修改后的备份名称，如果返回None则使用原始名称
        """
        pass

    @abstractmethod
    async def on_after_backup(self, backup_path: Path):
        """
        备份创建后调用

        Args:
            backup_path: 备份路径
        """
        pass

    @abstractmethod
    async def on_before_restore(self, backup_name: str):
        """
        数据恢复前调用

        Args:
            backup_name: 备份名称
        """
        pass

    @abstractmethod
    async def on_after_restore(self, backup_name: str):
        """
        数据恢复后调用

        Args:
            backup_name: 备份名称
        """
        pass
