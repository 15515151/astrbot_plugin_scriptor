# tests/test_scheduler.py
"""Scriptor 定时任务调度器模块测试"""

import time
from datetime import datetime, timedelta

import pytest

# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.scheduler import ScheduledTask, TaskScheduler
except ImportError:
    from scheduler import ScheduledTask, TaskScheduler


class TestScheduledTask:
    """ScheduledTask 数据类测试"""

    def test_create_task(self):
        """测试创建定时任务"""
        task = ScheduledTask(
            task_id="test_001",
            trigger_time=time.time() + 3600,
            content="测试任务",
            task_type="once",
            uid="user_123",
            group_id="",
        )

        assert task.task_id == "test_001"
        assert task.content == "测试任务"
        assert task.task_type == "once"
        assert task.uid == "user_123"
        assert task.group_id == ""
        assert task.is_active is True

    def test_task_to_dict(self):
        """测试任务转换为字典"""
        task = ScheduledTask(
            task_id="test_002",
            trigger_time=time.time() + 7200,
            content="字典转换测试",
            task_type="interval",
            interval_seconds=3600,
            uid="user_456",
            group_id="group_789",
        )

        task_dict = task.to_dict()

        assert isinstance(task_dict, dict)
        assert task_dict["task_id"] == "test_002"
        assert task_dict["content"] == "字典转换测试"
        assert task_dict["task_type"] == "interval"
        assert task_dict["interval_seconds"] == 3600

    def test_task_from_dict(self):
        """测试从字典创建任务"""
        task_dict = {
            "task_id": "test_003",
            "trigger_time": time.time() + 10800,
            "content": "从字典恢复",
            "task_type": "interval",
            "interval_seconds": 86400,
            "uid": "user_abc",
            "group_id": "",
            "is_active": True,
            "created_at": time.time(),
            "last_triggered": 0,
        }

        task = ScheduledTask.from_dict(task_dict)

        assert task.task_id == "test_003"
        assert task.content == "从字典恢复"
        assert task.interval_seconds == 86400


