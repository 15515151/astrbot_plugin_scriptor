# core/exceptions.py
"""Scriptor 统一异常处理模块

提供分层的异常体系：
1. ScriptorException - 基础异常
2. MemoryException - 记忆操作异常
3. ConfigException - 配置相关异常
4. SecurityException - 安全相关异常
5. SearchException - 搜索引擎异常
6. ToolException - 工具执行异常

使用方式：
    from core.exceptions import MemoryException, raise_if_memory_error

    try:
        memory_manager.record(...)
    except MemoryException as e:
        logger.error(f"记忆操作失败: {e}")
        # 处理错误

设计原则：
- 异常应该携带上下文信息（操作、原因、建议修复方案）
- 异常层次清晰，便于精确捕获
- 支持链式异常（__cause__）
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(Enum):
    """错误严重程度"""

    CRITICAL = "critical"  # 严重错误，需要立即处理
    ERROR = "error"  # 一般错误
    WARNING = "warning"  # 警告（非致命）
    INFO = "info"  # 信息性提示


@dataclass
class ErrorContext:
    """错误上下文信息"""

    operation: str  # 发生错误的操作
    component: str  # 出错的组件/模块
    user_message: str  # 用户友好的错误消息
    technical_details: Optional[str] = None  # 技术细节（用于日志）
    suggested_fix: Optional[str] = None  # 建议的修复方案
    error_code: Optional[str] = None  # 错误码（用于文档索引）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 API 响应）"""
        return {
            "operation": self.operation,
            "component": self.component,
            "user_message": self.user_message,
            "technical_details": self.technical_details,
            "suggested_fix": self.suggested_fix,
            "error_code": self.error_code,
            "metadata": self.metadata,
        }


class ScriptorException(Exception):
    """
    Scriptor 基础异常

    所有自定义异常的基类，提供统一的错误信息格式和上下文。
    """

    default_severity: ErrorSeverity = ErrorSeverity.ERROR
    default_user_message: str = "发生未知错误"

    def __init__(
        self, message: str, context: Optional[ErrorContext] = None, severity: Optional[ErrorSeverity] = None, **kwargs
    ):
        super().__init__(message)

        self.message = message
        self.context = context or ErrorContext(
            operation="unknown", component="unknown", user_message=self.default_user_message
        )

        self.severity = severity or self.default_severity

        # 额外的关键字参数存储到元数据中
        if kwargs:
            self.context.metadata.update(kwargs)

    @property
    def user_friendly_message(self) -> str:
        """返回用户友好的错误消息"""
        return self.context.user_message

    @property
    def technical_message(self) -> str:
        """返回技术性详细消息"""
        if self.context.technical_details:
            return f"{self.message} | {self.context.technical_details}"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 API 响应）"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "context": self.context.to_dict(),
        }

    def to_api_response(self, status_code: int = 500) -> Dict[str, Any]:
        """转换为 API 响应格式"""
        return {
            "success": False,
            "error": self.to_dict(),
            "status_code": status_code,
        }

    def __str__(self) -> str:
        return f"[{self.__class__.__name__}] {self.message}"


class MemoryException(ScriptorException):
    """记忆操作异常"""

    default_severity = ErrorSeverity.ERROR
    default_user_message = "记忆操作失败"

    def __init__(
        self,
        message: str,
        memory_type: str = "unknown",  # personal/group/global/cross
        operation: str = "unknown",  # read/write/delete/search
        uid: Optional[str] = None,
        group_id: Optional[str] = None,
        **kwargs,
    ):
        context = ErrorContext(
            operation=operation,
            component="memory_manager",
            user_message=f"{memory_type} 记忆{operation}失败: {message}",
            technical_details=message,
            error_code=f"MEM_{operation.upper()}_{memory_type.upper()}",
            metadata={
                "memory_type": memory_type,
                "operation": operation,
                "uid": uid,
                "group_id": group_id,
            },
        )

        super().__init__(message, context=context, **kwargs)


class MemoryNotFoundException(MemoryException):
    """记忆未找到异常"""

    default_severity = ErrorSeverity.WARNING
    default_user_message = "指定的记忆不存在"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)
        self.context.error_code = "MEM_NOT_FOUND"
        self.context.suggested_fix = "请检查记忆 ID 或搜索关键词是否正确"


class MemoryWriteException(MemoryException):
    """记忆写入异常"""

    default_severity = ErrorSeverity.ERROR
    default_user_message = "无法写入记忆"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, operation="write", **kwargs)
        self.context.error_code = "MEM_WRITE_ERROR"
        self.context.suggested_fix = "检查文件权限或磁盘空间是否充足"


class MemoryReadException(MemoryException):
    """记忆读取异常"""

    default_severity = ErrorSeverity.ERROR
    default_user_message = "无法读取记忆"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, operation="read", **kwargs)
        self.context.error_code = "MEM_READ_ERROR"
        self.context.suggested_fix = "检查记忆文件是否存在且格式正确"


