from __future__ import annotations

import json
from typing import Any, Protocol

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from small_agent.config import Settings
from small_agent.state import (
    AgentDecision,
    AgentState,
    DecisionType,
    ToolCallRequest,
)
from small_agent.tooling import ToolRegistry


SYSTEM_PROMPT = "你是一个友好、准确、回答简洁的 AI 助手。"
AGENT_SYSTEM_PROMPT = """你是一个教学用任务 Agent 的决策模块。
你只能基于用户目标、公开步骤和真实工具 Observation 决定下一步。
根据工具描述选择最匹配的工具；涉及算术时必须调用 calculator，不得自行计算或假装工具已经执行。
只有确实需要外部能力时才调用工具；普通知识问答可以直接完成。
需要工具时使用原生 Function Calling；每次只请求一个工具调用。
收到成功的工具结果后，用该结果回答，不要重复计算。
不需要工具时返回一个 JSON 对象，不要使用 Markdown，不要披露隐藏思维过程。
action 和 observation 只写简短、可公开检查的说明。
decision 只能是 continue、complete 或 fail：
- 能直接给出可靠答案时使用 complete，并填写 final_answer；
- 还需一个步骤时使用 continue；
- 目标无法在当前能力和步骤限制内完成时使用 fail，并填写 failure_reason。
所有情况下都必须填写 action 和 observation。"""


class LLMError(RuntimeError):
    """模型请求失败或没有返回可用文本。"""


class TextGenerator(Protocol):
    """阶段 0 为离线测试保留的最小文本生成边界。"""

    def generate(self, user_input: str) -> str:
        """根据一条用户输入生成一条文本回复。"""


class SiliconFlowLLMClient:
    """通过硅基流动的 OpenAI 兼容接口完成一次文本生成。"""

    def __init__(
        self,
        settings: Settings,
        sdk_client: OpenAI | None = None,
    ) -> None:
        self._model = settings.model
        self._sdk_client = sdk_client or OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )

    def generate(self, user_input: str) -> str:
        try:
            response = self._sdk_client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                ],
            )
        except OpenAIError as exc:
            raise LLMError(
                "调用模型失败，请检查网络、API Key、模型名称和账户权限。"
            ) from exc

        if not response.choices:
            raise LLMError("模型没有返回可显示的文本。")

        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise LLMError("模型没有返回可显示的文本。")

        reply = content.strip()
        return reply

    def decide(
        self,
        state: AgentState,
        registry: ToolRegistry,
    ) -> AgentDecision:
        """让模型返回原生工具调用或经过校验的 JSON 决策。"""
        try:
            response = self._sdk_client.chat.completions.create(
                model=self._model,
                messages=self._build_agent_messages(state),
                tools=registry.definitions(),
                tool_choice="auto",
                max_tokens=1024,
            )
        except OpenAIError as exc:
            raise LLMError(
                "调用模型失败，请检查网络、API Key、模型名称和账户权限。"
            ) from exc

        choices = getattr(response, "choices", None)
        if not choices:
            raise LLMError("模型没有返回可用的 Agent 决策。")

        message = choices[0].message
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            if len(tool_calls) != 1:
                raise LLMError("当前每一步只允许一个工具调用。")
            tool_call = tool_calls[0]
            try:
                request = ToolCallRequest(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments_json=tool_call.function.arguments,
                )
            except (AttributeError, ValidationError) as exc:
                raise LLMError("模型返回的工具调用结构无效。") from exc
            return AgentDecision(
                decision=DecisionType.TOOL_CALL,
                action=f"请求调用工具 {request.name}",
                observation="等待程序校验参数并执行工具。",
                tool_call=request,
            )

        content = self._extract_content(response)
        try:
            decision = AgentDecision.model_validate_json(content)
        except ValidationError as exc:
            raise LLMError("模型返回的 Agent 决策不是有效的约定 JSON。") from exc
        if decision.decision == DecisionType.TOOL_CALL:
            raise LLMError("工具调用必须使用原生 Function Calling。")
        return decision

    @staticmethod
    def _build_agent_messages(state: AgentState) -> list[dict[str, Any]]:
        prompt = {
            "goal": state.goal,
            "current_step": state.current_step,
            "max_steps": state.max_steps,
            "required_json_schema_when_not_calling_a_tool": {
                "decision": "continue | complete | fail",
                "action": "非空字符串",
                "observation": "非空字符串",
                "final_answer": "complete 时为非空字符串，否则可为 null",
                "failure_reason": "fail 时为非空字符串，否则可为 null",
            },
        }
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False),
            },
        ]

        for step in state.steps:
            if step.tool_call is not None and step.tool_observation is not None:
                messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": step.tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": step.tool_call.name,
                                    "arguments": step.tool_call.arguments_json,
                                },
                            }
                        ],
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": step.tool_call.id,
                        "content": step.tool_observation.model_dump_json(
                            exclude_none=True
                        ),
                    }
                )
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "decision": step.decision.value,
                                "action": step.action,
                                "observation": step.observation,
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
                messages.append(
                    {"role": "user", "content": "请根据当前状态继续下一步。"}
                )
        return messages

    @staticmethod
    def _extract_content(response: object) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            raise LLMError("模型没有返回可显示的文本。")

        content = getattr(choices[0].message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise LLMError("模型没有返回可显示的文本。")
        return content.strip()
