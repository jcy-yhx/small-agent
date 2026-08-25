from __future__ import annotations

from small_agent.llm import TextGenerator


class InputValidationError(ValueError):
    """用户输入不满足阶段 0 的最小要求。"""


def ask_once(generator: TextGenerator, user_input: str) -> str:
    """验证一条用户输入并完成一次模型调用。"""
    normalized_input = user_input.strip()
    if not normalized_input:
        raise InputValidationError("问题不能为空。")

    return generator.generate(normalized_input)

