from __future__ import annotations

import pytest

from small_agent.chat import InputValidationError, ask_once


class FakeGenerator:
    def __init__(self, reply: str = "模拟回复") -> None:
        self.reply = reply
        self.inputs: list[str] = []

    def generate(self, user_input: str) -> str:
        self.inputs.append(user_input)
        return self.reply


def test_ask_once_returns_fake_reply() -> None:
    generator = FakeGenerator("你好！")

    reply = ask_once(generator, "  你好  ")

    assert reply == "你好！"
    assert generator.inputs == ["你好"]


def test_ask_once_rejects_blank_input_without_calling_model() -> None:
    generator = FakeGenerator()

    with pytest.raises(InputValidationError, match="问题不能为空"):
        ask_once(generator, " \n\t ")

    assert generator.inputs == []

