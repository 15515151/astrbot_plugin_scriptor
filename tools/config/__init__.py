# tools/config/__init__.py
"""配置管理模块 - 集中管理各类配置"""

from .compactor_prompts import (
    COMPACT_PROMPT,
    EXPERIENCE_EXTRACTION_PROMPT,
    PROFILE_REFINEMENT_PROMPT,
    SLEEP_CONSOLIDATION_PROMPT,
)
from .enhanced_patterns import (
    FINAL_LIMIT,
    GROUP_LIMITS,
    MEMORY_TRIGGER_WORDS,
    REFLECTION_CONFIG,
    SIMPLE_PATTERNS,
    TYPE_GROUPS,
)
from .memory_patterns import (
    MEMORY_KEYWORDS,
    MEMORY_TYPES,
)
from .sanitizer_rules import (
    ERROR_PATTERNS,
    PLATFORM_RULES,
)

__all__ = [
    "COMPACT_PROMPT",
    "ERROR_PATTERNS",
    "EXPERIENCE_EXTRACTION_PROMPT",
    "FINAL_LIMIT",
    "GROUP_LIMITS",
    "MEMORY_KEYWORDS",
    "MEMORY_TRIGGER_WORDS",
    "MEMORY_TYPES",
    "PLATFORM_RULES",
    "PROFILE_REFINEMENT_PROMPT",
    "REFLECTION_CONFIG",
    "SIMPLE_PATTERNS",
    "SLEEP_CONSOLIDATION_PROMPT",
    "TYPE_GROUPS",
]
