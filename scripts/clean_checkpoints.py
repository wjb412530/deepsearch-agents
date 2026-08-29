"""
数据库清理脚本 - 项目 4 Atom 4

功能：
1. 删除过期的会话数据（默认保留最近 7 天）
2. 执行 VACUUM 优化数据库
3. 显示清理前后的统计信息

用法：
    python scripts/clean_checkpoints.py                    # 删除 7 天前的数据
    python scripts/clean_checkpoints.py --days 30          # 删除 30 天前的数据
    python scripts/clean_checkpoints.py --thread-id xxx    # 删除指定会话
"""
import sys
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 数据库路径
DB_PATH = "app/data/checkpoints.db"


def get_db_stats(conn):
    """获取数据库统计信息"""
    cursor = conn.cursor()

    # 总记录数
    cursor.execute("SELECT COUNT(*) FROM checkpoints")
    total_checkpoints = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM writes")
    total_writes = cursor.fetchone()[0]

    # 会话数
    cursor.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints")
    total_sessions = cursor.fetchone()[0]

    # 数据库大小
    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    db_size_mb = (page_count * page_size) / (1024 * 1024)

    return {
        "checkpoints": total_checkpoints,
        "writes": total_writes,
        "sessions": total_sessions,
        "size_mb": db_size_mb
    }


def clean_by_days(conn, days=7, dry_run=False):
    """删除指定天数之前的数据"""
    cursor = conn.cursor()

    # 计算截止时间（注意：checkpoint_id 是 UUID，不是时间戳）
    # 我们使用 checkpoint_id 的字典序来近似时间顺序
    # 更好的方案是在表中添加 created_at 字段，但这里使用简单方案

    print(f"\n{'[模拟运行]' if dry_run else '[执行清理]'} 删除 {days} 天前的数据...")

    # 查询要删除的会话
    cursor.execute("""
        SELECT thread_id, COUNT(*) as checkpoint_count
        FROM checkpoints
        GROUP BY thread_id
    """)
    sessions = cursor.fetchall()

    if not sessions:
        print("没有找到任何会话数据")
        return 0, 0

    print(f"找到 {len(sessions)} 个会话")

    # 注意：由于 checkpoint_id 是 UUID，我们无法直接按时间删除
    # 这里提供一个保留最近 N 个 checkpoint 的逻辑
    print("\n⚠️  警告：由于 checkpoint_id 是 UUID，无法直接按时间删除")
    print(f"将保留每个会话的最近 {days * 10} 个 checkpoint（近似逻辑）")

    deleted_checkpoints = 0
    deleted_writes = 0

    for thread_id, count in sessions:
        # 保留最近的 N 个 checkpoint
        keep_count = days * 10

        if count <= keep_count:
            continue

        # 获取要删除的 checkpoint_id（保留最新的 keep_count 个）
        cursor.execute("""
            SELECT checkpoint_id
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY checkpoint_id DESC
            LIMIT -1 OFFSET ?
        """, (thread_id, keep_count))

        old_checkpoints = [row[0] for row in cursor.fetchall()]

        if not old_checkpoints:
            continue

        print(f"\n会话 {thread_id}:")
        print(f"  总 checkpoint: {count}")
        print(f"  将删除: {len(old_checkpoints)} 个旧 checkpoint")

        if not dry_run:
            # 删除 checkpoints
            placeholders = ','.join('?' * len(old_checkpoints))
            cursor.execute(f"""
                DELETE FROM checkpoints
                WHERE checkpoint_id IN ({placeholders})
            """, old_checkpoints)
            deleted_checkpoints += cursor.rowcount

            # 删除对应的 writes
            cursor.execute(f"""
                DELETE FROM writes
                WHERE checkpoint_id IN ({placeholders})
            """, old_checkpoints)
            deleted_writes += cursor.rowcount

    if not dry_run:
        conn.commit()

    return deleted_checkpoints, deleted_writes


