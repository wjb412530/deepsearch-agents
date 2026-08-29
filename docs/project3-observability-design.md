# 项目 3：可观测性 - 设计简要

## 核心功能

1. **LangSmith Trace 集成** - 利用 LangChain/LangGraph 原生支持自动收集完整链路
2. **工具调用耗时增强** - 在现有 monitor 事件中补充 duration_ms 字段
3. **可选：链路查询脚本** - 按 thread_id 检索 trace 日志

## 主要文件

- `app/api/monitor.py` - 改造 ToolMonitor，添加耗时记录
- `.env.example` - 添加 LangSmith 配置项
- `scripts/trace_query.py` (可选) - 新建链路查询工具

## 技术选型

- **Trace 方案**: LangSmith（LangChain 官方，零代码集成）
- **耗时记录**: 在 `report_tool()` 和 `report_assistant()` 内记录 start_time 和 duration_ms
- **配置方式**: 环境变量启用/关闭，不影响核心功能

## 关键优势

- **最小改动量**: LangChain/LangGraph 自动注入 trace，只需配置环境变量
- **完整链路可见**: 主 Agent → 子 Agent → 工具调用的完整执行树
- **零运行时依赖**: 关闭 tracing 后对性能无任何影响

## 风险评估

- **兼容性风险**: LangSmith 与当前 deepagents 0.5.7 的兼容性（需实测验证）
- **性能影响**: 开启 tracing 后每次工具调用会发送数据到 LangSmith（网络开销约 10-50ms）
- **成本考量**: LangSmith 免费版有调用次数限制（需查阅文档）

## 新增环境变量

```bash
# LangSmith 可观测性配置
LANGSMITH_API_KEY=              # LangSmith API 密钥（从 https://smith.langchain.com 获取）
LANGSMITH_TRACING=              # 启用 tracing: v1 或 true，空值表示关闭
TRACING_PROVIDER=               # trace 提供商，默认 langsmith（预留扩展）
```

## 原子任务分解

### Atom 1: 环境变量配置 (`.env.example`)
- 添加 3 个 LangSmith 相关环境变量
- 添加详细注释说明用途和默认值
- **验证方式**: 检查文件内容格式正确

### Atom 2: LangSmith Trace 验证
- 配置环境变量 `LANGSMITH_TRACING=v1` 和 `LANGSMITH_API_KEY`
- 运行一个简单任务（网络搜索或数据库查询）
- 在 LangSmith 面板验证完整链路可见
- **验证方式**: 
  1. 用户在 https://smith.langchain.com 注册并获取 API Key
  2. 配置环境变量后启动服务
  3. 提交一个测试任务
  4. 在 LangSmith 面板查看是否出现 trace 记录
  5. 确认主 Agent → 子 Agent → 工具的完整调用链
- **降级方案**: 如果 LangSmith 集成失败，清空 `LANGSMITH_TRACING` 继续原有流程

### Atom 3: Monitor 耗时增强 (`app/api/monitor.py`)
- 修改 `report_tool()` 方法，记录工具调用开始时间
- 修改 `report_assistant()` 方法，记录子智能体调用开始时间
- 在事件数据中添加 `duration_ms` 字段
- 修改事件结构，支持 start/end 两阶段上报
- **验证方式**: 
  1. 运行测试任务
  2. 在 WebSocket 事件中检查是否包含 `duration_ms` 字段
  3. 验证耗时数据合理性（非负数，单位毫秒）

### Atom 4 (可选): 链路查询脚本 (`scripts/trace_query.py`)
- 创建脚本，使用 LangSmith API 按 thread_id 查询 trace
- 输出格式化的调用链路和耗时数据
- **验证方式**: 运行脚本，传入已知 thread_id，输出完整链路

## 回滚方案

- 设置 `LANGSMITH_TRACING=` (空值) 关闭 tracing，系统恢复原有行为
- Monitor 耗时字段为增量功能，前端可选择性使用
- 链路查询脚本为独立工具，不影响主流程

## 验证标准

- ✅ LangSmith 面板可见主 Agent → 子 Agent → 工具的完整链路
- ✅ 可定位最慢节点的耗时数据
- ✅ 关闭 tracing 后系统正常运行（性能无退化）
- ✅ WebSocket 事件包含 `duration_ms` 字段
- ✅ 耗时数据准确反映实际执行时间

## 实施注意事项

1. **LangSmith 账号准备**: 用户需要先在 https://smith.langchain.com 注册账号并获取 API Key
2. **渐进式验证**: 先验证 LangSmith 基础集成，再添加耗时增强
3. **兼容性测试**: 确认 deepagents 0.5.7 与 LangSmith 的兼容性
4. **网络依赖**: LangSmith 需要网络连接，离线环境下需要关闭 tracing
