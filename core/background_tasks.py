"""
Scriptor 后台任务模块

从 main.py 中抽离的重量级后台任务，包括：
- 定时调度循环
- 知识图谱夜间整合
- 主动事件处理（早安/晚安/复盘）
- 网页搜索处理
- 复盘任务执行
"""

import asyncio
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from astrbot.api import logger


class BackgroundTasks:
    """
    Scriptor 后台任务管理器

    将所有重量级后台任务从主类中分离，降低 main.py 复杂度。
    通过组合模式持有对插件实例的引用来访问所需组件。
    """

    def __init__(self, plugin):
        self.plugin = plugin

    async def scheduler_loop(self):
        """定时任务触发检查循环"""
        while not self.plugin._is_terminating:
            try:
                await asyncio.sleep(30)

                def trigger_callback(task):
                    asyncio.create_task(self.send_scheduled_message(task))

                self.plugin.scheduler.check_and_trigger(trigger_callback)

            except asyncio.CancelledError:
                break
            except (OSError, RuntimeError) as e:
                logger.error(f"[Scheduler] 调度循环出错: {e}")
                await asyncio.sleep(60)

    async def send_scheduled_message(self, task):
        """发送定时任务消息或处理内部事件"""
        try:
            if task.content.startswith("SYSTEM_PROACTIVE_EVENT:"):
                event_type = task.content.split(":", 1)[1]
                await self.handle_proactive_event(event_type, task.uid, task.group_id)
                return

            msg_content = f"⏰ **定时提醒**\n\n{task.content}"

            session_str = None
            if task.group_id and task.group_id != "private":
                session_str = task.group_id
            elif task.uid:
                session_str = task.uid

            if not session_str:
                logger.warning("[Scheduler] 定时任务缺少 session 信息")
                return

            if "!" not in session_str:
                if task.group_id and task.group_id != "private":
                    session_str = f"webchat!{task.group_id}!{task.group_id}"
                else:
                    session_str = f"webchat!{task.uid}!{task.uid}"

            from astrbot.core.message.components import Plain
            from astrbot.core.message.message_event_result import MessageChain
            from astrbot.core.platform.astr_message_event import MessageSesion

            session = MessageSesion.from_str(session_str)
            message_chain = MessageChain([Plain(msg_content)])

            success = await self.plugin.context.send_message(session, message_chain)
            if success:
                logger.info(f"[Scheduler] 已发送定时提醒: {task.content}")
            else:
                logger.warning(f"[Scheduler] 发送定时提醒失败: {task.content}")

        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError) as e:
            logger.error(f"[Scheduler] 发送定时消息失败: {e}")

    async def nightly_graph_consolidation(self):
        """夜间知识图谱整理任务"""
        while not self.plugin._is_terminating:
            try:
                if not getattr(self.plugin.config, "nightly_graph_consolidation_enabled", True):
                    await asyncio.sleep(3600)
                    continue

                now = datetime.now()
                target_hour = getattr(self.plugin.config, "nightly_graph_consolidation_hour", 3)
                target_minute = 0

                next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                if now >= next_run:
                    next_run += timedelta(days=1)

                wait_seconds = (next_run - now).total_seconds()
                logger.info(f"[KnowledgeGraph] 下次整理将在 {next_run.strftime('%Y-%m-%d %H:%M')} 进行")

                await asyncio.sleep(wait_seconds)

                if self.plugin._is_terminating:
                    break

                await self.run_graph_consolidation()

            except asyncio.CancelledError:
                break
            except (OSError, RuntimeError) as e:
                logger.error(f"[KnowledgeGraph] 夜间整理出错: {e}")
                await asyncio.sleep(3600)

    async def run_graph_consolidation(self):
        """执行知识图谱整合（带超时保护）"""
        try:
            logger.info("[KnowledgeGraph] 开始夜间知识图谱整理...")

            await self.plugin._wait_for_ready()

            profiles_dir = self.plugin.data_dir / "profiles"
            if not profiles_dir.exists():
                return

            start_time = time.time()
            max_total_time = getattr(self.plugin.config, "graph_consolidation_max_time", 25) * 60

            total_processed = 0
            for uid_dir in profiles_dir.iterdir():
                if time.time() - start_time > max_total_time:
                    logger.warning("[KnowledgeGraph] 夜间整理超时，剩余用户将跳过")
                    break

                if not uid_dir.is_dir():
                    continue

                memory_dir = uid_dir / "memory"
                if not memory_dir.exists():
                    continue

                processed = await self.consolidate_user_graph(uid_dir)
                total_processed += processed

            logger.info(
                f"[KnowledgeGraph] 夜间知识图谱整理完成，处理了 {total_processed} 个日记，耗时 {int(time.time() - start_time)} 秒"
            )

        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError) as e:
            logger.error(f"[KnowledgeGraph] 夜间整理任务失败: {e}")

    async def consolidate_user_graph(self, uid_dir: Path) -> int:
        """整合单个用户的知识图谱（增量 + 限量）"""
        memory_dir = uid_dir / "memory"
        if not memory_dir.exists():
            return 0

        uid = uid_dir.name
        all_diaries = sorted(memory_dir.glob("????-??-??.md"), reverse=True)

        processed_count = 0
        max_per_night = getattr(self.plugin.config, "graph_consolidation_max_diaries", 10)

        for diary_file in all_diaries:
            if processed_count >= max_per_night:
                break

            date_str = diary_file.stem
            if self.plugin.knowledge_graph.is_diary_processed(uid, date_str):
                continue

            if await self.process_diary_for_graph(diary_file, uid):
                self.plugin.knowledge_graph.mark_diary_processed(uid, date_str)
                processed_count += 1

        return processed_count

    async def process_diary_for_graph(self, diary_file: Path, uid: str) -> bool:
        """处理单个日记文件，提取实体和关系"""
        date_str = diary_file.stem

        try:
            content = diary_file.read_text(encoding="utf-8")
            user_name = self.plugin.identity_manager.uid_metadata.get(uid, {}).get("primary_name", f"User_{uid[-4:]}")
            prompt = self.build_graph_extraction_prompt(content, uid, user_name)

            try:
                llm_timeout = getattr(self.plugin.config, "llm_call_timeout", 60)
                # 使用 AstrBot v4.x 推荐的 llm_generate 接口
                response = await asyncio.wait_for(
                    self.plugin.context.llm_generate(
                        chat_provider_id=await self.plugin.context.get_current_chat_provider_id(None),
                        prompt=prompt
                    ),
                    timeout=llm_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(f"[KnowledgeGraph] 整合日记 {date_str} 超时，跳过")
                return False

            content_text = response.completion_text.strip() if response.completion_text else ""
            from .tools.common.json_parser import safe_json_loads

            data = safe_json_loads(content_text, default={})

            if data:
                entities = data.get("entities", [])
                relations = data.get("relations", [])
                self.plugin.knowledge_graph.add_entities_and_relations(entities, relations)
                logger.info(f"[KnowledgeGraph] 整合了用户 {uid} 在 {date_str} 的日记")
                return True

            return False

        except (OSError, RuntimeError) as e:
            logger.error(f"[KnowledgeGraph] 整合日记 {date_str} 失败: {e}")
            return False

    def build_graph_extraction_prompt(self, content: str, uid: str, user_name: str) -> str:
        """构建知识图谱提取 Prompt"""
        return f"""请分析以下日记内容，提取实体和关系。

用户: {user_name} (ID: {uid})
日期: {datetime.now().strftime("%Y-%m-%d")}

日记内容:
{content[:2000]}

请以 JSON 格式返回：
{{
  "entities": [
    {{"name": "实体名称", "type": "人物/地点/组织/概念/事件/其他", "description": "简短描述"}}
  ],
  "relations": [
    {{"source": "实体A", "target": "实体B", "relation": "关系类型", "weight": 1.0}}
  ]
}}

只提取重要且有长期价值的实体和关系。"""

    async def handle_proactive_event(self, event_type: str, uid: str, group_id: str):
        """处理主动事件（如早安、晚安、复盘）"""
        try:
            logger.info(f"[Scriptor] 触发主动事件: {event_type} (uid={uid}, group={group_id})")

            if event_type == "heartbeat_review":
                await self.run_heartbeat_review()
            elif event_type == "morning_greeting":
                await self.run_morning_greeting()
            elif event_type == "evening_summary":
                await self.run_evening_summary()

        except Exception as e:
            logger.error(f"[Scriptor] 处理主动事件失败: {e}")

    async def run_morning_greeting(self):
        """执行早安问候"""
        logger.info("[Scriptor] 开始执行早安问候...")
        today_date = datetime.now().date()

        for uid, meta in self.plugin.identity_manager.uid_metadata.items():
            last_active = meta.get("last_active", 0)
            if not last_active:
                continue

            last_active_date = datetime.fromtimestamp(last_active).date()
            delta_days = (today_date - last_active_date).days

            if 0 <= delta_days <= 1:
                name = meta.get("primary_name", uid[-6:])
                logger.info(f"[Scriptor] 早安问候将发送给: {name} ({uid}), 最后活跃: {delta_days}天前")
                await self.send_morning_greeting_to_user(uid, name)

    async def send_morning_greeting_to_user(self, uid: str, name: str):
        """向用户发送早安问候"""
        umo_list = self.plugin.identity_manager.get_user_umo_list(uid)
        if not umo_list:
            logger.warning(f"[Scriptor] 无法发送早安问候给 {name}：没有可用的 UMO")
            return

        preferred_name = self._get_user_preferred_name(uid)
        display_name = preferred_name if preferred_name else name

        try:
            from ..core.todo_manager import TodoManager

            todo_manager = TodoManager(self.plugin.data_dir, scope="personal")

            archived_count = todo_manager.archive_old_completed(uid)
            if archived_count > 0:
                logger.info(f"[Scriptor] 早安问候时归档了 {archived_count} 条旧待办: {name}")

            hot_memory = todo_manager.get_hot_memory(uid)
            pending_tasks = []

            if "未完成" in hot_memory and "**无未完成待办**" not in hot_memory:
                task_matches = re.findall(
                    r"\d+\.\s*(.+)", hot_memory.split("已完成")[0] if "已完成" in hot_memory else ""
                )
                pending_tasks = [t.strip() for t in task_matches if t.strip()]
        except Exception as e:
            logger.warning(f"[Scriptor] 获取 TODO 热记忆失败: {e}")
            pending_tasks = []

        lines = [f"☀️ 早安，{display_name}！新的一天开始了。"]

        if pending_tasks:
            lines.append("")
            lines.append("📋 **当前待办：**")
            for task in pending_tasks[:5]:
                lines.append(f"• {task}")

        lines.append("")
        lines.append("今天有什么计划吗？")

        greeting_text = "\n".join(lines)

        from astrbot.core.message.components import Plain
        from astrbot.core.message.message_event_result import MessageChain

        message_chain = MessageChain([Plain(greeting_text)])

        for umo in umo_list:
            try:
                await self.plugin.context.send_message(umo, message_chain)
                logger.info(f"[Scriptor] 早安问候已发送给: {name} via {umo}")
                break
            except Exception as e:
                logger.warning(f"[Scriptor] 通过 {umo} 发送失败: {e}")
                continue

    def _get_user_preferred_name(self, uid: str) -> str:
        """获取用户偏好名称"""
        profile_dir = self.plugin.data_dir / "profiles" / uid
        profile_file = profile_dir / "P_PROFILE.md"

        if profile_file.exists():
            try:
                content = profile_file.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    if line.startswith("**昵称**") or line.startswith("**名称**") or line.startswith("**名字**"):
                        return line.split(":", 1)[-1].strip().strip("*").strip()
            except Exception:
                pass

        return None

    async def run_evening_summary(self):
        """执行晚安总结 - 收集今日活跃用户并生成个性化总结"""
        logger.info("[Scriptor] 开始执行晚安总结...")
        today = datetime.now().strftime("%Y-%m-%d")
        summary_data = []

        for uid, meta in self.plugin.identity_manager.uid_metadata.items():
            last_active = meta.get("last_active", 0)
            last_active_date = datetime.fromtimestamp(last_active).strftime("%Y-%m-%d") if last_active else None

            if last_active_date != today:
                continue

            name = meta.get("primary_name", uid[-6:])
            profile_dir = self.plugin.data_dir / "profiles" / uid

            today_memory_file = profile_dir / "memory" / f"{today}.md"

            conversation_summary = ""
            if today_memory_file.exists():
                try:
                    content = today_memory_file.read_text(encoding="utf-8")
                    lines = content.split("\n")
                    conversation_lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]
                    conversation_summary = "\n".join(conversation_lines[-20:]) if conversation_lines else ""
                except Exception as e:
                    logger.debug(f"[Scriptor] 读取今日记忆失败: {e}")

            summary_data.append(
                {
                    "uid": uid,
                    "name": name,
                    "today_file": str(today_memory_file),
                    "conversation_preview": conversation_summary[:500] if conversation_summary else "今日无对话记录",
                }
            )
            logger.info(f"[Scriptor] 晚安总结 - 用户: {name}, 对话长度: {len(conversation_summary)}")

        if summary_data:
            logger.info(f"[Scriptor] 晚安总结已为 {len(summary_data)} 位用户生成，正在发送...")
            for data in summary_data:
                await self.send_evening_summary_to_user(data)
        else:
            logger.info("[Scriptor] 今日无活跃用户，跳过晚安总结")

    async def send_evening_summary_to_user(self, data: dict):
        """向用户发送晚安总结"""
        uid = data["uid"]
        name = data["name"]
        conversation_preview = data["conversation_preview"]

        umo_list = self.plugin.identity_manager.get_user_umo_list(uid)
        if not umo_list:
            logger.warning(f"[Scriptor] 无法发送晚安总结给 {name}：没有可用的 UMO")
            return

        summary_text = await self.generate_daily_summary_with_llm(uid, name, conversation_preview)

        from astrbot.core.message.components import Plain
        from astrbot.core.message.message_event_result import MessageChain

        message_chain = MessageChain([Plain(summary_text)])

        for umo in umo_list:
            try:
                await self.plugin.context.send_message(umo, message_chain)
                logger.info(f"[Scriptor] 晚安总结已发送给: {name} via {umo}")
                break
            except Exception as e:
                logger.warning(f"[Scriptor] 通过 {umo} 发送失败: {e}")
                continue

    def generate_daily_summary_text(self, uid: str, name: str, conversation_preview: str, today_file: str) -> str:
        """生成每日总结文本（同步版本 - 回退）"""
        return f"""🌙 晚安，{name}！今日回顾：

{conversation_preview[:300] if conversation_preview else '今日暂无对话记录'}

好好休息，明天见！💤"""

    async def generate_daily_summary_with_llm(self, uid: str, name: str, conversation_preview: str) -> str:
        """使用 LLM 生成每日总结"""
        if not conversation_preview:
            return f"🌙 晚安，{name}！今日暂无对话记录，好好休息，明天见！💤"

        try:
            prompt = f"""请为以下今日对话记录生成一份简洁温馨的晚安总结。

要求：
1. 提炼今日互动的核心主题和关键事件
2. 总结用户的主要需求和情绪状态
3. 用温暖、亲切的语气，不超过 100 字
4. 不要简单复述对话，要真正总结和提炼

今日对话记录：
{conversation_preview[:2000]}

请直接输出总结内容，不要有任何前缀或格式标记："""

            # 使用 AstrBot v4.x 推荐的 llm_generate 接口
            # umo 为 None 时使用默认 provider
            response = await self.plugin.context.llm_generate(
                chat_provider_id=await self.plugin.context.get_current_chat_provider_id(None),
                prompt=prompt
            )
            
            summary = response.completion_text.strip() if response.completion_text else conversation_preview[:200]

            return f"""🌙 晚安，{name}！今日回顾：

{summary}

好好休息，明天见！💤"""

        except Exception as e:
            logger.error(f"[Scriptor] LLM 生成每日总结失败: {e}")
            return self.generate_daily_summary_text(uid, name, conversation_preview, "")

    async def run_heartbeat_review(self):
        """执行后台复盘任务 (Heartbeat)"""
        try:
            logger.info("[Scriptor] 开始执行后台复盘 (Heartbeat)...")

            now = time.time()
            inactivity_threshold = getattr(self.plugin.config, "heartbeat_inactivity_threshold", 3600)

            profiles_dir = self.plugin.data_dir / "profiles"
            if not profiles_dir.exists():
                return

            for uid_dir in profiles_dir.iterdir():
                if not uid_dir.is_dir():
                    continue

                uid = uid_dir.name
                session_id = f"{uid}_private"

                if not self.plugin._has_new_content.get(session_id, False):
                    logger.debug(f"[Scriptor] 用户 {uid} 无新内容，跳过复盘")
                    continue

                last_active = self.plugin._last_interaction_time.get(session_id, 0)
                if now - last_active < inactivity_threshold:
                    logger.debug(f"[Scriptor] 用户 {uid} 活跃中，跳过复盘")
                    continue

                if not uid_dir.exists():
                    continue

                await self.review_user_working_files(uid, "private")
                self.plugin._has_new_content[session_id] = False

            groups_dir = self.plugin.data_dir / "groups"
            if groups_dir.exists():
                for gid_dir in groups_dir.iterdir():
                    if not gid_dir.is_dir():
                        continue
                    gid = gid_dir.name
                    session_id = f"*_{gid}"

                    if not self.plugin._has_new_content.get(session_id, False):
                        logger.debug(f"[Scriptor] 群组 {gid} 无新内容，跳过复盘")
                        continue

                    last_active = self.plugin._last_interaction_time.get(session_id, 0)
                    if now - last_active < inactivity_threshold:
                        logger.debug(f"[Scriptor] 群组 {gid} 活跃中，跳过复盘")
                        continue

                    await self.review_user_working_files("*", gid)
                    self.plugin._has_new_content[session_id] = False

        except Exception as e:
            logger.error(f"[Scriptor] 后台复盘失败: {e}")

    async def review_user_working_files(self, uid: str, group_id: str):
        """为特定用户/群组执行复盘"""
        try:
            working_context = self.plugin.file_manager.get_working_context(uid, group_id)
            if not working_context or "工作目录为空" in working_context:
                return

            heartbeat_instruction = ""
            try:
                if group_id == "private":
                    hb_path = self.plugin.data_dir / "profiles" / uid / "P_HEARTBEAT.md"
                else:
                    hb_path = self.plugin.data_dir / "groups" / group_id / "G_HEARTBEAT.md"

                if hb_path.exists():
                    content = hb_path.read_text(encoding="utf-8").strip()
                    lines = [line for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
                    heartbeat_instruction = "\n".join(lines)
            except Exception as e:
                logger.debug(f"[Scriptor] 读取 HEARTBEAT 文件失败：{e}")

            if not heartbeat_instruction:
                heartbeat_instruction = """
1. 检查 `NOTES.md` 和 `TODO.md`。
2. 识别出其中值得长期保留的重要事件、教训或见解。
3. 如果有重要发现，请使用 `file_read_tool` 读取详情，然后使用 `file_append_tool` 或 `file_edit_tool` 将其提炼到 `MEMORY.md`。
4. 如果 `TODO.md` 中有已完成的任务，可以考虑将其移动到归档或删除。
5. 如果 `NOTES.md` 内容过多且已处理，请进行清理。
"""

            prompt = f"""你现在是 AI 管家。这是你当前的工作区文件摘要：

{working_context}

请执行以下后台复盘任务：
{heartbeat_instruction}

请直接开始行动（调用工具）。如果没有需要整理的内容，请直接回复"无需整理"。"""

            from .tools.common.file_ops import file_append, file_edit, file_grep, file_list, file_read, file_write

            class MockEvent:
                def __init__(self, plugin, uid, gid):
                    self._plugin = plugin
                    self._uid = uid
                    self._gid = gid

                def get_sender_id(self):
                    return self._uid

                def get_group_id(self):
                    return self._gid

                def get_plugin(self):
                    return self._plugin

                def get_sender_name(self):
                    return "System"

                def plain_result(self, text):
                    return text

            mock_event = MockEvent(self.plugin, uid, group_id)

            messages = [
                {"role": "system", "content": "你是一个正在进行后台复盘的 AI 管家。你必须通过调用工具来完成任务。"},
                {"role": "user", "content": prompt},
            ]

            tool_map = {
                "file_read_tool": file_read,
                "file_write_tool": file_write,
                "file_edit_tool": file_edit,
                "file_append_tool": file_append,
                "file_search_tool": file_grep,
                "file_list_tool": file_list,
                "archives_query_tool": (
                    self.plugin.archive_manager.execute_query if self.plugin.archive_manager else None
                ),
                "web_search_tool": self.handle_web_search if self.plugin.web_search_tool else None,
            }

            llm_timeout = getattr(self.plugin.config, "llm_call_timeout", 60)
            
            for i in range(5):
                try:
                    # 使用 AstrBot v4.x 推荐的 tool_loop_agent 接口
                    # event 为 None，因为这是后台任务，没有触发事件
                    response = await asyncio.wait_for(
                        self.plugin.context.tool_loop_agent(
                            event=None,
                            chat_provider_id=await self.plugin.context.get_current_chat_provider_id(None),
                            contexts=messages,
                            tool_call_timeout=llm_timeout
                        ),
                        timeout=llm_timeout * 1.5, # 留出工具执行的时间
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"[Scriptor] 复盘 LLM 调用超时 (第{i+1}轮)")
                    break

                if response.completion_text:
                    messages.append({"role": "assistant", "content": response.completion_text})
                    logger.debug(f"[Scriptor] 复盘思考 ({i+1}): {response.completion_text[:100]}...")

                if not response.tool_calls:
                    break

                for tool_call in response.tool_calls:
                    tool_name = tool_call.function.name
                    from .tools.common.json_parser import safe_json_loads

                    tool_args = safe_json_loads(tool_call.function.arguments, default={})

                    logger.info(f"[Scriptor] 复盘执行工具: {tool_name} (args={tool_args})")

                    if tool_map.get(tool_name):
                        try:
                            tool_func = tool_map[tool_name]

                            if tool_name == "archives_query_tool":
                                result = tool_func(tool_args.get("sql", ""))
                                result_str = str(result)
                            else:
                                result_str = ""
                                import inspect

                                if inspect.isasyncgenfunction(tool_func):
                                    async for part in tool_func(mock_event, **tool_args, plugin=self.plugin):
                                        result_str += str(part)
                                else:
                                    result_str = await tool_func(mock_event, **tool_args, plugin=self.plugin)

                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "name": tool_name,
                                    "content": str(result_str),
                                }
                            )
                        except Exception as e:
                            logger.error(f"[Scriptor] 复盘工具执行失败: {tool_name}, 错误: {e}")
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "name": tool_name,
                                    "content": f"Error: {e!s}",
                                }
                            )
                    else:
                        logger.warning(f"[Scriptor] 复盘中尝试调用未知工具: {tool_name}")
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": f"Error: Tool {tool_name} not found.",
                            }
                        )

            logger.info(f"[Scriptor] 用户 {uid}/{group_id} 的复盘任务已完成。")

        except Exception as e:
            logger.error(f"[Scriptor] 复盘用户 {uid} 失败: {e}")

    async def handle_web_search(self, event, query: str, depth: str = "normal", save_to_memory: bool = False):
        """处理网页搜索请求"""
        if not self.plugin.web_search_tool:
            return "⚠️ **网页搜索功能未启用**"

        from .tools.web_search_tool import SearchDepth

        depth_map = {"quick": SearchDepth.QUICK, "normal": SearchDepth.NORMAL, "deep": SearchDepth.DEEP}

        search_depth = depth_map.get(depth.lower(), SearchDepth.NORMAL)

        uid = getattr(event, "_uid", "unknown")
        group_id = getattr(event, "_gid", "private")

        user_context = {"uid": uid, "group_id": group_id}

        result = await self.plugin.web_search_tool.search(
            query=query, depth=search_depth, save_to_memory=save_to_memory, user_context=user_context
        )

        return result
