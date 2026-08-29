# deepsearch-agents · 单人落地操作手册（定稿 · main 分支开发版）

> 本手册基于对仓库源码的真实核验撰写,每步都标注**依据的来源文件**。核心原则（用户要求）：**必须可落地、可实操；交付繁琐可接受,项目最终必须能运行**。因此每一步都附带"降级开关 + 回滚",任何改动失败都可以安全退回,绝不把项目改坏。
>
> **开发模式（用户确认）**：单人开发,**所有改动直接在 main 分支上进行**,不另建 feature 分支、不设分支保护、不走 PR 流程。为保证 main 始终健康,后续文档的每一步验证与回滚都同等重要。
>
> 本机现状（用户确认）：**已能完整跑通原项目**（大模型 Key / MySQL 就绪）；任务队列选型 **Celery + RabbitMQ**。
>
> **RAGFlow 现状（用户确认）**：尚未部署,**无法进行有效测试**。因此本手册对 RAGFlow 相关部分**只保留优化改进**（列表缓存、MCP 工具迁移等）,**删除或暂缓其执行测试与验证**（含软件基线、MCP 回归、评测用例）,待 RAGFlow 部署后再行补测。

---

## 0. 前置：环境基线锁定（第 1 步必须先做）

- **目的**：在任何改动前,先确认"当前 main 是健康可运行的",并记录一份 **baseline 数据**供后续评测对比（项目7 依赖）。
- **来源**：`README.md` 快速开始；`docker/docker-compose.yaml`（仅 MySQL 服务）；`.env.example`（13 个变量）。
- **前置配置**：
  - 已装 `uv`、`pnpm`、Docker；`.env` 已按 `.env.example` 配好（含 `OPENAI_API_KEY` / `TAVILY_API_KEY` / `RAGFLOW_*` / `MYSQL_*`）。
  - `docker compose -f docker/docker-compose.yaml up -d` 启动 MySQL 教学库。
- **操作**：
  1. `uv sync && uv run uvicorn app.api.server:app --port 8000 --reload`
  2. 跑通 README 的典型任务（网络搜索 / 数据库查询）,确认全链路 OK（**RAGFlow 因未部署暂停其执行测试**,只保留优化）。
  3. 记录 baseline：每个任务**端到端耗时 + 是否成功**,存为 `docs/baseline.md`。
  4. **本次开发直接在 main 分支上进行**,不另建开发分支；每次改动落实后保持 main 始终处于可运行、可回滚状态。
- **验证**：网络搜索 / 数据库任务成功,baseline 已记录（RAGFlow 部分暂不纳入验证）。
- **回滚**：无风险,仅是记录。

---

## 项目 0｜Git 协作规范 + CI 骨架（先立规矩）

- **来源**：根目录现状——无 `CONTRIBUTING.md`、无 `.github/`、无 `tests/`（已核实 Not Found）。
- **前置配置**：无新增依赖。开发直接在 **main 分支**上进行,不设置分支保护,也不走 feature / PR 流程。
- **落地步骤**：
  1. 新增 `CONTRIBUTING.md`：约定**直接在 main 分支开发**、commit 规范（延续现有 `feat:/fix:/docs:/chore:` 前缀）、以及"每次改动必须保持 main 可运行、失败即回滚"的纪律。
  2. 新增 `.github/workflows/ci.yml`（**在 main 分支 push 时触发冒烟**）。**注意**：仓库当前无测试文件,首次 CI 不能直接写 `pytest`（会因无测试失败）,先做冒烟：
     - `uv run python -c "import app.api.server; print('backend smoke ok')"`
     - `cd frontend && pnpm install && pnpm build`
  3. 在 GitHub 把 8 个项目各建一个 issue（作为工作项追踪,单人亦可用于打勾核对进度）。
- **验证**：推送到 main 后,CI 冒烟通过（无新增测试,仅验证导入与构建）。
- **回滚**：纯增量文件,删除即可。
- **降级开关**：不设,低风险。

---

## 项目 1｜检索结果缓存（Redis）· 最快见效、零耦合

- **来源**：`app/tools/tavily_tool.py`（`internet_search`,模块级 `tavily_client`）；`app/tools/ragflow_tools.py`（`get_assistant_list`/`create_ask_delete`,`ragflow_client`）；无集中 config 文件。
- **前置配置（新增依赖与环境变量）**：
  - 新增依赖：`redis`
  - `.env.example` 新增：`REDIS_ENABLED`（默认 false）、`REDIS_URL`（默认 `redis://localhost:6379/0`）、`SEARCH_CACHE_TTL`（默认 3600）
