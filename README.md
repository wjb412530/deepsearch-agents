<div align='center'>
  <h1 style="margin-top: 15px;">deepsearch-agents</h1>
  <p><em>DeepAgents 多智能体深度研究系统 · 学习复现与个人扩展仓库</em></p>
</div>

<div align='center'>

![Python](https://img.shields.io/badge/Python-3.12-blue)
![DeepAgents](https://img.shields.io/badge/DeepAgents-0.5.7-1C3C3C.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-WebSocket-009688.svg?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Vite-61dafb.svg?logo=react&logoColor=white)

</div>

> **仓库定位说明**
> 本仓库基于开源教程项目 [didilili/deepsearch-agents](https://github.com/didilili/deepsearch-agents)（[ai-agents-from-zero 教程](https://didilili.github.io/ai-agents-from-zero/)配套实战代码）复现搭建，感谢原作者 [didilili](https://github.com/didilili) 的系统化教程。
> 我在此基础上进行本地部署、代码研读与个人扩展开发（见下方[个人扩展](#-个人扩展规划)章节）。基础框架代码版权归原项目所有。

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

## 🔨 个人扩展规划

原项目定位为教学骨架，刻意不覆盖生产治理能力。以下是我计划在这个基础上亲手实现的扩展（完成的会打勾并附实现说明）：

- [ ] **评测体系**：`evals/` 目录 + 测试问题集，自动化度量任务完成率、工具调用成功率、端到端耗时——让扩展效果可量化
- [ ] **工具层 MCP 化**：将 9 类工具改造为标准 MCP server，验证跨端调度与统一治理
- [ ] **事件持久化与会话恢复**：WebSocket 事件写入 SQLite，支持历史会话回放与断点恢复（替换 `InMemorySaver`）
- [ ] **可观测性接入**：LangSmith / LangGraph trace，逐节点定位长任务瓶颈
- [ ] **检索结果缓存**：Redis 缓存高频检索结果，降低重复任务开销
- [ ] **一键部署**：Docker Compose 拉起前后端 + 全套依赖

## 📝 学习笔记

（记录跟读教程过程中的个人理解与踩坑，按章节追加）

- [DeepAgents 基础与流式解析 →]()

## 🙏 致谢

- 原项目：[didilili/deepsearch-agents](https://github.com/didilili/deepsearch-agents)
- 配套教程：[ai-agents-from-zero · 实战项目-深度研搜](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E6%B7%B1%E5%BA%A6%E7%A0%94%E6%90%9C/0-%E5%89%8D%E8%A8%80)

## License

MIT（沿用原项目协议）
