# 第 3 阶段：Tool Registry 与多工具路由

- 状态：已完成
- 开始日期：2026-08-25
- 完成日期：2026-08-27（包含代码审查修正）
- 开始前 commit：`6883433`（tag `stage-02`）
- 完成 commit：本文件所在最终提交，以 `stage-03` tag 定位
- Git tag：`stage-03`
- 相关 ADR：[ADR-0006](../decisions/ADR-0006-tool-registry-and-low-risk-builtins.md)

## 1. 本阶段学习目标

- 理解为什么多个工具不能持续堆叠 `if/elif`；
- 用统一 Tool 接口表达名称、描述、Schema、校验和执行；
- 用 Registry 完成能力发现、重复检查和按名分发；
- 观察工具描述如何影响模型路由，并验证“无需工具”分支。

## 2. 上一阶段回顾

阶段 2 已跑通 Calculator Function Calling，但 Runner 直接认识 Calculator。新增工具会修改核心循环，参数错误和执行结果也没有跨工具统一类型。本阶段保留原生 `tool_calls -> Observation` 协议，只替换硬编码执行边界。

## 3. 本阶段新增概念

- `BaseTool`：工具的统一生命周期，先解析和校验，再执行已验证参数。
- `ToolRegistry`：注册、拒绝重名、生成模型 definitions、按名称分发。
- `ToolResult`：统一成功、参数错误、执行错误和未知工具。
- 多工具路由：模型根据名称、描述和 Schema 选择工具，或选择不调用。

## 4. 为什么需要这个能力

如果每增加一个工具就修改 Agent Loop，循环会同时承担模型决策、工具发现、参数校验和业务执行，难以测试也容易产生绕过路径。Registry 让模型看到的能力集合与程序真正可执行的集合来自同一事实来源。

## 5. 架构变化

```text
Registry -> tool definitions -> Model -> tool_call(name, arguments)
   ^                                      |
   |                                      v
BaseTool <- Registry dispatch <- AgentRunner
   |
validated arguments -> execute -> ToolResult -> ToolObservation
```

Runner 不再导入或判断任何具体工具名称。

## 6. 项目目录变化

新增 `tooling.py`、`builtin_tools.py`、`test_tooling.py`、`test_builtin_tools.py`、ADR-0006 和本记录。Calculator 迁移到 `BaseTool`；Agent、LLM、CLI、State 和既有测试改为使用 Registry。项目版本升级为 `0.3.0`。没有删除文件，没有新增第三方依赖。

新增数据结构：`ToolErrorCode`、`ToolResult`、各工具 Arguments Model。`ToolObservation` 增加 `error_code`。Calculator 外部接口从 `execute(raw_json)` 迁移为统一 `invoke(raw_json)`；`execute` 只接收已验证参数。

## 7. 实现步骤

1. 提取 BaseTool、统一 JSON/Decimal 解析和 ToolResult。
2. 实现 Registry 注册、重复检查、definitions 和分发。
3. 迁移 Calculator，不改变数值语义。
4. 增加 UTC 时间、文本统计和受限文件读取。
5. 让 CLI 创建唯一 Registry，由 Runner 在决策和执行两侧复用同一实例。
6. 补齐确定性测试和五类真实路由验收。
7. 根据阶段后代码审查移除 Client/Runner 的独立默认能力来源，并加固只读文件的描述符级检查和限长读取。
8. 补齐最终对象非阻塞打开和 FIFO 拒绝，并让 Registry 注册与模型调用复用同一工具名称协议。

## 8. 项目代码与关键接口

- `BaseTool.invoke(raw_json)`：统一参数解析、校验和结果规范化。
- `BaseTool.execute(validated_args)`：具体工具只实现业务行为。
- `ToolRegistry.register/definitions/execute`：注册、发现和分发。
- `build_default_registry(workspace)`：当前四工具唯一装配入口。
- `SiliconFlowLLMClient.decide(state, registry)`：直接从 Runner 传入的 Registry 生成模型能力声明。
- `AgentRunner(decision_maker, registry, ...)`：持有单次运行唯一 Registry，决策和执行不再依赖两套默认集合或具体工具类。

## 9. 当前工具

| 名称 | 能力 | 关键边界 |
|---|---|---|
| `calculator` | Decimal 加减乘除 | 100 位、50 位小数、拒绝除零 |
| `current_time` | 当前 UTC ISO 时间 | 只支持 UTC |
| `text_stats` | 字符、空白分词、行数 | 输入最多 10,000 字符 |
| `read_text_file` | 读取 UTF-8 文本 | 工作区、非隐藏 `.txt/.md`、64 KiB |

## 10. 测试与验收

- 自动化：`.venv/bin/python -m pytest -q`，`71 passed`。
- Registry：注册、名称协议、重复名、definition、未知工具和自定义 Echo 的 Runner + Fake LLM 闭环测试通过；模型能力声明与执行使用同一实例。
- 文件安全：绝对路径、`..`、隐藏文件、错误后缀、符号链接逃逸、FIFO 和超限均拒绝；最终对象非阻塞打开，同一文件描述符完成类型/大小检查，限长读取覆盖检查后增长模型。
- 版本：运行时 `small_agent.__version__` 与安装元数据一致。
- 真实路由：Calculator、UTC 时间、文本统计、README 读取和无需工具五类全部正确，5/5。
- 回归：阶段 0～2 全部测试继续通过。

