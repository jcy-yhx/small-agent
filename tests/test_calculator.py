from __future__ import annotations

import pytest

from small_agent.calculator import Calculator
from small_agent.tooling import ToolErrorCode


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ('{"operation":"multiply","a":12345,"b":678}', "8369910"),
        ('{"operation":"add","a":0.1,"b":0.2}', "0.3"),
        (
            '{"operation":"subtract","a":1000000000000000000000001,"b":1}',
            "1000000000000000000000000",
        ),
        (
            '{"operation":"multiply",'
            '"a":9999999999999999999999999999999999999999,'
            '"b":9999999999999999999999999999999999999999}',
            "99999999999999999999999999999999999999980000000000000000000000000000000000000001",
        ),
        ('{"operation":"divide","a":1,"b":8}', "0.125"),
    ],
)
def test_calculator_executes_decimal_operations_exactly(
    arguments: str, expected: str
) -> None:
    result = Calculator().invoke(arguments)

    assert result.success is True
    assert result.output == expected


@pytest.mark.parametrize(
    ("arguments", "message", "error_code"),
    [
        ('{"operation":"divide","a":1,"b":0}', "除以零", ToolErrorCode.EXECUTION_ERROR),
        ('{"operation":"multiply","a":2}', "参数格式或类型无效", ToolErrorCode.INVALID_ARGUMENTS),
        ('{"operation":"power","a":2,"b":3}', "参数格式或类型无效", ToolErrorCode.INVALID_ARGUMENTS),
        ('{"operation":"add","a":"abc","b":1}', "参数格式或类型无效", ToolErrorCode.INVALID_ARGUMENTS),
        ('{"operation":"add","a":1,"b":2,"code":"ignored"}', "参数格式或类型无效", ToolErrorCode.INVALID_ARGUMENTS),
        (
            '{"operation":"add","a":'
            '11111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111,'
            '"b":1}',
            "参数格式或类型无效", ToolErrorCode.INVALID_ARGUMENTS,
        ),
        (
            '{"operation":"add","a":0.111111111111111111111111111111111111111111111111111,'
            '"b":1}',
            "参数格式或类型无效", ToolErrorCode.INVALID_ARGUMENTS,
        ),
    ],
)
def test_calculator_rejects_unsafe_or_invalid_arguments(
    arguments: str, message: str, error_code: ToolErrorCode
) -> None:
    result = Calculator().invoke(arguments)

    assert result.success is False
    assert result.error is not None and message in result.error
    assert result.error_code == error_code
