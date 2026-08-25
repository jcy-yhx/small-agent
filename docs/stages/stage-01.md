# 第 1 阶段：Agent State 与 Agent Loop

- 状态：已完成
- 开始日期：2026-08-25
- 完成日期：2026-08-25
- 开始前 commit：`2d7e785`（tag `stage-00`）
- 完成 commit：本文件所在提交，以 `stage-01` tag 定位
- Git tag：`stage-01`
- 相关 ADR：[ADR-0004](../decisions/ADR-0004-explicit-state-and-validated-json-decisions.md)

## 1. 本阶段学习目标

- 理解 Agent 与单次 LLM 调用的差异；
- 用显式 State 保存目标、步骤、状态、结果和错误；
- 让程序而不是模型掌握循环与终止权；
- 校验结构化模型决策，并为所有终止路径编写测试。

## 2. 上一阶段回顾

阶段 0 已具备配置加载、一次 Chat Completions 调用、CLI 和 Fake 测试。它不保存目标或步骤，每次模型回复后立即退出。本阶段在保留 `generate`/`ask_once` 回归能力的基础上增量加入循环。

## 3. 本阶段新增概念

- `AgentState`：一次运行的事实来源，含目标、当前步、步数预算、公开步骤、状态和终止原因。
- `AgentDecision`：模型的一步结构化提议，类型为 `continue`、`complete` 或 `fail`。
- `AgentRunner`：程序控制的循环，负责记录步骤和强制停止。
- Observation：公开、简短的状态说明，不是隐藏思维链，也不是工具结果。

## 4. 为什么需要这个能力

一次生成无法表达“任务还没完成，请继续”，也无法可靠限制模型反复请求。显式状态让每次转移都可检查；最大步数让非确定性模型不会造成无界调用；结构化 Schema 把“模型说了什么”和“程序是否接受”分开。

## 5. 架构变化

```text
Goal -> AgentRunner -> AgentState -> DecisionMaker
            ^                           |
            |                    validated JSON
            +---- continue <------------+
            |
            +---- completed / failed / cancelled / error
```

CLI 展示每步的决策、行动、观察以及终止原因。模型不能修改 `current_step`、`max_steps` 或运行状态。

## 6. 项目目录变化

新增 `state.py`、`agent.py`、三个测试文件、ADR-0004 和本记录。修改 `llm.py`、`cli.py`、`config.py`、配置示例、项目版本和相关长期文档。直接依赖新增 `pydantic==2.13.4`；锁文件中的版本未变化，因为它已是 OpenAI SDK 的传递依赖。

核心数据结构：`AgentDecision`、`AgentStep`、`AgentState`、`DecisionType`、`AgentStatus`、`TerminationReason`。本阶段没有删除阶段 0 的 `TextGenerator` 或单次生成能力。

## 7. 实现步骤

1. 定义严格 Pydantic Schema 和五类终止原因。
2. 实现可注入 `DecisionMaker` 的同步循环。
3. 使用硅基流动 JSON Mode 获取决策并校验。
4. 将 CLI 改为目标输入和公开步骤输出。
5. 用脚本化决策覆盖全部控制流，再执行一次真实模型验收。
6. 同步架构、阶段、测试、故障和 ADR 文档。

## 8. 项目代码与关键接口

- `AgentRunner.run(goal, should_cancel)`：运行循环并返回最终 State。
- `SiliconFlowLLMClient.decide(state)`：请求并校验一步决策。
- `AgentDecision`：禁止额外字段；完成必须有答案，失败必须有原因。
- `Settings.max_steps`：由 `AGENT_MAX_STEPS` 配置，范围 1～10。

迁移方式：原 `.env` 可继续使用；未设置最大步数时默认 3。原 `small-agent` 命令仍存在，但提示语和输出格式变为 Agent 流程。

