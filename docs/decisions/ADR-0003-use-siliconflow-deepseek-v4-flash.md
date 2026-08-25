# ADR-0003：阶段 0 改用硅基流动 DeepSeek-V4-Flash

- 状态：已接受
- 日期：2026-08-25
- 决策者：学习者
- 相关阶段：stage-00
- 取代：[ADR-0001](ADR-0001-use-openai-responses-api-for-stage-00.md)
- 被取代：无

## 背景

阶段 0 初始实现使用 OpenAI Responses API。学习者在真实验收前明确选择硅基流动平台和 `deepseek-ai/DeepSeek-V4-Flash`。硅基流动官方文档提供 OpenAI Python SDK 兼容方式，但当前文档示例和 API Reference 使用 `/v1/chat/completions`。

## 候选方案

### 方案 A：保留 OpenAI Responses API

- 优点：已有实现和测试无需变化。
- 缺点：不能直接使用学习者选择的硅基流动接口完成验收。

### 方案 B：使用 OpenAI SDK 调用硅基流动 Chat Completions

- 优点：符合平台官方示例，支持学习者选择的模型；无需增加 SDK 依赖。
- 缺点：响应读取方式从 `output_text` 改为 `choices[0].message.content`。

## 决策

选择方案 B：

- Base URL：`https://api.siliconflow.cn/v1`；
- 模型：`deepseek-ai/DeepSeek-V4-Flash`；
- 接口：Chat Completions；
- 首选变量：`SILICONFLOW_API_KEY`、`SILICONFLOW_MODEL`、`SILICONFLOW_BASE_URL`；
- 为不破坏已填写的 `.env`，兼容 `OPENAI_API_KEY` 和 `OPENAI_MODEL`。

## 后果

- System 与 User 消息都进入 `messages`；Assistant 文本从第一个 choice 读取。
- Client 更名为 `SiliconFlowLLMClient`，不建立通用 Provider Framework。
- 配置只读取当前工作目录的 `.env`，避免测试向父目录发现真实 Secret。
- 后续 Function Calling 阶段必须以硅基流动当时的模型能力和官方文档为准。

## 验证方法

- Fake SDK 验证 Base URL 之外的 Chat Completions 请求结构。
- 配置测试验证新变量优先、旧变量兼容、默认值正确。
- 回归测试验证不会向父目录搜索 `.env`。
- 真实调用由学习者本地手动验收。

## 回滚或迁移方案

更换平台或模型时新增 ADR 取代本记录，同步配置、Client、测试、运行说明和阶段记录。

## 相关资料

- [硅基流动快速上手](https://docs.siliconflow.cn/cn/userguide/quickstart)
- [硅基流动 Chat Completions API](https://docs.siliconflow.cn/cn/api-reference/chat-completions/chat-completions)
- [阶段 0 实施记录](../stages/stage-00.md)
