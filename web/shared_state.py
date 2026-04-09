# web/shared_state.py
"""
共享状态模块 - 用于主插件和 Web API 之间的数据共享
"""

import asyncio
from pathlib import Path
from typing import Any, Optional

_shared_state = {
    "data_dir": None,
    "search_engine": None,
    "identity_manager": None,
    "group_manager": None,
    "memory_manager": None,
    "config": None,
    "knowledge_base": None,
    "research_tool": None,
    "archive_manager": None,
    "archive_router": None,
    "data_ingestor": None,
    "initialized": False,
    "lock": asyncio.Lock(),
}


def set_shared_state(
    data_dir: Path,
    search_engine: Any,
    identity_manager: Any,
    group_manager: Any,
    memory_manager: Any,
    config: Any,
    knowledge_base: Any = None,
    research_tool: Any = None,
    archive_manager: Any = None,
    archive_router: Any = None,
    data_ingestor: Any = None,
):
    """设置共享状态（由主插件调用）"""
    _shared_state["data_dir"] = data_dir
    _shared_state["search_engine"] = search_engine
    _shared_state["identity_manager"] = identity_manager
    _shared_state["group_manager"] = group_manager
    _shared_state["memory_manager"] = memory_manager
    _shared_state["config"] = config
    _shared_state["knowledge_base"] = knowledge_base
    _shared_state["research_tool"] = research_tool
    _shared_state["archive_manager"] = archive_manager
    _shared_state["archive_router"] = archive_router
    _shared_state["data_ingestor"] = data_ingestor
    _shared_state["initialized"] = True


def get_data_dir() -> Optional[Path]:
    """获取数据目录"""
    return _shared_state["data_dir"]


def get_search_engine() -> Any:
    """获取搜索引擎实例"""
    return _shared_state["search_engine"]


def get_identity_manager() -> Any:
    """获取身份管理器实例"""
    return _shared_state["identity_manager"]


def get_group_manager() -> Any:
    """获取群体管理器实例"""
    return _shared_state["group_manager"]


def get_memory_manager() -> Any:
    """获取记忆管理器实例"""
    return _shared_state["memory_manager"]


def get_config() -> Any:
    """获取配置"""
    return _shared_state["config"]


def get_knowledge_base() -> Any:
    """获取知识库实例"""
    return _shared_state["knowledge_base"]


def get_research_tool() -> Any:
    """获取研究工具实例"""
    return _shared_state["research_tool"]


def get_archive_manager() -> Any:
    """获取档案管理器实例"""
    return _shared_state["archive_manager"]


def get_archive_router() -> Any:
    """获取档案路由器实例（三级架构）"""
    return _shared_state["archive_router"]


def get_data_ingestor() -> Any:
    """获取数据导入器实例"""
    return _shared_state["data_ingestor"]


def is_initialized() -> bool:
    """检查是否已初始化"""
    return _shared_state["initialized"]


async def trigger_reindex():
    """触发重新索引（编辑文件后调用）"""
    search_engine = get_search_engine()
    if search_engine and hasattr(search_engine, "_collect_all_docs_for_indexing"):
        try:
            all_docs = await search_engine._collect_all_docs_for_indexing("*", "*", "all")
            if all_docs:
                await search_engine.index_documents(all_docs)
                return True
        except Exception as e:
            print(f"[灵笔司书] 重新索引失败: {e}")
    return False
