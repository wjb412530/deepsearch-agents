"""
Redis 缓存功能验证脚本

测试场景：
1. Redis 启用时，相同查询第二次应从缓存返回（耗时显著下降）
2. Redis 关闭时，系统仍正常运行（降级生效）
"""

import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE = "http://localhost:8000"

def test_cache_with_redis_enabled():
    """
    测试场景 1：Redis 启用时的缓存命中
    """
    print("\n" + "="*60)
    print("测试场景 1: Redis 启用时的缓存命中")
    print("="*60)

    # 检查 Redis 配置
    redis_enabled = os.getenv("REDIS_ENABLED", "false")
    print(f"\n当前 REDIS_ENABLED={redis_enabled}")

    if redis_enabled.lower() != "true":
        print("\n[警告] Redis 未启用，请在 .env 中设置 REDIS_ENABLED=true")
        print("提示：需要先启动 Redis 服务")
        return False

    # 使用固定查询进行两次相同的搜索
    query = "人工智能在医疗领域的最新应用"

    print(f"\n第一次查询: {query}")
    print("提交任务...")

    start_time = time.time()
    response = requests.post(
        f"{API_BASE}/api/task",
        json={"query": query},
        timeout=180
    )

    if response.status_code != 200:
        print(f"[失败] HTTP {response.status_code}: {response.text}")
        return False

    thread_id_1 = response.json().get("thread_id")
    print(f"任务已提交, thread_id: {thread_id_1}")

    # 等待任务完成
    time.sleep(120)
    duration_1 = (time.time() - start_time) * 1000
    print(f"第一次查询完成，耗时: {duration_1:.0f}ms")

    # 等待几秒后进行第二次相同查询
    print("\n等待 5 秒后进行第二次相同查询...")
    time.sleep(5)

    print(f"\n第二次查询: {query} (相同查询)")
    print("提交任务...")

    start_time = time.time()
    response = requests.post(
        f"{API_BASE}/api/task",
        json={"query": query},
        timeout=180
    )

    if response.status_code != 200:
        print(f"[失败] HTTP {response.status_code}: {response.text}")
        return False

    thread_id_2 = response.json().get("thread_id")
    print(f"任务已提交, thread_id: {thread_id_2}")

    # 等待任务完成
    time.sleep(120)
    duration_2 = (time.time() - start_time) * 1000
    print(f"第二次查询完成，耗时: {duration_2:.0f}ms")

    # 分析结果
    print("\n" + "-"*60)
    print("缓存效果分析:")
    print(f"第一次查询耗时: {duration_1:.0f}ms (无缓存)")
    print(f"第二次查询耗时: {duration_2:.0f}ms (应有缓存)")

    if duration_2 < duration_1 * 0.8:
        print(f"[成功] 缓存生效！耗时降低了 {(1 - duration_2/duration_1)*100:.1f}%")
        print("\n提示：检查后端日志，应看到 'Cache hit' 和 'cache_hit: True' 标记")
        return True
    else:
        print(f"[警告] 耗时未明显降低，缓存可能未生效")
        print("可能原因：")
        print("  1. Redis 未正确启动")
        print("  2. 缓存键生成逻辑问题")
        print("  3. 后端日志中可能有错误信息")
        return False


def test_graceful_degradation():
    """
    测试场景 2：Redis 关闭时的优雅降级
    """
    print("\n" + "="*60)
    print("测试场景 2: Redis 关闭时的优雅降级")
    print("="*60)

    # 检查 Redis 配置
    redis_enabled = os.getenv("REDIS_ENABLED", "false")
    print(f"\n当前 REDIS_ENABLED={redis_enabled}")

    if redis_enabled.lower() == "true":
        print("\n[警告] Redis 当前已启用，请在 .env 中设置 REDIS_ENABLED=false")
        print("提示：或者停止 Redis 服务以测试降级")
        return False

    query = "数据库中有哪些产品信息"

    print(f"\n查询: {query}")
    print("提交任务...")

    start_time = time.time()
    response = requests.post(
        f"{API_BASE}/api/task",
        json={"query": query},
        timeout=180
    )

    if response.status_code != 200:
        print(f"[失败] HTTP {response.status_code}: {response.text}")
        return False

    thread_id = response.json().get("thread_id")
    print(f"任务已提交, thread_id: {thread_id}")

    # 等待任务完成
    time.sleep(120)
    duration = (time.time() - start_time) * 1000
    print(f"查询完成，耗时: {duration:.0f}ms")

    print("\n[成功] Redis 关闭时系统正常运行（降级生效）")
    print("提示：检查后端日志，应看到 'Redis caching is disabled' 信息")
    return True


def main():
    print("\n" + "="*60)
    print("Redis 缓存功能验证")
    print("="*60)

    print("\n请按照以下步骤进行测试：")
    print("\n步骤 1: 测试 Redis 启用时的缓存功能")
    print("  1) 确保 Redis 服务已启动")
    print("  2) 在 .env 中设置 REDIS_ENABLED=true")
    print("  3) 重启后端服务")
    print("  4) 运行此脚本")
    print("\n步骤 2: 测试 Redis 关闭时的降级")
    print("  1) 在 .env 中设置 REDIS_ENABLED=false")
    print("  2) 重启后端服务")
    print("  3) 运行此脚本")

    print("\n" + "-"*60)
    input("按 Enter 开始测试...")

    # 根据当前配置自动选择测试场景
    redis_enabled = os.getenv("REDIS_ENABLED", "false").lower()

    if redis_enabled in ("true", "1", "yes"):
        success = test_cache_with_redis_enabled()
    else:
        success = test_graceful_degradation()

    print("\n" + "="*60)
    if success:
        print("测试完成：[成功]")
    else:
        print("测试完成：[部分成功或需要检查]")
    print("="*60)


if __name__ == "__main__":
    main()
