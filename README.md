<div align='center'>
  <h1 style="margin-top: 15px;">deepsearch-agents</h1>
  <p><em>DeepAgents 多智能体深度研究系统 · 学习复现与个人扩展仓库</em></p>
</div>
<div align='center'>
</div>

## 📖 项目简介
「深度研搜」是一个对话式多智能体研究系统：输入一个研究任务，主智能体负责任务规划与调度，三个专家子智能体分别检索不同信息源，最终汇总生成 Markdown / PDF 交付物，全过程通过 WebSocket 实时推送到前端。
一个典型任务的样子：
```text
结合公开资料、数据库信息和我上传的文档，整理一份机器人行业研究报告，并生成 PDF。
```
系统背后的执行链路：
```text
用户任务
  -> FastAPI 接收请求，创建会话目录
  -> 主智能体分析任务并规划步骤
  -> 分派给网络搜索 / 数据库查询 / RAGFlow 知识库助手
  -> 主智能体汇总多来源信息
  -> 调用文件工具生成 Markdown / PDF
  -> monitor 通过 WebSocket 推送全过程事件
  -> 前端实时展示事件流、答案与文件列表
```

## 🏗️ 系统架构
![系统架构图](docs/images/deepsearch-system-architecture.svg)
采用 DeepAgents 的 Orchestrator-Workers 模式：
| 归属 | 能力 | 工具 |
| --- | --- | --- |
| 主智能体 | 任务规划、助手调度、结果汇总、文件交付 | `read_file_content` / `generate_markdown` / `convert_md_to_pdf` |
| 网络搜索助手 | 查询互联网公开信息 | `internet_search`（Tavily） |
| 数据库查询助手 | 发现表结构、执行 SQL | `list_sql_tables` / `get_table_data` / `execute_sql_query` |
| RAGFlow 助手 | 私有知识库问答 | `get_assistant_list` / `create_ask_delete` |

关键工程设计（也是我重点研读的部分）：
- **会话级上下文隔离**：`ContextVar` 携带 `thread_id` 与 `session_dir`，深层工具无需显式传参即可获取会话身份，各会话文件互不干扰
- **事件驱动的前后端联动**：工具调用、子智能体调用、任务结果、取消与异常均通过 `monitor` 以 WebSocket 事件推送前端
- **子智能体各持工具、上下文隔离**：主智能体不直接持有检索类工具，通过任务描述驱动子智能体，控制上下文规模
![前端任务执行页](docs/images/deepsearch-network-search-result.jpg)

## 🛠️ 技术栈
| 模块 | 技术 |
| --- | --- |
| 智能体框架 | DeepAgents 0.5.7 / LangGraph / LangChain |
| 大模型接入 | OpenAI 兼容接口（通义千问 qwen-max） |
| 检索与数据 | Tavily / MySQL / RAGFlow（ragflow-sdk） |
| 文件处理 | pypdf / python-docx / pandas / ReportLab |
| 后端 | FastAPI + Uvicorn + WebSocket |
| 前端 | React + Vite + TypeScript + Ant Design |
| 工程化 | uv / pnpm / pre-commit / Docker Compose |

## 📁 项目结构
```text
deepsearch-agents/
├── app/
│   ├── agent/
│   │   ├── subagents/              # 网络搜索、数据库查询、RAGFlow 三个子智能体
│   │   ├── llm.py                  # OpenAI 兼容模型初始化
│   │   ├── main_agent.py           # 主智能体组装与 run_deep_agent 执行入口
│   │   └── prompts.py              # 提示词加载
│   ├── api/
│   │   ├── context.py              # ContextVar 会话上下文
│   │   ├── monitor.py              # WebSocket 事件推送
│   │   └── server.py               # FastAPI 任务/上传/下载/WS 接口
│   ├── prompt/prompts.yml          # 主智能体与子智能体提示词配置
│   ├── ragflow/                    # RAGFlow 配置与调用示例
│   ├── tools/                      # 9 类工具实现
│   └── utils/                      # 路径解析、文档转换工具
├── docker/                         # 本地 MySQL 教学环境（药品/库存/销售数据）
├── docs/knowledge_base/            # RAGFlow 知识库示例文档（电商/金融行业报告）
├── examples/                       # DeepAgents 章节示例脚本（15 个）
├── frontend/                       # React 前端
├── CLAUDE.md                       # Claude Code 项目协作指南
└── .env.example                    # 环境变量模板
```

