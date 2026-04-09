# tools/common/async_io.py
"""异步IO工具模块"""

import asyncio
from pathlib import Path

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


async def async_read_json(file_path: Path, default=None):
    """
    异步读取 JSON 文件

    Args:
        file_path: 文件路径
        default: 读取失败时的默认值

    Returns:
        解析后的 JSON 对象或 default
    """
    import json

    if not file_path.exists():
        return default

    try:

        def _read_sync():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return await asyncio.to_thread(_read_sync)
    except Exception as e:
        logger.error(f"[Scriptor] 读取 JSON 文件失败 {file_path}: {e}")
        return default


async def async_write_json(file_path: Path, data):
    """
    异步写入 JSON 文件

    Args:
        file_path: 文件路径
        data: 要写入的数据
    """
    import json

    try:

        def _write_sync():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        await asyncio.to_thread(_write_sync)
    except Exception as e:
        logger.error(f"[Scriptor] 写入 JSON 文件失败 {file_path}: {e}")


async def async_read_text(file_path: Path, default: str = "") -> str:
    """
    异步读取文本文件

    Args:
        file_path: 文件路径
        default: 读取失败时的默认值

    Returns:
        文件内容或 default
    """
    if not file_path.exists():
        return default

    try:

        def _read_sync():
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        return await asyncio.to_thread(_read_sync)
    except Exception as e:
        logger.error(f"[Scriptor] 读取文本文件失败 {file_path}: {e}")
        return default


async def async_write_text(file_path: Path, text: str):
    """
    异步写入文本文件

    Args:
        file_path: 文件路径
        text: 要写入的文本
    """
    try:

        def _write_sync():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)

        await asyncio.to_thread(_write_sync)
    except Exception as e:
        logger.error(f"[Scriptor] 写入文本文件失败 {file_path}: {e}")


async def async_append_text(file_path: Path, text: str):
    """
    异步追加文本到文件

    Args:
        file_path: 文件路径
        text: 要追加的文本
    """
    try:

        def _append_sync():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(text)

        await asyncio.to_thread(_append_sync)
    except Exception as e:
        logger.error(f"[Scriptor] 追加文本文件失败 {file_path}: {e}")
