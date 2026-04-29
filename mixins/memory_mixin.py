from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from astrbot.api import logger
from astrbot.api.event import filter

from .base import BaseMixin

if TYPE_CHECKING:
    from astrbot.api.event import AstrMessageEvent


class MemoryMixin(BaseMixin):
    """
    记忆管理 Mixin

    包含：
    - 记忆状态查询命令
    - 记忆搜索命令
    - 记忆维护命令
    - 睡眠巩固
    - LLM 深度记忆提取

    注意：所有命令装饰器已移至 main.py 中注册，避免指令冲突
    """

    async def cmd_status(self, event: AstrMessageEvent):
        """查看记忆系统状态"""
        uid, group_id, _ = self._get_identity(event)

        user_name = self.identity_manager.get_user_primary_name(uid)
        user_groups = self.identity_manager.get_user_groups(uid)

        msg = f"""## 🧠 Scriptor 记忆系统状态

- **用户**: {user_name} (UID: {uid})
- **当前群体**: {group_id}
- **参与群体数**: {len(user_groups)}

### 当前群体成员
"""

        if group_id != "private":
            members = self.group_manager.get_group_members(group_id)
            for m in members[:5]:
                msg += f"- {m.alias} ({m.role})\n"
            if len(members) > 5:
                msg += f"... 还有 {len(members) - 5} 人\n"

        yield event.plain_result(msg)

    async def cmd_debug_memory(self, event: AstrMessageEvent):
        """[调试] 查看当前记忆状态（仅私聊或管理员可用）"""
        is_private = event.is_private() if hasattr(event, "is_private") else False

        uid, group_id, _ = self._get_identity(event)

        admin_uids = getattr(self.config, "admin_uids", [])
        is_admin = uid in admin_uids if admin_uids else False

        if not is_private and not is_admin:
            yield event.plain_result("⚠️ 调试命令仅支持私聊或管理员使用")
            return

        await self._wait_for_ready()

        try:
            unprocessed = len(self.memory_manager.get_unprocessed_messages(uid, group_id))

            vector_count = 0
            if self.search_engine and self.search_engine.collection:
                vector_count = self.search_engine.collection.count()

            hot_memory = self.prompt_builder.build_system_prompt(uid, group_id)
            hot_memory_len = len(hot_memory) if hot_memory else 0

            msg = f"""## 🛠️ 记忆系统调试信息

- **当前 UID**: `{uid}`
- **当前 Group**: `{group_id}`
- **未处理消息数**: `{unprocessed} / {self.memory_manager.LLM_EXTRACTION_THRESHOLD}`
- **向量库总条目**: `{vector_count}`
- **热记忆长度**: `{hot_memory_len} 字符`
- **Embedding 引擎**: `{self.config.embedding_provider}`
- **组件就绪**: `{self._is_ready}`
"""
            yield event.plain_result(msg)
        except (OSError, RuntimeError) as e:
            logger.error(f"[Scriptor] Debug 命令执行失败: {e}")
            yield event.plain_result(f"❌ 调试信息获取失败: {e}")

    async def cmd_search(self, event: AstrMessageEvent, *, remainder: str = ""):
        """检索记忆脑区

        用法：
        - /search <内容> - 检索与内容相关的记忆
        - /search <内容> personal - 仅搜索个人记忆
        - /search <内容> group - 仅搜索当前群组记忆
        - /search <内容> cross - 搜索跨群记忆
        """
        if not remainder or not remainder.strip():
            yield event.plain_result("❌ 请提供搜索关键词。\n用法： `/search <内容>`")
            return

        query = remainder.strip()
        uid, group_id, _ = self._get_identity(event)

        if not uid:
            yield event.plain_result("❌ 无法识别的身份，请先发送消息建立身份。")
            return

        is_private_context = group_id == "private"
        scope = "cross" if is_private_context else "group"
        parts = query.split()
        if len(parts) >= 2 and parts[-1] in ("personal", "group", "cross"):
            scope = parts[-1]
            query = " ".join(parts[:-1])

        await self._wait_for_ready()

        try:
            results = await self.search_engine.search(query=query, uid=uid, group_id=group_id, scope=scope, limit=5)
        except Exception as e:
            logger.error(f"[Scriptor] 搜索失败: {e}")
            yield event.plain_result(f"❌ 搜索失败：{e!s}")
            return

        if not results:
            yield event.plain_result(
                f"🔍 未找到与「{query}」相关的记忆。\n\n💡 尝试更换关键词，或扩大搜索范围（group/personal/cross）"
            )
            return

        msg = f"🔍 找到 {len(results)} 条与「{query}」相关的记忆：\n\n"
        for i, res in enumerate(results, 1):
            source_type_emoji = {"memory": "🧠", "note": "📝", "task": "📋", "file": "📄", "profile": "👤"}.get(
                res.source_type, "📌"
            )

            content_preview = res.content[:150] + "..." if len(res.content) > 150 else res.content
            time_str = (
                res.timestamp.strftime("%Y-%m-%d %H:%M") if hasattr(res, "timestamp") and res.timestamp else "未知时间"
            )

            msg += f"{source_type_emoji} **#{i}** [{res.source_type}] ({time_str})\n"
            msg += f"   {content_preview}\n\n"

        msg += "💡 输入 `/search <关键词> personal/group/cross` 可切换搜索范围。"
        yield event.plain_result(msg)

    async def cmd_mem_report(self, event: AstrMessageEvent):
        """生成记忆维护建议报告 (半自动维护)"""
        uid, group_id, _ = self._get_identity(event)

        yield event.plain_result("🔍 正在分析记忆状态，请稍候...")

        try:
            report = await self.compactor.analyze_maintenance_needs(
                self.data_dir, self.identity_manager, self.group_manager
            )
            yield event.plain_result(report)
        except (OSError, RuntimeError) as e:
            logger.error(f"[Scriptor] 生成维护报告失败: {e}")
            yield event.plain_result(f"❌ 生成维护报告失败: {e}")

    async def _try_sleep_consolidation(self, uid: str, group_id: str):
        """尝试执行睡眠巩固"""
        recent_notes = self.memory_manager.get_recent_notes_text(uid, group_id, limit=3)
        if not recent_notes:
            return

        try:
            consolidated_memory = await self.compactor.consolidate_sleep(recent_notes)
            if consolidated_memory:
                lines = consolidated_memory.split("\n")
                active_memory = []
                archive_memory = []
                memories_to_merge = []

                for line in lines:
                    if "[ARCHIVE]" in line:
                        archive_memory.append(line.replace("[ARCHIVE]", "").strip())
                    elif "[MERGE]" in line:
                        memories_to_merge.append(line.replace("[MERGE]", "").strip())
                    else:
                        active_memory.append(line)

                if active_memory:
                    active_content = "\n".join(active_memory).strip()
                    if active_content:
                        from ..core.interfaces import MemoryRecordParams

                        await self.memory_manager.record_long_term_memory(
                            MemoryRecordParams(
                                uid=uid,
                                group_id=group_id,
                                content=active_content,
                                memory_type="consolidated",
                                privacy_level="private" if group_id == "private" else "group",
                            ),
                            search_engine=self.search_engine,
                        )

                if memories_to_merge and len(memories_to_merge) >= 2:
                    logger.info(f"[Scriptor] 睡眠巩固中合并 {len(memories_to_merge)} 条相似记忆...")
                    merged_content, total_score = await self.compactor.merge_memories(memories_to_merge)
                    if merged_content:
                        from ..core.interfaces import MemoryRecordParams

                        await self.memory_manager.record_long_term_memory(
                            MemoryRecordParams(
                                uid=uid,
                                group_id=group_id,
                                content=merged_content,
                                memory_type="consolidated",
                                privacy_level="private" if group_id == "private" else "group",
                                useful_score=total_score,
                                strength=2.0,
                            ),
                            search_engine=self.search_engine,
                        )

                if archive_memory:
                    archive_content = "\n".join(archive_memory).strip()
                    if archive_content:
                        await self._archive_memory(uid, group_id, archive_content)

                logger.info(
                    f"[Scriptor] 睡眠巩固完成: 活跃 {len(active_memory)} 条, 合并 {len(memories_to_merge)} 条, 归档 {len(archive_memory)} 条"
                )
        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError) as e:
            logger.error(f"[Scriptor] 睡眠巩固过程出错: {e}")

    async def _archive_memory(self, uid: str, group_id: str, content: str):
        """将冷记忆写入 ARCHIVE.md"""
        if group_id == "private":
            target_dir = self.data_dir / "profiles" / uid
        else:
            target_dir = self.data_dir / "groups" / group_id

        archive_file = target_dir / "ARCHIVE.md"

        now = time.time()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))

        entry = f"\n### [{timestamp}] (archived)\n{content}\n"

        lock = await self.memory_manager._get_lock(archive_file)
        async with lock:
            with open(archive_file, "a", encoding="utf-8") as f:
                f.write(entry)

    async def _run_llm_extraction(self, uid: str, group_id: str):
        """运行 LLM 驱动的深度记忆提取"""
        messages = self.memory_manager.get_unprocessed_messages(uid, group_id)
        if not messages:
            return

        logger.info(f"[Scriptor] 开始执行 LLM 深度记忆提取: uid={uid}, group={group_id}, messages={len(messages)}")

        try:
            profile_dir = self.data_dir / "profiles" / uid
            profile_file = profile_dir / "PROFILE.md"
            current_profile = profile_file.read_text(encoding="utf-8") if profile_file.exists() else ""

            new_profile_facts = await self.compactor.refine_profile(messages, current_profile)
            if new_profile_facts:
                await self.memory_manager.update_profile(uid, group_id, new_profile_facts, scope="personal")
                logger.info(f"[Scriptor] LLM 提取到新画像信息: {new_profile_facts[:50]}...")

            new_experience = await self.compactor.extract_experience(messages)
            if new_experience:
                from ..core.interfaces import MemoryRecordParams

                await self.memory_manager.record_long_term_memory(
                    MemoryRecordParams(
                        uid=uid,
                        group_id=group_id,
                        content=new_experience,
                        memory_type="rule",
                        privacy_level="private" if group_id == "private" else "group",
                    ),
                    search_engine=self.search_engine,
                )
                logger.info(f"[Scriptor] LLM 提取到新经验法则: {new_experience[:50]}...")

        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError) as e:
            logger.error(f"[Scriptor] LLM 深度记忆提取失败: {e}")
        finally:
            self.memory_manager.clear_unprocessed_messages(uid, group_id)
