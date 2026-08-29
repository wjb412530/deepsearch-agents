"""
安全防护验证测试脚本

测试项目 2 的三大安全功能：
1. SQL 注入防护 - 验证危险 SQL 被拦截
2. 文件上传防护 - 验证超大文件和非法扩展名被拦截
3. 合法操作回归测试 - 验证正常功能不受影响
"""

import os
import sys
import tempfile
from pathlib import Path

# Windows 控制台编码问题修复
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.safety import (
    validate_sql_query,
    limit_sql_rows,
    validate_table_name,
    validate_file_upload,
    get_security_config,
)


def test_sql_injection_protection():
    """测试场景 1: SQL 注入防护"""
    print("\n" + "="*60)
    print("测试场景 1: SQL 注入防护")
    print("="*60)

    # 危险 SQL 测试用例
    dangerous_sqls = [
        ("DROP TABLE users", "DROP TABLE 攻击"),
        ("SELECT * FROM users; DELETE FROM users", "多语句注入"),
        ("SELECT * FROM users WHERE id=1--", "注释注入 --"),
        ("SELECT * FROM users /* comment */ WHERE 1=1", "注释注入 /* */"),
        ("UPDATE users SET password='hacked'", "UPDATE 操作"),
        ("DELETE FROM users WHERE 1=1", "DELETE 操作"),
        ("INSERT INTO users VALUES (1, 'hacker')", "INSERT 操作"),
        ("ALTER TABLE users ADD COLUMN hacked INT", "ALTER 操作"),
        ("CREATE TABLE hacked (id INT)", "CREATE 操作"),
        ("TRUNCATE TABLE users", "TRUNCATE 操作"),
    ]

    passed = 0
    failed = 0

    for sql, description in dangerous_sqls:
        is_valid, error_msg = validate_sql_query(sql)
        if not is_valid:
            print(f"✅ [{description}] 成功拦截: {error_msg}")
            passed += 1
        else:
            print(f"❌ [{description}] 拦截失败！危险 SQL 通过了验证")
            failed += 1

    # 合法 SQL 测试用例
    safe_sqls = [
        ("SELECT * FROM users", "基本 SELECT"),
        ("SELECT id, name FROM users WHERE age > 18", "带 WHERE 的 SELECT"),
        ("SELECT * FROM users LIMIT 10", "带 LIMIT 的 SELECT"),
        ("SHOW TABLES", "SHOW TABLES"),
        ("SELECT COUNT(*) FROM users", "聚合查询"),
    ]

    for sql, description in safe_sqls:
        is_valid, error_msg = validate_sql_query(sql)
        if is_valid:
            print(f"✅ [{description}] 正确通过")
            passed += 1
        else:
            print(f"❌ [{description}] 错误拦截！合法 SQL 被拒绝: {error_msg}")
            failed += 1

    print(f"\n📊 SQL 注入防护测试: {passed} 通过, {failed} 失败")
    return failed == 0


def test_sql_row_limit():
    """测试场景 1.1: SQL 行数限制"""
    print("\n" + "="*60)
    print("测试场景 1.1: SQL 行数自动限制")
    print("="*60)

    test_cases = [
        ("SELECT * FROM users", "SELECT * FROM users LIMIT 100", "无 LIMIT 自动添加"),
        ("SELECT * FROM users LIMIT 50", "SELECT * FROM users LIMIT 50", "LIMIT 50 保持不变"),
        ("SELECT * FROM users LIMIT 200", "SELECT * FROM users LIMIT 100", "LIMIT 200 自动调整为 100"),
        ("SELECT * FROM users;", "SELECT * FROM users LIMIT 100", "移除末尾分号并添加 LIMIT"),
    ]

    passed = 0
    failed = 0

    for input_sql, expected_output, description in test_cases:
        result = limit_sql_rows(input_sql, max_rows=100)
        if result == expected_output:
            print(f"✅ [{description}] 正确处理")
            passed += 1
        else:
            print(f"❌ [{description}] 处理错误")
            print(f"   期望: {expected_output}")
            print(f"   实际: {result}")
            failed += 1

    print(f"\n📊 SQL 行数限制测试: {passed} 通过, {failed} 失败")
    return failed == 0


