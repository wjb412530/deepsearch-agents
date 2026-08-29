"""
提交测试任务验证 AsyncSqliteSaver 持久化
"""
import sys
import requests
import time

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 提交任务
url = "http://localhost:8000/api/task"
data = {
    "query": "简单测试任务",
    "thread_id": "final_test_001"
}

print("=" * 60)
print("提交测试任务...")
print("=" * 60)

response = requests.post(url, json=data)
print(f"响应状态码: {response.status_code}")
print(f"响应内容: {response.json()}")

# 等待任务执行
print("\n等待 20 秒让任务完整执行...")
time.sleep(20)

print("\n任务提交成功，请查看数据库验证持久化")
