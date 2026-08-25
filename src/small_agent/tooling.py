from __future__ import annotations

import json
from abc import ABC, abstractmethod
from decimal import Decimal
from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator


ArgumentsT = TypeVar("ArgumentsT", bound=BaseModel)


class ToolErrorCode(StrEnum):
    INVALID_ARGUMENTS = "invalid_arguments"
    EXECUTION_ERROR = "execution_error"
    UNKNOWN_TOOL = "unknown_tool"


class ToolExecutionError(RuntimeError):
    """参数有效，但工具无法完成本次执行。"""


class ToolRegistrationError(ValueError):
    """工具无法安全注册。"""


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: str
    success: bool
    arguments: str | None = None
    output: str | None = None
    error: str | None = None
    error_code: ToolErrorCode | None = None

    @model_validator(mode="after")
    def validate_result(self) -> ToolResult:
        if self.success and (
            self.output is None or self.error is not None or self.error_code is not None
        ):
            raise ValueError("成功结果必须只包含 output")
        if not self.success and (
            self.error is None or self.error_code is None or self.output is not None
        ):
            raise ValueError("失败结果必须包含 error 和 error_code")
        return self


class BaseTool(ABC, Generic[ArgumentsT]):
    name: str
    description: str
    arguments_model: type[ArgumentsT]
    parameters_schema: dict[str, object]

    def definition(self) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

    def invoke(self, arguments_json: str) -> ToolResult:
        try:
            raw = json.loads(
                arguments_json,
                parse_float=Decimal,
                parse_int=Decimal,
                parse_constant=self._reject_non_json_number,
            )
            arguments = self.arguments_model.model_validate(raw)
        except (TypeError, ValueError):
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"{self.name} 参数格式或类型无效。",
                error_code=ToolErrorCode.INVALID_ARGUMENTS,
            )

        normalized = json.dumps(
            arguments.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        try:
            output = self.execute(arguments)
        except ToolExecutionError as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                arguments=normalized,
                error=str(exc),
                error_code=ToolErrorCode.EXECUTION_ERROR,
            )
        except Exception:
            return ToolResult(
                tool_name=self.name,
                success=False,
                arguments=normalized,
                error=f"{self.name} 执行时发生内部错误。",
                error_code=ToolErrorCode.EXECUTION_ERROR,
            )

        return ToolResult(
            tool_name=self.name,
            success=True,
            arguments=normalized,
            output=output,
        )

    @abstractmethod
    def execute(self, arguments: ArgumentsT) -> str:
        """执行已经校验的参数。"""

    @staticmethod
    def _reject_non_json_number(value: str) -> None:
        raise ValueError(f"非法 JSON 数字：{value}")


class ToolRegistry:
    def __init__(self, tools: list[BaseTool[Any]] | None = None) -> None:
        self._tools: dict[str, BaseTool[Any]] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: BaseTool[Any]) -> None:
        if tool.name in self._tools:
            raise ToolRegistrationError(f"工具名称重复：{tool.name}")
        self._tools[tool.name] = tool

    def definitions(self) -> list[dict[str, object]]:
        return [tool.definition() for tool in self._tools.values()]

    def execute(self, name: str, arguments_json: str) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"未知工具：{name}",
                error_code=ToolErrorCode.UNKNOWN_TOOL,
            )
        return tool.invoke(arguments_json)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)