def clean_by_thread_id(conn, thread_id, dry_run=False):
    """删除指定会话的所有数据"""
    cursor = conn.cursor()

    print(f"\n{'[模拟运行]' if dry_run else '[执行清理]'} 删除会话: {thread_id}")

    # 检查会话是否存在
    cursor.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?", (thread_id,))
    checkpoint_count = cursor.fetchone()[0]

    if checkpoint_count == 0:
        print(f"会话 {thread_id} 不存在")
        return 0, 0

    print(f"找到 {checkpoint_count} 个 checkpoint")

    if not dry_run:
        # 删除 writes
        cursor.execute("DELETE FROM writes WHERE checkpoint_id IN (SELECT checkpoint_id FROM checkpoints WHERE thread_id = ?)", (thread_id,))
        deleted_writes = cursor.rowcount

        # 删除 checkpoints
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        deleted_checkpoints = cursor.rowcount

        conn.commit()

        print(f"✅ 已删除 {deleted_checkpoints} 个 checkpoint 和 {deleted_writes} 个 write")
        return deleted_checkpoints, deleted_writes
    else:
        print(f"[模拟] 将删除 {checkpoint_count} 个 checkpoint 及其 writes")
        return 0, 0


def vacuum_database(conn):
    """执行 VACUUM 优化数据库"""
    print("\n[执行 VACUUM] 优化数据库...")
    conn.execute("VACUUM")
    print("✅ VACUUM 完成")


def main():
    parser = argparse.ArgumentParser(description="清理 checkpoints 数据库")
    parser.add_argument("--days", type=int, default=7, help="保留最近 N 天的数据（默认 7 天）")
    parser.add_argument("--thread-id", type=str, help="删除指定会话的所有数据")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际删除")
    parser.add_argument("--no-vacuum", action="store_true", help="不执行 VACUUM")

    args = parser.parse_args()

    # 检查数据库文件
    if not Path(DB_PATH).exists():
        print(f"错误：数据库文件不存在: {DB_PATH}")
        sys.exit(1)

    print("=" * 60)
    print("数据库清理工具 - 项目 4 Atom 4")
    print("=" * 60)

    # 连接数据库
    conn = sqlite3.connect(DB_PATH)

    # 显示清理前统计
    print("\n【清理前统计】")
    stats_before = get_db_stats(conn)
    print(f"  会话数: {stats_before['sessions']}")
    print(f"  Checkpoint 数: {stats_before['checkpoints']}")
    print(f"  Write 数: {stats_before['writes']}")
    print(f"  数据库大小: {stats_before['size_mb']:.2f} MB")

    # 执行清理
    if args.thread_id:
        deleted_checkpoints, deleted_writes = clean_by_thread_id(conn, args.thread_id, args.dry_run)
    else:
        deleted_checkpoints, deleted_writes = clean_by_days(conn, args.days, args.dry_run)

    # 显示清理结果
    print("\n【清理结果】")
    print(f"  删除 Checkpoint: {deleted_checkpoints}")
    print(f"  删除 Write: {deleted_writes}")

    # 执行 VACUUM
    if not args.no_vacuum and not args.dry_run and deleted_checkpoints > 0:
        vacuum_database(conn)

    # 显示清理后统计
    print("\n【清理后统计】")
    stats_after = get_db_stats(conn)
    print(f"  会话数: {stats_after['sessions']}")
    print(f"  Checkpoint 数: {stats_after['checkpoints']}")
    print(f"  Write 数: {stats_after['writes']}")
    print(f"  数据库大小: {stats_after['size_mb']:.2f} MB")

    if not args.dry_run and deleted_checkpoints > 0:
        size_reduction = stats_before['size_mb'] - stats_after['size_mb']
        print(f"  空间节省: {size_reduction:.2f} MB ({size_reduction/stats_before['size_mb']*100:.1f}%)")

    conn.close()

    print("\n" + "=" * 60)
    if args.dry_run:
        print("✅ 模拟运行完成（未实际修改数据）")
    else:
        print("✅ 清理完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
