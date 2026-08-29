"""
查看 checkpoints.db 数据库内容的辅助脚本
"""
import sqlite3
import sys
from pathlib import Path

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

db_path = Path(__file__).parent.parent / "app" / "data" / "checkpoints.db"

if not db_path.exists():
    print(f"Database file not found: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("=" * 60)
print("Checkpoints Database Statistics")
print("=" * 60)

# 查看表结构
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"\nTables: {tables}")

# 查看 checkpoints 表
cursor.execute("SELECT COUNT(*) FROM checkpoints")
checkpoint_count = cursor.fetchone()[0]
print(f"\nCheckpoints table records: {checkpoint_count}")

if checkpoint_count > 0:
    cursor.execute("SELECT thread_id, checkpoint_ns, checkpoint_id FROM checkpoints LIMIT 10")
    print("\nRecent checkpoints:")
    print("-" * 60)
    for row in cursor.fetchall():
        print(f"  thread_id: {row[0]}")
        print(f"  namespace: {row[1]}")
        print(f"  checkpoint_id: {row[2]}")
        print("-" * 60)

# 查看 writes 表
cursor.execute("SELECT COUNT(*) FROM writes")
writes_count = cursor.fetchone()[0]
print(f"\nWrites table records: {writes_count}")

conn.close()

print("\n" + "=" * 60)
print("Query completed")
print("=" * 60)
