from __future__ import annotations

from typing import Protocol

from openai import OpenAI, OpenAIError

from small_agent.config import Settings


SYSTEM_PROMPT = "你是一个友好、准确、回答简洁的 AI 助手。"


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
