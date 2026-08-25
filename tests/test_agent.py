from __future__ import annotations

from small_agent.agent import AgentRunner
from small_agent.llm import LLMError
from small_agent.state import (
    AgentDecision,
    AgentState,
    AgentStatus,
    DecisionType,
    TerminationReason,
    ToolCallRequest,
)


class ScriptedDecisionMaker:
    def __init__(self, decisions: list[AgentDecision] | None = None) -> None:
        self.decisions = decisions or []
        self.call_count = 0
        self.states: list[AgentState] = []

    def decide(self, state: AgentState) -> AgentDecision:
        self.call_count += 1
        self.states.append(state.model_copy(deep=True))
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


def tool_decision(
    arguments: str,
    name: str = "calculator",
) -> AgentDecision:
    return AgentDecision(
        decision=DecisionType.TOOL_CALL,
        action=f"请求调用 {name}",
        observation="等待执行",
        tool_call=ToolCallRequest(
            id="call-1",
            name=name,
            arguments_json=arguments,
        ),
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


def test_runner_executes_calculator_then_returns_observation_to_model() -> None:
    maker = ScriptedDecisionMaker(
        [
            tool_decision('{"operation":"multiply","a":12345,"b":678}'),
            decision(DecisionType.COMPLETE),
        ]
    )

    state = AgentRunner(maker, max_steps=3).run("计算 12345 × 678")

    tool_step = state.steps[0]
    assert state.status == AgentStatus.COMPLETED
    assert tool_step.tool_observation is not None
    assert tool_step.tool_observation.success is True
    assert tool_step.tool_observation.output == "8369910"
    assert maker.states[1].steps[0].tool_observation == tool_step.tool_observation


def test_runner_returns_invalid_arguments_as_failed_observation() -> None:
    maker = ScriptedDecisionMaker(
        [
            tool_decision('{"operation":"multiply","a":2}'),
            decision(DecisionType.FAIL),
        ]
    )

    state = AgentRunner(maker).run("计算")

    observation = state.steps[0].tool_observation
    assert observation is not None
    assert observation.success is False
    assert "参数格式或类型无效" in observation.error  # type: ignore[operator]
    assert observation.arguments is None


def test_runner_rejects_unknown_tool_without_executing_it() -> None:
    maker = ScriptedDecisionMaker(
        [tool_decision("{}", name="shell"), decision(DecisionType.FAIL)]
    )

    state = AgentRunner(maker).run("执行未知工具")

    observation = state.steps[0].tool_observation
    assert observation is not None
    assert observation.success is False
    assert observation.error == "未知工具：shell"
