# Small Agent

这是一个从最小 LLM 程序开始、逐阶段学习 AI Agent 核心机制的项目。

## 当前阶段

阶段 1（Agent State 与 Agent Loop）已完成，当前等待阶段 2 的明确确认。

当前版本可以：

- 从命令行读取一个任务目标；
- 使用显式 `AgentState` 在最大步骤数内循环；
- 让模型返回经过 Pydantic 校验的 JSON 决策；
- 显示每步的公开行动、观察、决策及终止原因；
- 从环境变量或本地 `.env` 加载 API Key 和模型名称；
- 使用 Fake LLM 完成不联网的自动化测试。

当前版本是一个无工具的最小 Agent：它有状态和受限循环，但没有工具、记忆、规划、RAG、MCP 或 Multi-Agent。

## 文档

完整需求、学习路线、架构和安全规范见 [docs/README.md](docs/README.md)。本阶段记录见 [docs/stages/stage-01.md](docs/stages/stage-01.md)。

## 环境要求

- Python 3.11 或更高版本；
- 当前环境使用 venv + pip；
- 一个由你自行保管的硅基流动 API Key，仅真实调用时需要。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`requirements.lock` 记录本阶段验证时的完整依赖版本。需要严格复现时可先安装锁定依赖，再以不解析依赖的方式安装本项目：

```bash
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
```

## 配置

复制 `.env.example` 为 `.env`，然后只在本地填写：

```dotenv
SILICONFLOW_API_KEY=your_real_key
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V4-Flash
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
AGENT_MAX_STEPS=3
```

`.env` 已被 Git 忽略。不要把真实 Key 粘贴到源码、测试、文档、日志或聊天记录。为了兼容此前创建的本地配置，程序也接受 `OPENAI_API_KEY` 和 `OPENAI_MODEL`；新配置建议使用含义更明确的 `SILICONFLOW_*` 名称。

## 运行

```bash
small-agent
```

也可以使用：

```bash
python -m small_agent
```

程序会提示输入任务目标，然后展示 Agent 的公开步骤和终止原因。`AGENT_MAX_STEPS` 允许 1～10，默认 3；空目标会在本地被拒绝。

## 测试

```bash
python -m pytest
```

自动化测试使用 Fake LLM，不需要 API Key，也不会产生模型费用。
