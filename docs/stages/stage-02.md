# 第 2 阶段：单工具与 Function Calling

- 状态：已完成
- 开始日期：2026-08-25
- 完成日期：2026-08-25
- 开始前 commit：`9158238`（tag `stage-01`）
- 完成 commit：本文件所在提交，以 `stage-02` tag 定位
- Git tag：`stage-02`
- 相关 ADR：[ADR-0005](../decisions/ADR-0005-native-function-calling-with-single-calculator.md)

## 1. 本阶段学习目标

- 理解 Tool、Function Calling 与 Tool Execution 的边界；
- 让模型第一次提出结构化外部能力调用；
- 由程序校验 Calculator 参数并执行，而不是信任模型；
- 将真实结果作为 Observation 回到 Agent Loop，再生成最终回答。

## 2. 上一阶段回顾

阶段 1 已有 `AgentState`、`AgentDecision`、最大步数和五类终止原因，但 `action` 只是公开说明，没有外部行动。当前限制是模型可能知道计算方法，却没有可由程序验证的工具执行证据。本阶段解决“模型提出调用后，谁真正执行并证明结果”的问题。

## 3. 本阶段新增概念

- Tool：程序暴露的一项受限能力，本阶段只有无副作用 Calculator。
- Function Calling：模型以 `tool_calls` 表达名称和 JSON 参数；它只是请求，不是执行。
- Tool Execution：程序校验名称和参数后运行 Calculator。
- Tool Observation：程序记录成功结果或受控错误，并用同一 `tool_call_id` 回传模型。
- 工具 Schema：描述 `calculator(operation, a, b)` 的允许输入。

## 4. 为什么需要这个能力

语言模型按 Token 生成文本，不能把“它写出一个算式答案”当作可靠执行证据。Function Calling 提供结构化意图，但仍不能自动获得权限。程序必须掌握白名单、Schema 和真实执行，才能区分“模型想调用”与“工具已经返回”。

## 5. 架构变化

```text
Goal -> Model + calculator schema
             |
        native tool_calls
             |
  name check -> Pydantic arguments -> Decimal Calculator
                                        |
                                  ToolObservation
                                        |
                    matching tool_call_id -> Model
                                        |
                               validated final answer
```

模型不能直接调用 Python 函数。`AgentRunner` 当前硬编码唯一 Calculator，这是阶段 2 的有意限制，不是可扩展 Registry。

## 6. 项目目录变化

### 新增

- `src/small_agent/calculator.py`
- `tests/test_calculator.py`
- `docs/decisions/ADR-0005-native-function-calling-with-single-calculator.md`
- `docs/stages/stage-02.md`

### 修改

- `state.py`：增加 `TOOL_CALL`、`ToolCallRequest` 和 `ToolObservation`。
- `agent.py`：增加单 Calculator 执行和 Observation 写入。
- `llm.py`：发送工具 Schema，解析 `tool_calls`，重建 Assistant/Tool 消息。
- `cli.py`：区分调用意图、程序执行、参数、结果和错误。
- 测试、README、架构、阶段、开发、故障和 ADR 索引文档。
- `pyproject.toml`：版本从 `0.1.0` 更新为 `0.2.0`。

### 删除与依赖

- 删除文件：无。
- 新增第三方依赖：无；继续使用 OpenAI SDK、Pydantic 和 pytest。
- `requirements.lock` 仅更新验证阶段说明，具体版本未变化。

## 7. 实现步骤

1. 根据官方 Function Calling 格式定义 Calculator tool Schema。
2. 使用 Pydantic 定义操作与有限十进制参数，拒绝额外字段。
3. 用 `Decimal` 实现加减乘除，设置明确位数边界和内部精度。
4. 扩展状态，保存原生调用 ID、规范化参数、输出或错误。
5. 在 Runner 中硬编码唯一工具执行路径，并把 Observation 返回下一轮。
6. 增加 Fake SDK、控制流、CLI 和 Calculator 测试。
7. 修复 JSON number 先转浮点导致 Decimal 精度丢失的问题。
8. 对照真实模型修复 JSON Mode/Function Calling 兼容性问题。

## 8. 项目代码与关键接口

- `CALCULATOR_TOOL_DEFINITION`：发给模型的名称、描述和 JSON Schema。
- `CalculatorArguments`：`operation/a/b` 的程序级 Schema。
- `Calculator.execute(arguments_json)`：返回规范化参数和字符串结果，或抛出受控 `ToolExecutionError`。
- `ToolCallRequest`：模型调用意图。
- `ToolObservation`：程序执行事实，成功时只有 output，失败时只有 error。
- `SiliconFlowLLMClient.decide`：在原生工具调用与普通 JSON 决策间分流。

从阶段 1 迁移不需要修改 `.env`。CLI 输出新增工具字段；注入式 `DecisionMaker` 测试仍兼容。若最大步数设为 1，工具执行后没有预算生成最终答案，因此计算闭环建议至少为 2。