- **落地步骤**：
  1. 新增 `app/utils/cache.py`：封装 `redis` 连接与 `get/set`,**连接失败时静默降级**（短路返回 None,不抛错,保证主链路不挂）。
  2. 缓存 Tavily：在 `internet_search` 内层,key=`md5(query+topic+max_results)`,命中直接返回。
  3. 缓存 RAGFlow 的 **`get_assistant_list`**（`list_chats` 只读,安全可缓存）。
  4. **`create_ask_delete` 不缓存或仅对有副作用的调用加开关**：它每次创建又删除临时会话；如要缓存问答,须先`delete` 原会话再复用结果,复杂度高——单人落地建议**暂只缓存 assistant 列表**,问答级缓存放到项目7 评测后再定。
  5. `.env.example` 补齐说明。
- **验证**：Redis 启动后,对 Tavily 网络搜索的同一查询提交两次,观察耗时下降 + `cache_hit`；关闭 Redis 再跑,任务仍成功（降级生效）。（RAGFlow 列表缓存优化保留,其缓存命中验证待 RAGFlow 部署后再补。）
- **回滚**：`REDIS_ENABLED=false` 即完全回到原逻辑。

---

## 项目 2｜Agent 安全防护 · 封住高危口子

- **来源**：`app/tools/db_tools.py`——`execute_sql_query` 直接 `cursor.execute(query)`（任意 SQL）；`get_table_data` 直接拼接表名 `LIMIT 100`；`list_sql_tables` 直接 `SHOW TABLES`；**全无白名单**,连接 `autocommit=True`（源码注释自标"生产应限制"）。`app/api/server.py` `/api/upload` 无大小/类型限制。
- **前置配置（新增环境变量）**：`ALLOWED_SQL_TABLES`（逗号分隔,可空）、`SQL_QUERY_TIMEOUT`（默认5）、`SQL_MAX_ROWS`（默认100）、`MAX_UPLOAD_MB`（默认20）
- **落地步骤**：
  1. 新增 `app/utils/safety.py`：`validate_sql(q)`（仅放行 SELECT/SHOW）、`validate_table(name)`（表白名单,名单为空则不启用表级限制）、`check_prompt_injection(text)`（Tavily 正文/上传文档的注入模式检测,命中打标）。
  2. 改造 `db_tools.py`：`execute_sql_query` 先过 `validate_sql`；`get_table_data` 过 `validate_table`；都做结果行数截断。
  3. `server.py` 上传处加大小与类型白名单校验。
  4. 前端确认无 `dangerouslySetInnerHTML`（React 默认转义即安全）,复查渲染链路。
- **验证**：输入 `DROP TABLE ...`、注入样例、超长文档,确认被拦截；构造一条正常 SELECT 回归通过（**重点回归,勿误伤合法链路**）。
- **回滚**：白名单相关可直接置空 `ALLOWED_SQL_TABLES`；**SELECT/SHOW 限制是始终生效的最低安全基线**,如极端误伤可暂时注释,但要知悉风险。

---

## 项目 3｜可观测性打点（trace）· 最大简化点

- **来源**：`app/agent/llm.py`（`init_chat_model(model=os.getenv("LLM_QWEN_MAX"), model_provider="openai")`；`OPENAI_BASE_URL`/`OPENAI_API_KEY` 实际由 langchain-openai 从环境注入,故能跑通）；`app/api/monitor.py`（`ToolMonitor` 单例 + `_emit()`,事件 `tool_start/assistant_call/task_result/task_cancelled/session_created`,payload 含 `timestamp`、`data.tool_name/args`）。
- **关键简化**：LangChain + LangGraph 原生支持 LangSmith,**只需配置环境变量即可自动拿到完整 trace,几乎不用改代码**。
- **前置配置（新增依赖与环境变量）**：新增依赖 `langsmith`；`.env.example` 新增 `LANGSMITH_API_KEY`、`LANGSMITH_TRACING`、`TRACING_PROVIDER`（默认空=关闭）。
- **落地步骤**：
  1. 先仅配 `LANGSMITH_TRACING=v1` 与环境变量,跑一个任务,验证 trace 面板出现主智能体→子智能体→工具的完整链路。
  2. 在 `monitor.py` 的 `report_tool`/`report_assistant` 上补**耗时字段**（记录调用起点/终点 duration_ms 写入 `data`）,用于前端与日志。
  3. 可选：新增 `scripts/trace_query.py` 按 `thread_id` 检索链路日志。
- **验证**：trace 面板可见各环节耗时,能定位最慢节点。
- **回滚**：`LANGSMITH_TRACING` 置空即关闭,不影响运行。

---

## 项目 4｜会话持久化与断点恢复

