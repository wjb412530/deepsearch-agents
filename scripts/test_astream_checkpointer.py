"""
测试 astream 模式下 SqliteSaver checkpointer 是否正常工作
"""
import sys
import os
import asyncio
import sqlite3
from pathlib import Path

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import find_dotenv, load_dotenv
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver
from deepagents import create_deep_agent

load_dotenv(find_dotenv())

llm = init_chat_model(
    model=os.getenv("LLM_QWEN_MAX"),
    model_provider="openai",
)

@tool
def test_tool(query: str):
    """测试工具，返回查询结果"""
    print(f"调用 test_tool，查询: {query}")
    return f"查询结果: {query}"

# 创建测试用的 SqliteSaver
db_path = Path(__file__).parent.parent / "app" / "data" / "test_astream_checkpoints.db"
if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
checkpointer = SqliteSaver(conn)
checkpointer.setup()

print("=" * 60)
print("开始测试 astream 模式下的 SqliteSaver checkpointer")
print("=" * 60)

# 创建带 checkpointer 的 agent
test_agent = create_deep_agent(
    model=llm,
    tools=[test_tool],
    checkpointer=checkpointer,
    system_prompt="你是一个测试助手，使用工具回答用户问题",
)

async def test_astream():
    thread_config = {
        "configurable": {
            "thread_id": "astream_test_001",
        }
    }

    print("\n使用 astream 执行任务...")
    async for chunk in test_agent.astream(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "帮我查询天气信息",
                }
            ]
        },
        config=thread_config,
    ):
        # 模拟实际应用中的处理
        for node_name, state in chunk.items():
            if state and "messages" in state:
                messages = state["messages"]
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'content') and last_msg.content:
                        print(f"[{node_name}] {last_msg.content[:50]}...")

    print("\nastream 执行完成")

    # 检查数据库
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM checkpoints")
    checkpoint_count = cursor.fetchone()[0]
    print(f"\n数据库检查: checkpoints 表记录数 = {checkpoint_count}")

    cursor.execute("SELECT COUNT(*) FROM writes")
    writes_count = cursor.fetchone()[0]
    print(f"数据库检查: writes 表记录数 = {writes_count}")

    if checkpoint_count > 0:
        print("\n成功！astream 模式下 SqliteSaver 正常工作，数据已持久化")
        cursor.execute("SELECT thread_id, checkpoint_ns FROM checkpoints LIMIT 5")
        print("\n前5条 checkpoint 记录:")
        for row in cursor.fetchall():
            print(f"  thread_id: {row[0]}, namespace: {row[1]}")
    else:
        print("\n失败！astream 模式下 SqliteSaver 没有保存任何数据")

# 运行异步测试
asyncio.run(test_astream())

conn.close()
print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
