# ADR-0005：原生 Function Calling 与单 Calculator 执行边界

- 状态：已接受
- 日期：2026-08-25
- 决策者：学习者授权阶段 2，Codex 在阶段范围内实施
- 相关阶段：stage-02
- 取代：ADR-0004 中“工具启用请求同时使用 JSON Mode”的传输选择
- 被取代：[ADR-0006](ADR-0006-tool-registry-and-low-risk-builtins.md) 取代硬编码单工具分发；原生 Function Calling 与程序执行边界仍有效

## 背景

阶段 2 要区分模型的 Function Calling 意图与程序的 Tool Execution。硅基流动当前 Chat Completions 支持 `tools`、`tool_calls` 和 `role=tool`。真实验证发现，`DeepSeek-V4-Flash` 在 `tool_choice=auto` 与 `response_format=json_object` 同时启用时返回了不完整普通 JSON，没有产生工具调用；移除 JSON Mode 后原生工具调用正常。

## 决策驱动因素

- 工具是否执行必须由程序事实证明；
- 非法名称或参数不得映射为任意 Python 调用；
- `12345 × 678`、小数和大整数需要可验证结果；
- 阶段 2 只有一个工具，不提前实现 Registry；
- 必须适配用户当前的 DeepSeek-V4-Flash。

## 候选方案

### 方案 A：解析模型自由文本并调用函数

- 优点：请求简单。
- 缺点：解析脆弱，无法清晰区分意图与执行，安全边界差。

### 方案 B：原生 Function Calling + 硬编码单工具执行器

- 优点：协议结构明确；名称和参数可独立校验；符合阶段范围。
- 缺点：核心循环暂时知道 Calculator；扩展第二个工具会产生分支。

### 方案 C：立即实现 Tool Registry

- 优点：易扩展。
- 缺点：提前实现阶段 3，掩盖单工具闭环的学习重点。

## 决策

采用方案 B。请求只提供一个 `calculator` 定义，模型可通过原生 `tool_calls` 提议调用；程序只接受该名称，用 Pydantic 校验 `operation/a/b`，再用 `Decimal` 执行。禁止 `eval`、动态 import 或按模型名称反射函数。

工具启用请求不同时发送 `response_format`。无工具分支仍要求模型输出约定 JSON，并由 `AgentDecision` 校验；格式错误安全终止。该取舍以真实模型兼容性验证为依据，不代表完全取消结构化校验。

## 后果

### 正面影响

- 调用意图、参数校验、执行和 Observation 在日志中可区分；
- 未知工具、未知操作、缺参、额外字段、错误类型和除零均被拒绝；
- 工具结果通过匹配的 `tool_call_id` 回传模型；
- Calculator 无文件、网络或 Shell 副作用。

### 负面影响与成本

- 普通决策仅靠 Prompt 形成 JSON，再由 Pydantic 拒绝错误格式；
- 当前 Runner 硬编码 Calculator，不能直接增加第二个工具；
- 除法使用 210 位 Decimal 上下文，不代表无限精度；操作数限制为最多 100 位、最多 50 位小数。

### 后续工作

- 阶段 3 用 Tool 接口和 Registry 替换硬编码分支；
- 保留兼容性回归测试，模型或平台行为变化时重新评估 JSON Mode 组合。

## 验证方法

- Fake SDK 验证 `tools`、`tool_choice=auto`、原生 `tool_calls` 和 `tool_call_id`；
- 单元测试验证 Decimal 计算与所有拒绝路径；
- 真实 DeepSeek-V4-Flash 完成 `12345 × 678` 的两步闭环。

## 回滚或迁移方案

若平台未来稳定支持 JSON Mode 与 Function Calling 同时启用，可增加在线兼容性测试后恢复 `response_format`。阶段 3 迁移时保留 Calculator Schema 和执行测试，把分发职责移动到 Registry。

## 相关资料

- [硅基流动 Function Calling](https://docs.siliconflow.cn/cn/userguide/guides/function-calling)
- [硅基流动模型中心](https://www.siliconflow.cn/models)
- [阶段 2 实施记录](../stages/stage-02.md)
