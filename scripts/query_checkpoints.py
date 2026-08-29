"""
查询 checkpoints.db 数据库中的记录数量
"""
import sys
import sqlite3

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

db_path = "app/data/checkpoints.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查询 checkpoints 表
    cursor.execute("SELECT COUNT(*) FROM checkpoints")
    checkpoint_count = cursor.fetchone()[0]
    print(f"checkpoints 表记录数: {checkpoint_count}")

    # 查询 writes 表
    cursor.execute("SELECT COUNT(*) FROM writes")
    writes_count = cursor.fetchone()[0]
    print(f"writes 表记录数: {writes_count}")

    # 查看最新的几条 checkpoint 记录
    if checkpoint_count > 0:
        print("\n最近的 checkpoint 记录:")
        cursor.execute("SELECT thread_id, checkpoint_ns, checkpoint_id FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 5")
        for row in cursor.fetchall():
            print(f"  thread_id={row[0]}, checkpoint_ns={row[1]}, checkpoint_id={row[2]}")

    conn.close()
    print("\n数据库查询完成")

except Exception as e:
    print(f"查询失败: {e}")
