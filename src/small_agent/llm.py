from __future__ import annotations

import json
from typing import Protocol

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from small_agent.config import Settings
from small_agent.state import AgentDecision, AgentState


SYSTEM_PROMPT = "你是一个友好、准确、回答简洁的 AI 助手。"
AGENT_SYSTEM_PROMPT = """你是一个教学用任务 Agent 的决策模块。
你只能基于用户目标和公开步骤记录决定下一步，不得声称使用了尚不存在的工具。
返回一个 JSON 对象，不要使用 Markdown，不要披露隐藏思维过程。
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

    def __init__(self, settings: Settings, sdk_client: OpenAI | None = None) -> None:
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

    def decide(self, state: AgentState) -> AgentDecision:
        """让模型为 Agent 循环返回一个经过校验的 JSON 决策。"""
        public_steps = [step.model_dump(mode="json") for step in state.steps]
        prompt = {
            "goal": state.goal,
            "current_step": state.current_step,
            "max_steps": state.max_steps,
            "previous_steps": public_steps,
            "required_schema": {
                "decision": "continue | complete | fail",
                "action": "非空字符串",
                "observation": "非空字符串",
                "final_answer": "complete 时为非空字符串，否则可为 null",
                "failure_reason": "fail 时为非空字符串，否则可为 null",
            },
        }
        try:
            response = self._sdk_client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(prompt, ensure_ascii=False),
                    },
                ],
                response_format={"type": "json_object"},
                max_tokens=1024,
            )
        except OpenAIError as exc:
            raise LLMError(
                "调用模型失败，请检查网络、API Key、模型名称和账户权限。"
            ) from exc

        content = self._extract_content(response)
        try:
            return AgentDecision.model_validate_json(content)
        except ValidationError as exc:
            raise LLMError("模型返回的 Agent 决策不是有效的约定 JSON。") from exc

    @staticmethod
    def _extract_content(response: object) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            raise LLMError("模型没有返回可显示的文本。")

        content = getattr(choices[0].message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise LLMError("模型没有返回可显示的文本。")
        return content.strip()