- **来源**：`app/agent/main_agent.py`——`from langgraph.checkpoint.memory import InMemorySaver`,`checkpointer=InMemorySaver()`,`config={"configurable":{"thread_id":session_id}}`；`app/api/context.py`（`thread_id`/`session_dir` ContextVar）；`app/api/server.py`。目录 `output/`、`updated/` 已做文件级持久化,但 checkpointer 是内存态,**重启即丢**。
- **前置配置**：新增依赖 `langgraph-checkpoint-sqlite`（SQLite 零服务）；`.env.example` 新增 `CHECKPOINT_DB_PATH`（默认 `./checkpoints.db`）。**无需外部数据库服务**。
- **落地步骤**：
  1. 新增 `app/storage/__init__.py` 与 `app/storage/checkpoint.py`：构造 `SqliteSaver`。
  2. 修改 `main_agent.py`：`InMemorySaver()` → 持久化 saver（接收 `CHECKPOINT_DB_PATH`）。
  3. **⚠ 兼容性实测关**：`deepagents==0.5.7` 的 `checkpointer` 参数是否兼容 LangGraph sqlite saver,需先在 **main 分支直接改动并实测**（跑一个任务/断点续跑）。若兼容则进入步骤4；若不兼容则回滚此改动,保留 InMemorySaver,仅做步骤4b 的 WebSocket 事件持久化。
  4. 断点续跑验证：任务跑一半重启服务,同 `thread_id` 再发起,应能续跑或读到 checkpoint。
  4b. （无论兼容与否都做）`app/storage/event_store.py`：把 `monitor` 的 WebSocket 事件写 SQLite（WAL）,支持历史回放,新增 `GET /api/threads/{id}/events`。
- **验证**：断点续跑成功；历史事件可回放。
- **回滚**：切回 `InMemorySaver`,删除 checkpoint 逻辑即可；event_store 为增量无副作用。

---

## 项目 5｜任务队列与并发治理（Celery + RabbitMQ,已确认）

- **来源**：`app/api/server.py`——`/api/task` 用 `asyncio.create_task(run_deep_agent(...))` + `active_tasks` 字典（同 thread 取消旧任务）,返回 `{"status":"started","thread_id"}`。非 FastAPI BackgroundTasks,需按其真实实现改造。
- **前置配置（新增依赖/服务/变量）**：新增依赖 `celery`、`redis`（复用项目1）；**新增 RabbitMQ 服务**（改 `docker/docker-compose.yaml` 加 `rabbitmq`,或 apt/brew 起本地）；`.env.example` 新增 `RABBITMQ_URL`、`CELERY_ENABLED`（默认false）、`CELERY_CONCURRENCY`（默认4）、`CELERY_TASK_TIMEOUT`（默认600）。
- **落地步骤（两阶段,务必先限流再切队列）**：
  1. **stage A（低风险）**：先在现状 asyncio 上加**并发信号量**限流（`asyncio.Semaphore(CELERY_CONCURRENCY)`）,收敛并行度,验证对项目无害。
  2. **stage B（切队列）**：
     - 新增 `app/worker/celery_app.py`、`app/worker/tasks.py`,将 `run_deep_agent` 包装为 Celery task（async 用 `asyncio.run` 包裹）。
     - `server.py` 在 `CELERY_ENABLED=true` 时改为提交 Celery 任务并返回 `task_id`；否则保持原 asyncio 路径（**双模式并存**,降级安全）。
     - 新增 `GET /api/task/{id}/status`；配置并发、超时、重试（指数退避,最多3次）、结果写入共享存储。
- **验证**：并发提交多任务按并发上限排队；kill 一个 worker 后任务可重试不丢；状态接口正常。
- **回滚**：`CELERY_ENABLED=false` 即回 asyncio 原路径,项目不依赖队列也能运行。

---

## 项目 6｜工具层 MCP 化（架构重构,放最后动工具）

- **来源**：9 个 `@tool` 分布在 6 个文件——`db_tools.py`(3)、`markdown_tools.py`(`generate_markdown`)、`pdf_tools.py`(`convert_md_to_pdf`)、`ragflow_tools.py`(2)、`tavily_tool.py`(`internet_search`)、`upload_file_read_tool.py`(`read_file_content`)。主智能体直接 import 3 个文件工具,三子智能体各自 import 所属工具。
- **前置配置（新增依赖/变量）**：新增依赖 `fastmcp`；`.env.example` 新增 `MCP_ENABLED`（默认false）、`MCP_AUTH_TOKEN`。
- **落地步骤**：
  1. 新增 `mcp/` server：将 9 个工具用 FastMCP 声明为 tools；以 stdio/SSE 暴露；请求头 token 鉴权。
  2. 主智能体改为在 `MCP_ENABLED=true` 时通过 MCP 客户端按需加载工具,否则保持直接 import（**双模式**）。
  3. 渐进迁移：先迁移只读工具（Tavily/RAGFlow list/文件读）,验证通过后再迁移 SQL 与写操作。
