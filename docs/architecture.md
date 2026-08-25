# 架构说明

## 1. 文档规则

本文件同时描述“当前架构”和“最终目标架构”，二者不得混用：

- 当前架构只记录仓库中已经存在并通过检查的事实。
- 目标架构是路线方向，不代表相应模块、接口或依赖已经存在。
- 每完成一个阶段，必须先以代码和测试为依据更新当前架构，再更新阶段状态。
- 重要、长期且存在权衡的架构选择应记录 ADR，而不是只修改架构图。

## 2. 当前架构

更新时间：2026-08-25。

当前已完成阶段 1：显式状态、受限 Agent Loop、离线测试和硅基流动真实模型验收均已通过。阶段 2 尚未开始。

```text
small-agent/
├── .env.example             # 不含真实 Secret 的配置示例
├── pyproject.toml           # 项目元数据和固定直接依赖
├── requirements.lock        # 经验证环境的完整固定依赖
├── src/small_agent/
│   ├── __main__.py          # python -m small_agent 入口
│   ├── cli.py               # 任务输入和公开步骤输出
│   ├── config.py            # API、模型和最大步数配置
│   ├── state.py             # 状态、步骤、决策和终止枚举
│   ├── agent.py             # 受最大步数约束的 Agent Loop
│   ├── chat.py              # 阶段 0 单次生成能力（保留）
│   └── llm.py               # 文本生成与 JSON 决策 Client
├── tests/                   # Fake Decision Maker/SDK 离线测试
└── docs/                    # 需求、架构、阶段和交接文档
```

当前执行流：

```text
CLI 任务目标 -> Settings -> AgentRunner -> AgentState
                                  |
                                  v
                     SiliconFlowLLMClient.decide
                                  |
                     JSON Mode Chat Completions
                                  |
                     Pydantic AgentDecision 校验
                                  |
                     记录公开 Step 并判断终止
                                  |
                   continue 时回到 AgentRunner
                                  |
                         CLI 展示步骤和结果
```

System、User、Assistant 在当前决策调用中的对应关系：

- System：`messages` 中角色为 `system` 的固定提示，约束助手角色和回答风格。
- User：任务目标、步数预算和此前公开步骤组成的 JSON 上下文。
- Assistant：Chat Completions 返回并由 Pydantic 校验的 JSON 决策。

当前仍不存在：

- 工具、记忆、RAG、MCP 或 Multi-Agent；
- 仓库中的真实 API Key或跨轮会话；
- 运行时日志、数据库或向量索引。

当前程序是教学用最小 Agent：模型可选择继续、完成或主动失败，程序负责校验、记录状态并强制终止。它没有行动工具，`action` 只是公开说明，不代表发生了外部副作用。

## 3. 已确定的架构原则

这些原则来自项目需求，具体实现仍需在对应阶段确认：

1. 使用显式状态而不是只依赖聊天历史。
2. 模型决策、参数校验、权限检查和工具执行分离。
3. 模型输出、外部文档和工具结果均视为不可信输入。
4. Agent Loop 必须具有外部可验证的终止条件和预算。
5. Short-term Memory、Long-term Memory 与 RAG 分工明确。
6. 本地 Tool 和 MCP Tool 最终通过受控适配接入统一执行边界。
7. 测试与评估贯穿阶段演进。
8. 抽象在出现实际复用需求后提炼，不为未来假设过度设计。
9. 同步实现起步，只有明确需要时才引入异步。
10. Agent Runtime 与具体业务 Agent 在最终框架中分离。

## 4. 架构演进

### 4.1 阶段 0：一次 LLM 调用

```text
CLI Input -> Prompt/Messages -> Official LLM SDK -> Assistant Output
                                ^
                         Environment Config
```

该结构已经实现，并通过离线测试及一次真实 API 手动验收。它还不是 Agent。

### 4.2 阶段 1：显式状态循环

```text
Goal -> State -> Decide -> Act -> Observe -> Update State
           ^                                      |
           +---------- Continue or Stop ----------+
```

终止原因包括完成、主动失败、最大步数、用户取消和不可恢复错误。

该结构已实现。当前五类终止原因分别为 `task_completed`、`active_failure`、`max_steps_reached`、`user_cancelled` 和 `unrecoverable_error`；最大步数限制为 1～10，默认 3。

### 4.3 阶段 2～4：工具与安全边界

```text
Agent Loop
    |
    v
Structured Tool Call
    |
    v
Schema Validation -> Permission Policy -> Human Approval if needed
                                              |
                                              v
Observation <- Result Normalization <- Restricted Tool Execution
```

模型只能提出调用意图，程序拥有最终执行权。

### 4.4 阶段 5～7：上下文、记忆和检索

