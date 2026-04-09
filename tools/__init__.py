# tools/__init__.py
"""
Scriptor 工具模块
提供通用工具函数和类，供 core 和其他模块使用
"""

from .common.async_io import (
    async_append_text,
    async_read_json,
    async_read_text,
    async_write_json,
    async_write_text,
)
from .common.json_parser import (
    extract_json_from_llm_output,
    safe_json_loads,
)
from .security.sanitizer import (
    SAFE_FILENAME_PATTERN,
    sanitize_filename,
    sanitize_id,
    sanitize_log_message,
)
from .storage.debounced_writer import DebouncedWriter

try:
    from .performance.monitor import (
        OperationMetric,
        OperationTimer,
        PerformanceMonitor,
        PerformanceSnapshot,
        PerformanceTracker,
        get_operation_timer,
        track_operation,
    )

    _has_performance = True
except ImportError:
    _has_performance = False

__all__ = [
    # security
    "sanitize_id",
    "sanitize_filename",
    "sanitize_log_message",
    "SAFE_FILENAME_PATTERN",
    # common
    "safe_json_loads",
    "extract_json_from_llm_output",
    "async_read_json",
    "async_write_json",
    "async_read_text",
    "async_write_text",
    "async_append_text",
    # storage
    "DebouncedWriter",
]

if _has_performance:
    __all__.extend(
        [
            "OperationMetric",
            "OperationTimer",
            "PerformanceMonitor",
            "PerformanceSnapshot",
            "PerformanceTracker",
            "get_operation_timer",
            "track_operation",
        ]
    )
