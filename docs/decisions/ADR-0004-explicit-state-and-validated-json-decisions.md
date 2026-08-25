# ADR-0004：显式状态与经过校验的 JSON 决策

- 状态：已接受
- 日期：2026-08-25
- 决策者：学习者授权阶段 1，Codex 在阶段范围内实施
- 相关阶段：stage-01
- 取代：无
- 被取代：无

## 背景

阶段 0 只有一次文本生成。阶段 1 需要可测试的 Agent Loop，并保证模型格式错误不能导致无限循环或伪造成功。当前模型服务提供 OpenAI 兼容 Chat Completions 和 JSON Mode。

## 决策驱动因素

- 教学上必须能看见状态、步骤和终止原因；
- 模型输出是不可信输入，不能直接驱动控制流；
- 离线测试需要绕过真实网络并脚本化每个决策；
- 本阶段不能提前加入工具、记忆或通用 Agent 框架。

## 候选方案

### 方案 A：自由文本约定

- 优点：代码少。
- 缺点：解析脆弱，字段缺失难以可靠拒绝，终止条件不清晰。

### 方案 B：JSON Mode + Pydantic + 程序循环

- 优点：Schema 明确、错误可控、状态转换可离线测试。
- 缺点：增加 Pydantic 直接依赖；JSON Mode 仍不能保证业务字段有效。

### 方案 C：引入成熟 Agent 框架

- 优点：现成功能多。
- 缺点：掩盖核心机制，并提前引入本阶段不需要的抽象。

## 决策

采用方案 B。模型只产生 `continue`、`complete` 或 `fail` 决策；Pydantic 校验数据；`AgentRunner` 独立维护步数和最终状态。日志只包含公开行动与观察，不请求或保存隐藏思维链。

## 后果

### 正面影响

- 五类终止路径可确定性测试；
- 模型无法自行提高最大步数或绕过状态机；
- 后续阶段可在同一循环边界接入受控工具。

### 负面影响与成本

- 每个循环步骤需要一次模型请求；
- JSON 截断或字段不合法会作为不可恢复错误终止；
- 当前 `action` 只是公开描述，没有真实外部行动。

### 后续工作

- 阶段 2 在程序控制的执行边界内加入一个 Calculator；
- 后续可靠性阶段再评估结构化输出重试、超时和预算。

## 验证方法

使用脚本化 Decision Maker 覆盖完成、主动失败、步数上限、取消和模型错误；使用 Fake SDK 验证 JSON Mode 参数及 Schema；最后执行一次真实模型烟雾测试。

## 回滚或迁移方案

若供应商的结构化输出能力变化，可保留 `DecisionMaker` 和 `AgentDecision` 边界，仅替换 Client 的解析方式。除非有测试证据，不移除程序级校验和终止预算。

## 相关资料

- [硅基流动 JSON Mode](https://docs.siliconflow.cn/cn/userguide/guides/json-mode)
- [硅基流动 Chat Completions](https://docs.siliconflow.cn/cn/api-reference/chat-completions/chat-completions)
- [阶段 1 实施记录](../stages/stage-01.md)
