# ADR-0006：统一 Tool Registry 与低风险内置工具

- 状态：已接受
- 日期：2026-08-25
- 决策者：学习者授权阶段 3，Codex 在阶段范围内实施
- 相关阶段：stage-03
- 取代：ADR-0005 的硬编码单工具分发
- 被取代：无

## 背景

阶段 2 的 Runner 直接判断 Calculator 名称，增加第二个工具就必须继续增加分支。阶段 3 需要集中提供模型工具描述、拒绝重复名称、统一参数校验和结果，同时限制新工具为低风险能力。

## 决策

采用 `BaseTool`、`ToolRegistry`、`ToolResult` 三层。Tool 声明名称、描述、参数模型、JSON Schema 和执行方法；Registry 负责注册、去重、生成 `tools` 列表及按名称分发；Result 统一成功、参数错误、执行错误和未知工具。Agent Runner 只调用 Registry，不认识具体工具名。

默认注册 Calculator、UTC 时间、文本统计和受限文本文件读取。`AgentRunner` 持有单次运行唯一 Registry：每次调用 DecisionMaker 时传入该 Registry 生成模型工具定义，工具调用随后仍由同一实例执行。Client 和 Runner 不再各自创建默认 Registry。

文件读取根目录为启动时工作区，只允许非隐藏相对路径、`.txt/.md`、UTF-8 和最大 64 KiB。在支持所需 POSIX 原语的平台上，程序以工作区目录描述符为起点逐级使用 `O_NOFOLLOW` 打开路径，对最终文件描述符执行 `fstat`，再限长读取；平台不支持时安全拒绝。

## 候选方案

- 在 Runner 继续增加 `if/elif`：直观但不可扩展，拒绝。
- 使用字典保存普通函数：简单，但 Schema、校验和错误职责分散，拒绝。
- 当前方案：增加少量抽象，已由四个真实工具和测试 Echo Tool 证明复用价值。

## 后果

- 新增无副作用工具不修改 Agent Loop；
- 模型收到的定义与程序可执行集合来自同一 Registry；
- 预期错误成为 Tool Observation，编程错误不会被任意 `eval` 路径吞掉；
- 当前尚无权限等级、审批、超时或有副作用工具，这些属于阶段 4；
- 工作区文件内容会进入模型上下文，用户只能对有权处理的非敏感文件提出读取任务。

## 验证与迁移

Calculator 从 `execute(raw_json)` 迁移为统一 `invoke(raw_json)`，内部 `execute(validated_args)`。65 个测试覆盖回归、Registry 单一来源、自定义 Echo 闭环、文件描述符边界和包版本一致性；五个真实路由案例全部正确。若后续需要权限，阶段 4 在 Registry 与执行之间增加 Policy，不改变模型 Function Calling 协议。

## 相关资料

- [硅基流动 Function Calling](https://docs.siliconflow.cn/cn/userguide/guides/function-calling)
- [阶段 3 实施记录](../stages/stage-03.md)