## 🚀 快速开始
### 环境要求
- Python 3.12（不支持 3.13）+ [uv](https://docs.astral.sh/uv/)
- Node.js + pnpm
- Docker（MySQL 教学库）
- 大模型 API Key（OpenAI 兼容）、Tavily API Key；RAGFlow 为可选依赖

### 后端
```bash
git clone https://github.com/wjb412530/deepsearch-agents.git
cd deepsearch-agents
uv sync                          # 安装依赖
cp .env.example .env             # 配置模型/搜索/数据库密钥
docker compose -f docker/docker-compose.yaml up -d   # 启动 MySQL 教学库
uv run uvicorn app.api.server:app --host 0.0.0.0 --port 8000 --reload
```
后端接口：
| 接口 | 说明 |
| --- | --- |
| `POST /api/task` | 启动一次 DeepAgents 后台任务 |
| `POST /api/task/{thread_id}/cancel` | 取消指定会话任务 |
| `POST /api/upload` | 上传文件到当前会话 |
| `GET /api/files` / `GET /api/download` | 列出 / 下载生成文件 |
| `WebSocket /ws/{thread_id}` | 实时推送执行事件 |

### 前端
```bash
cd frontend
pnpm install && pnpm dev
```

### 试几个任务
```text
从数据库中查询心血管药品的库存情况，并生成 Markdown 报告。
搜索 2026 年 AI 在电商行业的应用趋势，并结合知识库资料生成一份 PDF。
请先读取我上传的行业报告，再结合公开资料整理一份研究摘要。
```

## 🔬 改进路线图（面向 Agent 工程落地 · 含单人落地方案）

> 原项目定位为教学骨架，刻意不覆盖生产治理与效果度量能力。以下改进项均基于对源码的研读与原作者「能力边界」说明整理，是我在本仓库上亲手实现的扩展方向。每一项都写清 **改什么 / 为什么改 / 前置配置 / 落地要点 / 验证方式 / 回滚开关 / 依据来源**，并按**可落地的实施顺序**排列（基础设施 → 低风险快收益 → 护栏 → 观测 → 运行时重构 → 架构重构 → 度量收敛 → 部署收口）。
> **每步都带降级开关与回滚，任何改动失败均可安全退回，保证项目始终可运行**。

### 阶段 0｜Git 协作规范 + CI 骨架
- **改什么**：新增 `CONTRIBUTING.md`、main 分支保护；`ci.yml` 先做冒烟（`import app.api.server` + 前端构建）；把以下 8 项改进各建一个 issue 认领。
- **为什么**：先立规矩 —— 所有后续改动在"可复现、可回滚、PR 隔离"的土壤上进行，这是双人协作与逐步验证的工程叙事前提。
- **前置配置**：无新依赖；GitHub 分支保护权限。
- **落地要点**：仓库当前无 `tests/`，CI 首次不能用 `pytest`（无测试会失败），先冒烟。
- **回滚开关**：低风险，删增量文件即可。
- **依据来源**：根目录现状（无 `.github/`、无 `CONTRIBUTING.md`，已核实）。
- **工程能力**：协作工程化、交付可复现性。

### 阶段 1｜检索结果缓存（Redis · 最快见效）
- **改什么**：新增 `app/utils/cache.py`；对 Tavily 检索与 RAGFlow 助手列表做 Redis TTL 缓存；连接失败静默降级。
- **为什么**：多智能体多次规划会重复检索同一关键词，既烧 token 又慢；缓存显著降耗时与成本。
- **前置配置**：新增依赖 `redis`；`REDIS_ENABLED`（默认false）`REDIS_URL`、`SEARCH_CACHE_TTL`。
- **落地要点**：RAGFlow `create_ask_delete` 每次会**创建又删除临时会话**（有副作用），暂只缓存只读的 `get_assistant_list`，问答级缓存留到评测后再定。
- **验证**：同查询两次耗时下降 + `cache_hit`；关 Redis 任务仍成功（降级生效）。
- **回滚开关**：`REDIS_ENABLED=false` 即回到原逻辑。
- **依据来源**：`app/tools/tavily_tool.py`、`app/tools/ragflow_tools.py`。
- **工程能力**：RAG 全链路性能优化、缓存一致性、成本收益权衡。

### 阶段 2｜Agent 安全与防护（护栏先上）
- **改什么**：新增 `app/utils/safety.py`；`execute_sql_query` 仅放行 `SELECT/SHOW`；`get_table_data` 表名白名单；结果行数与查询超时上限；上传大小/类型限制；对 Tavily 正文与上传文档做提示注入检测；前端渲染转义复查。
- **为什么**：源码 `execute_sql_query` 可执行**任意 SQL**、表名直接拼接，是典型 SQL 注入/RCE 面；多来源检索下的网页/文档还可能构成提示注入。
- **前置配置**：`ALLOWED_SQL_TABLES`、`SQL_QUERY_TIMEOUT`、`SQL_MAX_ROWS`、`MAX_UPLOAD_MB`。
- **落地要点**：表名白名单可空（未配置则不启用表级限制，避免误伤合法查询）；**SELECT/SHOW 限制是始终生效的最低安全基线**。
- **验证**：`DROP TABLE`、注入样例、超长文档被拦；正常 SELECT 回归通过（重点回归，勿误伤）。
- **回滚开关**：白名单置空。
- **依据来源**：`app/tools/db_tools.py`（任意 SQL + `autocommit=True`，源码注释自标"生产应限制"）。
- **工程能力**：Agent 安全工程，识别并封堵工具级副作用漏洞 —— Demo 走向生产的关键差异点。

### 阶段 3｜可观测性打点（trace · 最大简化点）
- **改什么**：配置 LangSmith 环境变量自动 trace；在 `monitor` 的 `report_tool`/`report_assistant` 补耗时字段；可选 `scripts/trace_query.py` 按 `thread_id` 检索链路。
- **为什么**：没有 trace，长任务卡在哪一步只能靠猜；这是评测体系的**观测基础**，也为后续改执行链定位问题。
- **前置配置**：新增依赖 `langsmith`；`LANGSMITH_API_KEY`、`LANGSMITH_TRACING`。
- **落地要点**：LangChain/LangGraph 原生支持 LangSmith，**配环境变量即可拿到完整 trace**，几乎不改代码。
- **验证**：trace 面板可见主→子→工具的完整链路与各环节耗时。
- **回滚开关**：`LANGSMITH_TRACING` 置空即关闭。
- **依据来源**：`app/agent/llm.py`、`app/api/monitor.py`（`ToolMonitor` 单例 + 统一事件 `timestamp/data.tool_name`）。
- **工程能力**：可观测性、长任务瓶颈定位。

### 阶段 4｜会话持久化与断点恢复
- **改什么**：用持久化 checkpoint 替换内存态 `InMemorySaver`；新增 WebSocket 事件落库与历史回放接口。
- **为什么**：内存态重启即丢，长任务中断无法续跑；持久化后既是"记忆"，又能支撑审计与回放调优。
- **前置配置**：`langgraph-checkpoint-sqlite`（SQLite 零服务）；`CHECKPOINT_DB_PATH`。
- **落地要点**：**必须先实测 `deepagents==0.5.7` 与 sqlite saver 的兼容性**，不兼容则保留 `InMemorySaver`、仅做 WebSocket 事件持久化（`app/storage/event_store.py`）。
- **验证**：任务跑一半重启服务，同 `thread_id` 可断点续跑；历史事件可回放。
- **回滚开关**：切回 `InMemorySaver`。
- **依据来源**：`app/agent/main_agent.py`（`InMemorySaver`、`config={"configurable":{"thread_id":session_id}}`）。
- **工程能力**：Agent 状态管理与长期记忆 —— 区分短期上下文与持久记忆。

### 阶段 5｜任务队列与并发治理（Celery + RabbitMQ）
- **改什么**：分两阶段 —— 先给 `asyncio.create_task` 加并发信号量限流，再切到 Celery + RabbitMQ 任务队列；新增任务状态接口。
- **为什么**：当前长任务在进程内后台执行，进程重启即丢、多实例无法协作、并发不可控；队列化才能横向扩容、灰度与限流。
- **前置配置**：新增依赖 `celery`、`redis`；RabbitMQ 服务；`RABBITMQ_URL`、`CELERY_ENABLED`（默认false）、`CELERY_CONCURRENCY`、`CELERY_TASK_TIMEOUT`。
- **落地要点**：**must 两阶段**（先限流再切队列）；`run_deep_agent` 是 async，需用 `asyncio.run` 正确包裹；`CELERY_ENABLED=true` 时提交任务并返回 `task_id`，否则保持原路径（双模式并存）。
- **验证**：并发提交按并发上限排队；kill 一个 worker 任务可重试不丢。
- **回滚开关**：`CELERY_ENABLED=false` 即回 asyncio 原路径。
- **依据来源**：`app/api/server.py`（`asyncio.create_task(run_deep_agent(...))` + `active_tasks` 字典）。
- **工程能力**：异步与分布式调度、可靠性治理 —— 把"跑起来的 Agent"变成"可运维的 Agent 服务"。

### 阶段 6｜工具层 MCP 化
- **改什么**：将 9 类工具封装为标准 MCP Server（FastMCP），以 stdio/SSE 暴露；`MCP_ENABLED` 双模式加载。
- **为什么**：MCP 让"工具"成为与智能体框架解耦的独立资产，一份工具可被多客户端/多框架复用，并能统一鉴权与权限治理。
- **前置配置**：新增依赖 `fastmcp`；`MCP_ENABLED`、`MCP_AUTH_TOKEN`。
- **落地要点**：渐进迁移 —— 先迁移只读工具（Tavily/RAGFlow 列表/文件读），验证通过后再迁移 SQL 与写操作。
- **验证**：3 类任务在 MCP 模式全回归通过；未带 token 被拒。
- **回滚开关**：`MCP_ENABLED=false` 整体回直接 import。
- **依据来源**：9 个工具分布在 `db_tools.py`(3)、`markdown_tools.py`、`pdf_tools.py`、`ragflow_tools.py`(2)、`tavily_tool.py`、`upload_file_read_tool.py`（共 6 文件 9 函数）。
- **工程能力**：MCP/Skill 工具生态标准化 —— 工具即服务（TaaS）。

### 阶段 7｜评测体系 + CI 门禁（量化收敛）
- **改什么**：新增 `evals/questions.yaml`、`run_evals.py`、`metrics.py`；输出任务完成率/工具成功率/端到端耗时/token 成本报告并与 baseline 对比；CI 按 PR 出报告，`EVAL_GATE` 可拦截。
- **为什么**：多智能体系统正确性无法靠几个用例断言，必须"可度量、可回归、可定位"；同时把"改进了多少"变成可写进简历的量化数字。
- **前置配置**：新增依赖 `pytest`；`EVAL_GATE`（默认 false）；**需可用 LLM Key 并接受 token 消耗**（本项目已就绪）。
- **落地要点**：评测集 5~15 条代表性问题，覆盖网络搜索/数据库/RAGFlow/多源混合；依赖前置 baseline 数据对比。
- **验证**：跑一次输出完整报告；PR 自动触发评测。
- **回滚开关**：`EVAL_GATE=false` 仅出报告不拦截。
- **依据来源**：`.env` 的 LLM 配置（`OPENAI_BASE_URL`/`OPENAI_API_KEY`/`LLM_QWEN_MAX`）+ 快速开始产生的 baseline。
- **工程能力**：效果度量与迭代闭环 ——「不裸答、不裸跑」，改一处必须能量化影响。

### 阶段 8｜一键部署完善 + 交接
- **改什么**：Docker Compose 补齐 redis、rabbitmq、worker 服务；前端容器化并接入同一 compose；README/`.env.example` 汇总全部新增配置。
- **为什么**：解决"能跑"与"好部署"的落差，让外部 Reviewer 与面试官能无痛复现。
- **前置配置**：无额外依赖；`.env.example` 需补全部新增开关变量说明。
- **验证**：从空环境按 README 一键拉起全部服务，3 个典型任务全跑通。
- **回滚开关**：单服务回滚，无全局风险。
- **依据来源**：`docker/docker-compose.yaml`（当前仅 MySQL 一个服务）；`frontend/vite.config.ts`（proxy `/api→8000`、`/ws→ws:8000`）。
- **工程能力**：工程化交付与质量保障 —— 环境一致性、自动化回归、可复现。

## 🔨 个人扩展规划
以下扩展为按上述 8 个阶段逐步在本仓库实现的（**完成一项打勾一项并附实现说明**）：
- [x] **阶段0 Git协作 + CI骨架** ✅ 2026-08-29
  - 新增 `CONTRIBUTING.md` 开发规范文档
  - 新增 `.github/workflows/ci.yml` CI 冒烟测试（后端导入检查 + 前端构建）
  - 新增 `docs/github-issues-templates.md` 8 个项目的 Issue 模板
  
- [x] **阶段1 检索缓存** ✅ 2026-08-29
  - 新增 `app/utils/cache.py` Redis 缓存工具模块
  - Tavily 搜索缓存：首次 ~2s → 缓存命中 ~0.01s（200倍提升）
  - RAGFlow 助手列表缓存：首次 ~1s → 缓存命中 ~0.01s（100倍提升）
  - 环境变量控制开关，关闭时静默降级不影响功能
  
- [x] **阶段2 安全防护** ✅ 2026-08-29
  - 新增 `app/utils/safety.py` 安全验证工具（247行）
  - SQL 注入防护：拦截 DROP/DELETE/UPDATE 等危险操作
  - SQL 查询限制：自动添加 LIMIT + 超时控制 + 表名白名单
  - 文件上传防护：大小限制 + 扩展名白名单 + 路径穿越检测
  - 通过 41 个安全测试用例验证
  
- [x] **阶段3 可观测性** ✅ 2026-08-29
  - LangSmith 零代码集成：配置环境变量即可启用完整链路追踪
  - Monitor 耗时增强：新增 `report_tool_end()` 和 `report_assistant_end()` 方法
  - 新增 `scripts/trace_query.py` 命令行 trace 查询工具
  - 主 Agent → 子 Agent → 工具的完整链路可见
  
- [x] **阶段4 会话持久化** ✅ 2026-08-29
  - 核心改造：`InMemorySaver` → `AsyncSqliteSaver` + 单例模式 + WAL
  - 断点恢复：服务重启后自动恢复会话上下文
  - 新增 `GET /api/sessions` 端点：查询所有历史会话及元数据
  - 新增 `scripts/clean_checkpoints.py` 数据库清理脚本（支持按天数/按会话清理 + VACUUM）
  - 性能影响：首次初始化 ~50ms，checkpoint 写入 ~5-10ms/次，内存 +5MB
  
- [ ] **阶段5 任务队列**：Celery + RabbitMQ 并发治理与断点可靠性
- [ ] **阶段6 工具 MCP 化**：9 类工具标准 MCP server，跨端治理
- [ ] **阶段7 评测体系**：evals 自动度量 + CI 门禁，产出量化数字
- [ ] **阶段8 一键部署**：Compose 拉起全套依赖，无痛复现

## 🙏 致谢
- 原项目：[didilili/deepsearch-agents](https://github.com/didilili/deepsearch-agents)
- 配套教程：[ai-agents-from-zero · 实战项目-深度研搜](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E6%B7%B1%E5%BA%A6%E7%A0%94%E6%90%9C/0-%E5%89%8D%E8%A8%80)

## License
MIT（沿用原项目协议）