```text
                     +-> Working Memory / Task State
Context Builder -----+-> Long-term Memory / SQLite
                     +-> Retriever -> Vector Store -> Source Documents
                     +-> Recent Messages / Summaries
```

四种信息源进入 Prompt 前需要选择、排序、裁剪和来源标注。

### 4.5 阶段 8～10：复杂任务与外部能力

```text
Goal -> Planner -> Plan -> Executor -> Local Tool Registry
           ^                  |             |
           |                  |             +-> MCP Tool Adapter -> MCP Client -> MCP Server
           +---- Replanner <--+

Optional Multi-Agent Coordinator
    +-> Planner Agent
    +-> Executor Agent
    +-> Reviewer Agent
```

Multi-Agent 是待后期验证的任务分工方式，不是所有任务的默认结构。

### 4.6 阶段 11～13：评估、框架和工程可靠性

```text
                         +-> Prompt / Context Builder
                         +-> State / Loop / Planning
Business Agent Config -> Agent Runtime -> Tool and MCP Gateway
                         +-> Memory / Retrieval
                         +-> Policy / Budget / Approval
                         +-> Trace / Checkpoint / Evaluation
```

## 5. 最终目标模块

| 模块 | 计划职责 | 首次引入阶段 |
|---|---|---:|
| `models` | 官方 SDK 调用、模型响应和使用量 | 0 |
| `prompts` | 角色、任务、输出格式和上下文组装 | 0，后续演进 |
| `state` | 目标、步骤、Observation、错误、预算和终止状态 | 1 |
| `agent` | 状态转换循环和最终 Runtime | 1 / 12 |
| `tools` | Tool 接口、Registry、校验、执行和权限 | 2～4 |
| `memory` | 当前任务工作记忆和跨会话持久记忆 | 5～6 |
| `retrieval` | 文档、切分、Embedding、索引、检索和来源 | 7 |
| `planning` | Plan、Executor、Replanner 和策略 | 8 |
| `mcp` | Client、Server 和 Tool Adapter | 9 |
| `multi_agent` | 角色协议、协调、共享状态和全局终止 | 10 |
| `evaluation` | 数据集、运行器、指标和报告 | 11 |
| `observability` | Run ID、结构化日志、Trace 和成本 | 13 |

模块名和边界是目标草案；只有在对应阶段实现并记录后才成为当前架构。

## 6. 核心数据流约束

最终预期的单轮安全执行链如下：

```text
Untrusted Input
  -> Context Selection
  -> Model Decision
  -> Structured Parsing
  -> Schema Validation
  -> Permission and Budget Check
  -> Optional Human Approval
  -> Restricted Execution
  -> Result Sanitization
  -> Observation
  -> State Update
  -> Stop or Next Step
```

任何跳过校验或权限检查的快捷路径都必须被视为架构缺陷。

## 7. 持久化边界

计划中可能持久化的数据：

- Long-term Memory 及其来源、时间和删除状态；
- RAG 文档元数据、Chunk 与向量索引；
- 后期运行 Trace、预算使用量和恢复 Checkpoint；
- 评估数据集和不含敏感信息的评估结果。

默认不持久化：

- API Key 和其他 Secret；
- 模型隐藏思维链；
- 未经用户允许的全部聊天原文；
- 超出任务需要的文件或工具输出。

## 8. 当前架构决策与待确认项

- 阶段 0 已决定使用 OpenAI SDK 3.3.1 调用硅基流动 Chat Completions API，默认模型为 `deepseek-ai/DeepSeek-V4-Flash`，见 [ADR-0003](decisions/ADR-0003-use-siliconflow-deepseek-v4-flash.md)；
- 当前环境已决定使用 venv + pip，见 [ADR-0002](decisions/ADR-0002-use-venv-and-pip.md)；
- 阶段 1 已决定采用 Pydantic v2 状态模型、JSON Mode 决策和程序控制终止，见 [ADR-0004](decisions/ADR-0004-explicit-state-and-validated-json-decisions.md)；
- 阶段 4 的 Shell 允许列表范围；
- Token 估算来源与预算算法；
- Embedding 模型和向量存储；
- MCP SDK 版本、transport 和异步边界；
- Framework 的最终扩展接口。

除已链接 ADR 的事项外，其余事项不得仅凭路线图转为“已决定”。

## 9. 阶段完成时的更新方法

每次阶段完成后：

1. 更新“当前架构”的日期、目录、模块和能力。
2. 增加或更新真实数据流图。
3. 将已经实现的模块从“目标”转述为可核对的事实。
4. 删除已经不成立的当前限制，新增实际限制。
5. 检查核心数据流是否存在绕过安全边界的路径。
6. 链接相关 ADR 和阶段记录。
7. 对照实际文件、测试和锁文件逐项核验。
