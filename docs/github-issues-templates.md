# GitHub Issues 模板 - deepsearch-agents 改进项目

> 本文档提供 8 个改进项目的 GitHub Issue 模板，可直接复制使用

---

## Issue 1: Redis 缓存层实现

**标题**: `feat: implement Redis caching for search results`

**描述**:
```markdown
## 目标
为 Tavily 网络搜索和 RAGFlow 列表查询添加 Redis 缓存，提升重复查询性能。

## 核心任务
- [ ] 新增 `app/utils/cache.py` 封装 Redis 连接（支持降级）
- [ ] 为 `tavily_tool.py` 的 `internet_search` 添加缓存
- [ ] 为 `ragflow_tools.py` 的 `get_assistant_list` 添加缓存
- [ ] 更新 `.env.example` 添加 Redis 相关配置

## 新增依赖
- `redis`

## 新增环境变量
- `REDIS_ENABLED` (默认 false)
- `REDIS_URL` (默认 redis://localhost:6379/0)
- `SEARCH_CACHE_TTL` (默认 3600)

## 验证标准
- [ ] Redis 启动后，同一查询第二次耗时显著下降
- [ ] 关闭 Redis 后，系统仍可正常运行（降级生效）
- [ ] 缓存命中时返回 `cache_hit: true` 标记

## 回滚方案
设置 `REDIS_ENABLED=false` 即可完全回退到原逻辑

## 参考文档
- 详细计划：`docs/improvement-plan-solo.md` - 项目 1
- 执行日志：`docs/execution-log.md`
```

---

## Issue 2: Agent 安全防护实现

**标题**: `feat: implement security hardening for SQL and file operations`

**描述**:
```markdown
## 目标
为数据库查询和文件上传添加安全防护，防止 SQL 注入和恶意文件。

## 核心任务
- [ ] 新增 `app/utils/safety.py` 实现安全验证函数
- [ ] 改造 `db_tools.py` 添加 SQL 白名单和查询限制
- [ ] 改造 `server.py` 添加文件上传大小和类型限制
- [ ] 更新 `.env.example` 添加安全相关配置

## 新增环境变量
- `ALLOWED_SQL_TABLES` (逗号分隔白名单，可空)
- `SQL_QUERY_TIMEOUT` (默认 5)
- `SQL_MAX_ROWS` (默认 100)
- `MAX_UPLOAD_MB` (默认 20)

## 验证标准
- [ ] `DROP TABLE` / `DELETE` 等危险 SQL 被拦截
- [ ] 仅 `SELECT` / `SHOW` 语句可执行
- [ ] 超大文件上传被拒绝
- [ ] 合法查询正常通过（回归测试）

## 回滚方案
白名单相关可置空 `ALLOWED_SQL_TABLES`；SELECT/SHOW 限制是最低安全基线

## 参考文档
- 详细计划：`docs/improvement-plan-solo.md` - 项目 2
- 执行日志：`docs/execution-log.md`
```

---

## Issue 3: 可观测性打点实现

**标题**: `feat: implement observability with LangSmith tracing`

**描述**:
```markdown
## 目标
集成 LangSmith 实现完整的 Agent 调用链路追踪，提升问题定位能力。

## 核心任务
- [ ] 配置 LangSmith 环境变量，验证 trace 自动上报
- [ ] 在 `monitor.py` 补充耗时字段（duration_ms）
- [ ] 可选：新增 `scripts/trace_query.py` 支持按 thread_id 查询

## 新增依赖
- `langsmith`

## 新增环境变量
- `LANGSMITH_API_KEY`
- `LANGSMITH_TRACING` (默认空=关闭)
- `TRACING_PROVIDER` (默认空)

## 验证标准
- [ ] LangSmith 面板可见主 Agent → 子 Agent → 工具的完整链路
- [ ] 可定位最慢节点的耗时数据
- [ ] 关闭 tracing 后系统正常运行

## 回滚方案
设置 `LANGSMITH_TRACING` 为空即可关闭，不影响运行

## 参考文档
- 详细计划：`docs/improvement-plan-solo.md` - 项目 3
- 执行日志：`docs/execution-log.md`
```

