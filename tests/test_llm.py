from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from small_agent.builtin_tools import build_default_registry
from small_agent.config import Settings
from small_agent.llm import (
    AGENT_SYSTEM_PROMPT,
    LLMError,
    SYSTEM_PROMPT,
    SiliconFlowLLMClient,
)
from small_agent.state import AgentState, DecisionType
from small_agent.state import AgentStep, ToolCallRequest, ToolObservation


class FakeCompletions:
    def __init__(
        self,
        output_text: str | None,
        tool_calls: list[SimpleNamespace] | None = None,
    ) -> None:
        self.output_text = output_text
        self.tool_calls = tool_calls
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=self.output_text,
                        tool_calls=self.tool_calls,
                    )
                )
            ]
        )


class FakeSDKClient:
    def __init__(
        self,
        output_text: str | None,
        tool_calls: list[SimpleNamespace] | None = None,
    ) -> None:
        self.chat = SimpleNamespace(
            completions=FakeCompletions(output_text, tool_calls)
        )


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

    result = client.decide(
        AgentState(goal="答案是什么", max_steps=3),
        build_default_registry(Path.cwd()),
    )

    call = sdk_client.chat.completions.calls[0]
    messages = call["messages"]
    assert result.decision == DecisionType.COMPLETE
    assert result.final_answer == "42"
    assert "response_format" not in call
    assert call["max_tokens"] == 1024
    assert call["tool_choice"] == "auto"
    assert isinstance(call["tools"], list)
    tool_names = {
        definition["function"]["name"]  # type: ignore[index]
        for definition in call["tools"]
    }
    assert tool_names == {
        "calculator",
        "current_time",
        "text_stats",
        "read_text_file",
    }
    assert isinstance(messages, list)
    assert messages[0] == {"role": "system", "content": AGENT_SYSTEM_PROMPT}


def test_siliconflow_client_rejects_invalid_json_decision() -> None:
    client = SiliconFlowLLMClient(
        Settings(api_key="test-key"),
        sdk_client=FakeSDKClient("not-json"),  # type: ignore[arg-type]
    )

    with pytest.raises(LLMError, match="约定 JSON"):
        client.decide(
            AgentState(goal="任务", max_steps=3),
            build_default_registry(Path.cwd()),
        )


def test_siliconflow_client_parses_native_function_call() -> None:
    sdk_client = FakeSDKClient(
        None,
        tool_calls=[
            SimpleNamespace(
                id="call-123",
                function=SimpleNamespace(
                    name="calculator",
                    arguments='{"operation":"multiply","a":12,"b":3}',
                ),
            )
        ],
    )
    client = SiliconFlowLLMClient(
        Settings(api_key="test-key"),
        sdk_client=sdk_client,  # type: ignore[arg-type]
    )

    result = client.decide(
        AgentState(goal="计算 12 × 3", max_steps=3),
        build_default_registry(Path.cwd()),
    )

    assert result.decision == DecisionType.TOOL_CALL
    assert result.tool_call == ToolCallRequest(
        id="call-123",
        name="calculator",
        arguments_json='{"operation":"multiply","a":12,"b":3}',
    )


def test_siliconflow_client_returns_tool_observation_with_matching_id() -> None:
    sdk_client = FakeSDKClient(
        '{"decision":"complete","action":"回答",'
        '"observation":"工具已返回","final_answer":"36"}'
    )
    client = SiliconFlowLLMClient(
        Settings(api_key="test-key"),
        sdk_client=sdk_client,  # type: ignore[arg-type]
    )
    state = AgentState(
        goal="计算 12 × 3",
        max_steps=3,
        current_step=1,
        steps=[
            AgentStep(
                index=1,
                decision=DecisionType.TOOL_CALL,
                action="请求调用 calculator",
                observation="工具执行成功：36",
                tool_call=ToolCallRequest(
                    id="call-123",
                    name="calculator",
                    arguments_json=(
                        '{"operation":"multiply","a":12,"b":3}'
                    ),
                ),
                tool_observation=ToolObservation(
                    tool_call_id="call-123",
                    tool_name="calculator",
                    arguments='{"operation":"multiply","a":"12","b":"3"}',
                    success=True,
                    output="36",
                ),
            )
        ],
    )

    result = client.decide(state, build_default_registry(Path.cwd()))

    messages = sdk_client.chat.completions.calls[0]["messages"]
    assert result.final_answer == "36"
    assert isinstance(messages, list)
    assert messages[-2]["tool_calls"][0]["id"] == "call-123"
    assert messages[-1]["role"] == "tool"
    assert messages[-1]["tool_call_id"] == "call-123"


def test_siliconflow_client_rejects_multiple_tool_calls() -> None:
    tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="calculator", arguments="{}"),
    )
    client = SiliconFlowLLMClient(
        Settings(api_key="test-key"),
        sdk_client=FakeSDKClient(None, [tool_call, tool_call]),  # type: ignore[arg-type]
    )

    with pytest.raises(LLMError, match="只允许一个"):
        client.decide(
            AgentState(goal="任务", max_steps=3),
            build_default_registry(Path.cwd()),
        )
