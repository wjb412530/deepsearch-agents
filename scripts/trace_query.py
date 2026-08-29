"""
LangSmith 链路查询脚本（项目 3 - 可观测性）

功能：
1. 通过 LangSmith API 按 thread_id 查询 trace 记录
2. 格式化输出调用链路和耗时数据
3. 支持离线分析和批量查询

使用方法：
    python scripts/trace_query.py <thread_id>
    python scripts/trace_query.py --recent 5  # 查询最近 5 条 trace

环境变量：
    LANGSMITH_API_KEY: LangSmith API 密钥（必需）
"""

import argparse
import os
import sys
from pathlib import Path

# Windows 控制台编码问题修复
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_langsmith_config():
    """检查 LangSmith 配置是否正确"""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("❌ 错误：未设置 LANGSMITH_API_KEY 环境变量")
        print("请在 .env 文件中配置：")
        print("  LANGSMITH_API_KEY=your_api_key")
        sys.exit(1)
    return api_key


def query_traces_by_thread_id(thread_id: str, api_key: str):
    """
    按 thread_id 查询 trace 记录

    Args:
        thread_id: 会话 ID
        api_key: LangSmith API 密钥
    """
    try:
        from langsmith import Client
    except ImportError:
        print("❌ 错误：未安装 langsmith 依赖")
        print("请运行：uv pip install langsmith")
        sys.exit(1)

    client = Client(api_key=api_key)

    print(f"\n🔍 查询 thread_id: {thread_id}")
    print("=" * 70)

    try:
        # 查询 runs（LangSmith 中 trace 的基本单位）
        runs = list(client.list_runs(
            project_name=os.getenv("LANGSMITH_PROJECT", "default"),
            filter=f'eq(metadata_key, "thread_id") and eq(metadata_value, "{thread_id}")'
        ))

        if not runs:
            print(f"⚠️  未找到 thread_id 为 '{thread_id}' 的 trace 记录")
            print("提示：")
            print("  1. 确认 thread_id 正确")
            print("  2. 确认 LANGSMITH_TRACING 已启用")
            print("  3. 检查 LangSmith 面板是否有对应记录")
            return

        print(f"✅ 找到 {len(runs)} 条相关记录\n")

        # 按开始时间排序
        runs = sorted(runs, key=lambda r: r.start_time)

        # 格式化输出
        for i, run in enumerate(runs, 1):
            duration_ms = int((run.end_time - run.start_time).total_seconds() * 1000) if run.end_time else 0

            print(f"[{i}] {run.name}")
            print(f"    类型: {run.run_type}")
            print(f"    状态: {run.status}")
            print(f"    开始: {run.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if run.end_time:
                print(f"    结束: {run.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    耗时: {duration_ms}ms")

            if run.error:
                print(f"    错误: {run.error}")

            print()

    except Exception as e:
        print(f"❌ 查询失败: {e}")
        sys.exit(1)


def query_recent_traces(limit: int, api_key: str):
    """
    查询最近的 trace 记录

    Args:
        limit: 返回记录数量
        api_key: LangSmith API 密钥
    """
    try:
        from langsmith import Client
    except ImportError:
        print("❌ 错误：未安装 langsmith 依赖")
        print("请运行：uv pip install langsmith")
        sys.exit(1)

    client = Client(api_key=api_key)

    print(f"\n🔍 查询最近 {limit} 条 trace 记录")
    print("=" * 70)

    try:
        runs = list(client.list_runs(
            project_name=os.getenv("LANGSMITH_PROJECT", "default"),
            limit=limit
        ))

        if not runs:
            print("⚠️  未找到任何 trace 记录")
            return

        print(f"✅ 找到 {len(runs)} 条记录\n")

        for i, run in enumerate(runs, 1):
            duration_ms = int((run.end_time - run.start_time).total_seconds() * 1000) if run.end_time else 0

            # 提取 thread_id（如果有）
            thread_id = run.extra.get("metadata", {}).get("thread_id", "N/A")

            print(f"[{i}] {run.name}")
            print(f"    Thread ID: {thread_id}")
            print(f"    类型: {run.run_type}")
            print(f"    开始: {run.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    耗时: {duration_ms}ms")
            print()

    except Exception as e:
        print(f"❌ 查询失败: {e}")
        sys.exit(1)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="LangSmith 链路查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 按 thread_id 查询
  python scripts/trace_query.py abc-123-def

  # 查询最近 5 条 trace
  python scripts/trace_query.py --recent 5

  # 查询最近 10 条 trace
  python scripts/trace_query.py -r 10
        """
    )

    parser.add_argument(
        "thread_id",
        nargs="?",
        help="要查询的 thread_id（会话 ID）"
    )

    parser.add_argument(
        "-r", "--recent",
        type=int,
        metavar="N",
        help="查询最近 N 条 trace 记录"
    )

    args = parser.parse_args()

    # 检查参数
    if not args.thread_id and not args.recent:
        parser.print_help()
        sys.exit(1)

    # 检查 LangSmith 配置
    api_key = check_langsmith_config()

    # 执行查询
    if args.recent:
        query_recent_traces(args.recent, api_key)
    else:
        query_traces_by_thread_id(args.thread_id, api_key)


if __name__ == "__main__":
    main()