---

## Issue 4: 会话持久化实现

**标题**: `feat: implement session persistence with SQLite checkpoint`

**描述**:
```markdown
## 目标
将 InMemorySaver 替换为 SQLite 持久化存储，支持断点续跑和历史事件回放。

## 核心任务
- [ ] 新增 `app/storage/checkpoint.py` 构造 SqliteSaver
- [ ] 修改 `main_agent.py` 切换到持久化 checkpointer
- [ ] 验证 deepagents 0.5.7 与 sqlite checkpointer 兼容性
- [ ] 新增 `app/storage/event_store.py` 持久化 WebSocket 事件
- [ ] 新增 API `GET /api/threads/{id}/events` 支持历史回放

## 新增依赖
- `langgraph-checkpoint-sqlite`

## 新增环境变量
- `CHECKPOINT_DB_PATH` (默认 ./checkpoints.db)

## 验证标准
- [ ] 任务跑一半重启服务，同 thread_id 可续跑
- [ ] 历史事件可通过 API 回放
- [ ] 如 checkpointer 不兼容，降级为仅事件持久化

## 回滚方案
切回 `InMemorySaver`，删除 checkpoint 逻辑；event_store 为增量无副作用

## 参考文档
- 详细计划：`docs/improvement-plan-solo.md` - 项目 4
- 执行日志：`docs/execution-log.md`
```

---

## Issue 5: 任务队列实现 (Celery + RabbitMQ)

**标题**: `feat: implement task queue with Celery and RabbitMQ`

**描述**:
```markdown
## 目标
引入 Celery + RabbitMQ 任务队列，支持并发治理、任务重试和结果持久化。

## 核心任务

### Stage A - 并发限流（低风险）
- [ ] 在现有 asyncio 上添加 Semaphore 限流
- [ ] 验证并发控制对系统无害

### Stage B - 切换队列
- [ ] 新增 `app/worker/celery_app.py` 和 `app/worker/tasks.py`
- [ ] 包装 `run_deep_agent` 为 Celery task
- [ ] 改造 `server.py` 支持双模式（Celery / asyncio）
- [ ] 新增 `GET /api/task/{id}/status` 查询接口
- [ ] 配置并发、超时、重试策略

## 新增依赖
- `celery`
- `redis` (复用项目 1)

## 新增服务
- RabbitMQ (docker-compose 或本地安装)

## 新增环境变量
- `RABBITMQ_URL`
- `CELERY_ENABLED` (默认 false)
- `CELERY_CONCURRENCY` (默认 4)
- `CELERY_TASK_TIMEOUT` (默认 600)

## 验证标准
- [ ] 并发提交多任务按并发上限排队
- [ ] Kill worker 后任务可重试不丢失
- [ ] 状态查询接口正常返回

## 回滚方案
设置 `CELERY_ENABLED=false` 即回 asyncio 原路径

## 参考文档
- 详细计划：`docs/improvement-plan-solo.md` - 项目 5
- 执行日志：`docs/execution-log.md`
```

---

## Issue 6: MCP 工具层改造

**标题**: `feat: migrate tools to MCP architecture`

**描述**:
```markdown
## 目标
将 9 个工具迁移到 MCP 架构，提升工具复用性和安全性。

## 核心任务
- [ ] 新增 `mcp/` 目录，使用 FastMCP 声明 9 个工具
- [ ] 实现 stdio/SSE 暴露和 token 鉴权
- [ ] 主 Agent 支持 MCP 客户端模式加载工具
- [ ] 渐进迁移：先只读工具，后写操作工具

## 工具清单
- `internet_search` (Tavily)
- `get_assistant_list`, `create_ask_delete` (RAGFlow)
- `list_sql_tables`, `get_table_data`, `execute_sql_query` (Database)
- `read_file_content` (File)
- `generate_markdown`, `convert_md_to_pdf` (Document)

## 新增依赖
- `fastmcp`

## 新增环境变量
- `MCP_ENABLED` (默认 false)
- `MCP_AUTH_TOKEN`

## 验证标准
- [ ] 网络搜索 / 数据库任务在 MCP 模式下回归通过
- [ ] 工具可在独立 MCP client 中复用
- [ ] 未带 token 的请求被拒绝

## 回滚方案
设置 `MCP_ENABLED=false` 整体回直接 import，零影响

## 参考文档
- 详细计划：`docs/improvement-plan-solo.md` - 项目 6
- 执行日志：`docs/execution-log.md`
```

