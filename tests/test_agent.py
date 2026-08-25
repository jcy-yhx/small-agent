from __future__ import annotations

from small_agent.agent import AgentRunner
from small_agent.llm import LLMError
from small_agent.state import (
    AgentDecision,
    AgentState,
    AgentStatus,
    DecisionType,
    TerminationReason,
)


class ScriptedDecisionMaker:
    def __init__(self, decisions: list[AgentDecision] | None = None) -> None:
        self.decisions = decisions or []
        self.call_count = 0

    def decide(self, state: AgentState) -> AgentDecision:
        self.call_count += 1
        return self.decisions.pop(0)


class FailingDecisionMaker:
    def decide(self, state: AgentState) -> AgentDecision:
        raise LLMError("结构化响应无效")


def decision(kind: DecisionType) -> AgentDecision:
    return AgentDecision(
        decision=kind,
        action="执行公开动作",
        observation="记录公开观察",
        final_answer="最终答案" if kind == DecisionType.COMPLETE else None,
        failure_reason="主动终止原因" if kind == DecisionType.FAIL else None,
    )


def test_runner_completes_after_multiple_steps() -> None:
    maker = ScriptedDecisionMaker(
        [decision(DecisionType.CONTINUE), decision(DecisionType.COMPLETE)]
    )

    state = AgentRunner(maker, max_steps=3).run("完成任务")

    assert state.status == AgentStatus.COMPLETED
    assert state.termination_reason == TerminationReason.TASK_COMPLETED
    assert state.current_step == 2
    assert state.final_answer == "最终答案"


def test_runner_records_active_failure() -> None:
    state = AgentRunner(
        ScriptedDecisionMaker([decision(DecisionType.FAIL)])
    ).run("无法完成的任务")

    assert state.status == AgentStatus.FAILED
    assert state.termination_reason == TerminationReason.ACTIVE_FAILURE
    assert state.error == "主动终止原因"


def test_runner_stops_at_max_steps() -> None:
    maker = ScriptedDecisionMaker([decision(DecisionType.CONTINUE)])

    state = AgentRunner(maker, max_steps=1).run("持续任务")

    assert state.status == AgentStatus.FAILED
    assert state.termination_reason == TerminationReason.MAX_STEPS_REACHED
    assert state.current_step == 1
    assert maker.call_count == 1


def test_runner_can_be_cancelled_before_model_call() -> None:
    maker = ScriptedDecisionMaker([decision(DecisionType.COMPLETE)])

    state = AgentRunner(maker).run("任务", should_cancel=lambda: True)

    assert state.status == AgentStatus.CANCELLED
    assert state.termination_reason == TerminationReason.USER_CANCELLED
    assert maker.call_count == 0


def test_runner_converts_model_error_to_unrecoverable_state() -> None:
    state = AgentRunner(FailingDecisionMaker()).run("任务")

    assert state.status == AgentStatus.ERROR
    assert state.termination_reason == TerminationReason.UNRECOVERABLE_ERROR
    assert state.error == "结构化响应无效"
