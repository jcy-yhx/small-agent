from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from small_agent.tooling import (
    BaseTool,
    ToolErrorCode,
    ToolExecutionError,
    ToolRegistrationError,
    ToolRegistry,
)


class EchoArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


class EchoTool(BaseTool[EchoArguments]):
    name = "echo"
    description = "返回输入文本"
    arguments_model = EchoArguments
    parameters_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    }

    def execute(self, arguments: EchoArguments) -> str:
        return arguments.text


class BrokenTool(EchoTool):
    name = "broken"

    def execute(self, arguments: EchoArguments) -> str:
        raise ToolExecutionError("模拟执行失败")


class UnexpectedBrokenTool(EchoTool):
    name = "unexpected_broken"

    def execute(self, arguments: EchoArguments) -> str:
        raise RuntimeError("不应暴露的内部细节")


def test_registry_registers_defines_and_dispatches_tool() -> None:
    registry = ToolRegistry([EchoTool()])

    result = registry.execute("echo", '{"text":"hello"}')

    assert registry.names == ("echo",)
    assert registry.definitions()[0]["function"]["name"] == "echo"  # type: ignore[index]
    assert result.success is True
    assert result.output == "hello"


def test_registry_rejects_duplicate_name() -> None:
    registry = ToolRegistry([EchoTool()])

    with pytest.raises(ToolRegistrationError, match="重复"):
        registry.register(EchoTool())


def test_registry_normalizes_unknown_tool() -> None:
    result = ToolRegistry().execute("missing", "{}")

    assert result.success is False
    assert result.error_code == ToolErrorCode.UNKNOWN_TOOL


def test_base_tool_normalizes_invalid_arguments_and_execution_error() -> None:
    invalid = EchoTool().invoke("{}")
    failed = BrokenTool().invoke('{"text":"hello"}')

    assert invalid.error_code == ToolErrorCode.INVALID_ARGUMENTS
    assert failed.error_code == ToolErrorCode.EXECUTION_ERROR
    assert failed.arguments == '{"text":"hello"}'


def test_base_tool_hides_unexpected_exception_details() -> None:
    result = UnexpectedBrokenTool().invoke('{"text":"hello"}')

    assert result.error_code == ToolErrorCode.EXECUTION_ERROR
    assert result.error == "unexpected_broken 执行时发生内部错误。"
