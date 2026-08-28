# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**deepsearch-agents** is a multi-agent deep research system built with DeepAgents framework. It orchestrates a main agent with three specialist sub-agents (network search, database query, RAGFlow knowledge base) to handle complex research tasks involving multiple information sources, file uploads, and document generation (Markdown/PDF).

The system uses FastAPI for HTTP/WebSocket APIs, React for the frontend, and DeepAgents for agent orchestration. Tasks execute asynchronously in the background with real-time progress updates pushed via WebSocket.

## Commands

### Backend

```bash
# Install dependencies (using uv)
uv sync

# Start backend server (development with auto-reload)
uv run uvicorn app.api.server:app --host 0.0.0.0 --port 8000 --reload

# Run a specific example script
uv run python examples/1-deep-agent-quickstart-search.py

# Start local MySQL (teaching data)
docker compose -f docker/docker-compose.yaml up -d

# Stop MySQL
docker compose -f docker/docker-compose.yaml down
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev          # Development server
pnpm build        # Production build
```

## Architecture

### Multi-Agent Structure (Orchestrator-Workers Pattern)

- **Main Agent** (`app/agent/main_agent.py`): Task planning, sub-agent coordination, result synthesis, file delivery
  - Tools: `read_file_content`, `generate_markdown`, `convert_md_to_pdf`
  - Sub-agents: network search, database query, RAGFlow knowledge base

- **Network Search Agent** (`app/agent/subagents/network_search_agent.py`): Public internet search via Tavily
  - Tools: `internet_search`

- **Database Query Agent** (`app/agent/subagents/database_query_agent.py`): MySQL structured data queries
  - Tools: `list_sql_tables`, `get_table_data`, `execute_sql_query`

- **RAGFlow Agent** (`app/agent/subagents/knowledge_base_agent.py`): Private knowledge base queries
  - Tools: `get_assistant_list`, `create_ask_delete`

### Core Execution Flow

```
User Task → FastAPI /api/task
  → run_deep_agent (background asyncio.Task)
  → Main Agent analyzes task
  → Dispatches to sub-agents (network/database/RAGFlow)
  → Sub-agents call tools and return results
  → Main Agent synthesizes results
  → Generates Markdown/PDF if requested
  → monitor pushes events via WebSocket /ws/{thread_id}
  → Frontend displays progress and results
```

### Session Isolation

- **ContextVar** (`app/api/context.py`): `thread_id` and `session_dir` propagate through tool calls without explicit parameters
- **Session Directory**: Each task gets `app/output/session_{thread_id}/` for generated files
- **Upload Directory**: User uploads land in `app/updated/session_{thread_id}/`, then copied to session output dir before agent execution
- **Checkpointer**: `InMemorySaver` in main_agent uses `thread_id` to maintain conversation context across multiple turns

### Real-Time Communication

- **WebSocket Manager** (`app/api/monitor.py`): Tracks WebSocket connections by `thread_id`
- **Event Types**: `tool_call`, `assistant_call`, `task_result`, `task_cancelled`, `error`, `session_dir`
- **Lifecycle**: FastAPI lifespan binds event loop to manager; background agent tasks emit events via `monitor.report_*()` methods

## Key Files and Responsibilities

- `app/agent/main_agent.py`: Main agent assembly, `run_deep_agent()` entry point
- `app/agent/llm.py`: OpenAI-compatible model initialization
- `app/agent/prompts.py`: Loads prompts from `app/prompt/prompts.yml`
- `app/prompt/prompts.yml`: System prompts for main agent and all sub-agents
- `app/api/server.py`: FastAPI routes (`/api/task`, `/api/upload`, `/api/files`, `/api/download`, `/ws/{thread_id}`)
- `app/api/context.py`: ContextVar for `session_dir` and `thread_id`
- `app/api/monitor.py`: WebSocket event emission
- `app/tools/`: Tool implementations (Tavily, MySQL, RAGFlow, file reading, Markdown/PDF generation)
- `docker/docker-compose.yaml`: Local MySQL with teaching data (pharma products, inventory, sales)

## Configuration

- **Environment**: Copy `.env.example` to `.env` and configure:
  - `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `LLM_QWEN_MAX`: LLM endpoint and model
  - `TAVILY_API_KEY`: Tavily search API key
  - `RAGFLOW_API_URL`, `RAGFLOW_API_KEY`: RAGFlow service connection
  - `MYSQL_*`: MySQL connection parameters (default port 3307 to avoid conflicts)

- **Prompts**: Edit `app/prompt/prompts.yml` to modify agent behavior. Changes take effect on next agent creation (server restart in development).

## Development Patterns

### Adding a New Tool

1. Create tool function in `app/tools/` (use `@tool` decorator from LangChain)
2. Import and add to appropriate agent's `tools=[]` list in `app/agent/subagents/` or `app/agent/main_agent.py`
3. Update agent's system prompt in `app/prompt/prompts.yml` to describe the new tool

### Adding a New Sub-Agent

1. Create agent file in `app/agent/subagents/`
2. Use `create_deep_agent()` with model, tools, and system prompt from `prompts.yml`
3. Add to main agent's `subagents=[]` list in `app/agent/main_agent.py`
4. Add agent description and system prompt to `app/prompt/prompts.yml` under `sub_agents`

### Working with Session Context

Tools that need access to current session directory or thread_id should import from `app/api/context.py`:

```python
from app.api.context import get_session_context, get_thread_context

session_dir = get_session_context()  # Returns absolute path string
thread_id = get_thread_context()     # Returns thread_id string
```

### Emitting WebSocket Events

From within agent execution or tool calls:

```python
from app.api.monitor import monitor

monitor.report_tool_call("tool_name", {"arg": "value"})
monitor.report_assistant("assistant_name", {"description": "..."})
monitor.report_task_result("Final answer text")
monitor.report_task_cancelled()
monitor._emit("error", "Error message")
```

## Testing with Branch History

This repository uses git branches to track tutorial progression. Each branch corresponds to a tutorial chapter:

- `02-quickstart-streaming`: DeepAgents basics
- `03-deepagents-subagents-async`: Sub-agents and async execution
- `04-deepagents-langgraph-langchain`: LangGraph and LangChain integration
- `05-deepagents-hitl-interrupt`: Human-in-the-loop
- `06-deepagents-backends-memory`: Long-term memory backends
- `07-deepagents-middleware-governance`: Middleware and skills
- `09-deepsearch-core-config`: Project initialization
- `10-deepsearch-network-subagent`: Network search agent
- `11-deepsearch-database-subagent`: Database query agent
- `12-deepsearch-ragflow-subagent`: RAGFlow agent
- `13-deepsearch-main-agent`: Main agent with file tools
- `14-deepsearch-api-websocket`: FastAPI and WebSocket (current/main)

Use `git checkout <branch>` to view code at different stages.

## Important Constraints

- **File Operations**: All generated files MUST go to `app/output/session_{thread_id}/`. Tools use absolute paths; prompts use relative paths (relative to `app/` directory).
- **Upload Files**: When reading uploaded files, use filename only (no path prefix) with `read_file_content` tool.
- **Concurrent Tasks**: Only one active task per `thread_id`. New task on same `thread_id` cancels previous task.
- **WebSocket Lifecycle**: Frontend must establish WebSocket connection to `/ws/{thread_id}` before or immediately after submitting task to receive progress updates.
- **RAGFlow Dependency**: RAGFlow is external service not included in docker-compose. Tasks requiring private knowledge base need working RAGFlow instance.

## Python Version

Requires Python 3.12 (not 3.13). Uses `uv` for dependency management.
