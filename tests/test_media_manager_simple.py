# tests/test_media_manager_simple.py
"""
媒体管理器简单测试

测试 MediaManager 的基本功能：
1. 保存和检索图片
2. 保存和检索文件
3. 索引管理
4. 搜索功能
"""

import asyncio
import sys
from pathlib import Path

# 添加插件目录到路径
PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR))

# 直接导入 MediaManager，避免 core.__init__ 的复杂导入
import importlib.util

spec = importlib.util.spec_from_file_location("media_manager", PLUGIN_DIR / "core" / "media_manager.py")
media_manager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media_manager_module)
MediaManager = media_manager_module.MediaManager


class MockConfig:
    """模拟配置对象"""

    media_auto_save_enabled = True
    media_max_image_size_mb = 20
    media_max_file_size_mb = 20
    media_allowed_file_types = "txt,md,doc,docx,jpg,jpeg,png,gif"
    media_retention_days = 30
    media_save_to_memory = False


class TestMediaManager:
    """MediaManager 测试类"""

    def __init__(self):
        self.data_dir = PLUGIN_DIR / "test_data"
        self.config = MockConfig()
        self.media_manager = MediaManager(self.data_dir, self.config)

        # 测试用户和群组
        self.test_uid = "test_user_123"
        self.test_group_id = "test_group_456"

        # 测试数据
        self.test_image_data = b"fake_image_data_png"
        self.test_file_data = b"fake_text_file_content"

    async def test_save_image(self):
        """测试保存图片"""
        print("\n=== 测试保存图片 ===")

        sender_info = {"uid": self.test_uid, "name": "测试用户"}

        result = await self.media_manager.save_image(
            image_data=self.test_image_data,
            uid=self.test_uid,
            group_id="private",
            sender_info=sender_info,
            description="测试图片描述",
            original_name="test_image.png",
        )

        if result:
            print("✅ 图片保存成功")
            print(f"   文件名：{result['filename']}")
            print(f"   原始名：{result['original_name']}")
            print(f"   大小：{result['size_bytes']} bytes")
            print(f"   描述：{result['description']}")
            return True
        else:
            print("❌ 图片保存失败")
            return False

    async def test_save_file(self):
        """测试保存文件"""
        print("\n=== 测试保存文件 ===")

        sender_info = {"uid": self.test_uid, "name": "测试用户"}

        result = await self.media_manager.save_file(
            file_data=self.test_file_data,
            filename="test_document.txt",
            uid=self.test_uid,
            group_id="private",
            sender_info=sender_info,
            description="测试文件描述",
        )

        if result:
            print("✅ 文件保存成功")
            print(f"   文件名：{result['filename']}")
            print(f"   原始名：{result['original_name']}")
            print(f"   类型：{result['file_type']}")
            print(f"   大小：{result['size_bytes']} bytes")
            return True
        else:
            print("❌ 文件保存失败")
            return False

    async def test_search_images(self):
        """测试搜索图片"""
        print("\n=== 测试搜索图片 ===")

        # 先保存一张图片
        sender_info = {"uid": self.test_uid, "name": "测试用户"}
        await self.media_manager.save_image(
            image_data=b"search_test_image",
            uid=self.test_uid,
            group_id="private",
            sender_info=sender_info,
            description="这是一张测试图片用于搜索",
            original_name="search_test.png",
        )

        # 搜索
        results = await self.media_manager.search_images(uid=self.test_uid, group_id="private", keyword="测试", limit=5)

        if results:
            print(f"✅ 搜索成功，找到 {len(results)} 张图片")
            for img in results:
                print(f"   - {img['original_name']}: {img.get('description', '')[:30]}")
            return True
        else:
            print("❌ 搜索失败或未找到结果")
            return False

    async def test_search_files(self):
        """测试搜索文件"""
        print("\n=== 测试搜索文件 ===")

        # 先保存一个文件
        sender_info = {"uid": self.test_uid, "name": "测试用户"}
        await self.media_manager.save_file(
            file_data=b"search test content",
            filename="search_test.txt",
            uid=self.test_uid,
            group_id="private",
            sender_info=sender_info,
            description="测试搜索功能的文件",
        )

        # 搜索
        results = await self.media_manager.search_files(uid=self.test_uid, group_id="private", keyword="搜索", limit=5)

        if results:
            print(f"✅ 搜索成功，找到 {len(results)} 个文件")
            for f in results:
                print(f"   - {f['original_name']} ({f['file_type']}): {f.get('description', '')[:30]}")
            return True
        else:
            print("❌ 搜索失败或未找到结果")
            return False

    async def test_get_stats(self):
        """测试获取统计信息"""
        print("\n=== 测试获取统计信息 ===")

        stats = await self.media_manager.get_stats(self.test_uid, "private")

        print("✅ 统计信息获取成功")
        print(f"   图片数量：{stats['image_count']}")
        print(f"   文件数量：{stats['file_count']}")
        print(f"   总大小：{stats['total_size_mb']} MB")
        return True

    async def test_group_media(self):
        """测试群组媒体保存"""
        print("\n=== 测试群组媒体保存 ===")

        sender_info = {"uid": self.test_uid, "name": "测试用户"}

        # 保存图片到群组
        image_result = await self.media_manager.save_image(
            image_data=b"group_image_data",
            uid=self.test_uid,
            group_id=self.test_group_id,
            sender_info=sender_info,
            description="群组图片",
            original_name="group_photo.jpg",
        )

        # 保存文件到群组
        file_result = await self.media_manager.save_file(
            file_data=b"group file content",
            filename="group_doc.txt",
            uid=self.test_uid,
            group_id=self.test_group_id,
            sender_info=sender_info,
        )

        if image_result and file_result:
            print("✅ 群组媒体保存成功")

            # 搜索群组图片
            group_images = await self.media_manager.search_images(self.test_uid, self.test_group_id, "", 5)
            print(f"   群组图片数：{len(group_images)}")

            # 搜索群组文件
            group_files = await self.media_manager.search_files(self.test_uid, self.test_group_id, "", "", 5)
            print(f"   群组文件数：{len(group_files)}")

            return True
        else:
            print("❌ 群组媒体保存失败")
            return False

    async def test_file_type_filter(self):
        """测试文件类型过滤"""
        print("\n=== 测试文件类型过滤 ===")

        sender_info = {"uid": self.test_uid, "name": "测试用户"}

        # 保存不同类型的文件
        await self.media_manager.save_file(
            file_data=b"txt content",
            filename="test.txt",
            uid=self.test_uid,
            group_id="private",
            sender_info=sender_info,
        )

        await self.media_manager.save_file(
            file_data=b"docx content",
            filename="test.docx",
            uid=self.test_uid,
            group_id="private",
            sender_info=sender_info,
        )

        # 按类型搜索
        txt_files = await self.media_manager.search_files(self.test_uid, "private", "", "txt", 5)

        docx_files = await self.media_manager.search_files(self.test_uid, "private", "", "docx", 5)

        print("✅ 文件类型过滤成功")
        print(f"   TXT 文件数：{len(txt_files)}")
        print(f"   DOCX 文件数：{len(docx_files)}")

        return len(txt_files) > 0 and len(docx_files) > 0

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("MediaManager 功能测试")
        print("=" * 60)

        tests = [
            ("保存图片", self.test_save_image),
            ("保存文件", self.test_save_file),
            ("搜索图片", self.test_search_images),
            ("搜索文件", self.test_search_files),
            ("获取统计", self.test_get_stats),
            ("群组媒体", self.test_group_media),
            ("类型过滤", self.test_file_type_filter),
        ]

        results = []
        for name, test_func in tests:
            try:
                result = await test_func()
                results.append((name, result))
            except Exception as e:
                print(f"\n❌ 测试失败 [{name}]: {e}")
                import traceback

                traceback.print_exc()
                results.append((name, False))

        # 汇总结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        passed = sum(1 for _, r in results if r)
        total = len(results)

        for name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{status} - {name}")

        print(f"\n总计：{passed}/{total} 测试通过")

        # 清理测试数据
        print("\n清理测试数据...")
        import shutil

        test_data_dir = self.data_dir
        if test_data_dir.exists():
            shutil.rmtree(test_data_dir)
            print(f"已删除测试目录：{test_data_dir}")

        return passed == total


async def main():
    """主函数"""
    tester = TestMediaManager()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
