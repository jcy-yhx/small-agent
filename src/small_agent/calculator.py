from __future__ import annotations

import json
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


CALCULATOR_NAME = "calculator"
FiniteDecimal = Annotated[
    Decimal,
    Field(allow_inf_nan=False, max_digits=100, decimal_places=50),
]


class CalculatorOperation(StrEnum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class CalculatorArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: CalculatorOperation
    a: FiniteDecimal
    b: FiniteDecimal

    @field_validator("a", "b")
    @classmethod
    def validate_decimal_size(cls, value: Decimal) -> Decimal:
        digits = len(value.as_tuple().digits)
        exponent = value.as_tuple().exponent
        total_digits = digits + max(exponent, 0)
        decimal_places = max(-exponent, 0)
        if total_digits > 100 or decimal_places > 50:
            raise ValueError("数字最多 100 位且最多 50 位小数")
        return value


class ToolExecutionError(RuntimeError):
    """工具请求已被程序安全拒绝。"""


CALCULATOR_TOOL_DEFINITION: dict[str, object] = {
    "type": "function",
    "function": {
        "name": CALCULATOR_NAME,
        "description": "精确执行两个十进制数的加、减、乘、除。数学计算必须使用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [operation.value for operation in CalculatorOperation],
                    "description": "add、subtract、multiply 或 divide",
                },
                "a": {"type": "number", "description": "左操作数"},
                "b": {"type": "number", "description": "右操作数"},
            },
            "required": ["operation", "a", "b"],
            "additionalProperties": False,
        },
    },
}


class Calculator:
    """阶段 2 唯一允许执行的无副作用工具。"""

    name = CALCULATOR_NAME

    def execute(self, arguments_json: str) -> tuple[CalculatorArguments, str]:
        try:
            raw_arguments = json.loads(
                arguments_json,
                parse_float=Decimal,
                parse_int=Decimal,
                parse_constant=self._reject_non_json_number,
            )
            arguments = CalculatorArguments.model_validate(raw_arguments)
        except (TypeError, ValueError) as exc:
            raise ToolExecutionError("Calculator 参数格式或类型无效。") from exc

        with localcontext() as context:
            # 两个最多 100 位的十进制数相乘需要最多 200 位有效数字。
            context.prec = 210
            if arguments.operation == CalculatorOperation.ADD:
                value = arguments.a + arguments.b
            elif arguments.operation == CalculatorOperation.SUBTRACT:
                value = arguments.a - arguments.b
            elif arguments.operation == CalculatorOperation.MULTIPLY:
                value = arguments.a * arguments.b
            elif arguments.b == 0:
                raise ToolExecutionError("Calculator 不允许除以零。")
            else:
                value = arguments.a / arguments.b

        return arguments, self._format_decimal(value)

    @staticmethod
    def arguments_for_log(arguments: CalculatorArguments) -> str:
        return json.dumps(
            {
                "operation": arguments.operation.value,
                "a": str(arguments.a),
                "b": str(arguments.b),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        formatted = format(value, "f")
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        return "0" if formatted in {"-0", ""} else formatted

    @staticmethod
    def _reject_non_json_number(value: str) -> None:
        raise ValueError(f"非法 JSON 数字：{value}")
