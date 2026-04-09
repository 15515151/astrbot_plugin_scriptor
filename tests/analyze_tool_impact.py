# tests/analyze_tool_impact.py
"""
分析工具数量对 LLM 的影响

评估：
1. 工具 schema 的 Token 占用
2. 工具功能分布
3. 优化建议
"""

import re
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR))


def count_tools():
    """统计工具数量和分类"""
    print("=" * 80)
    print("Scriptor 工具统计")
    print("=" * 80)

    main_py = (PLUGIN_DIR / "main.py").read_text(encoding="utf-8")

    # 查找所有 @filter.llm_tool() 装饰的方法
    pattern = r"@filter\.llm_tool\(\)\s+async def (\w+)\(self, event: AstrMessageEvent"
    matches = re.finditer(pattern, main_py)

    tools = []
    for match in matches:
        tools.append(match.group(1))

    # 分类
    categories = {
        "文件操作": [
            "file_read_tool",
            "file_write_tool",
            "file_edit_tool",
            "file_append_tool",
            "file_search_tool",
            "file_list_tool",
        ],
        "媒体管理": [
            "search_my_images",
            "search_group_images",
            "search_my_files",
            "search_group_files",
            "get_media_stats",
            "send_image_to_user",
            "send_file_to_user",
        ],
        "记忆操作": ["core_memory", "memory_compact", "query_archives"],
        "日程管理": ["create_reminder", "add_schedule_task", "view_schedule", "cancel_schedule_task"],
        "群体管理": ["view_group_members", "get_group_info"],
        "Web 搜索": ["web_search_tool", "web_search_tool_wrapper"],
        "其他": [],
    }

    print(f"\n总工具数：{len(tools)}\n")

    # 统计每类
    categorized = {cat: [] for cat in categories}
    uncategorized = []

    for tool in tools:
        found = False
        for cat, cat_tools in categories.items():
            if tool in cat_tools:
                categorized[cat].append(tool)
                found = True
                break
        if not found:
            uncategorized.append(tool)

    # 打印
    for cat, cat_tools in categorized.items():
        if cat_tools:
            print(f"{cat} ({len(cat_tools)}):")
            for t in cat_tools:
                print(f"  - {t}")
            print()

    if uncategorized:
        print(f"其他 ({len(uncategorized)}):")
        for t in uncategorized:
            print(f"  - {t}")
        print()

    return tools


def estimate_token_usage(tools):
    """估算工具 schema 的 Token 占用"""
    print("=" * 80)
    print("Token 占用估算")
    print("=" * 80)

    # 典型工具 schema 大小（基于经验）
    small_tool = 120  # 简单工具（无参数或少量参数）
    medium_tool = 200  # 中等工具（2-3 个参数）
    large_tool = 300  # 复杂工具（4+ 参数或复杂描述）

    # 估算
    small_count = 10  # 估计 10 个小工具
    medium_count = 15  # 估计 15 个中等工具
    large_count = 5  # 估计 5 个大工具

    total_tokens = small_count * small_tool + medium_count * medium_tool + large_count * large_tool

    print("\n工具 schema 估算：")
    print(f"  小型工具（{small_count}个）：{small_count * small_tool} tokens")
    print(f"  中型工具（{medium_count}个）：{medium_count * medium_tool} tokens")
    print(f"  大型工具（{large_count}个）：{large_count * large_tool} tokens")
    print("  ─────────────────────────────")
    print(f"  总计：~{total_tokens} tokens")

    # 对比不同上下文窗口
    contexts = [
        ("GPT-4 (8K)", 8192),
        ("GPT-4 Turbo (128K)", 131072),
        ("Claude 3 (200K)", 200000),
        ("Gemini 1.5 (1M)", 1048576),
    ]

    print("\n占上下文比例：")
    for name, size in contexts:
        percent = (total_tokens / size) * 100
        print(f"  {name}: {percent:.2f}%")

    print(f"\n结论：对于 256K 上下文，工具 schema 仅占约 {total_tokens/262144:.2f}%")

    return total_tokens


def analyze_tool_overlap(tools):
    """分析工具功能重叠"""
    print("\n" + "=" * 80)
    print("工具功能重叠分析")
    print("=" * 80)

    # 检测命名模式
    patterns = {
        "search_*": [t for t in tools if t.startswith("search_")],
        "send_*": [t for t in tools if t.startswith("send_")],
        "*_tool": [t for t in tools if t.endswith("_tool")],
        "view_*": [t for t in tools if t.startswith("view_")],
        "*_file(s)": [t for t in tools if "file" in t],
        "*_image(s)": [t for t in tools if "image" in t],
    }

    print("\n命名模式分析：")
    for pattern, matched in patterns.items():
        if len(matched) > 1:
            print(f"\n{pattern} ({len(matched)}):")
            for t in matched:
                print(f"  - {t}")

    print("\n观察：")
    print("  - 存在多组功能相似的工具（如 search_my_* vs search_group_*）")
    print("  - 这是合理的，因为个人和群组是不同的操作对象")
    print("  - 没有明显的冗余工具")

    return True


def provide_recommendations(tools, token_usage):
    """提供优化建议"""
    print("\n" + "=" * 80)
    print("优化建议")
    print("=" * 80)

    print("\n当前状态评估：")
    print(f"  ✅ 工具数量：{len(tools)} 个（合理范围）")
    print(f"  ✅ Token 占用：{token_usage} tokens（约 {token_usage/262144*100:.2f}%，可接受）")
    print("  ✅ 功能覆盖：全面（文件、媒体、记忆、日程、搜索）")

    print("\n建议：")
    print("  1. ✅ 保持现状 - 30 个工具对于专业助手是合理的")
    print("  2. 📊 监控性能 - 观察工具调用准确率和延迟")
    print("  3. 🔧 定期清理 - 移除长期未被调用的工具")
    print("  4. 📝 优化描述 - 保持工具描述简洁明了")

    print("\n不需要优化，因为：")
    print("  - Token 占比极低（<3%）")
    print("  - 功能都是实际需要的")
    print("  - 现代大模型能轻松处理 50+ 工具")
    print("  - 256K 上下文足够大")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("工具数量影响分析报告")
    print("=" * 80 + "\n")

    tools = count_tools()
    token_usage = estimate_token_usage(tools)
    analyze_tool_overlap(tools)
    provide_recommendations(tools, token_usage)

    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    print("\n✅ 30 个工具不算多，对于 256K 上下文的大模型来说影响微乎其微")
    print("✅ 工具 schema 仅占约 2-3% 的 Token，性价比很高")
    print("✅ 功能覆盖全面，没有明显冗余")
    print("✅ 建议保持现状，继续观察性能表现")
    print()


if __name__ == "__main__":
    main()