## 9. 如何运行

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
small-agent
```

输入一个无需工具即可完成的目标，例如“用一句话解释什么是 Agent Loop”。预期至少看到一个步骤、终止原因和最终答案。

## 10. 测试与验收

- 正常案例：`continue` 后 `complete`，状态为 `completed`。
- 边界案例：最大步数为 1 时继续决策触发 `max_steps_reached`。
- 失败案例：主动 `fail`、非法 JSON 和模型错误均安全终止。
- 取消案例：取消回调在调用模型前产生 `user_cancelled`。
- 自动化命令：`.venv/bin/python -m pytest`。
- 结果：`25 passed in 0.55s`，覆盖阶段 0 回归；默认测试不联网。
- 真实验收：2026-08-25，DeepSeek-V4-Flash 第一步返回合法 `complete` 决策，CLI 退出码 0，答案非空且相关。

## 11. 执行过程示例

```text
步骤 1
决策：complete
行动：基于已有知识直接给出定义
观察：该问题无需额外工具即可回答
终止原因：task_completed
助手：<一句话定义>
```

这些是公开控制记录，不包含模型隐藏思维链。

## 12. 常见问题与排查方法

- 非法 JSON：确认模型支持 JSON Mode；当前安全终止，不自动重试。
- 达到最大步数：缩小任务，或在 1～10 内调整 `AGENT_MAX_STEPS`；不能用取消上限掩盖循环问题。
- 任务要求外部行动：当前没有工具，应明确失败或只说明能力边界，不能声称已经执行。

详见 [troubleshooting.md](../troubleshooting.md)。

## 13. 当前版本的能力边界

当前可以：围绕纯文本目标进行有限循环、校验决策、展示公开过程、用五类原因停止。

当前不能：调用任何工具、访问文件或网络资料、保存记忆、规划复杂依赖、重试模型错误、统计 Token/费用。`action` 字段不等于真实行动。本版本仍不适合生产环境，缺少超时、Trace、恢复、权限和完整预算。

## 14. 本阶段总结

项目从“问一次、答一次”演进为最小 Agent Runtime 雏形。关键不是多调用一次模型，而是程序拥有一个可验证的状态机：模型提议，Schema 校验，Runner 决定是否继续。这样后续工具执行才能接在受控边界之后。

## 15. 小红书学习笔记草稿

### 可选标题

1. 我写出了第一个 Agent Loop：原来核心不是“多问模型几次”
2. 从 LLM 到 Agent 的分水岭：State、Loop 和停止条件
3. 不用框架，25 个测试看懂 Agent 怎么跑起来

### 正文

今天把阶段 0 的单次 LLM 程序升级成了一个最小 Agent。最大的变化不是 Prompt 更长，而是程序终于有了显式状态：目标是什么、现在第几步、之前发生了什么、最终为什么停止，都不再藏在聊天文本里。

每一步模型只返回三种结构化决策：继续、完成或失败。JSON Mode 负责让返回值更像 JSON，Pydantic 再检查字段是否真的符合约定。比如模型说“完成”却没给最终答案，程序会拒绝，而不是装作成功。真正控制循环的也是 Python：最多执行 1～10 步，默认 3 步；完成、主动失败、达到上限、用户取消和不可恢复错误都能明确停下来。

我也第一次认真区分了“公开过程”和“隐藏思维链”。日志只展示简短的行动、观察和终止原因，足够排查控制流，但不要求模型暴露内部推理。当前 action 仍只是说明，因为我们还没加入工具，不能假装真的查了网页或改了文件。

这轮共跑过 25 个离线测试，并用真实 DeepSeek 模型完成一次 JSON 决策。下一阶段才会加入第一个 Calculator，让“行动”第一次变成程序可验证的工具执行。#AIAgent #Python #大模型开发 #AgentLoop #从零学习

## 16. 下一阶段预告

阶段 2 将引入单个 Calculator、Function Calling、参数 Schema、执行结果 Observation 和最终回答。本阶段不提前实现这些能力。

## 17. 文档与交接检查

- [x] 当前架构、阶段状态、测试策略和故障记录已更新
- [x] ADR-0004 已记录结构化决策边界
- [x] `.env.example` 与配置代码一致
- [x] 文档确认当前没有工具或真实行动
- [x] 自动化与真实模型验收已记录
- [x] 未记录 Secret 或隐藏思维链
- [x] Git commit/tag 已通过 `stage-01` 定位

## 18. 待确认项

- 阶段 2 的 Calculator 参数 Schema、数值类型与除零错误语义将在进入阶段后确定。
- 阶段 1 的提交和 tag 使用 `stage-01` 定位。

## 19. 等待确认

阶段 1 已完成并停止。只有学习者明确确认“进入阶段 2”或表达同等意图后，才开始实现工具能力。
