# core/scheduler.py
"""定时任务调度器模块"""

import json
import tarfile
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """定时任务"""

    task_id: str
    trigger_time: float
    content: str
    task_type: str = "once"
    interval_seconds: int = 0
    uid: str = ""
    group_id: str = ""
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    last_triggered: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        return cls(**data)


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.tasks_file = data_dir / "scheduled_tasks.json"
        self.state_file = data_dir / "scheduler_state.json"
        self.backup_dir = data_dir / "backups"
        self.tasks: List[ScheduledTask] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 60
        self._last_backup_time = 0
        self._load_greeting_state()
        self._load_tasks()

    def _load_greeting_state(self):
        """加载问候状态（防止多个实例重复触发）"""
        self._morning_greeted_today: Optional[str] = None
        self._evening_greeted_today: Optional[str] = None
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self._morning_greeted_today = state.get("morning_greeted")
                    self._evening_greeted_today = state.get("evening_greeted")
            except (OSError, json.JSONDecodeError):
                pass

    def _save_greeting_state(self):
        """保存问候状态"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"morning_greeted": self._morning_greeted_today, "evening_greeted": self._evening_greeted_today},
                    f,
                    ensure_ascii=False,
                )
        except (OSError, json.JSONDecodeError):
            pass

    def _load_tasks(self):
        """从文件加载任务"""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = [ScheduledTask.from_dict(t) for t in data]
                logger.info(f"[Scheduler] 加载了 {len(self.tasks)} 个定时任务")
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"[Scheduler] 加载任务失败: {e}")
                self.tasks = []

    def _save_tasks(self):
        """保存任务到文件"""
        try:
            self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tasks_file, "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in self.tasks], f, ensure_ascii=False, indent=2)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"[Scheduler] 保存任务失败: {e}")

    def add_task(self, task: ScheduledTask) -> str:
        """添加新任务"""
        with self._lock:
            self.tasks.append(task)
            self._save_tasks()
        logger.info(f"[Scheduler] 添加了新任务: {task.task_id}, 触发时间: {datetime.fromtimestamp(task.trigger_time)}")
        return task.task_id

    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        with self._lock:
            original_count = len(self.tasks)
            self.tasks = [t for t in self.tasks if t.task_id != task_id]
            if len(self.tasks) < original_count:
                self._save_tasks()
                return True
        return False

    def get_tasks(self, uid: str = None, group_id: str = None) -> List[ScheduledTask]:
        """获取任务列表"""
        with self._lock:
            tasks = self.tasks
            if uid:
                tasks = [t for t in tasks if t.uid == uid]
            if group_id:
                tasks = [t for t in tasks if t.group_id == group_id]
            return [t for t in tasks if t.is_active]

    def check_and_trigger(self, callback) -> List[ScheduledTask]:
        """检查并触发到期任务"""
        current_time = time.time()
        triggered_tasks = []

        with self._lock:
            for task in self.tasks:
                if not task.is_active:
                    continue

                should_trigger = False

                if task.task_type == "once":
                    if current_time >= task.trigger_time:
                        should_trigger = True
                elif task.task_type == "interval":
                    if current_time - task.last_triggered >= task.interval_seconds:
                        should_trigger = True

                if should_trigger:
                    triggered_tasks.append(task)
                    task.last_triggered = current_time

                    if task.task_type == "once":
                        task.is_active = False

            if triggered_tasks:
                self._save_tasks()

        for task in triggered_tasks:
            try:
                callback(task)
            except (OSError, RuntimeError) as e:
                logger.error(f"[Scheduler] 触发任务失败: {task.task_id}, error: {e}")

        return triggered_tasks

    def start(self):
        """启动调度器"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("[Scheduler] 调度器已启动")

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[Scheduler] 调度器已停止")

    def _run_loop(self):
        """后台轮询循环"""
        while self._running:
            try:
                self._check_and_run_backup()
                self._check_and_trigger_proactive_tasks()
                time.sleep(self._check_interval)
            except (OSError, RuntimeError) as e:
                logger.error(f"[Scheduler] 轮询循环异常: {e}")
                time.sleep(self._check_interval)

    def _check_and_trigger_proactive_tasks(self):
        """检查并触发主动问候/提醒任务"""
        now = time.time()
        current_hour = datetime.fromtimestamp(now).hour
        today_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d")

        # 每天早上 8 点触发早安问候
        if current_hour == 8:
            if self._morning_greeted_today != today_str:
                self._trigger_proactive_event("morning_greeting")
                self._morning_greeted_today = today_str
                self._save_greeting_state()

        # 每天晚上 22 点触发晚安/总结提醒
        if current_hour == 22:
            if self._evening_greeted_today != today_str:
                self._trigger_proactive_event("evening_summary")
                self._evening_greeted_today = today_str
                self._save_greeting_state()

    def _trigger_proactive_event(self, event_type: str, uid: str = "*", group_id: str = "*"):
        """触发主动事件，生成一个内部任务供主插件处理"""
        task_id = f"proactive_{event_type}_{int(time.time())}"
        task = ScheduledTask(
            task_id=task_id,
            trigger_time=time.time(),
            content=f"SYSTEM_PROACTIVE_EVENT:{event_type}",
            task_type="once",
            uid=uid,
            group_id=group_id,
        )
        self.add_task(task)
        logger.info(f"[Scheduler] 已生成主动事件任务: {event_type} (uid={uid}, group={group_id})")

    def _check_and_run_backup(self):
        """检查并执行每日备份"""
        now = time.time()
        # 每天凌晨 4 点执行备份 (或者距离上次备份超过 24 小时)
        current_hour = datetime.fromtimestamp(now).hour

        if current_hour == 4 and (now - self._last_backup_time) > 20 * 3600:
            self._perform_backup()
            self._last_backup_time = now

    def _perform_backup(self):
        """执行数据备份"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"scriptor_backup_{timestamp}.tar.gz"

            logger.info(f"[Scheduler] 开始执行自动备份: {backup_file}")

            # 排除不需要备份的目录 (如 backups 本身)
            def exclude_filter(tarinfo):
                if "backups" in tarinfo.name or "chroma_db" in tarinfo.name:
                    return None
                return tarinfo

            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(self.data_dir, arcname=self.data_dir.name, filter=exclude_filter)

            logger.info(f"[Scheduler] 自动备份完成: {backup_file}")

            # 清理旧备份 (保留最近 7 天)
            self._cleanup_old_backups()

        except (OSError, RuntimeError) as e:
            logger.error(f"[Scheduler] 自动备份失败: {e}")

    def _cleanup_old_backups(self):
        """清理超过 7 天的旧备份"""
        try:
            now = time.time()
            retention_seconds = 7 * 24 * 3600

            for backup_file in self.backup_dir.glob("scriptor_backup_*.tar.gz"):
                if backup_file.is_file():
                    file_age = now - backup_file.stat().st_mtime
                    if file_age > retention_seconds:
                        backup_file.unlink()
                        logger.info(f"[Scheduler] 已清理过期备份: {backup_file.name}")
        except OSError as e:
            logger.error(f"[Scheduler] 清理旧备份失败: {e}")
