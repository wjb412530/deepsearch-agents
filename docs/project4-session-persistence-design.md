# 项目 4：会话持久化与断点恢复 - 设计简要

## 核心功能

1. **持久化 Checkpointer** - 将 InMemorySaver 替换为 SqliteSaver，实现会话状态持久化
2. **断点恢复** - 任务中断后可以从上次检查点继续执行
3. **会话历史查询** - 提供 API 查询历史会话列表和详情

## 当前架构分析

### 现有实现 (InMemorySaver)
- **位置**: `app/agent/main_agent.py:41` - `checkpointer=InMemorySaver()`
- **特点**: 
  - 会话状态存储在内存中
  - 服务重启后会话丢失
  - 无法实现真正的断点恢复
  - 性能好，但不适合生产环境

### 会话标识机制
- **thread_id**: 每个任务的唯一标识 (UUID)
- **ContextVar**: 协程级上下文变量，传递 thread_id 和 session_dir
- **active_tasks**: 字典存储活跃的 asyncio.Task

### 会话生命周期
```
用户提交任务 (/api/task)
  → 生成 thread_id
  → 创建 session_dir (output/session_{thread_id})
  → 创建后台 asyncio.Task
  → Agent 执行 (checkpointer 自动保存状态)
  → 任务完成/取消
  → 从 active_tasks 移除
```

## 技术方案

### 1. Checkpointer 升级
- **从**: `InMemorySaver()` 
- **到**: `SqliteSaver.from_conn_string("checkpoints.db")`
- **优势**: 
  - 自动持久化到 SQLite
  - 重启后会话状态保留
  - 支持多进程共享(可选)

### 2. 数据库文件位置
```
deepsearch-agents/
  app/
    data/
      checkpoints.db       # SQLite 数据库文件
      checkpoints.db-shm   # SQLite 共享内存文件
      checkpoints.db-wal   # SQLite 预写日志文件
```

### 3. 新增 API 端点

#### 3.1 查询会话列表
```
GET /api/sessions
返回: { "sessions": [{ "thread_id": "...", "created_at": "...", "status": "..." }] }
```

#### 3.2 恢复会话
```
POST /api/task/resume
请求: { "thread_id": "xxx", "query": "继续上次的任务" }
返回: { "status": "resumed", "thread_id": "xxx" }
```

#### 3.3 查询会话详情
```
GET /api/sessions/{thread_id}
返回: { "thread_id": "...", "messages": [...], "status": "..." }
```

### 4. 数据库清理策略
- **定期清理**: 清理 30 天前的会话
- **手动清理**: 提供 API 删除指定会话
- **自动清理**: 启动时清理过期会话

## 主要文件

### 新增文件
- `app/data/checkpoints.db` - SQLite 数据库文件 (自动生成)
- `app/utils/checkpoint.py` - Checkpointer 管理工具 (可选)
- `scripts/clean_checkpoints.py` - 数据库清理脚本 (可选)

### 修改文件
- `app/agent/main_agent.py` - 替换 checkpointer
- `app/api/server.py` - 添加会话管理 API
- `.env.example` - 添加持久化配置项
- `.gitignore` - 排除数据库文件

## 原子任务分解

### Atom 1: 升级 Checkpointer (核心)
**目标**: 将 InMemorySaver 替换为 SqliteSaver

**文件**:
- `app/agent/main_agent.py` - 修改 checkpointer 初始化
- `app/data/` - 创建数据目录

**步骤**:
1. 导入 SqliteSaver: `from langgraph.checkpoint.sqlite import SqliteSaver`
2. 创建数据目录: `app/data/`
3. 替换 checkpointer: `checkpointer=SqliteSaver.from_conn_string("app/data/checkpoints.db")`
4. 添加 .gitignore 规则排除数据库文件

**验证**:
- 提交任务，检查是否生成 `app/data/checkpoints.db`
- 重启服务，使用相同 thread_id 提交新消息，验证上下文是否保留
- 检查数据库文件大小合理

**用户验证步骤**:
1. 启动服务
2. 提交任务: "查询 AI 新闻"
3. 等待任务完成
4. 检查 `app/data/checkpoints.db` 文件是否存在
5. 重启服务
6. 使用相同 thread_id 提交新任务: "继续总结刚才的结果"
7. 验证 Agent 是否能记住之前的上下文

---

### Atom 2: 会话列表查询 API (增强)
**目标**: 提供 API 查询所有历史会话

**文件**:
- `app/api/server.py` - 添加 `/api/sessions` 端点

