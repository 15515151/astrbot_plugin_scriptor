# tools/recurrence_parser.py
"""
自然语言循环表达式解析器

支持的表达式：
- "every monday" / "每周一"
- "every day" / "每天"
- "every week" / "每周"
- "every month" / "每月"
- "every 2 days" / "每2天"
- "every monday wednesday" / "每周一、三"
- "weekdays" / "工作日"
- "weekends" / "周末"

输出：
- recurrence_type: daily/weekly/monthly/custom
- interval: 间隔（天/周/月）
- weekdays: 星期几列表 (0=周一, 6=周日)
- next_trigger: 下次触发时间
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class RecurrenceType(Enum):
    """循环类型"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


@dataclass
class ParsedRecurrence:
    """解析结果"""

    recurrence_type: RecurrenceType
    interval: int = 1
    weekdays: List[int] = None
    month_day: int = None
    description: str = ""
    raw_expression: str = ""
    valid: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recurrence_type": self.recurrence_type.value,
            "interval": self.interval,
            "weekdays": self.weekdays,
            "month_day": self.month_day,
            "description": self.description,
            "raw_expression": self.raw_expression,
            "valid": self.valid,
        }


WEEKDAY_MAP_CN = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "1": 0,
    "2": 1,
    "3": 2,
    "4": 3,
    "5": 4,
    "6": 5,
    "7": 6,
}

WEEKDAY_MAP_EN = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}


