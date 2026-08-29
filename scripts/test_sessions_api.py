"""
测试会话列表 API (/api/sessions)

验证项目 4 - Atom 3: 会话列表查询功能
"""
import sys
import requests

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 服务地址
BASE_URL = "http://localhost:8001"

def test_sessions_list():
    """测试会话列表查询"""
    print("\n=== 测试 1: 查询会话列表 ===")

    try:
        response = requests.get(f"{BASE_URL}/api/sessions")

        if response.status_code == 200:
            data = response.json()

            if "error" in data:
                print(f"查询失败: {data['error']}")
                return False

            print(f"状态: {data.get('status')}")
            print(f"总会话数: {data.get('total')}")
            print("\n会话列表:")

            for session in data.get('sessions', []):
                print(f"  - thread_id: {session['thread_id']}")
                print(f"    checkpoint 数量: {session['checkpoint_count']}")
                print(f"    最后 checkpoint_id: {session['last_checkpoint_id']}")
                print()

            return True
        else:
            print(f"HTTP 错误: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"请求失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试会话列表 API...")
    success = test_sessions_list()

    if success:
        print("\n✅ 会话列表 API 测试通过")
    else:
        print("\n❌ 会话列表 API 测试失败")
