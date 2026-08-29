"""
安全验证工具模块

提供 SQL 注入防护、查询限制和文件上传验证功能
"""

import os
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def validate_sql_query(sql: str) -> Tuple[bool, str]:
    """
    验证 SQL 查询的安全性

    安全策略：
    1. 仅允许 SELECT 和 SHOW 语句
    2. 拒绝危险操作：DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE, REPLACE
    3. 拒绝注释注入：-- 和 /* */
    4. 拒绝多语句执行：分号分隔

    Args:
        sql: 待验证的 SQL 语句

    Returns:
        (is_valid, error_message)
        - is_valid: True 表示安全，False 表示危险
        - error_message: 不安全时的错误提示
    """
    if not sql or not sql.strip():
        return False, "SQL 语句不能为空"

    sql_upper = sql.strip().upper()

    # 1. 仅允许 SELECT 和 SHOW 开头的语句
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("SHOW")):
        return False, "仅允许 SELECT 和 SHOW 查询语句"

    # 2. 检查危险关键字（即使在子查询中也要拦截）
    dangerous_keywords = [
        r"\bDROP\b",
        r"\bDELETE\b",
        r"\bUPDATE\b",
        r"\bINSERT\b",
        r"\bALTER\b",
        r"\bCREATE\b",
        r"\bTRUNCATE\b",
        r"\bREPLACE\b",
        r"\bEXEC\b",
        r"\bEXECUTE\b",
    ]

    for keyword in dangerous_keywords:
        if re.search(keyword, sql_upper):
            matched = re.search(keyword, sql_upper).group()
            return False, f"拒绝执行包含危险操作的 SQL: {matched}"

    # 3. 检查 SQL 注释注入
    if "--" in sql:
        return False, "SQL 语句不能包含注释符号 '--'"

    if "/*" in sql or "*/" in sql:
        return False, "SQL 语句不能包含注释符号 '/* */'"

    # 4. 检查多语句注入（简单检查分号）
    # 注意：这里只是基础检查，复杂场景可能需要 SQL 解析器
    semicolon_count = sql.count(";")
    if semicolon_count > 1:
        return False, "不允许执行多条 SQL 语句"

    # 允许末尾有一个分号
    if semicolon_count == 1 and not sql.strip().endswith(";"):
        return False, "检测到可疑的分号位置"

    return True, ""


def limit_sql_rows(sql: str, max_rows: int = 100) -> str:
    """
    为 SQL 查询自动添加 LIMIT 子句限制返回行数

    策略：
    1. 如果 SQL 已包含 LIMIT，检查是否超过 max_rows
    2. 如果未包含 LIMIT，自动添加
    3. 确保 LIMIT 不会被注入绕过

    Args:
        sql: 原始 SQL 语句
        max_rows: 最大返回行数（默认 100）

    Returns:
        添加/修正 LIMIT 后的 SQL 语句
    """
    sql_upper = sql.strip().upper()

    # 移除末尾的分号（如果有）
    sql_clean = sql.strip().rstrip(";")

    # 检查是否已有 LIMIT
    limit_match = re.search(r"\bLIMIT\s+(\d+)", sql_upper)

    if limit_match:
        # 已有 LIMIT，检查是否超过限制
        existing_limit = int(limit_match.group(1))
        if existing_limit > max_rows:
            logger.warning(f"SQL LIMIT {existing_limit} 超过最大限制 {max_rows}，已自动调整")
            # 替换为最大限制
            sql_clean = re.sub(
                r"\bLIMIT\s+\d+",
                f"LIMIT {max_rows}",
                sql_clean,
                flags=re.IGNORECASE
            )
    else:
        # 未有 LIMIT，自动添加
        sql_clean = f"{sql_clean} LIMIT {max_rows}"

    return sql_clean


def validate_table_name(table_name: str, allowed_tables: Optional[str] = None) -> Tuple[bool, str]:
    """
    验证表名是否在白名单中

    Args:
        table_name: 待验证的表名
        allowed_tables: 允许的表名白名单（逗号分隔字符串），None 或空字符串表示不限制

    Returns:
        (is_valid, error_message)
    """
    if not table_name or not table_name.strip():
        return False, "表名不能为空"

    # 检查表名格式（防止 SQL 注入）
    # 仅允许字母、数字、下划线
    if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
        return False, f"表名 '{table_name}' 包含非法字符，仅允许字母、数字、下划线"

    # 如果未配置白名单，则不限制
    if not allowed_tables or not allowed_tables.strip():
        return True, ""

    # 解析白名单
    allowed_list = [t.strip() for t in allowed_tables.split(",") if t.strip()]

    if table_name not in allowed_list:
        return False, f"表名 '{table_name}' 不在白名单中，允许的表：{', '.join(allowed_list)}"

    return True, ""


def validate_file_upload(filename: str, size_mb: float, max_size_mb: int = 20,
                        allowed_extensions: Optional[str] = None) -> Tuple[bool, str]:
    """
    验证上传文件的安全性

    Args:
        filename: 文件名
        size_mb: 文件大小（MB）
        max_size_mb: 最大允许大小（MB），默认 20
        allowed_extensions: 允许的扩展名白名单（逗号分隔），None 表示不限制

    Returns:
        (is_valid, error_message)
    """
    if not filename or not filename.strip():
        return False, "文件名不能为空"

    # 1. 检查文件大小
    if size_mb > max_size_mb:
        return False, f"文件大小 {size_mb:.2f}MB 超过限制 {max_size_mb}MB"

    # 2. 检查文件扩展名
    if allowed_extensions:
        # 获取文件扩展名（含点号，如 .txt）
        file_ext = ""
        if "." in filename:
            file_ext = "." + filename.rsplit(".", 1)[-1].lower()

        # 解析白名单
        allowed_list = [ext.strip().lower() for ext in allowed_extensions.split(",") if ext.strip()]

        # 确保白名单中的扩展名都带点号
        allowed_list = [ext if ext.startswith(".") else f".{ext}" for ext in allowed_list]

        if file_ext not in allowed_list:
            return False, f"文件扩展名 '{file_ext}' 不允许上传，允许的扩展名：{', '.join(allowed_list)}"

    # 3. 检查文件名中的危险字符
    dangerous_chars = ["../", "..\\", "<", ">", "|", ":", "*", "?", '"']
    for char in dangerous_chars:
        if char in filename:
            return False, f"文件名包含非法字符: {char}"

    return True, ""


# 从环境变量读取安全配置
def get_security_config():
    """
    从环境变量读取安全配置

    Returns:
        dict: 安全配置字典
    """
    return {
        "allowed_tables": os.getenv("ALLOWED_SQL_TABLES", ""),
        "sql_timeout": int(os.getenv("SQL_QUERY_TIMEOUT", "5")),
        "sql_max_rows": int(os.getenv("SQL_MAX_ROWS", "100")),
        "max_upload_mb": int(os.getenv("MAX_UPLOAD_MB", "20")),
        "allowed_extensions": os.getenv("ALLOWED_FILE_EXTENSIONS", ".txt,.md,.pdf,.docx,.xlsx,.csv"),
    }
