"""
杀掉占用8001端口的所有进程
"""
import subprocess
import re

# 查找占用8001端口的进程
result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
lines = result.stdout.split('\n')

pids = set()
for line in lines:
    if ':8001' in line and 'LISTENING' in line:
        parts = line.split()
        if parts:
            pid = parts[-1]
            if pid.isdigit():
                pids.add(pid)

print(f"找到 {len(pids)} 个进程占用端口8001")

for pid in pids:
    try:
        subprocess.run(['taskkill', '/F', '/PID', pid], check=True, capture_output=True)
        print(f"已杀掉进程 {pid}")
    except:
        print(f"无法杀掉进程 {pid}")

print("清理完成")
