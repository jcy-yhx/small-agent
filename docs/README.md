# Small Agent 开发文档

## 1. 文档目的

本目录保存 Small Agent 渐进式学习项目的长期开发上下文。目标是让学习者、开发者或新的 AI 在不重新设计项目的前提下，理解项目意图、确认当前进度，并从最后一个已完成阶段继续开发。

文档描述必须与仓库中的实际代码一致。任何计划中的能力都必须明确标记为“计划中”，不得写成已经实现。

## 2. 当前状态

- 当前里程碑：阶段 1 已完成，等待学习者明确确认是否进入阶段 2。
- 阶段 1 状态：已完成；25 个离线测试和一次真实模型验收均已通过。
- 当前代码：具有显式 State、受限 Loop 和结构化决策的无工具 Agent。
- 当前依赖：使用 venv + pip；`pyproject.toml` 与 `requirements.lock` 已创建。
- 当前配置：使用 OpenAI SDK 调用硅基流动 Chat Completions API，默认模型为 `deepseek-ai/DeepSeek-V4-Flash`；未读取或输出真实 API Key。
- 当前可运行能力：围绕任务目标循环，展示公开步骤，并以五类原因之一终止；测试使用脚本化 Decision Maker 离线运行。
- 当前版本：阶段 1 由 Git tag `stage-01` 定位；远程发布状态以仓库 remote 为准。

权威阶段状态以 [stage-specification.md](stage-specification.md) 为准，当前架构以 [architecture.md](architecture.md) 为准。

## 3. 文档导航

| 文档 | 职责 |
|---|---|
| [product-requirements.md](product-requirements.md) | 项目目标、非目标、用户成果、技术约束和最终完成标准 |
| [learning-roadmap.md](learning-roadmap.md) | 阶段 0～13 的学习顺序、依赖、成果和时间估算 |
| [architecture.md](architecture.md) | 当前架构、演进方向、最终目标架构和模块边界 |
| [development-guide.md](development-guide.md) | 环境、依赖、配置、实现、日志、提交和文档维护规范 |
| [stage-specification.md](stage-specification.md) | 阶段状态、输入、输出、依赖和验收标准 |
| [testing-strategy.md](testing-strategy.md) | 测试分层、固定案例、评估指标和阶段质量门槛 |
| [security-guidelines.md](security-guidelines.md) | 权限、安全控制、敏感信息和有副作用工具边界 |
| [troubleshooting.md](troubleshooting.md) | 通用排查流程和已经确认的问题记录 |
| [decisions/README.md](decisions/README.md) | 架构决策记录（ADR）规范和模板 |
| [stages/README.md](stages/README.md) | 阶段实施记录规范、模板和同步清单 |
| [stages/stage-00.md](stages/stage-00.md) | 阶段 0 的实际实现、测试、限制和验收结果 |
| [stages/stage-01.md](stages/stage-01.md) | 阶段 1 的 State、Loop、测试、限制和验收结果 |

## 4. 文档权威关系

发生冲突时按以下顺序处理，而不是默默选择一种说法：

1. 实际代码、自动化测试和锁文件代表仓库的客观事实。
2. `stage-specification.md` 代表阶段状态和验收结论。
3. `architecture.md` 代表当前模块和数据流。
4. 已接受的 ADR 代表技术决策及其理由。
5. `development-guide.md` 代表日常开发约定。
6. `learning-roadmap.md` 只代表计划，可随经确认的决策调整。

发现不一致时，应停止扩展功能，先记录差异并同步文档；不得通过修改文档掩盖失败测试或缺失实现。

## 5. 项目恢复开发清单

将项目交给新的开发者或 AI 时，至少提供：

- 完整仓库，包括 Git 历史、当前分支和未提交变更；
- 本 `docs/` 目录；
- 根目录项目说明、项目清单和依赖锁文件（创建后）；
- `.env.example`（创建后），但绝不提供真实 `.env` 或 API Key；
- 最近阶段记录 `docs/stages/stage-XX.md`；
- 所有已接受或待确认的 ADR；
- 当前测试及最近一次测试结果；
- 当前 Git commit、对应 stage tag（如有）和工作区状态；
- 已知故障、未解决问题和安全限制；
- 下一阶段需要学习者确认的待确认项。

接手者开始修改前应依次执行：

1. 阅读本文件和 `product-requirements.md`。
2. 查看 `stage-specification.md`，找到最后一个“已完成”阶段。
3. 阅读 `architecture.md` 的“当前架构”，不要从最终架构推断现状。
4. 阅读最近阶段记录、ADR、故障记录和安全规范。
5. 检查 Git 状态，不覆盖未提交的用户改动。
6. 按 `development-guide.md` 准备环境并运行现有测试。
7. 比较文档、代码、测试和锁文件；若不一致，先报告。
8. 只有得到学习者明确确认，才能开始下一个阶段。

## 6. 新开发者/新 AI 接手提示词模板

```text
你正在接手 Small Agent 渐进式学习项目。

仓库位置：<仓库路径>
当前分支与提交：<branch> / <commit>
最近阶段 Tag（如有）：<tag 或“无”>
用户未提交改动：<摘要或“无”>

请先阅读：
1. docs/README.md
2. docs/product-requirements.md
3. docs/stage-specification.md
4. docs/architecture.md
5. docs/development-guide.md
6. docs/testing-strategy.md
7. docs/security-guidelines.md
8. docs/troubleshooting.md
9. 最近的 docs/stages/stage-XX.md
10. docs/decisions/ 下相关 ADR

当前已完成阶段：<阶段或“无”>
准备进行的阶段：<阶段>
本次授权范围：<仅分析 / 实现当前阶段 / 修复问题等>
待确认技术选择：<列表>

要求：
- 先检查 Git 状态、代码、测试和文档是否一致；
- 不把路线图中的未来能力当成已实现；
- 基于上一阶段增量修改，不提前实现后续阶段；
- 不展示模型隐藏思维链，只记录必要的结构化决策和行动；
- 不读取、提交或输出真实 Secret；
- 未经明确授权不提交、推送、删除文件或执行高风险操作；
- 完成本阶段后同步规定文档并停止，等待下一阶段确认。

请先汇报你识别到的当前状态、限制、待确认项和本次计划，不要立即跨阶段开发。
```

## 7. 阶段完成后的强制同步

每个阶段完成后必须：

1. 更新 `architecture.md` 中的当前架构。
2. 更新 `stage-specification.md` 中的阶段状态和验收结果。
3. 新增 `docs/stages/stage-XX.md` 实施记录。
4. 把新出现的问题加入 `troubleshooting.md`。
5. 对重要且长期有效的技术选择新增 ADR。
6. 在阶段记录中写入对应 Git commit 和 tag；未创建时明确写“未创建”。
7. 确认文档、代码、测试、配置示例和依赖锁一致。

## 8. 进入下一阶段的门禁

完成文档同步不等于自动进入下一阶段。只有学习者明确回复“开始阶段 X”“进入下一阶段”或表达同等明确意图后，才允许实施下一阶段。