## 9. 如何运行

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
small-agent
```

示例目标：

```text
计算 12345 × 678，必须使用 Calculator 工具，并用一句话回答。
```

预期看到第一步 `tool_call`、工具执行结果 `8369910`，随后第二步 `complete` 和最终答案。

## 10. 测试与验收

- 正常案例：`12345 × 678 = 8369910`，调用后完成。
- 小数案例：`0.1 + 0.2 = 0.3`，避免二进制浮点误差。
- 大数案例：40 位整数相乘保持精确。
- 边界：每个操作数最多 100 位、最多 50 位小数；除法使用 210 位 Decimal 上下文。
- 失败：除零、缺参、错误类型、未知 operation、额外字段和未知工具均被拒绝。
- 协议：一次只允许一个调用；工具结果使用匹配的 `tool_call_id` 回传。
- 自动化：`.venv/bin/python -m pytest`，结果 `46 passed in 0.52s`。
- 真实验收：DeepSeek-V4-Flash 完成两次模型请求和一次本地 Calculator 执行，退出码 0。

## 11. 执行过程示例

```text
步骤 1
决策：tool_call
工具调用意图：calculator
工具执行：成功
工具参数：{"operation":"multiply","a":"12345","b":"678"}
工具结果：8369910
步骤 2
决策：complete
终止原因：task_completed
助手：12345 × 678 = 8,369,910。
```

这里的调用意图来自模型，参数校验和结果来自程序。日志不包含隐藏思维链。

## 12. 常见问题与排查方法

### 没有产生 tool_calls

检查模型是否支持工具调用、请求是否包含 `tools`，以及是否错误组合了当前模型不兼容的参数。阶段 2 的实测问题见 TR-0003。

### 参数被拒绝

查看 Tool Observation 的错误类别。不要通过 `eval` 或移除 `extra=forbid` 绕过；应让模型下一步纠正参数或明确失败。

### 达到最大步数

Calculator 调用和最终回答是两个模型步骤。确保 `AGENT_MAX_STEPS >= 2`，默认值 3 已满足。

## 13. 当前版本的能力边界

### 当前可以

- 原生请求一个 Calculator 调用；
- 精确处理规定范围内的加减乘除；
- 安全拒绝非法调用并把错误作为 Observation；
- 基于真实结果生成最终回答；
- 从日志区分意图、执行和结果。

### 当前不能

- 没有 Tool Registry 或第二个工具；
- 不能访问时间、文件、Shell、网络或外部 API；
- 工具错误没有自动重试策略；
- 没有权限策略、人工审批、统一 Tool 接口或超时；
- 没有记忆、RAG、规划、MCP 或 Multi-Agent。

当前仍是教学 Demo，不是生产级计算服务；Decimal 除法有明确但有限的精度。

## 14. 本阶段总结

阶段 2 把 `Act` 从一句描述变成了可验证程序行为。最重要的控制权没有交给模型：模型只选工具和参数，Pydantic 决定输入是否合法，Python 决定是否执行，Tool Observation 记录真实结果。阶段 3 才会解决多个硬编码分支不可维护的问题。

## 15. 小红书学习笔记草稿

### 可选标题

1. AI 说“我算过了”不算数：亲手实现第一个 Tool Calling
2. Function Calling 不是函数执行，我终于把这三层分清了
3. 从 Agent Loop 到 Calculator：模型只提议，Python 才有执行权

### 正文

今天给自己的最小 Agent 加入了第一个真实工具：Calculator。表面上只是算 `12345 × 678`，真正重要的是把三件事彻底分开。

第一层是 Function Calling：模型返回工具名和 JSON 参数，意思只是“我建议这样调用”。第二层是参数校验：程序检查名称是不是唯一允许的 calculator、operation 是否属于加减乘除、数字是否合法、有没有多余字段。第三层才是 Tool Execution：Python 使用 Decimal 真正计算，并把结果作为 Observation 返回模型。只有这条记录能证明工具执行过，模型自己写一句“已经调用工具”不算。

这次还踩到一个真实兼容性坑：DeepSeek-V4-Flash 同时收到 JSON Mode 和自动工具选择时，没有返回 tool_calls。做了对照请求后，我保留原生 Function Calling、移除这个组合里的 JSON Mode，同时继续用 Pydantic 校验普通决策。修复后，Agent 第一步请求 Calculator，程序得到 8369910，第二步模型再据此回答。

目前共有 46 个离线测试，覆盖 0.1+0.2、大整数、位数上限、除零、缺参、错误类型、未知操作和未知工具。下一阶段才会做 Tool Registry，让第二个、第三个工具不再靠硬编码分支。#AIAgent #FunctionCalling #Python #大模型开发 #从零学习

## 16. 下一阶段预告

阶段 3 将引入统一 Tool 接口、Tool Registry、多工具路由、结果标准化和低风险工具。不会在获得确认前实现。

## 17. 文档与交接检查

- [x] `architecture.md` 当前架构已更新
- [x] `stage-specification.md` 阶段 2 已标记完成
- [x] `troubleshooting.md` 已记录真实兼容性问题
- [x] ADR-0005 已记录 Function Calling 和执行边界
- [x] 环境变量与依赖说明一致
- [x] 46 个离线测试与真实模型验收已记录
- [x] 未记录 API Key 或隐藏思维链
- [x] Git commit/tag 已通过 `stage-02` 定位

## 18. 待确认项

- 阶段 3 的统一 Tool 接口、Registry 重复注册语义和新增低风险工具将在进入阶段后确认。
- 阶段 2 的提交和 tag 使用 `stage-02` 定位。

## 19. 等待确认

阶段 2 已完成并停止。只有学习者明确确认“进入阶段 3”或表达同等意图后，才开始多工具与 Registry。