class SearchException(ScriptorException):
    """搜索引擎异常"""

    default_severity = ErrorSeverity.ERROR
    default_user_message = "搜索操作失败"

    def __init__(
        self, message: str, search_engine: str = "unknown", query: Optional[str] = None, **kwargs  # bm25/vector/hybrid
    ):
        context = ErrorContext(
            operation="search",
            component=f"search_engine_{search_engine}",
            user_message=f"搜索失败 ({search_engine}): {message}",
            technical_details=message,
            error_code=f"SEARCH_{search_engine.upper()}_ERROR",
            metadata={"search_engine": search_engine, "query": query},
        )

        super().__init__(message, context=context, **kwargs)


class SearchTimeoutException(SearchException):
    """搜索超时异常"""

    default_severity = ErrorSeverity.WARNING
    default_user_message = "搜索超时，请稍后重试"

    def __init__(self, message: str, timeout_seconds: float = 0, **kwargs):
        super().__init__(message, **kwargs)
        self.context.error_code = "SEARCH_TIMEOUT"
        self.context.suggested_fix = "尝试简化搜索词或缩小范围"
        self.context.metadata["timeout_seconds"] = timeout_seconds


class ConfigException(ScriptorException):
    """配置相关异常"""

    default_severity = ErrorSeverity.CRITICAL
    default_user_message = "配置错误"

    def __init__(self, message: str, config_key: Optional[str] = None, config_section: Optional[str] = None, **kwargs):
        context = ErrorContext(
            operation="config_validation",
            component="config_manager",
            user_message=f"配置验证失败: {message}" if config_key else message,
            technical_details=message,
            error_code="CONFIG_VALIDATION_ERROR",
            metadata={
                "config_key": config_key,
                "config_section": config_section,
            },
        )

        super().__init__(message, context=context, **kwargs)


class SecurityException(ScriptorException):
    """安全相关异常"""

    default_severity = ErrorSeverity.CRITICAL
    default_user_message = "安全检查失败"

    def __init__(self, message: str, security_violation: str = "unknown", **kwargs):  # auth/csrf/path_traversal/xss
        context = ErrorContext(
            operation="security_check",
            component="security_layer",
            user_message=f"安全违规 ({security_violation})",
            technical_details=message,
            error_code=f"SECURITY_{security_violation.upper()}",
            metadata={"security_violation": security_violation},
        )

        super().__init__(message, context=context, **kwargs)


class AuthenticationException(SecurityException):
    """认证异常"""

    default_severity = ErrorSeverity.WARNING
    default_user_message = "认证失败"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, security_violation="auth", **kwargs)
        self.context.error_code = "SECURITY_AUTH_FAILED"
        self.context.suggested_fix = "请检查 API Key 或重新登录"


class AuthorizationException(SecurityException):
    """授权异常"""

    default_severity = ErrorSeverity.WARNING
    default_user_message = "权限不足"

    def __init__(self, message: str, required_permission: str = "unknown", **kwargs):
        super().__init__(message, security_violation="authorization", **kwargs)
        self.context.error_code = "SECURITY_AUTHZ_DENIED"
        self.context.suggested_fix = f"需要权限: {required_permission}"
        self.context.metadata["required_permission"] = required_permission


class ToolException(ScriptorException):
    """工具执行异常"""

    default_severity = ErrorSeverity.ERROR
    default_user_message = "工具执行失败"

    def __init__(self, message: str, tool_name: str = "unknown", tool_args: Optional[Dict] = None, **kwargs):
        context = ErrorContext(
            operation=f"tool_execute:{tool_name}",
            component="tool_system",
            user_message=f"工具 [{tool_name}] 执行失败: {message}",
            technical_details=message,
            error_code=f"TOOL_{tool_name.upper()}_ERROR",
            metadata={
                "tool_name": tool_name,
                "tool_args": tool_args or {},
            },
        )

        super().__init__(message, context=context, **kwargs)


class ToolTimeoutException(ToolException):
    """工具超时异常"""

    default_severity = ErrorSeverity.WARNING
    default_user_message = "工具执行超时"

    def __init__(self, message: str, timeout_seconds: float = 0, **kwargs):
        super().__init__(message, **kwargs)
        self.context.error_code = "TOOL_TIMEOUT"
        self.context.suggested_fix = "尝试简化任务或增加超时时间"
        self.context.metadata["timeout_seconds"] = timeout_seconds


class ToolPermissionDeniedException(ToolException):
    """工具权限拒绝异常"""

    default_severity = ErrorSeverity.WARNING
    default_user_message = "无权使用此工具"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)
        self.context.error_code = "TOOL_PERMISSION_DENIED"
        self.context.severity = ErrorSeverity.WARNING


