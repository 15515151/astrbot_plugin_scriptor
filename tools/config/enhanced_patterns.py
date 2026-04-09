# tools/config/enhanced_patterns.py
"""增强功能配置 - 轻量判断、反思调度、链式回忆配置"""

SIMPLE_PATTERNS = [
    r"^(你好|您好|hi|hello|hey|嗨)[，。！？!?]*$",
    r"^(再见|拜拜|bye|goodbye)[，。！？!?]*$",
    r"^(谢谢|感谢|thanks|thank you)[，。！？!?]*$",
    r"^(好的|ok|okay|是的|对)[，。！？!?]*$",
    r"^(现在几点|今天天气|今天星期几|今天几号)[，。！？!?]*$",
]

MEMORY_TRIGGER_WORDS = [
    "记得",
    "回忆",
    "上次",
    "之前",
    "过去",
    "以前",
    "我的",
    "你说过",
    "告诉过我",
    "我们",
    "任务",
    "提醒",
    "计划",
    "决定",
    "偏好",
    "喜欢",
    "讨厌",
    "习惯",
]

TYPE_GROUPS = {
    "preference": ["preference", "like", "dislike", "favorite"],
    "fact": ["fact", "information", "knowledge"],
    "task": ["task", "todo", "reminder", "plan"],
    "decision": ["decision", "choice", "plan"],
    "experience": ["experience", "rule", "lesson"],
}

GROUP_LIMITS = {
    "preference": 3,
    "fact": 5,
    "task": 4,
    "decision": 3,
    "experience": 2,
}

FINAL_LIMIT = 7

REFLECTION_CONFIG = {
    "message_threshold": 15,
    "time_threshold": 1800,
    "topic_change_threshold": 0.7,
}
