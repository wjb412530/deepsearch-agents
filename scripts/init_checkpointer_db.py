"""
初始化 AsyncSqliteSaver 数据库表结构
"""
import asyncio
from pathlib import Path
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async def init_db():
    db_path = Path(__file__).parent.parent / "app" / "data" / "checkpoints.db"

    print(f"初始化数据库: {db_path}")

    # from_conn_string 返回异步上下文管理器
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        # AsyncSqliteSaver 的 setup 也是异步方法
        await checkpointer.setup()

    print("数据库表结构初始化完成")

if __name__ == "__main__":
    asyncio.run(init_db())
