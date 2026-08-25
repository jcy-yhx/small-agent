# 第 0 阶段：项目初始化与最小 LLM 程序

- 状态：已完成
- 开始日期：2026-08-25
- 完成日期：2026-08-25
- 开始前 commit：无，当前目录不是 Git 仓库
- 完成 commit：本文件所在提交，以 `stage-00` tag 定位
- Git tag：`stage-00`
- 相关 ADR：[ADR-0001（已取代）](../decisions/ADR-0001-use-openai-responses-api-for-stage-00.md)、[ADR-0002](../decisions/ADR-0002-use-venv-and-pip.md)、[ADR-0003](../decisions/ADR-0003-use-siliconflow-deepseek-v4-flash.md)

## 1. 本阶段学习目标

完成本阶段后应能：

- 解释 CLI 输入如何经过 Prompt 和官方 SDK 变成模型回复；
- 区分 System、User、Assistant 三类消息的职责；
- 从环境变量加载 API Key，而不是写死在代码中；
- 使用 Fake LLM 在没有网络和 Key 时测试程序；
- 解释为什么一次 LLM 调用还不是 Agent。

## 2. 上一阶段回顾

- 已有能力：只有需求、路线、架构、安全和交接文档。
- 开始前目录：只有 `docs/`。
- 主要限制：没有 Python 包、依赖、配置、测试或运行能力。
- 本阶段解决的问题：建立一条最小、可运行、可测试的 LLM 调用路径。

## 3. 本阶段新增概念

### LLM 调用

程序向模型 API 提交输入并取得输出。本阶段每次启动只调用一次，不维护跨轮状态。

### Prompt 与消息角色

- System：当前由 Chat Completions 的 `system` 消息表达，定义助手角色和回答风格。
- User：用户在 CLI 输入的问题，以 `user` 消息发送。
- Assistant：模型返回的第一条 choice 中的消息文本。

### Fake LLM

Fake Generator 不是另一个模型，而是测试替身。它返回预设内容，用于验证输入、输出和错误控制流，不验证模型智能。

## 4. 为什么需要这个能力

Agent 的后续循环、工具和记忆最终都需要调用模型。如果无法单独确认“配置 → Prompt → SDK → 回复”这条链路，后续失败时就无法判断问题来自模型调用还是 Agent 控制逻辑。因此先建立最小基线，并把外部网络与本地程序逻辑分开测试。

## 5. 架构变化

### 变化前

```text
docs only
```

### 变化后

```text
CLI -> Input Validation -> Settings -> SiliconFlowLLMClient
                                      -> Chat Completions API
                                      -> Assistant content -> CLI
```

### 数据流或执行流程

1. CLI 读取一行用户输入。
2. 空白输入在本地被拒绝，不加载配置、不调用 API。
3. `Settings` 从环境或当前目录的 `.env` 加载硅基流动 Key、模型名和 Base URL。
4. `SiliconFlowLLMClient` 将 System 与 User 消息发送给 Chat Completions API。
5. Client 读取并清理 `choices[0].message.content`。
6. CLI 以 Assistant 回复形式打印文本。

### 新模块职责

- `config.py`：集中配置校验。
- `llm.py`：单次 OpenAI 模型调用。
- `chat.py`：输入规范化和一次生成。
- `cli.py`：终端交互及用户可理解的错误。
- `__main__.py`：模块运行入口。

### 在真实 Agent 系统中的位置

这是未来 Agent Runtime 使用的模型调用基础设施，但当前没有 Runtime、状态转换或自主行动。

## 6. 项目目录变化

### 新增文件

- `.gitignore`
- `.env.example`
- `pyproject.toml`
- `requirements.lock`
- `README.md`
- `src/small_agent/__init__.py`
- `src/small_agent/__main__.py`
- `src/small_agent/config.py`
- `src/small_agent/llm.py`
- `src/small_agent/chat.py`
- `src/small_agent/cli.py`
- `tests/test_chat.py`
- `tests/test_cli.py`
- `tests/test_config.py`
- `tests/test_llm.py`
- `docs/decisions/ADR-0001-use-openai-responses-api-for-stage-00.md`
- `docs/decisions/ADR-0002-use-venv-and-pip.md`
- `docs/decisions/ADR-0003-use-siliconflow-deepseek-v4-flash.md`
- `docs/stages/stage-00.md`

### 修改文件

- `docs/README.md`
- `docs/architecture.md`
- `docs/development-guide.md`
- `docs/stage-specification.md`
- `docs/testing-strategy.md`
- `docs/troubleshooting.md`

### 删除文件

- 无。

### 依赖变化

