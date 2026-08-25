from __future__ import annotations

from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from small_agent.tooling import BaseTool, ToolExecutionError

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


class Calculator(BaseTool[CalculatorArguments]):
    """精确执行基础十进制运算。"""

    name = CALCULATOR_NAME
    description = "精确执行两个十进制数的加、减、乘、除。数学计算必须使用此工具。"
    arguments_model = CalculatorArguments
    parameters_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [operation.value for operation in CalculatorOperation],
            },
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["operation", "a", "b"],
        "additionalProperties": False,
    }

    def execute(self, arguments: CalculatorArguments) -> str:
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

        return self._format_decimal(value)

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        formatted = format(value, "f")
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        return "0" if formatted in {"-0", ""} else formatted