**步骤**:
1. 创建端点 `/api/sessions`
2. 读取 SqliteSaver 中的 checkpoint 记录
3. 返回 thread_id 列表和元数据

**验证**:
- 调用 API，返回会话列表
- 检查返回数据格式正确

**用户验证步骤**:
1. 提交 2-3 个不同的任务(不同 thread_id)
2. 访问 `http://localhost:8000/api/sessions`
3. 验证返回的会话列表包含所有 thread_id

---

### Atom 3: 会话恢复功能 (核心)
**目标**: 支持使用已存在的 thread_id 继续对话

**文件**:
- `app/api/server.py` - 修改 `/api/task` 端点逻辑

**步骤**:
1. 检查 thread_id 是否已存在于 checkpointer
2. 如果存在，使用原有上下文继续执行
3. 如果不存在，创建新会话

**验证**:
- 提交任务 A (thread_id_1)
- 提交任务 B (thread_id_1)，验证 B 能看到 A 的上下文

**用户验证步骤**:
1. 提交任务: thread_id="test-001", query="从网络搜索 AI 新闻"
2. 等待完成
3. 提交任务: thread_id="test-001", query="请总结刚才的搜索结果"
4. 验证第二次任务是否能引用第一次的结果

---

### Atom 4: 数据库清理脚本 (可选)
**目标**: 提供清理过期会话的工具

**文件**:
- `scripts/clean_checkpoints.py` - 清理脚本
- `.env.example` - 添加清理配置

**步骤**:
1. 创建脚本读取 checkpoints.db
2. 删除超过 N 天的记录
3. 执行 VACUUM 释放空间

**验证**:
- 运行脚本，检查旧记录是否被删除
- 检查数据库文件大小是否减小

**用户验证步骤**:
1. 运行脚本: `python scripts/clean_checkpoints.py --days 30`
2. 检查控制台输出的清理统计
3. 验证数据库文件大小变化

## 新增环境变量

```bash
# 会话持久化配置（项目 4）
# SQLite 数据库文件路径（相对于项目根目录）
CHECKPOINT_DB_PATH=app/data/checkpoints.db
# 会话过期天数（清理策略），默认 30 天
SESSION_EXPIRE_DAYS=30
```

## 关键优势

1. **零业务代码改动**: SqliteSaver 是 InMemorySaver 的直接替代，API 完全兼容
2. **自动持久化**: LangGraph 自动保存每个执行节点的状态
3. **轻量级存储**: SQLite 无需额外服务，适合中小规模部署
4. **向后兼容**: 不影响现有任务提交流程

## 风险评估

1. **并发写入**: SQLite 默认模式可能有并发写入限制
   - **缓解**: 使用 WAL 模式 (Write-Ahead Logging)
   - **降级**: 如果遇到锁问题，回退到 InMemorySaver

2. **数据库增长**: 长期运行会导致数据库文件膨胀
   - **缓解**: 定期清理过期会话 (Atom 4)
   - **监控**: 添加数据库文件大小监控

3. **迁移风险**: 从 InMemorySaver 切换到 SqliteSaver
   - **缓解**: SqliteSaver 是 drop-in replacement，无需迁移
   - **测试**: 在测试环境先验证

## 回滚方案

如果 SqliteSaver 出现问题，一行代码即可回退:
```python
# 回退到内存存储
checkpointer = InMemorySaver()  # 替代 SqliteSaver.from_conn_string(...)
```

删除或重命名 `app/data/checkpoints.db` 即可清空所有历史会话。

## 验证标准

- ✅ 服务重启后会话状态保留
- ✅ 使用相同 thread_id 可以继续对话
- ✅ 会话列表 API 返回正确数据
- ✅ 数据库文件正常生成且大小合理
- ✅ 断点恢复功能正常工作
- ✅ 不影响现有任务提交流程
- ✅ 清理脚本能正确删除过期会话

## 实施注意事项

1. **数据库文件位置**: 使用项目根目录的相对路径，避免部署时路径问题
2. **Git 忽略**: 确保数据库文件不被提交到版本控制
3. **权限问题**: 确保 app/data/ 目录有写入权限
4. **备份策略**: 生产环境建议定期备份 checkpoints.db
5. **测试优先**: 先在 Atom 1 完成核心功能，验证通过后再添加增强功能

## 参考资料

- LangGraph Checkpointer 文档: https://langchain-ai.github.io/langgraph/how-tos/persistence/
- SQLite WAL 模式: https://www.sqlite.org/wal.html
