# deepsearch-agents 开发贡献指南

> 本项目采用**单人开发模式**，所有改动直接在 `main` 分支上进行

## 开发模式

- **分支策略**：直接在 `main` 分支开发，不设置分支保护，不走 feature 分支 / PR 流程
- **核心原则**：每次改动必须保持 `main` 分支始终可运行，失败即回滚
- **降级优先**：所有新功能都配备降级开关（环境变量），确保可以安全回退

## Commit 规范

延续项目现有的 commit message 格式，使用以下前缀：

- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `chore:` - 构建/工具/依赖更新
- `refactor:` - 代码重构（不改变功能）
- `test:` - 测试相关
- `style:` - 代码格式调整

**示例**：
```
feat: add Redis caching for Tavily search results
fix: handle Windows console encoding in baseline script
docs: update improvement plan with RAGFlow status
chore: add langsmith dependency for tracing
```

## 开发流程

### 1. 改动前

- 确认当前 `main` 分支处于健康状态（能正常运行）
- 检查 `docs/improvement-plan-solo.md` 确认当前任务的目标和约束
- 在 `docs/execution-log.md` 中标记任务开始

### 2. 开发中

- 遵循原子化交付原则（Vibe Coding）：每个功能点完成后立即验证
- 新增环境变量时必须同步更新 `.env.example` 并添加说明
- 新增依赖时使用 `uv add <package>` 确保 `pyproject.toml` 同步
- 保持代码风格与项目现有代码一致

### 3. 验证

每次改动后必须验证：

- **功能验证**：改动的功能正常工作
- **回归验证**：原有功能不受影响
- **回滚验证**：降级开关（如有）能正常回退

验证命令示例：
```bash
# 后端冒烟测试
uv run python -c "import app.api.server; print('backend smoke ok')"

# 启动服务测试
uv run uvicorn app.api.server:app --port 8000 --reload

# 前端构建测试
cd frontend && pnpm install && pnpm build
```

### 4. 回滚机制

如果改动导致问题：

1. 立即停止当前工作
2. 使用降级开关（环境变量）回退到改动前状态
3. 如果无降级开关，使用 `git revert` 回退 commit
4. 在 `docs/execution-log.md` 中记录问题和回滚操作
5. 分析根因后再重新开始

## 项目改进计划

本项目正在进行系统性改进，详细计划见 `docs/improvement-plan-solo.md`。

**改进项目清单**：
0. ✅ 前置：环境基线锁定
1. ⏳ 项目 0：Git 协作规范 + CI 骨架（当前）
2. ⏳ 项目 1：Redis 缓存
3. ⏳ 项目 2：安全防护
4. ⏳ 项目 3：可观测性
5. ⏳ 项目 4：会话持久化
6. ⏳ 项目 5：任务队列（Celery + RabbitMQ）
7. ⏳ 项目 6：MCP 工具层
8. ⏳ 项目 7：评测体系
9. ⏳ 项目 8：一键部署

执行进度追踪见 `docs/execution-log.md`。

## 代码规范

### Python (后端)

- 遵循 PEP 8 规范
- 使用类型注解（Type Hints）
- 函数/类添加 docstring 说明
- 复杂逻辑添加注释

### TypeScript/React (前端)

- 使用 TypeScript 严格模式
- 组件使用函数式组件 + Hooks
- 遵循 React 最佳实践
- 使用有意义的变量/组件命名

## 文件组织

- **新增工具**：放在 `app/tools/` 目录
- **新增 Agent**：放在 `app/agent/subagents/` 目录
- **新增脚本**：放在 `scripts/` 目录
- **文档**：放在 `docs/` 目录
- **配置示例**：更新 `.env.example`
- **生成文件**：输出到 `app/output/session_{thread_id}/`

## 依赖管理

- 使用 `uv` 管理 Python 依赖
- 使用 `pnpm` 管理前端依赖
- 新增依赖时在 `.env.example` 中说明相关环境变量

## 安全要求

- **不提交敏感信息**：API keys、密码等写入 `.env`（已在 `.gitignore` 中）
- **SQL 查询**：使用参数化查询，避免 SQL 注入
- **文件上传**：限制文件大小和类型
- **输入验证**：对用户输入进行验证和清理

## 获取帮助

- 查看 `README.md` 了解项目快速开始
- 查看 `CLAUDE.md` 了解项目架构和开发模式
- 查看 `docs/improvement-plan-solo.md` 了解改进计划详情
- 查看 `docs/baseline.md` 了解性能基线数据

---

**记住**：保持 `main` 分支始终健康可运行是第一优先级！
