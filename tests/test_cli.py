from __future__ import annotations

from small_agent.cli import main
from small_agent.llm import LLMError


class FakeGenerator:
    def __init__(self, reply: str = "模拟回复", error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.inputs: list[str] = []

    def generate(self, user_input: str) -> str:
        self.inputs.append(user_input)
        if self.error is not None:
            raise self.error
        return self.reply


def test_cli_prints_reply(monkeypatch, capsys) -> None:
    generator = FakeGenerator("测试成功")
    monkeypatch.setattr("builtins.input", lambda _: "请回复测试")

    exit_code = main(generator)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "助手：测试成功\n"
    assert captured.err == ""
    assert generator.inputs == ["请回复测试"]


def test_cli_rejects_blank_input_without_calling_model(monkeypatch, capsys) -> None:
    generator = FakeGenerator()
    monkeypatch.setattr("builtins.input", lambda _: "   ")

    exit_code = main(generator)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "问题不能为空" in captured.err
    assert generator.inputs == []


def test_cli_reports_model_failure(monkeypatch, capsys) -> None:
    generator = FakeGenerator(error=LLMError("模拟模型故障"))
    monkeypatch.setattr("builtins.input", lambda _: "你好")

    exit_code = main(generator)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == "错误：模拟模型故障\n"