def test_table_name_validation():
    """测试场景 1.2: 表名白名单验证"""
    print("\n" + "="*60)
    print("测试场景 1.2: 表名白名单验证")
    print("="*60)

    # 格式检查测试
    format_cases = [
        ("users", None, True, "合法表名"),
        ("user_profile", None, True, "带下划线的表名"),
        ("table123", None, True, "带数字的表名"),
        ("users; DROP TABLE", None, False, "包含分号的表名"),
        ("../etc/passwd", None, False, "路径穿越表名"),
        ("users--", None, False, "包含注释符的表名"),
    ]

    passed = 0
    failed = 0

    for table_name, allowed_tables, should_pass, description in format_cases:
        is_valid, error_msg = validate_table_name(table_name, allowed_tables)
        if (is_valid and should_pass) or (not is_valid and not should_pass):
            status = "通过" if should_pass else "拦截"
            print(f"✅ [{description}] 正确{status}")
            passed += 1
        else:
            print(f"❌ [{description}] 验证错误: {error_msg}")
            failed += 1

    # 白名单检查测试
    whitelist_cases = [
        ("users", "users,posts,comments", True, "表名在白名单中"),
        ("admin", "users,posts,comments", False, "表名不在白名单中"),
        ("posts", " users , posts , comments ", True, "白名单带空格"),
    ]

    for table_name, allowed_tables, should_pass, description in whitelist_cases:
        is_valid, error_msg = validate_table_name(table_name, allowed_tables)
        if (is_valid and should_pass) or (not is_valid and not should_pass):
            status = "通过" if should_pass else "拦截"
            print(f"✅ [{description}] 正确{status}")
            passed += 1
        else:
            print(f"❌ [{description}] 验证错误: {error_msg}")
            failed += 1

    print(f"\n📊 表名验证测试: {passed} 通过, {failed} 失败")
    return failed == 0


def test_file_upload_protection():
    """测试场景 2: 文件上传防护"""
    print("\n" + "="*60)
    print("测试场景 2: 文件上传防护")
    print("="*60)

    test_cases = [
        # (filename, size_mb, max_size_mb, allowed_extensions, should_pass, description)
        ("document.txt", 5, 20, ".txt,.pdf,.docx", True, "合法 TXT 文件"),
        ("report.pdf", 10, 20, ".txt,.pdf,.docx", True, "合法 PDF 文件"),
        ("data.xlsx", 15, 20, ".txt,.pdf,.docx,.xlsx", True, "合法 XLSX 文件"),
        ("largefile.txt", 25, 20, ".txt,.pdf,.docx", False, "文件超过大小限制"),
        ("malware.exe", 5, 20, ".txt,.pdf,.docx", False, "非法扩展名 .exe"),
        ("script.sh", 5, 20, ".txt,.pdf,.docx", False, "非法扩展名 .sh"),
        ("../etc/passwd", 5, 20, ".txt,.pdf,.docx", False, "路径穿越攻击"),
        ("hack<script>.txt", 5, 20, ".txt,.pdf,.docx", False, "文件名包含危险字符"),
    ]

    passed = 0
    failed = 0

    for filename, size_mb, max_size_mb, allowed_ext, should_pass, description in test_cases:
        is_valid, error_msg = validate_file_upload(filename, size_mb, max_size_mb, allowed_ext)
        if (is_valid and should_pass) or (not is_valid and not should_pass):
            status = "通过" if should_pass else "拦截"
            print(f"✅ [{description}] 正确{status}")
            passed += 1
        else:
            status = "通过" if is_valid else "拦截"
            print(f"❌ [{description}] 验证错误 (结果: {status})")
            if error_msg:
                print(f"   错误信息: {error_msg}")
            failed += 1

    print(f"\n📊 文件上传防护测试: {passed} 通过, {failed} 失败")
    return failed == 0


def test_security_config():
    """测试场景 3: 安全配置读取"""
    print("\n" + "="*60)
    print("测试场景 3: 安全配置读取")
    print("="*60)

    try:
        config = get_security_config()

        required_keys = [
            "allowed_tables",
            "sql_timeout",
            "sql_max_rows",
            "max_upload_mb",
            "allowed_extensions",
        ]

        passed = 0
        failed = 0

        for key in required_keys:
            if key in config:
                print(f"✅ 配置项 '{key}' 存在: {config[key]}")
                passed += 1
            else:
                print(f"❌ 配置项 '{key}' 缺失")
                failed += 1

        print(f"\n📊 配置读取测试: {passed} 通过, {failed} 失败")
        return failed == 0

    except Exception as e:
        print(f"❌ 配置读取失败: {e}")
        return False


def main():
    """主测试入口"""
    print("\n" + "="*70)
    print("项目 2: 安全防护功能验证测试")
    print("="*70)

    results = []

    # 执行所有测试
    results.append(("SQL 注入防护", test_sql_injection_protection()))
    results.append(("SQL 行数限制", test_sql_row_limit()))
    results.append(("表名白名单验证", test_table_name_validation()))
    results.append(("文件上传防护", test_file_upload_protection()))
    results.append(("安全配置读取", test_security_config()))

    # 汇总结果
    print("\n" + "="*70)
    print("测试汇总")
    print("="*70)

    total_passed = sum(1 for _, passed in results if passed)
    total_failed = len(results) - total_passed

    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name:25s} {status}")

    print("\n" + "="*70)
    print(f"总计: {total_passed}/{len(results)} 测试通过")
    print("="*70)

    if total_failed == 0:
        print("\n🎉 所有安全防护测试通过！项目 2 验证成功。")
        return 0
    else:
        print(f"\n⚠️  有 {total_failed} 个测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