- 运行时直接依赖：`openai==3.3.1`、`python-dotenv==1.2.3`。
- 开发直接依赖：`pytest==9.1.1`。
- 完整传递依赖版本记录在 `requirements.lock`。
- 当前使用 `.venv + pip`，原因见 ADR-0002。

### 数据结构变化

- 新增不可变 `Settings(api_key, model)`。
- 新增最小 `TextGenerator.generate(user_input) -> str` 测试边界。
- 没有 Agent State、消息历史或持久化数据结构。

## 7. 实现步骤

1. 初始实现核对 OpenAI Responses API；学习者选择硅基流动后，再核对其官方 Chat Completions API 和 `deepseek-ai/DeepSeek-V4-Flash`。
2. 检查 Python 和 uv 可用性，因 uv 不存在选择 venv + pip。
3. 建立项目元数据、配置示例和忽略规则。
4. 实现配置、最小 LLM Client、一次问答函数和 CLI。
5. 使用 Fake Generator 和 Fake SDK 编写离线测试。
6. 创建 `.venv`，安装固定直接依赖。
7. 运行测试、`pip check`、空输入与缺 Key 验收。
8. 生成完整 `requirements.lock`。
9. 同步架构、阶段状态、测试、故障和决策文档。
10. 将模型服务切换为硅基流动，并修复测试可能向父目录搜索 `.env` 的安全问题。

## 8. 项目代码与关键接口

- [`Settings.from_env`](../../src/small_agent/config.py)：加载并校验本地配置。
- [`SiliconFlowLLMClient.generate`](../../src/small_agent/llm.py)：完成一次硅基流动 Chat Completions 调用。
- [`ask_once`](../../src/small_agent/chat.py)：拒绝空输入并调用一次 Generator。
- [`main`](../../src/small_agent/cli.py)：CLI 输入、输出和错误码。
- [离线测试](../../tests/)：验证本地逻辑及 SDK 请求边界。

关键接口变化：项目从无代码变为提供 `small-agent` 命令和 `python -m small_agent` 入口。

从上一阶段迁移：无需迁移数据；按根目录 README 创建虚拟环境即可。

未采用的方案：没有引入通用 Provider、Pydantic Schema、Agent Loop 或多轮会话，因为它们不属于阶段 0。

## 9. 如何运行

### 环境准备

- Python 3.11+；验证环境为 Python 3.14.4。
- 当前采用 venv + pip。

### 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 环境变量

复制 `.env.example` 为 `.env`，只在本地填写 `SILICONFLOW_API_KEY`。默认模型是 `deepseek-ai/DeepSeek-V4-Flash`，默认 Base URL 是 `https://api.siliconflow.cn/v1`。为了兼容旧配置，也接受 `OPENAI_API_KEY` 与 `OPENAI_MODEL`。

### 启动命令

```bash
small-agent
```

### 预期输出

```text
请输入问题：用一句话解释什么是大语言模型
助手：<模型返回的一条回复>
```

实际文本具有非确定性，不应要求逐字一致。

## 10. 测试与验收

### 正常案例

- 输入：`请回复测试`。
- Fake 结果：输出 `助手：测试成功`，退出码为 0。
- 状态：自动化测试已通过。

### 边界案例

- 输入：只有空格或空行。
- 结果：输出“问题不能为空”，退出码为 2，Generator 调用次数为 0。
- 状态：自动化与命令行测试已通过。

### 失败案例

- 场景：既没有 `SILICONFLOW_API_KEY`，也没有兼容的 `OPENAI_API_KEY`。
- 结果：输出安全配置提示，退出码为 1，不显示任何 Key。
- 状态：自动化与命令行测试已通过。

### 自动化测试

- 命令：`.venv/bin/python -m pytest`
- 执行范围：4 个测试文件，共 11 个测试。
- 最新结果：`11 passed in 0.51s`。
- 日期：2026-08-25。
- 依赖检查：`pip check` 返回 `No broken requirements found.`。

### 手动验收

- 离线 CLI 边界检查：已执行并通过。
- 真实 API 调用：已由学习者在本地执行。
- 平台与模型：硅基流动，`deepseek-ai/DeepSeek-V4-Flash`。
- 输入：`请用一句话解释什么是大语言模型`。
- 实际结果：成功返回一句非空且相关的中文解释，程序正常结束。
- 安全检查：验收记录未包含 API Key，仓库中的 `.env` 仍被忽略。
- 通过标准：得到非空 Assistant 回复；Key 不出现在输出中；程序只完成一次调用后退出。

自动化和手动验收均已通过，本阶段状态更新为“已完成”。

## 11. 执行过程示例

当前阶段没有 Agent 状态或决策日志，必要流程记录如下：

```text
event=input_received
input_empty=false
provider=siliconflow
model=deepseek-ai/DeepSeek-V4-Flash
action=create_chat_completion
assistant_output=<非空文本>
termination=single_call_completed
```

