from __future__ import annotations

from small_agent.cli import main
from small_agent.llm import LLMError
from small_agent.state import AgentDecision, AgentState, DecisionType


class FakeDecisionMaker:
    def __init__(
        self,
        decisions: list[AgentDecision] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.decisions = decisions or []
        self.error = error
        self.states: list[AgentState] = []

    def decide(self, state: AgentState) -> AgentDecision:
        self.states.append(state.model_copy(deep=True))
        if self.error is not None:
            raise self.error
        return self.decisions.pop(0)


def complete(answer: str = "测试成功") -> AgentDecision:
    return AgentDecision(
        decision=DecisionType.COMPLETE,
        action="直接回答目标",
        observation="已有足够信息",
        final_answer=answer,
    )


def test_cli_prints_steps_and_final_answer(monkeypatch, capsys) -> None:
    decision_maker = FakeDecisionMaker([complete()])
    monkeypatch.setattr("builtins.input", lambda _: "请回复测试")

    exit_code = main(decision_maker)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "步骤 1\n" in captured.out
    assert "决策：complete\n" in captured.out
    assert "终止原因：task_completed\n" in captured.out
    assert "助手：测试成功\n" in captured.out
    assert captured.err == ""
    assert decision_maker.states[0].goal == "请回复测试"


def test_cli_rejects_blank_input_without_calling_model(monkeypatch, capsys) -> None:
    decision_maker = FakeDecisionMaker([complete()])
    monkeypatch.setattr("builtins.input", lambda _: "   ")

    exit_code = main(decision_maker)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "任务目标不能为空" in captured.err
    assert decision_maker.states == []


def test_cli_reports_model_failure(monkeypatch, capsys) -> None:
    decision_maker = FakeDecisionMaker(error=LLMError("模拟模型故障"))
    monkeypatch.setattr("builtins.input", lambda _: "你好")

    exit_code = main(decision_maker)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "终止原因：unrecoverable_error" in captured.out
    assert captured.err == "错误：模拟模型故障\n"
