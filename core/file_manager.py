# core/file_manager.py
"""工作文件管理器 - 参考 CoPaw 的 AgentMdManager 设计

工作文件管理器的核心理念：
1. AI 可以主动读写 working/ 目录下的文件
2. 区分不同类型的文件：TODO、NOTES、CONTEXT 等
3. 为 AI 提供工作文件的上下文信息
"""

import time
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    pass

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class FileManager:
    """工作文件管理器

    管理 AI 的工作空间，参考 CoPaw 的 AgentMdManager 设计。
    AI 可以主动读写用户/群组根目录下的文件来管理工作任务和笔记。

    工作目录结构（废除 working/ 中间层）:
        profiles/
            uid/
                SOUL.md          # 核心模板文件
                PROFILE.md       # 身份模板文件
                MEMORY.md        # 长期记忆
                HEARTBEAT.md     # 心跳指令
                TODO.md          # 待办事项
                NOTES.md         # 随手笔记
                CONTEXT.md       # 当前任务上下文
                memory/          # 每日日记
                    YYYY-MM-DD.md
                ARCHIVE/         # 归档的工作文件
        groups/
            gid/
                GROUP.md
                MEMORY.md
                TODO.md
                NOTES.md
                memory/
                    YYYY-MM-DD.md
    """

    WORKING_FILES = ["TODO.md", "NOTES.md", "CONTEXT.md"]

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def _get_root_dir(self, uid: str, group_id: str) -> Path:
        """获取用户或群组的根目录路径（废除 working/ 中间层）"""
        if group_id in ("private", "unknown"):
            return self.data_dir / "profiles" / uid
        else:
            return self.data_dir / "groups" / group_id

    def ensure_profile_dir(self, uid: str, group_id: str) -> Path:
        """确保根目录存在，并创建默认文件"""
        root_dir = self._get_root_dir(uid, group_id)
        root_dir.mkdir(parents=True, exist_ok=True)

        # 创建 memory 目录用于存放日记
        (root_dir / "memory").mkdir(exist_ok=True)

        # 创建 md_files 目录用于存放其他文档 (CoPaw 风格)
        (root_dir / "md_files").mkdir(exist_ok=True)

        archive_dir = root_dir / "ARCHIVE"
        archive_dir.mkdir(exist_ok=True)

        return root_dir

    def get_working_context(self, uid: str, group_id: str) -> str:
        """获取工作文件的上下文摘要，用于注入到提示词

        Returns:
            格式化的上下文信息
        """
        root_dir = self._get_root_dir(uid, group_id)
        if not root_dir.exists():
            return ""

        context_parts = []
        context_parts.append("### 📄 当前工作文件摘要")

        for filename in self.WORKING_FILES:
            file_path = root_dir / filename
            if file_path.exists():
                stat = file_path.stat()
                mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))

                content = file_path.read_text(encoding="utf-8").strip()

                summary = ""
                if content.startswith("---"):
                    try:
                        import yaml

                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            meta = yaml.safe_load(parts[1])
                            summary = meta.get("summary", "")
                    except:
                        pass

                if not summary:
                    clean_content = content
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            clean_content = parts[2].strip()

                    summary = (
                        clean_content[:150].replace("\n", " ") + "..." if len(clean_content) > 150 else clean_content
                    )

                context_parts.append(f"- **{filename}** (最后修改: {mtime}): {summary}")

        return "\n".join(context_parts)

    def list_working_files(self, uid: str, group_id: str) -> List[Dict]:
        """列出根目录和 md_files 中的文件（不含 memory/ 和 ARCHIVE/）

        Returns:
            文件信息列表
        """
        root_dir = self._get_root_dir(uid, group_id)
        if not root_dir.exists():
            return []

        exclude_dirs = {root_dir / "memory", root_dir / "ARCHIVE"}

        files = []
        # 扫描根目录和 md_files 目录
        for f in root_dir.rglob("*.md"):
            if f.is_file() and not any(f.is_relative_to(ex) for ex in exclude_dirs):
                stat = f.stat()
                files.append(
                    {
                        "filename": f.name,
                        "path": str(f.relative_to(root_dir)),
                        "size": stat.st_size,
                        "created_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
                        "modified_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                    }
                )

        return sorted(files, key=lambda x: x["modified_time"], reverse=True)

    def archive_old_file(self, uid: str, group_id: str, filename: str) -> bool:
        """将旧文件归档到 ARCHIVE 目录

        Args:
            uid: 用户 ID
            group_id: 群组 ID
            filename: 要归档的文件名

        Returns:
            是否归档成功
        """
        root_dir = self._get_root_dir(uid, group_id)
        source = root_dir / filename

        if not source.exists():
            return False

        archive_dir = root_dir / "ARCHIVE"
        archive_dir.mkdir(exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        archive_name = f"{source.stem}_{timestamp}.md"
        archive_path = archive_dir / archive_name

        source.rename(archive_path)
        logger.info(f"[Scriptor] 归档工作文件: {filename} -> {archive_name}")
        return True

    def get_default_file_content(self, filename: str) -> str:
        """获取默认文件内容模板"""
        templates = {
            "TODO.md": """---
summary: "待办事项列表"
---
# 待办事项

## 进行中
-

## 已完成
-

## 计划中
-

""",
            "NOTES.md": """---
summary: "随手笔记与灵感"
---
# 随手笔记

## 重要记录
-

## 想法
-

""",
            "CONTEXT.md": """---
summary: "当前任务背景与决策上下文"
---
# 当前任务上下文

## 当前任务
-

## 背景信息
-

## 关键决策
-

""",
            "MEMORY.md": """---
summary: "长期记忆与核心智慧"
---
# 长期记忆

## 重要事件与决策
-

## 经验教训
-

""",
        }
        return templates.get(filename, f"# {filename.replace('.md', '')}\n\n")
