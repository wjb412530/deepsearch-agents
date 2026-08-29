"""
向端口8001提交测试任务并验证持久化
"""
import sys
import requests
import time

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = "http://localhost:8001/api/task"
data = {
    "query": "测试任务",
    "thread_id": "persistence_test_final"
}

print("提交任务到端口8001...")
response = requests.post(url, json=data)
print(f"状态码: {response.status_code}")
print(f"响应: {response.json()}")

print("\n等待30秒让任务执行...")
time.sleep(30)
print("等待完成，可以检查数据库")