这只是调用流程示意，不是实际生产日志，也不包含隐藏思维链。

## 12. 常见问题与排查方法

### 找不到 uv

- 原因：当前系统未安装。
- 解决：使用文档规定的 venv + pip 方案。

### 缺少 SILICONFLOW_API_KEY

- 原因：没有创建本地 `.env` 或没有导出环境变量。
- 解决：参考 `.env.example` 配置，不能把真实值提交到仓库。

### 模型调用失败

- 可能原因：网络、Key、模型权限、账户额度或模型名称。
- 解决：先用最小调用检查配置和官方文档，不通过放宽安全规则解决。

### 模型返回空文本

- 处理：Client 抛出受控 `LLMError`，CLI 返回错误，不伪装为成功。

## 13. 当前版本的能力边界

### 当前可以做什么

- 接收一个非空命令行问题；
- 通过 OpenAI SDK 调用一次硅基流动 Chat Completions API；
- 展示一条文本回复；
- 使用 Fake 完成离线测试；
- 安全处理空输入、缺少配置、请求失败和空回复。

### 当前不能做什么

- 不能围绕目标循环；
- 不能维护 Agent State 或聊天历史；
- 不能调用工具；
- 没有短期/长期记忆；
- 没有 RAG、规划、MCP 或 Multi-Agent；
- 不统计 Token 或成本；
- 不自动重试。

### 不适合生产环境的部分

- 错误分类仍较粗；
- 没有超时、退避、可观察 Trace 或预算；
- 没有并发、限流或部署配置；
- 已完成一次真实 API 验收，但尚未实现生产级超时、重试、Trace 和预算。

## 14. 本阶段总结

项目建立了第一条真实运行路径，并把配置、模型 I/O、业务调用和 CLI 分开。这个拆分不是 Agent Framework，而是为了让模型外部依赖可以被 Fake 替换，从而确定性测试本地逻辑。下一阶段才能在这条一次性调用之上引入显式 State 和 Loop。

## 15. 小红书学习笔记草稿

### 可选标题

1. 我终于亲手写出了第一个 LLM 程序，但它真的不是 Agent
2. 从零做 AI Agent 第 0 关：先把一次模型调用拆明白
3. 不用 LangChain，我用 Python 跑通了最小 AI 调用链

### 正文

今天正式开始从零实现 AI Agent，但第一步故意没有写 Agent。当前程序只做一件事：从命令行读取问题，通过官方 SDK 调用一次模型，再打印回复。看起来简单，却让我第一次把完整链路拆清楚了：System 负责约束助手身份和风格，User 是本次输入，Assistant 是模型返回的文本；API Key 只是访问外部服务的凭据，必须留在本地环境，绝不能写进代码。

本阶段最大的认知变化是：接入 LLM 不等于拥有 Agent。当前程序不会维护目标，不会自己决定下一步，也没有循环、工具和记忆。它只是一个可测试的模型调用程序。

真实踩坑点不只有环境里没有 uv：切换硅基流动后，还发现 `python-dotenv` 默认可能向父目录搜索 `.env`。我显式限制它只读当前目录，并加入回归测试，避免测试碰到真实 Key。另一个重要做法是用 Fake Generator 写离线测试：不需要 API Key、不花调用费用，也能确认空输入不会触发请求、错误不会伪装成功。

下一阶段才是真正的转折：给程序加入显式 State 和 Agent Loop，让它开始围绕目标持续执行。#AIAgent #Python #大模型开发 #从零学习 #程序员成长

## 16. 下一阶段预告

阶段 1 将解决一次性程序无法围绕目标持续执行的问题，引入 Agent State、显式状态转换、最大步数和完整终止条件。本记录不提前实现这些能力。

## 17. 文档与交接检查

- [x] `architecture.md` 已更新并与代码一致
- [x] `stage-specification.md` 已更新
- [x] `troubleshooting.md` 已补充
- [x] ADR 已按需创建
- [x] 环境变量文档与 `.env.example` 一致
- [x] 项目清单与锁文件一致
- [x] 自动化测试记录完整
- [x] Git commit/tag 已通过 `stage-00` 定位
- [x] 未把未来能力描述为已实现
- [x] 未记录 Secret 或隐藏思维链
- [x] 真实 API 手动验收已执行并通过

## 18. 待确认项

- 阶段 0 已完成；是否进入阶段 1 仍需学习者明确确认。
- 学习者已明确要求初始化 Git、创建阶段 tag 并发布到 GitHub；本地版本使用 `stage-00` 定位。

## 19. 等待确认

阶段 0 已完成并停止。除非学习者明确确认“开始阶段 1”或表达同等意图，否则不进入阶段 1。