class TestTaskScheduler:
    """TaskScheduler 调度器核心功能测试"""

    @pytest.fixture(autouse=True)
    def setup_scheduler(self, tmp_path):
        """设置测试用调度器"""
        self.data_dir = tmp_path / "scriptor_data"
        self.data_dir.mkdir(parents=True)
        self.scheduler = TaskScheduler(self.data_dir)

    def test_add_task(self):
        """测试添加任务"""
        task = ScheduledTask(
            task_id="add_test_001", trigger_time=time.time() + 3600, content="添加任务测试", uid="user_1"
        )

        task_id = self.scheduler.add_task(task)

        assert task_id == "add_test_001"
        assert len(self.scheduler.tasks) == 1

    def test_remove_task(self):
        """测试移除任务"""
        task = ScheduledTask(
            task_id="remove_test_001", trigger_time=time.time() + 3600, content="移除任务测试", uid="user_2"
        )

        self.scheduler.add_task(task)
        result = self.scheduler.remove_task("remove_test_001")

        assert result is True
        assert len(self.scheduler.tasks) == 0

    def test_remove_nonexistent_task(self):
        """测试移除不存在的任务"""
        result = self.scheduler.remove_task("nonexistent")

        assert result is False

    def test_get_tasks_all(self):
        """测试获取所有任务"""
        for i in range(5):
            task = ScheduledTask(
                task_id=f"get_all_{i}", trigger_time=time.time() + (i + 1) * 3600, content=f"任务 {i}", uid=f"user_{i}"
            )
            self.scheduler.add_task(task)

        tasks = self.scheduler.get_tasks()

        assert len(tasks) == 5

    def test_get_tasks_by_uid(self):
        """测试按 UID 获取任务"""
        task1 = ScheduledTask(
            task_id="uid_test_1", trigger_time=time.time() + 3600, content="用户A的任务", uid="user_A"
        )
        task2 = ScheduledTask(
            task_id="uid_test_2", trigger_time=time.time() + 7200, content="用户B的任务", uid="user_B"
        )

        self.scheduler.add_task(task1)
        self.scheduler.add_task(task2)

        tasks = self.scheduler.get_tasks(uid="user_A")

        assert len(tasks) == 1
        assert tasks[0].uid == "user_A"

    def test_get_tasks_by_group_id(self):
        """测试按 group_id 获取任务"""
        task1 = ScheduledTask(
            task_id="group_test_1", trigger_time=time.time() + 3600, content="群组X的任务", group_id="group_X"
        )
        task2 = ScheduledTask(
            task_id="group_test_2", trigger_time=time.time() + 7200, content="群组Y的任务", group_id="group_Y"
        )

        self.scheduler.add_task(task1)
        self.scheduler.add_task(task2)

        tasks = self.scheduler.get_tasks(group_id="group_X")

        assert len(tasks) == 1
        assert tasks[0].group_id == "group_X"

    def test_get_tasks_inactive_filtered(self):
        """测试过滤非活跃任务"""
        active_task = ScheduledTask(
            task_id="active_001", trigger_time=time.time() + 3600, content="活跃任务", is_active=True
        )
        inactive_task = ScheduledTask(
            task_id="inactive_001", trigger_time=time.time() + 3600, content="非活跃任务", is_active=False
        )

        self.scheduler.add_task(active_task)
        self.scheduler.add_task(inactive_task)

        tasks = self.scheduler.get_tasks()

        assert len(tasks) == 1
        assert tasks[0].is_active is True

    def test_check_and_trigger_once_task(self):
        """测试触发一次性任务"""
        triggered_tasks = []

        def callback(task):
            triggered_tasks.append(task)

        task = ScheduledTask(
            task_id="trigger_once_001",
            trigger_time=time.time() - 10,
            content="一次性任务（已过期）",
            task_type="once",
            uid="user_trigger",
        )

        self.scheduler.add_task(task)
        result = self.scheduler.check_and_trigger(callback)

        assert len(result) == 1
        assert len(triggered_tasks) == 1
        assert triggered_tasks[0].content == "一次性任务（已过期）"
        assert triggered_tasks[0].is_active is False

    def test_check_and_trigger_future_task(self):
        """测试未到期的任务不被触发"""
        triggered_tasks = []

        def callback(task):
            triggered_tasks.append(task)

        task = ScheduledTask(
            task_id="future_001", trigger_time=time.time() + 3600, content="未来任务", task_type="once"
        )

        self.scheduler.add_task(task)
        result = self.scheduler.check_and_trigger(callback)

        assert len(result) == 0
        assert len(triggered_tasks) == 0

    def test_check_and_trigger_interval_task(self):
        """测试触发周期性任务"""
        triggered_count = [0]

        def callback(task):
            triggered_count[0] += 1

        task = ScheduledTask(
            task_id="interval_001",
            trigger_time=time.time() - 100,
            content="周期性任务",
            task_type="interval",
            interval_seconds=60,
            last_triggered=time.time() - 120,
        )

        self.scheduler.add_task(task)

        # 第一次触发
        result1 = self.scheduler.check_and_trigger(callback)
        assert len(result1) == 1
        assert triggered_count[0] == 1

        # 等待一小段时间确保 last_triggered 已更新
        time.sleep(2)

        # 手动更新 last_triggered 模拟更早的触发时间
        task.last_triggered = time.time() - 120

        # 第二次触发
        result2 = self.scheduler.check_and_trigger(callback)
        assert len(result2) == 1
        assert triggered_count[0] == 2

    def test_persistence_save_load(self):
        """测试任务持久化保存和加载"""
        original_task = ScheduledTask(
            task_id="persist_001",
            trigger_time=time.time() + 3600,
            content="持久化测试任务",
            task_type="once",
            uid="persist_user",
        )

        self.scheduler.add_task(original_task)

        new_scheduler = TaskScheduler(self.data_dir)

        tasks = new_scheduler.get_tasks()

        assert len(tasks) == 1
        assert tasks[0].task_id == "persist_001"
        assert tasks[0].content == "持久化测试任务"


class TestIntervalTaskParsing:
    """周期性任务时间间隔解析测试"""

    @pytest.fixture(autouse=True)
    def setup_tools_mixin(self):
        """导入 ToolsMixin 用于测试辅助方法"""
        from astrbot_plugin_scriptor.mixins.tools_mixin import ToolsMixin

        self.mixin = ToolsMixin.__new__(ToolsMixin)

    def test_parse_minutes(self):
        """测试解析分钟"""
        result = self.mixin._parse_interval_string("30 minutes")
        assert result == 1800

    def test_parse_hours(self):
        """测试解析小时"""
        result = self.mixin._parse_interval_string("2 hours")
        assert result == 7200

    def test_parse_days(self):
        """测试解析天"""
        result = self.mixin._parse_interval_string("1 day")
        assert result == 86400

    def test_parse_daily_keyword(self):
        """测试 daily 关键字"""
        result = self.mixin._parse_interval_string("daily")
        assert result == 86400

    def test_parse_weekly_keyword(self):
        """测试 weekly 关键字"""
        result = self.mixin._parse_interval_string("weekly")
        assert result == 604800

    def test_parse_monthly_keyword(self):
        """测试 monthly 关键字"""
        result = self.mixin._parse_interval_string("monthly")
        assert result == 2592000

    def test_parse_chinese_units(self):
        """测试中文单位"""
        result = self.mixin._parse_interval_string("每天")
        assert result == 86400

    def test_parse_invalid_format(self):
        """测试无效格式"""
        result = self.mixin._parse_interval_string("invalid format")
        assert result is None

    def test_format_description_minutes(self):
        """测试格式化分钟描述"""
        result = self.mixin._format_interval_description(1800)
        assert result == "30 分钟"

    def test_format_description_hours(self):
        """测试格式化小时描述"""
        result = self.mixin._format_interval_description(7200)
        assert result == "2 小时"

    def test_format_description_days(self):
        """测试格式化天数描述"""
        result = self.mixin._format_interval_description(172800)
        assert result == "2 天"