class RecurrenceParser:
    """循环表达式解析器"""

    def __init__(self):
        pass

    def parse(self, expression: str) -> ParsedRecurrence:
        """
        解析自然语言循环表达式

        Args:
            expression: 自然语言表达式，如 "every monday", "每天", "每周三"

        Returns:
            ParsedRecurrence 解析结果
        """
        if not expression or not expression.strip():
            return ParsedRecurrence(
                recurrence_type=RecurrenceType.CUSTOM, raw_expression=expression, valid=False, error="表达式为空"
            )

        expr = expression.strip().lower()

        patterns = [
            (self._parse_every_pattern, "every 模式"),
            (self._parse_chinese_frequency, "中文频率"),
            (self._parse_weekdays_weekends, "工作日/周末"),
            (self._parse_simple_daily, "简单每日"),
        ]

        for parser_func, pattern_name in patterns:
            try:
                result = parser_func(expr)
                if result and result.valid:
                    return result
            except Exception as e:
                logger.debug(f"[RecurrenceParser] {pattern_name} 解析失败: {e}")

        return ParsedRecurrence(
            recurrence_type=RecurrenceType.CUSTOM,
            raw_expression=expression,
            valid=False,
            error=f"无法识别的循环表达式: {expression}",
        )

    def _parse_every_pattern(self, expr: str) -> Optional[ParsedRecurrence]:
        """解析 every [interval] [weekday] 模式"""
        match = re.match(r"every\s+(\d+)?\s*(\w+)", expr)
        if not match:
            return None

        interval_str = match.group(1)
        unit_or_day = match.group(2)

        interval = int(interval_str) if interval_str else 1

        weekday = WEEKDAY_MAP_EN.get(unit_or_day)

        if weekday is not None:
            return ParsedRecurrence(
                recurrence_type=RecurrenceType.WEEKLY,
                interval=interval,
                weekdays=[weekday],
                description=f"每{interval}周{'一' if interval == 1 else ''}" + self._weekday_name_cn(weekday),
                raw_expression=expr,
            )

        if unit_or_day in ("day", "days", "daily"):
            return ParsedRecurrence(
                recurrence_type=RecurrenceType.DAILY,
                interval=interval,
                description=f"每{interval}天" if interval > 1 else "每天",
                raw_expression=expr,
            )

        if unit_or_day in ("week", "weeks", "weekly"):
            return ParsedRecurrence(
                recurrence_type=RecurrenceType.WEEKLY,
                interval=interval,
                description=f"每{interval}周" if interval > 1 else "每周",
                raw_expression=expr,
            )

        if unit_or_day in ("month", "months", "monthly"):
            return ParsedRecurrence(
                recurrence_type=RecurrenceType.MONTHLY,
                interval=interval,
                description=f"每{interval}个月" if interval > 1 else "每月",
                raw_expression=expr,
            )

        return None

    def _parse_chinese_frequency(self, expr: str) -> Optional[ParsedRecurrence]:
        """解析中文频率表达式"""
        if expr == "每天" or expr == "每日":
            return ParsedRecurrence(recurrence_type=RecurrenceType.DAILY, description="每天", raw_expression=expr)

        if expr in ("每周", "每星期"):
            return ParsedRecurrence(recurrence_type=RecurrenceType.WEEKLY, description="每周", raw_expression=expr)

        if expr in ("每月", "每个月"):
            return ParsedRecurrence(recurrence_type=RecurrenceType.MONTHLY, description="每月", raw_expression=expr)

        weekly_match = re.match(r"每(\d+)天", expr)
        if weekly_match:
            interval = int(weekly_match.group(1))
            return ParsedRecurrence(
                recurrence_type=RecurrenceType.DAILY,
                interval=interval,
                description=f"每{interval}天",
                raw_expression=expr,
            )

        weekly_cn_match = re.match(r"每(\d+)周", expr)
        if weekly_cn_match:
            interval = int(weekly_cn_match.group(1))
            return ParsedRecurrence(
                recurrence_type=RecurrenceType.WEEKLY,
                interval=interval,
                description=f"每{interval}周",
                raw_expression=expr,
            )

        weekday_cn_match = re.match(r"每周([一二三四五六日1234567]+)", expr)
        if weekday_cn_match:
            weekdays_str = weekday_cn_match.group(1)
            weekdays = []
            for char in weekdays_str:
                if char in WEEKDAY_MAP_CN:
                    wd = WEEKDAY_MAP_CN[char]
                    if wd not in weekdays:
                        weekdays.append(wd)

            if weekdays:
                weekdays.sort()
                names = [self._weekday_name_cn(wd) for wd in weekdays]
                return ParsedRecurrence(
                    recurrence_type=RecurrenceType.WEEKLY,
                    weekdays=weekdays,
                    description=f"每周{'、'.join(names)}",
                    raw_expression=expr,
                )

        return None

    def _parse_weekdays_weekends(self, expr: str) -> Optional[ParsedRecurrence]:
        """解析工作日/周末"""
        if expr in ("weekdays", "工作日", "工作天"):
            return ParsedRecurrence(
                recurrence_type=RecurrenceType.WEEKLY,
                weekdays=[0, 1, 2, 3, 4],
                description="工作日（周一至周五）",
                raw_expression=expr,
            )

        if expr in ("weekends", "周末", "休息日"):
            return ParsedRecurrence(
                recurrence_type=RecurrenceType.WEEKLY,
                weekdays=[5, 6],
                description="周末（周六、周日）",
                raw_expression=expr,
            )

        return None

    def _parse_simple_daily(self, expr: str) -> Optional[ParsedRecurrence]:
        """简单的每日匹配"""
        if expr in ("daily", "day"):
            return ParsedRecurrence(recurrence_type=RecurrenceType.DAILY, description="每天", raw_expression=expr)

        return None

    def _weekday_name_cn(self, weekday: int) -> str:
        """获取中文星期名称"""
        names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return names[weekday] if 0 <= weekday <= 6 else str(weekday)

    def calculate_next_trigger(
        self, recurrence: ParsedRecurrence, base_time: datetime = None, hour: int = 9, minute: int = 0
    ) -> datetime:
        """
        计算下次触发时间

        Args:
            recurrence: 解析后的循环规则
            base_time: 基准时间（默认当前时间）
            hour: 触发小时
            minute: 触发分钟

        Returns:
            下次触发时间
        """
        if base_time is None:
            base_time = datetime.now()

        if not recurrence.valid:
            raise ValueError(f"无效的循环规则: {recurrence.error}")

        if recurrence.recurrence_type == RecurrenceType.DAILY:
            next_time = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_time <= base_time:
                next_time += timedelta(days=recurrence.interval)
            return next_time

        elif recurrence.recurrence_type == RecurrenceType.WEEKLY:
            if recurrence.weekdays:
                target_weekdays = sorted(recurrence.weekdays)
                current_weekday = base_time.weekday()

                candidates = []
                for offset in range(8):
                    check_date = base_time + timedelta(days=offset)
                    check_weekday = check_date.weekday()
                    if check_weekday in target_weekdays:
                        candidate = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if candidate > base_time:
                            candidates.append(candidate)

                if candidates:
                    return min(candidates)

                next_monday = base_time + timedelta(
                    days=(7 - current_weekday + target_weekdays[0]) % 7
                    + (1 if current_weekday == target_weekdays[0] and base_time.hour >= hour else 0)
                )
                return next_monday.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                next_time = base_time + timedelta(weeks=recurrence.interval)
                return next_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

        elif recurrence.recurrence_type == RecurrenceType.MONTHLY:
            next_month = base_time.month + recurrence.interval - 1
            year_offset = next_month // 12
            month = (next_month % 12) + 1
            year = base_time.year + year_offset

            day = min(base_time.day, 28)
            try:
                next_time = datetime(year, month, day, hour, minute, 0, 0)
            except ValueError:
                next_time = datetime(year, month, 28, hour, minute, 0, 0)

            if next_time <= base_time:
                next_time = datetime(year, month + 1, day, hour, minute, 0, 0)

            return next_time

        else:
            return base_time + timedelta(days=recurrence.interval)


_parser_instance: Optional[RecurrenceParser] = None


def get_recurrence_parser() -> RecurrenceParser:
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = RecurrenceParser()
    return _parser_instance


def parse_recurrence(expression: str) -> ParsedRecurrence:
    """
    便捷函数：解析循环表达式

    Args:
        expression: 自然语言循环表达式

    Returns:
        ParsedRecurrence 解析结果
    """
    parser = get_recurrence_parser()
    return parser.parse(expression)
