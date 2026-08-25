# Small Agent

这是一个从最小 LLM 程序开始、逐阶段学习 AI Agent 核心机制的项目。

## 当前阶段

当前为阶段 0：项目初始化与最小 LLM 程序。

当前版本可以：

- 从命令行读取一个问题；
- 使用 OpenAI Python SDK 调用硅基流动的 OpenAI 兼容 Chat Completions API；
- 输出模型的文本回复；
- 从环境变量或本地 `.env` 加载 API Key 和模型名称；
- 使用 Fake LLM 完成不联网的自动化测试。

当前版本不是 Agent：它没有 Agent State、循环、工具、记忆、规划、RAG、MCP 或 Multi-Agent。

## 文档

完整需求、学习路线、架构和安全规范见 [docs/README.md](docs/README.md)。阶段 0 的实现与教学记录见 [docs/stages/stage-00.md](docs/stages/stage-00.md)。

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

程序会提示输入一个问题，然后打印一次模型回复。空输入会在本地被拒绝，不调用 API。

## 测试

```bash
python -m pytest
```

自动化测试使用 Fake LLM，不需要 API Key，也不会产生模型费用。