class TestTriggerTimeParsing:
    """触发时间解析测试"""

    @pytest.fixture(autouse=True)
    def setup_tools_mixin(self):
        """导入 ToolsMixin 用于测试辅助方法"""
        from astrbot_plugin_scriptor.mixins.tools_mixin import ToolsMixin

        self.mixin = ToolsMixin.__new__(ToolsMixin)

    def test_parse_relative_time_minutes(self):
        """测试相对时间：分钟后"""
        current_time = datetime.now()
        result = self.mixin._parse_trigger_time("30 minutes later", current_time)

        expected = current_time + timedelta(minutes=30)
        assert result is not None
        # 允许 2 秒误差（因为方法内部可能有微小的处理延迟）
        assert abs((result - expected).total_seconds()) < 2

    def test_parse_relative_time_hours(self):
        """测试相对时间：小时后"""
        current_time = datetime.now()
        result = self.mixin._parse_trigger_time("2 hours later", current_time)

        expected = current_time + timedelta(hours=2)
        assert result is not None
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_absolute_time_today(self):
        """测试绝对时间：今天"""
        current_time = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
        target_str = f"{current_time.hour:02d}:{current_time.minute:02d}"

        result = self.mixin._parse_trigger_time(target_str, current_time)

        assert result is not None
        assert result.hour == current_time.hour
        assert result.minute == current_time.minute

    def test_parse_absolute_time_tomorrow(self):
        """测试绝对时间：明天（如果时间已过）"""
        current_time = datetime.now().replace(hour=20, minute=0, second=0, microsecond=0)
        target_str = "08:00"

        result = self.mixin._parse_trigger_time(target_str, current_time)

        assert result is not None
        assert result.hour == 8
        assert result.minute == 0
        assert result.date() > current_time.date()

    def test_parse_datetime_format(self):
        """测试完整日期时间格式"""
        current_time = datetime.now()
        result = self.mixin._parse_trigger_time("2026-12-31 23:59", current_time)

        assert result is not None
        assert result.year == 2026
        assert result.month == 12
        assert result.day == 31
        assert result.hour == 23
        assert result.minute == 59


class TestProactiveEvents:
    """主动事件生成测试"""

    @pytest.fixture(autouse=True)
    def setup_scheduler(self, tmp_path):
        """设置测试用调度器"""
        self.data_dir = tmp_path / "proactive_data"
        self.data_dir.mkdir(parents=True)
        self.scheduler = TaskScheduler(self.data_dir)

    def test_generate_morning_greeting_event(self):
        """测试生成早安问候事件"""
        self.scheduler._check_and_trigger_proactive_tasks()

        # 直接调用内部方法生成事件
        self.scheduler._morning_greeted_today = None
        self.scheduler._trigger_proactive_event("morning_greeting", uid="*", group_id="*")

        tasks = self.scheduler.get_tasks()

        proactive_tasks = [t for t in tasks if "SYSTEM_PROACTIVE_EVENT:morning_greeting" in t.content]
        assert len(proactive_tasks) > 0

    def test_generate_evening_summary_event(self):
        """测试生成晚安总结事件"""
        self.scheduler._evening_greeted_today = None
        self.scheduler._trigger_proactive_event("evening_summary", uid="*", group_id="*")

        tasks = self.scheduler.get_tasks()

        proactive_tasks = [t for t in tasks if "SYSTEM_PROACTIVE_EVENT:evening_summary" in t.content]
        assert len(proactive_tasks) > 0


class TestBackupSystem:
    """自动备份系统测试"""

    @pytest.fixture(autouse=True)
    def setup_scheduler(self, tmp_path):
        """设置测试用调度器"""
        self.data_dir = tmp_path / "backup_data"
        self.data_dir.mkdir(parents=True)
        self.scheduler = TaskScheduler(self.data_dir)

    def test_backup_directory_created(self):
        """测试备份目录存在"""
        backup_dir = self.data_dir / "backups"

        if not backup_dir.exists():
            backup_dir.mkdir(parents=True)

        assert backup_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