class KnowledgeBaseException(ScriptorException):
    """知识库异常"""

    default_severity = ErrorSeverity.ERROR
    default_user_message = "知识库操作失败"

    def __init__(
        self,
        message: str,
        operation: str = "unknown",  # add/delete/search/update
        item_id: Optional[str] = None,
        **kwargs,
    ):
        context = ErrorContext(
            operation=f"kb_{operation}",
            component="knowledge_base",
            user_message=f"知识库{operation}失败: {message}",
            technical_details=message,
            error_code=f"KB_{operation.upper()}_ERROR",
            metadata={"item_id": item_id, "operation": operation},
        )

        super().__init__(message, context=context, **kwargs)


class ArchiveException(ScriptorException):
    """档案馆异常"""

    default_severity = ErrorSeverity.ERROR
    default_user_message = "档案馆操作失败"

    def __init__(self, message: str, table_name: Optional[str] = None, operation: str = "unknown", **kwargs):
        context = ErrorContext(
            operation=f"archive_{operation}",
            component="archive_manager",
            user_message=f"档案馆{operation}失败: {message}",
            technical_details=message,
            error_code=f"ARCHIVE_{operation.upper()}_ERROR",
            metadata={"table_name": table_name, "operation": operation},
        )

        super().__init__(message, context=context, **kwargs)


class ConcurrencyException(ScriptorException):
    """并发控制异常"""

    default_severity = ErrorSeverity.WARNING
    default_user_message = "并发冲突"

    def __init__(self, message: str, session_id: Optional[str] = None, conflict_type: str = "lock_timeout", **kwargs):
        context = ErrorContext(
            operation="concurrency_control",
            component="concurrency_guard",
            user_message=f"并发冲突 ({conflict_type}): {message}",
            technical_details=message,
            error_code=f"CONCURRENCY_{conflict_type.upper()}",
            metadata={"session_id": session_id, "conflict_type": conflict_type},
        )

        super().__init__(message, context=context, **kwargs)


class EncryptionException(ScriptorException):
    """加密相关异常"""

    default_severity = ErrorSeverity.CRITICAL
    default_user_message = "加密操作失败"

    def __init__(self, message: str, operation: str = "unknown", **kwargs):  # encrypt/decrypt/init
        context = ErrorContext(
            operation=f"encryption_{operation}",
            component="encryption_module",
            user_message=f"加密{operation}失败: {message}",
            technical_details=message,
            error_code=f"ENCRYPTION_{operation.upper()}_ERROR",
            metadata={"operation": operation},
        )

        super().__init__(message, context=context, **kwargs)


def create_exception_handler(logger_instance=None):
    """
    创建统一的异常处理器装饰器

    用法：
        exception_handler = create_exception_handler(logger)

        @exception_handler
        async def my_function():
            ...
    """
    import traceback as tb_module
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ScriptorException as e:
                if logger_instance:
                    logger_instance.error(f"[{e.context.operation}] {e.technical_message}")
                raise
            except Exception as e:
                if logger_instance:
                    logger_instance.error(f"[{func.__name__}] 未预期异常: {e!s}\n{tb_module.format_exc()}")
                raise ScriptorException(
                    f"未预期的内部错误: {e!s}",
                    context=ErrorContext(
                        operation=func.__name__,
                        component="unknown",
                        user_message="系统内部错误，请联系管理员",
                        technical_details=str(e),
                        error_code="INTERNAL_ERROR",
                    ),
                    severity=ErrorSeverity.CRITICAL,
                ) from e

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ScriptorException as e:
                if logger_instance:
                    logger_instance.error(f"[{e.context.operation}] {e.technical_message}")
                raise
            except Exception as e:
                if logger_instance:
                    logger_instance.error(f"[{func.__name__}] 未预期异常: {e!s}\n{tb_module.format_exc()}")
                raise ScriptorException(
                    f"未预期的内部错误: {e!s}",
                    context=ErrorContext(
                        operation=func.__name__,
                        component="unknown",
                        user_message="系统内部错误，请联系管理员",
                        technical_details=str(e),
                        error_code="INTERNAL_ERROR",
                    ),
                    severity=ErrorSeverity.CRITICAL,
                ) from e

        # 判断函数是否是异步的
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def safe_execute(func, *args, default_value=None, on_error=None, **kwargs):
    """
    安全执行函数，捕获所有异常并返回默认值

    Args:
        func: 要执行的函数
        *args: 函数位置参数
        default_value: 出错时的默认返回值
        on_error: 错误回调 (exception -> None)
        **kwargs: 函数关键字参数

    Returns:
        函数结果或 default_value
    """
    try:
        result = func(*args, **kwargs)

        # 如果是协程，直接返回（调用者需 await）
        import asyncio

        if asyncio.iscoroutine(result):
            return result

        return result
    except Exception as e:
        if on_error:
            on_error(e)
        return default_value