- **验证**：网络搜索 / 数据库任务在 MCP 模式回归通过；工具可在独立 MCP client 复用；未带 token 被拒。（RAGFlow 工具迁移优化保留,其回归验证待 RAGFlow 部署后再补。）
- **回滚**：`MCP_ENABLED=false` 整体回直接 import,零影响。

---

## 项目 7｜评测体系 + CI 门禁（量化收敛）

- **来源**：`.env` LLM 配置（`OPENAI_BASE_URL`/`OPENAI_API_KEY`/`LLM_QWEN_MAX`）；baseline（前置第0步记录）；已确认**可用 LLM key 并接受消耗**。
- **前置配置**：新增依赖 `pytest`；`.env.example` 可选 `EVAL_GATE`。无需外服。
- **落地步骤**：
  1. 新增 `evals/questions.yaml`（5~15 条代表性问题,覆盖网络搜索/数据库；**RAGFlow 相关用例暂缓,因其未部署无法执行**）,每条含预期成功判据。
  2. 新增 `evals/run_evals.py` 与 `evals/metrics.py`：跑完输出 JSON 报告（任务完成率 / 工具调用成功率 / 端到端耗时 / token 成本）,并与 `docs/baseline.md` diff。
  3. 新增 GitHub Actions job：**main push 时触发** → 跑 `evals/` → 报告作为 artifact；`EVAL_GATE=true` 时对不达标门禁置 failed。
- **验证**：本地一次 `evals/run_evals.py` 产出完整报告；推送 main 触发评测。
- **回滚**：`EVAL_GATE=false` 仅出报告不拦截。

---

## 项目 8｜一键部署完善 + 交接（收尾）

- **来源**：`docker/docker-compose.yaml` 仅 MySQL 一个服务；`frontend/vite.config.ts` 用 proxy `/api→8000`、`/ws→ws:8000`（无 axios/ws 依赖）。
- **前置配置**：`docker-compose.yaml` 补 `redis`、`rabbitmq`、`worker` 服务（配合项目1/5）。
- **落地步骤**：
  1. 在 `docker-compose.yaml` 增加 redis、rabbitmq、worker 服务。
  2. 前端容器化并接入同一 compose（`/api`、`/ws` 代理指向后端服务名）。
  3. 更新 `README.md` 一键启动章节与 `.env.example`（汇总全部新增变量并注明用途）。
  4. 将本手册归档至 `docs/improvement-plan-solo.md`,勾选完成项。
- **验证**：从空环境按 README 一键拉起全部服务,3 个典型任务全跑通。
- **回滚**：单服务回滚即可,无全局风险。

---

## 单人执行顺序与安全护栏总结

| 步骤 | 项目 | 新增依赖 | 新增服务 | 回滚开关 |
| --- | --- | --- | --- | --- |
| 1 | 前置 baseline | - | - | - |
| 2 | 项目0 CI 骨架 | - | - | 删文件 |
| 3 | 项目1 Redis 缓存 | redis | redis | `REDIS_ENABLED` |
| 4 | 项目2 安全防护 | - | - | 白名单置空 |
| 5 | 项目3 可观测 | langsmith | - | `LANGSMITH_TRACING` |
| 6 | 项目4 持久化 | langgraph-checkpoint-sqlite | - | 切回 InMemorySaver |
| 7 | 项目5 队列（先限流后切） | celery, redis | rabbitmq | `CELERY_ENABLED` |
| 8 | 项目6 MCP | fastmcp | - | `MCP_ENABLED` |
| 9 | 项目7 评测+CI | pytest | - | `EVAL_GATE` |
| 10 | 项目8 一键部署 | - | redis/rabbitmq/worker | 单服务回滚 |

**铁律**：任何一步失败,立即停在当步并用其回滚开关还原,**绝不带着疑点进入下一步堆代码**（对应你的 VIBE CODING 约定：交付繁琐可接受、功能不可验证不可接受、项目不能改到跑不起来）。

## ⚠ 落地前需留意的三个实测风险点
1. **deepagents 0.5.7 与 sqlite checkpointer 兼容性**（项目4）——必须先在 **main 分支** 直接改动并实测,不兼容则回滚为仅做事件持久化。
2. **Celery 的 async 任务包装**（项目5）——`run_deep_agent` 是 async,需 `asyncio.run` 正确包裹,避免 event loop 转圈。
3. **RAGFlow `create_ask_delete` 有创建/删除会话副作用**（项目1）——暂不缓存其问答结果,避免状态混乱。
