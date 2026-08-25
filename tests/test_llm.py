from __future__ import annotations

from types import SimpleNamespace

import pytest

from small_agent.config import Settings
from small_agent.llm import (
    AGENT_SYSTEM_PROMPT,
    LLMError,
    SYSTEM_PROMPT,
    SiliconFlowLLMClient,
)
from small_agent.state import AgentState, DecisionType


class FakeCompletions:
    def __init__(self, output_text: str | None) -> None:
        self.output_text = output_text
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=self.output_text))
            ]
        )


class FakeSDKClient:
    def __init__(self, output_text: str | None) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(output_text))


def test_siliconflow_client_sends_expected_messages() -> None:
    sdk_client = FakeSDKClient("  模型回复  ")
    client = SiliconFlowLLMClient(
        Settings(api_key="test-key", model="test-model"),
        sdk_client=sdk_client,  # type: ignore[arg-type]
    )

    reply = client.generate("用户问题")

    assert reply == "模型回复"
    assert sdk_client.chat.completions.calls == [
        {
            "model": "test-model",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "用户问题"},
            ],
        }
    ]


def test_siliconflow_client_rejects_empty_output() -> None:
    sdk_client = FakeSDKClient("   ")
    client = SiliconFlowLLMClient(
        Settings(api_key="test-key"),
        sdk_client=sdk_client,  # type: ignore[arg-type]
    )

    with pytest.raises(LLMError, match="没有返回"):
        client.generate("用户问题")


def test_siliconflow_client_requests_and_validates_json_decision() -> None:
    sdk_client = FakeSDKClient(
        '{"decision":"complete","action":"回答",'
        '"observation":"信息充分","final_answer":"42"}'
    )
    client = SiliconFlowLLMClient(
        Settings(api_key="test-key", model="test-model"),
        sdk_client=sdk_client,  # type: ignore[arg-type]
    )

    result = client.decide(AgentState(goal="答案是什么", max_steps=3))

    call = sdk_client.chat.completions.calls[0]
    messages = call["messages"]
    assert result.decision == DecisionType.COMPLETE
    assert result.final_answer == "42"
    assert call["response_format"] == {"type": "json_object"}
    assert call["max_tokens"] == 1024
    assert isinstance(messages, list)
    assert messages[0] == {"role": "system", "content": AGENT_SYSTEM_PROMPT}


def test_siliconflow_client_rejects_invalid_json_decision() -> None:
    client = SiliconFlowLLMClient(
        Settings(api_key="test-key"),
        sdk_client=FakeSDKClient("not-json"),  # type: ignore[arg-type]
    )

    with pytest.raises(LLMError, match="约定 JSON"):
        client.decide(AgentState(goal="任务", max_steps=3))
