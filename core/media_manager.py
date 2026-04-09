# core/media_manager.py
"""媒体资源管理器

实现群聊/私聊的图片和文件自动保存系统：
- 按用户/群组隔离存储
- 自动索引和元数据记录
- 支持检索和召回
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class MediaManager:
    """媒体资源管理器"""

    def __init__(self, data_dir: Path, config):
        """
        初始化媒体管理器

        Args:
            data_dir: 插件数据目录
            config: 配置对象
        """
        self.data_dir = data_dir
        self.config = config

        self._index_cache: Dict[str, Dict] = {}
        self._cache_lock = asyncio.Lock()
        self._cache_ttl = 300

        self._last_cache_cleanup = time.time()
        self._cache_cleanup_interval = 600

    def _get_root_dir(self, uid: str, group_id: str) -> Path:
        """获取用户或群组的根目录"""
        if group_id in ("private", "unknown"):
            return self.data_dir / "profiles" / uid
        else:
            return self.data_dir / "groups" / group_id

    def _get_media_dir(self, uid: str, group_id: str, media_type: str) -> Path:
        """
        获取媒体存储目录（自动创建）

        Args:
            uid: 用户 ID
            group_id: 群组 ID
            media_type: "images" 或 "files"

        Returns:
            媒体目录路径
        """
        root_dir = self._get_root_dir(uid, group_id)
        media_dir = root_dir / "media" / media_type
        media_dir.mkdir(parents=True, exist_ok=True)
        return media_dir

    def _get_index_path(self, uid: str, group_id: str) -> Path:
        """获取索引文件路径"""
        root_dir = self._get_root_dir(uid, group_id)
        return root_dir / "media_index.json"

    async def _load_index(self, uid: str, group_id: str) -> Dict:
        """加载索引文件（带缓存）"""
        cache_key = f"{uid}_{group_id}"

        async with self._cache_lock:
            if cache_key in self._index_cache:
                cache_entry = self._index_cache[cache_key]
                if time.time() - cache_entry["time"] < self._cache_ttl:
                    return cache_entry["data"]

            index_path = self._get_index_path(uid, group_id)

            if index_path.exists():
                try:
                    with open(index_path, "r", encoding="utf-8") as f:
                        index_data = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"[Scriptor] 加载索引文件失败：{e}，使用空索引")
                    index_data = {"images": [], "files": []}
            else:
                index_data = {"images": [], "files": []}

            self._index_cache[cache_key] = {"data": index_data, "time": time.time()}

            return index_data

    async def _save_index(self, uid: str, group_id: str, index_data: Dict):
        """保存索引文件"""
        cache_key = f"{uid}_{group_id}"
        index_path = self._get_index_path(uid, group_id)

        async with self._cache_lock:
            try:
                index_path.parent.mkdir(parents=True, exist_ok=True)

                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)

                if cache_key in self._index_cache:
                    self._index_cache[cache_key]["time"] = time.time()

                logger.debug(f"[Scriptor] 索引文件已保存：{index_path}")
            except Exception as e:
                logger.error(f"[Scriptor] 保存索引文件失败：{e}")

    async def _cleanup_cache(self):
        """清理过期的缓存"""
        if time.time() - self._last_cache_cleanup < self._cache_cleanup_interval:
            return

        async with self._cache_lock:
            now = time.time()
            expired_keys = [k for k, v in self._index_cache.items() if now - v["time"] > self._cache_ttl]

            for key in expired_keys:
                del self._index_cache[key]

            self._last_cache_cleanup = now
            logger.debug(f"[Scriptor] 清理了 {len(expired_keys)} 个过期缓存")

    def _generate_filename(self, original_name: str, md5_hash: str, media_type: str) -> str:
        """生成存储文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if media_type == "images":
            ext = Path(original_name).suffix.lower() if original_name else ".jpg"
            if not ext:
                ext = ".jpg"
            return f"{timestamp}_{md5_hash[:16]}{ext}"
        else:
            safe_name = "".join(c for c in original_name if c.isalnum() or c in "._- ")
            safe_name = safe_name[:50]
            return f"{timestamp}_{md5_hash[:16]}_{safe_name}"

    def _compute_md5(self, data: bytes) -> str:
        """计算数据的 MD5 哈希"""
        return hashlib.md5(data).hexdigest()

    def _check_file_size(self, data: bytes, max_size_mb: int, media_type: str) -> bool:
        """检查文件大小是否超过限制"""
        size_mb = len(data) / (1024 * 1024)
        if size_mb > max_size_mb:
            logger.warning(f"[Scriptor] 文件过大：{size_mb:.2f}MB > {max_size_mb}MB")
            return False
        return True

    def _check_file_type(self, filename: str, allowed_types: str) -> bool:
        """检查文件类型是否在白名单中"""
        if not allowed_types or allowed_types.strip() == "":
            return True

        allowed_list = [t.strip().lower() for t in allowed_types.split(",")]
        ext = Path(filename).suffix.lower().lstrip(".")

        if ext in allowed_list:
            return True

        logger.warning(f"[Scriptor] 文件类型不允许：{ext}")
        return False

    async def save_image(
        self,
        image_data: bytes,
        uid: str,
        group_id: str,
        sender_info: Dict[str, str],
        description: str = "",
        original_name: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        保存图片并更新索引

        Args:
            image_data: 图片二进制数据
            uid: 用户 ID
            group_id: 群组 ID
            sender_info: 发送者信息 {"uid": ..., "name": ...}
            description: 图片描述（可选）
            original_name: 原始文件名（可选）

        Returns:
            保存的媒体信息，失败返回 None
        """
        if not self.config.media_auto_save_enabled:
            return None

        max_size = self.config.media_max_image_size_mb
        if not self._check_file_size(image_data, max_size, "image"):
            return None

        md5_hash = self._compute_md5(image_data)
        filename = self._generate_filename(original_name, md5_hash, "images")

        media_dir = self._get_media_dir(uid, group_id, "images")
        file_path = media_dir / filename

        try:
            with open(file_path, "wb") as f:
                f.write(image_data)

            logger.info(f"[Scriptor] 图片已保存：{filename} ({len(image_data)} bytes)")

            media_info = {
                "filename": filename,
                "original_name": original_name or "",
                "sender_uid": sender_info.get("uid", "unknown"),
                "sender_name": sender_info.get("name", "unknown"),
                "timestamp": int(time.time()),
                "description": description,
                "md5": md5_hash,
                "size_bytes": len(image_data),
                "tags": [],
            }

            await self._add_to_index(uid, group_id, "images", media_info)

            return media_info

        except Exception as e:
            logger.error(f"[Scriptor] 保存图片失败：{e}")
            return None

    async def save_file(
        self,
        file_data: bytes,
        filename: str,
        uid: str,
        group_id: str,
        sender_info: Dict[str, str],
        description: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        保存文件并更新索引

        Args:
            file_data: 文件二进制数据
            filename: 文件名
            uid: 用户 ID
            group_id: 群组 ID
            sender_info: 发送者信息
            description: 文件描述（可选）

        Returns:
            保存的媒体信息，失败返回 None
        """
        if not self.config.media_auto_save_enabled:
            return None

        if not self._check_file_type(filename, self.config.media_allowed_file_types):
            return None

        max_size = self.config.media_max_file_size_mb
        if not self._check_file_size(file_data, max_size, "file"):
            return None

        md5_hash = self._compute_md5(file_data)
        storage_filename = self._generate_filename(filename, md5_hash, "files")

        media_dir = self._get_media_dir(uid, group_id, "files")
        file_path = media_dir / storage_filename

        try:
            with open(file_path, "wb") as f:
                f.write(file_data)

            logger.info(f"[Scriptor] 文件已保存：{storage_filename} ({len(file_data)} bytes)")

            file_type = Path(filename).suffix.lower().lstrip(".")

            media_info = {
                "filename": storage_filename,
                "original_name": filename,
                "sender_uid": sender_info.get("uid", "unknown"),
                "sender_name": sender_info.get("name", "unknown"),
                "timestamp": int(time.time()),
                "file_type": file_type,
                "size_bytes": len(file_data),
                "description": description,
                "tags": [],
            }

            await self._add_to_index(uid, group_id, "files", media_info)

            return media_info

        except Exception as e:
            logger.error(f"[Scriptor] 保存文件失败：{e}")
            return None

    async def _add_to_index(self, uid: str, group_id: str, media_type: str, media_info: Dict):
        """添加媒体到索引"""
        index_data = await self._load_index(uid, group_id)

        if media_type not in index_data:
            index_data[media_type] = []

        index_data[media_type].append(media_info)

        await self._save_index(uid, group_id, index_data)

    async def search_images(self, uid: str, group_id: str, keyword: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索图片

        Args:
            uid: 用户 ID
            group_id: 群组 ID
            keyword: 搜索关键词（匹配描述、标签、文件名）
            limit: 返回数量限制

        Returns:
            图片信息列表
        """
        index_data = await self._load_index(uid, group_id)
        images = index_data.get("images", [])

        if keyword:
            keyword_lower = keyword.lower()
            filtered = []
            for img in images:
                if (
                    keyword_lower in img.get("description", "").lower()
                    or keyword_lower in img.get("original_name", "").lower()
                    or keyword_lower in img.get("filename", "").lower()
                    or any(keyword_lower in tag.lower() for tag in img.get("tags", []))
                ):
                    filtered.append(img)
            images = filtered

        images = sorted(images, key=lambda x: x.get("timestamp", 0), reverse=True)
        return images[:limit]

    async def search_files(
        self, uid: str, group_id: str, keyword: str = "", file_type: str = "", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索文件

        Args:
            uid: 用户 ID
            group_id: 群组 ID
            keyword: 搜索关键词
            file_type: 文件类型过滤
            limit: 返回数量限制

        Returns:
            文件信息列表
        """
        index_data = await self._load_index(uid, group_id)
        files = index_data.get("files", [])

        if keyword:
            keyword_lower = keyword.lower()
            filtered = []
            for f in files:
                if (
                    keyword_lower in f.get("description", "").lower()
                    or keyword_lower in f.get("original_name", "").lower()
                    or keyword_lower in f.get("filename", "").lower()
                ):
                    filtered.append(f)
            files = filtered

        if file_type:
            file_type_lower = file_type.lower()
            files = [f for f in files if f.get("file_type", "").lower() == file_type_lower]

        files = sorted(files, key=lambda x: x.get("timestamp", 0), reverse=True)
        return files[:limit]

    def get_image_path(self, uid: str, group_id: str, filename: str) -> Optional[Path]:
        """获取图片文件路径"""
        media_dir = self._get_media_dir(uid, group_id, "images")
        file_path = media_dir / filename

        if file_path.exists():
            return file_path
        return None

    def get_file_path(self, uid: str, group_id: str, filename: str) -> Optional[Path]:
        """获取文件路径

        支持通过以下方式查找：
        1. 精确匹配实际文件名（如：20260331_215948_xxx_原始名.txt）
        2. 通过索引匹配原始文件名（如：原始名.txt）
        """
        media_dir = self._get_media_dir(uid, group_id, "files")
        file_path = media_dir / filename

        if file_path.exists():
            return file_path

        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._load_index(uid, group_id))
                    index_data = future.result()
            else:
                index_data = asyncio.run(self._load_index(uid, group_id))

            for f in index_data.get("files", []):
                if f.get("original_name") == filename or f.get("filename") == filename:
                    actual_filename = f.get("filename")
                    actual_path = media_dir / actual_filename
                    if actual_path.exists():
                        return actual_path
        except Exception as e:
            logger.debug(f"[Scriptor] 索引查找失败: {e}")

        return None

    async def delete_media(self, uid: str, group_id: str, media_type: str, filename: str) -> bool:
        """
        删除媒体文件和索引记录

        Args:
            uid: 用户 ID
            group_id: 群组 ID
            media_type: "images" 或 "files"
            filename: 文件名

        Returns:
            是否删除成功
        """
        index_data = await self._load_index(uid, group_id)

        if media_type not in index_data:
            return False

        media_list = index_data[media_type]
        media_item = next((m for m in media_list if m["filename"] == filename), None)

        if not media_item:
            return False

        media_dir = self._get_media_dir(uid, group_id, media_type)
        file_path = media_dir / filename

        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"[Scriptor] 已删除媒体文件：{filename}")

            index_data[media_type] = [m for m in media_list if m["filename"] != filename]
            await self._save_index(uid, group_id, index_data)

            return True

        except Exception as e:
            logger.error(f"[Scriptor] 删除媒体失败：{e}")
            return False

    async def search_media(
        self, uid: str, group_id: str, query: str = "", media_type: str = "all", days: int = 30, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        统一搜索媒体文件

        Args:
            uid: 用户 ID
            group_id: 群组 ID
            query: 搜索关键词
            media_type: 媒体类型 (all/images/files)
            days: 搜索最近多少天
            limit: 返回数量限制

        Returns:
            媒体信息列表
        """
        cutoff_time = time.time() - (days * 86400)
        results = []

        index_data = await self._load_index(uid, group_id)

        if media_type in ["all", "images"]:
            images = index_data.get("images", [])
            for img in images:
                if img.get("timestamp", 0) < cutoff_time:
                    continue
                if query:
                    query_lower = query.lower()
                    if not (
                        query_lower in img.get("description", "").lower()
                        or query_lower in img.get("original_name", "").lower()
                        or query_lower in img.get("filename", "").lower()
                    ):
                        continue
                img["type"] = "image"
                results.append(img)

        if media_type in ["all", "files"]:
            files = index_data.get("files", [])
            for f in files:
                if f.get("timestamp", 0) < cutoff_time:
                    continue
                if query:
                    query_lower = query.lower()
                    if not (
                        query_lower in f.get("description", "").lower()
                        or query_lower in f.get("original_name", "").lower()
                        or query_lower in f.get("filename", "").lower()
                    ):
                        continue
                f["type"] = "file"
                results.append(f)

        results = sorted(results, key=lambda x: x.get("timestamp", 0), reverse=True)
        return results[:limit]

    async def list_recent_media(
        self, uid: str, group_id: str, media_type: str = "all", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        列出最近的媒体文件

        Args:
            uid: 用户 ID
            group_id: 群组 ID
            media_type: 媒体类型 (all/images/files)
            limit: 返回数量限制

        Returns:
            媒体信息列表
        """
        results = []
        index_data = await self._load_index(uid, group_id)

        if media_type in ["all", "images"]:
            images = index_data.get("images", [])
            for img in images:
                img["type"] = "image"
                results.append(img)

        if media_type in ["all", "files"]:
            files = index_data.get("files", [])
            for f in files:
                f["type"] = "file"
                results.append(f)

        results = sorted(results, key=lambda x: x.get("timestamp", 0), reverse=True)
        return results[:limit]

    async def get_media_by_filename(self, uid: str, group_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        根据文件名获取媒体信息

        Args:
            uid: 用户 ID
            group_id: 群组 ID
            filename: 文件名

        Returns:
            媒体信息，包含 path、media_type、original_name 等
        """
        index_data = await self._load_index(uid, group_id)

        images = index_data.get("images", [])
        for img in images:
            if img.get("filename") == filename:
                img["media_type"] = "image"
                img["path"] = str(self._get_media_dir(uid, group_id, "images") / filename)
                return img

        files = index_data.get("files", [])
        for f in files:
            if f.get("filename") == filename:
                f["media_type"] = "file"
                f["path"] = str(self._get_media_dir(uid, group_id, "files") / filename)
                return f

        return None

    async def get_stats(self, uid: str, group_id: str) -> Dict[str, Any]:
        """
        获取媒体统计信息

        Returns:
            统计信息 {"image_count": ..., "file_count": ..., "total_size_bytes": ...}
        """
        index_data = await self._load_index(uid, group_id)

        images = index_data.get("images", [])
        files = index_data.get("files", [])

        total_size = sum(img.get("size_bytes", 0) for img in images)
        total_size += sum(f.get("size_bytes", 0) for f in files)

        return {
            "image_count": len(images),
            "file_count": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

    async def cleanup_expired_media(self, retention_days: int) -> int:
        """
        清理过期的媒体文件

        Args:
            retention_days: 保留天数

        Returns:
            清理的文件数量
        """
        if retention_days <= 0:
            return 0

        cutoff_time = time.time() - (retention_days * 86400)
        cleaned_count = 0

        profiles_dir = self.data_dir / "profiles"
        groups_dir = self.data_dir / "groups"

        for root_dir in [profiles_dir, groups_dir]:
            if not root_dir.exists():
                continue

            for item_dir in root_dir.iterdir():
                if not item_dir.is_dir():
                    continue

                index_path = item_dir / "media_index.json"
                if not index_path.exists():
                    continue

                try:
                    with open(index_path, "r", encoding="utf-8") as f:
                        index_data = json.load(f)

                    for media_type in ["images", "files"]:
                        media_list = index_data.get(media_type, [])
                        expired = [m for m in media_list if m.get("timestamp", 0) < cutoff_time]

                        for media_item in expired:
                            filename = media_item["filename"]
                            file_path = item_dir / "media" / media_type / filename

                            if file_path.exists():
                                file_path.unlink()
                                cleaned_count += 1
                                logger.debug(f"[Scriptor] 清理过期媒体：{filename}")

                        index_data[media_type] = [m for m in media_list if m.get("timestamp", 0) >= cutoff_time]

                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(index_data, f, ensure_ascii=False, indent=2)

                except Exception as e:
                    logger.error(f"[Scriptor] 清理过期媒体失败：{e}")

        logger.info(f"[Scriptor] 清理了 {cleaned_count} 个过期媒体文件")
        return cleaned_count

    async def initialize(self):
        """初始化（异步清理任务）"""
        await self._cleanup_cache()

        if self.config.media_retention_days > 0:
            await self.cleanup_expired_media(self.config.media_retention_days)
