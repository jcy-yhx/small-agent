# ADR-0001：阶段 0 使用 OpenAI Responses API

- 状态：已取代
- 日期：2026-08-25
- 决策者：学习者授权默认路线；当前阶段实现确认
- 相关阶段：stage-00
- 取代：无
- 被取代：[ADR-0003](ADR-0003-use-siliconflow-deepseek-v4-flash.md)

## 背景

阶段 0 需要选择一个模型供应商和官方 Python SDK，实现一次最小文本调用。路线图已将 OpenAI 作为默认建议、Anthropic 作为备选，学习者随后明确要求开始阶段 0。当前阶段不应为多供应商兼容建立复杂 Provider 抽象。

## 决策驱动因素

- 教学清晰度：只展示一次 LLM 调用的核心路径。
- 实现复杂度：官方 SDK 可直接读取响应文本。
- 安全性：API Key 通过本地环境变量提供。
- 可测试性：最小 `TextGenerator` 边界可由 Fake 实现替代。
- 成本与性能：默认使用 mini 模型，模型名允许通过环境变量覆盖。
- 可迁移性：阶段 12 再评估正式 Provider 接口。

## 候选方案

### 方案 A：OpenAI 官方 SDK 与 Responses API

- 优点：官方 API 当前支持 `instructions`、用户输入和 `output_text`；可延续到后期工具能力。
- 缺点：依赖外部服务和账号权限，真实调用产生费用。
- 风险：模型、SDK、价格和账号可用性会变化。

### 方案 B：Anthropic 官方 SDK 与 Messages API

- 优点：可作为后期供应商对比和迁移练习。
- 缺点：同时实现会让阶段 0 偏离“一次最小调用”。
- 风险：过早建立通用接口导致过度设计。

## 决策

阶段 0 选择 OpenAI 官方 Python SDK 3.3.1、Responses API 和默认模型 `gpt-5.4-mini`。模型可通过 `OPENAI_MODEL` 覆盖。请求使用 `store=False`，程序只读取 `output_text`。

只保留用于测试注入的最小 `TextGenerator` Protocol，不把它扩展为多供应商配置框架。

## 后果

### 正面影响

- 调用链短，System/User/Assistant 三种作用可直接解释。
- 自动测试不需要真实网络和 API Key。
- 后续可以在不改 CLI 的情况下替换 Fake Generator。

### 负面影响与成本

- 当前实现绑定 OpenAI SDK。
- 在线运行需要用户账号、Key 和费用预算。
- API 变更时需要更新实现、锁文件和文档。

### 后续工作

- 每个涉及 OpenAI API 的阶段开始前核对官方文档。
- 阶段 12 再评估是否引入正式 Provider Adapter。

## 验证方法

- Fake SDK 测试断言模型名、`instructions`、用户消息和 `store=False`。
- 离线 CLI 测试验证输入与输出。
- 学习者本地配置 Key 后执行一次在线手动验收。

## 回滚或迁移方案

如果账号不可用或后续需求选择其他供应商，先新增取代本 ADR 的决策记录，再修改 Client、配置、测试和运行文档。不得在阶段 0 同时维护两个实现。

## 相关资料

- [OpenAI Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [阶段 0 实施记录](../stages/stage-00.md)