---

## Issue 7: 评测体系 + CI 门禁

**标题**: `feat: implement evaluation system with CI gates`

**描述**:
```markdown
## 目标
建立自动化评测体系，量化改进效果，并在 CI 中设置质量门禁。

## 核心任务
- [ ] 新增 `evals/questions.yaml` 定义 5-15 个代表性测试用例
- [ ] 新增 `evals/run_evals.py` 执行评测并生成报告
- [ ] 新增 `evals/metrics.py` 计算指标（完成率、耗时、成本）
- [ ] 与 baseline 数据对比，生成 diff 报告
- [ ] 在 GitHub Actions 中添加评测 job

## 评测指标
- 任务完成率
- 工具调用成功率
- 端到端耗时
- Token 成本

## 新增依赖
- `pytest`

## 新增环境变量
- `EVAL_GATE` (可选，控制是否门禁)

## 验证标准
- [ ] 本地运行 `evals/run_evals.py` 产出完整报告
- [ ] 推送 main 触发 CI 评测
- [ ] `EVAL_GATE=true` 时不达标会阻止合并

## 回滚方案
设置 `EVAL_GATE=false` 仅出报告不拦截

## 参考文档
- 详细计划：`docs/improvement-plan-solo.md` - 项目 7
- 基线数据：`docs/baseline.md`
- 执行日志：`docs/execution-log.md`
```

---

## Issue 8: 一键部署完善

**标题**: `feat: implement one-click deployment with Docker Compose`

**描述**:
```markdown
## 目标
完善 docker-compose 配置，实现包含所有服务的一键部署。

## 核心任务
- [ ] 在 `docker-compose.yaml` 中添加 redis、rabbitmq、worker 服务
- [ ] 前端容器化并接入 compose（配置 /api 和 /ws 代理）
- [ ] 更新 `README.md` 一键启动文档
- [ ] 汇总更新 `.env.example` 所有新增环境变量
- [ ] 归档改进手册到 `docs/improvement-plan-solo.md`

## 新增服务
- redis (复用项目 1)
- rabbitmq (复用项目 5)
- worker (Celery worker)
- frontend (React 应用)

## 验证标准
- [ ] 从空环境按 README 一键拉起全部服务
- [ ] 3 个典型任务（网络搜索、数据库查询、文件上传）全跑通
- [ ] 前端能正常访问和使用

## 回滚方案
单服务回滚即可，无全局风险

## 参考文档
- 详细计划：`docs/improvement-plan-solo.md` - 项目 8
- 执行日志：`docs/execution-log.md`
```

---

## 使用说明

### 创建 Issues 步骤

1. 访问 GitHub 仓库的 Issues 页面
2. 点击 "New issue"
3. 复制对应项目的标题和描述
4. 添加标签：`enhancement`, `improvement-plan`
5. 可选：设置 Milestone "deepsearch-agents 改进计划"
6. 创建 issue

### 推荐标签体系

- `enhancement` - 功能增强
- `improvement-plan` - 改进计划相关
- `infrastructure` - 基础设施（项目 0, 5, 8）
- `performance` - 性能优化（项目 1）
- `security` - 安全相关（项目 2）
- `observability` - 可观测性（项目 3）
- `persistence` - 持久化（项目 4）
- `architecture` - 架构改造（项目 6）
- `testing` - 测试相关（项目 7）

### 进度追踪

所有 issues 的执行进度同步更新到 `docs/execution-log.md`。
