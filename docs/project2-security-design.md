# 项目 2：安全防护 - 设计简要

## 核心功能

1. **SQL 注入防护** - 限制危险 SQL 操作，仅允许 SELECT/SHOW 查询
2. **SQL 查询限制** - 超时控制、结果行数限制、表名白名单
3. **文件上传防护** - 文件大小限制、扩展名白名单

## 主要文件

- `app/utils/safety.py` - 新建安全验证工具模块
- `app/tools/db_tools.py` - 改造 3 个 SQL 工具函数
- `app/api/server.py` - 改造 `/api/upload` 端点
- `.env.example` - 添加安全配置项

## 技术选型

- **SQL 防护策略**: 正则表达式检查 + SELECT/SHOW 白名单
- **超时控制**: `mysql.connector` 的 `connection_timeout` 参数
- **行数限制**: 自动改写 SQL 添加 `LIMIT` 子句
- **文件验证**: FastAPI 的 `File` 大小限制 + 扩展名白名单

## 风险评估

- **兼容性风险**: 限制 SELECT/SHOW 后，现有合法查询需要回归测试
- **性能影响**: 正则检查和 SQL 改写对单次查询增加 <5ms 开销
- **功能限制**: 白名单模式可能误杀复杂但合法的 SQL（通过环境变量可关闭白名单）

## 新增环境变量

```bash
# SQL 安全配置
ALLOWED_SQL_TABLES=         # 表名白名单（逗号分隔），空则不限制
SQL_QUERY_TIMEOUT=5         # 查询超时秒数
SQL_MAX_ROWS=100            # 单次查询最大返回行数

# 文件上传配置
MAX_UPLOAD_MB=20            # 单文件最大 MB 数
ALLOWED_FILE_EXTENSIONS=.txt,.md,.pdf,.docx,.xlsx,.csv  # 允许的扩展名
```

## 原子任务分解

### Atom 1: 安全工具模块 (`app/utils/safety.py`)
- 创建 `validate_sql_query(sql)` - SQL 安全检查
- 创建 `limit_sql_rows(sql, max_rows)` - 自动添加 LIMIT
- 创建 `validate_table_name(table, allowed)` - 表名白名单检查
- 创建 `validate_file_upload(filename, size_mb)` - 文件验证
- **验证方式**: 单元测试各函数，确认危险 SQL 被拦截

### Atom 2: 数据库工具改造 (`app/tools/db_tools.py`)
- 修改 `get_db_config()` 添加超时参数
- 修改 `get_table_data()` 添加表名白名单检查
- 修改 `execute_sql_query()` 添加 SQL 安全检查 + 行数限制
- **验证方式**: 提交危险 SQL 查询，确认被拦截；提交合法查询，确认正常通过

### Atom 3: 文件上传改造 (`app/api/server.py`)
- 修改 `/api/upload` 端点添加文件大小检查
- 添加文件扩展名白名单验证
- **验证方式**: 上传超大文件和非法扩展名文件，确认被拒绝

### Atom 4: 环境变量配置 (`.env.example`)
- 添加 5 个新环境变量及注释
- **验证方式**: 检查文件内容格式正确

### Atom 5: 验证测试脚本 (`scripts/test_security.py`)
- 创建自动化测试脚本
- 测试场景 1: 危险 SQL 拦截
- 测试场景 2: 超大文件上传拦截
- 测试场景 3: 合法操作回归测试
- **验证方式**: 运行脚本，所有测试通过

## 回滚方案

- 设置 `ALLOWED_SQL_TABLES=` (空值) 关闭表名白名单
- SELECT/SHOW 限制是最低安全基线，不可关闭
- 文件大小限制可通过调大 `MAX_UPLOAD_MB` 放宽

## 验证标准

- ✅ `DROP TABLE` / `DELETE` / `UPDATE` 被拦截
- ✅ `SELECT * FROM users` 正常执行
- ✅ 上传 21MB 文件被拒绝（MAX_UPLOAD_MB=20）
- ✅ 上传 `.exe` 文件被拒绝
- ✅ 上传 `.txt` 文件成功
- ✅ 现有 baseline 测试仍然通过（回归测试）