## 11. 执行示例

```text
目标：请使用文本统计工具统计：hello world
决策：tool_call
工具调用意图：text_stats
工具执行：成功
工具结果：{"characters":11,"words":2,"lines":1}
决策：complete
终止原因：task_completed
```

工具调用意图来自模型，分发和结果来自程序，不记录隐藏思维链。

## 12. 常见问题与排查

- 未知工具：确认工具已在 Runner 持有的 Registry 注册；Runner 会把同一实例交给 DecisionMaker 并用于执行。
- 重复注册：名称是唯一协议标识，修改名称而不是覆盖旧工具。
- 文件拒绝：检查工作区、相对路径、后缀、隐藏部分、编码和 64 KiB 上限。
- 模型选错工具：先改清晰、互斥的名称和描述，再用固定案例评估；不要在 Runner 写路由特判。

## 13. 当前版本能力边界

当前可以通过统一 Registry 使用四个低风险工具，也能直接回答无需工具的问题。当前不能写文件、运行 Shell、访问网络、处理任意二进制或读取隐藏/越界文件；没有权限等级、审批、超时、通用输出截断、记忆、RAG、规划、MCP 或 Multi-Agent。本版本仍是教学 Demo。

## 14. 本阶段总结

项目第一次出现了由真实复用需求推动的抽象：四个工具共享发现、校验、错误和结果边界，而 Agent Loop 只处理状态转换。Registry 不是“让模型更聪明”，而是让程序能力集合可维护、可审查。

## 15. 小红书学习笔记草稿

### 可选标题

1. 第二个 AI 工具加入后，我终于明白为什么需要 Tool Registry
2. 别再给 Agent 堆 if/elif：四个工具如何共享一个执行入口
3. 模型会选工具还不够，程序必须有自己的能力清单

### 正文

今天把只有 Calculator 的 Agent 升级成了四工具版本：精确计算、UTC 时间、文本统计和受限文件读取。真正的主角却不是新工具，而是 Tool Registry。

上一阶段 Runner 直接写死 calculator。继续加 if/elif 虽然能跑，但模型看到的工具、程序能执行的工具、每个参数怎么校验会越来越分散。现在每个 Tool 声明自己的名称、描述、Schema 和执行方法；Registry 负责拒绝重名、把统一 definitions 发给模型，再按模型返回的名称分发。新增测试 Echo Tool 时，Agent Loop 一行都不用改。

文件读取让我再次看到“只读”也不等于没风险。我把范围限制为启动工作区内、非隐藏的 `.txt/.md`、UTF-8、最大 64 KiB；程序从工作区目录描述符逐级安全打开路径，对同一已打开对象检查并限长读取。`.env`、绝对路径、`..` 和链接逃逸都会被程序拒绝，不支持安全打开原语的平台也会拒绝。

71 个离线测试通过后，五个既有真实案例也保持通过记录：四种工具全部选对，普通 Python 知识题则没有乱用工具，路由 5/5。下一阶段才会面对真正危险的写文件和 Shell，并加入权限与人工确认。#AIAgent #ToolCalling #Python #Agent开发 #从零学习

## 16. 下一阶段预告

阶段 4 将引入有副作用工具、代码级权限、工作区策略、超时、输出限制和 Human-in-the-loop。未确认前不会实现。

## 17. 文档与交接检查

- [x] 当前架构和阶段状态已更新
- [x] ADR-0006 已记录 Registry 决策
- [x] troubleshooting 已记录路由和文件边界
- [x] 71 个测试和 5/5 在线案例已记录
- [x] 文档与默认四工具一致
- [x] 文件工具未读取 `.env`，验收未输出或记录 API Key
- [x] Git commit/tag 已通过 `stage-03` 定位

代码审查修正（2026-08-27）：修复模型声明与执行能力可能来自不同 Registry、文件检查与读取之间的竞态窗口、运行时版本号漂移和 Tool 消息文档过窄四项问题。原 `stage-03` 本地标签按学习者要求删除并在本次最终提交上重建；远程标签是否同步需单独执行推送。

收尾验收修正（2026-08-27）：最终文件使用 `O_NONBLOCK` 打开，真实 FIFO 回归测试确认非普通文件立即拒绝；Registry 注册和 `ToolCallRequest` 复用同一名称约束，非法名称在注册阶段拒绝。全量测试更新为 71 项，最终提交由更新后的 `stage-03` tag 定位。

## 18. 待确认项

- 阶段 4 的写入范围、Shell 白名单、审批交互和超时语义需在进入阶段后确定。
- 阶段 3 的最终提交和 tag 使用 `stage-03` 定位。

## 19. 等待确认

阶段 3 已完成并停止。只有明确确认进入阶段 4 后，才实现有副作用工具与安全控制。
