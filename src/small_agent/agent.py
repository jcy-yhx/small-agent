from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from small_agent.calculator import Calculator, ToolExecutionError
from small_agent.llm import LLMError
from small_agent.state import (
    AgentDecision,
    AgentState,
    AgentStatus,
    AgentStep,
    DecisionType,
    TerminationReason,
    ToolObservation,
)


class DecisionMaker(Protocol):
    def decide(self, state: AgentState) -> AgentDecision:
        """根据当前公开状态决定下一步。"""


class AgentRunner:
    """执行受最大步数约束的最小 Agent 循环。"""

    def __init__(
        self,
        decision_maker: DecisionMaker,
        max_steps: int = 3,
        calculator: Calculator | None = None,
    ) -> None:
        if not 1 <= max_steps <= 10:
            raise ValueError("max_steps 必须在 1 到 10 之间。")
        self._decision_maker = decision_maker
        self._max_steps = max_steps
        self._calculator = calculator or Calculator()

    def run(
        self,
        goal: str,
        should_cancel: Callable[[], bool] | None = None,
    ) -> AgentState:
        clean_goal = goal.strip()
        if not clean_goal:
            raise ValueError("任务目标不能为空。")

        state = AgentState(goal=clean_goal, max_steps=self._max_steps)

        while state.status == AgentStatus.RUNNING:
            if should_cancel is not None and should_cancel():
                self._terminate_cancelled(state)
                break

            try:
                decision = self._decision_maker.decide(state)
            except KeyboardInterrupt:
                self._terminate_cancelled(state)
                break
            except LLMError as exc:
                state.status = AgentStatus.ERROR
                state.error = str(exc)
                state.termination_reason = TerminationReason.UNRECOVERABLE_ERROR
                break

            state.current_step += 1

            if decision.decision == DecisionType.TOOL_CALL:
                tool_observation = self._execute_tool(decision)
                state.steps.append(
                    AgentStep(
                        index=state.current_step,
                        decision=decision.decision,
                        action=decision.action,
                        observation=(
                            f"工具执行成功：{tool_observation.output}"
                            if tool_observation.success
                            else f"工具执行失败：{tool_observation.error}"
                        ),
                        tool_call=decision.tool_call,
                        tool_observation=tool_observation,
                    )
                )
            else:
                state.steps.append(
                    AgentStep(
                        index=state.current_step,
                        decision=decision.decision,
                        action=decision.action,
                        observation=decision.observation,
                    )
                )

            if decision.decision == DecisionType.COMPLETE:
                state.status = AgentStatus.COMPLETED
                state.final_answer = decision.final_answer
                state.termination_reason = TerminationReason.TASK_COMPLETED
            elif decision.decision == DecisionType.FAIL:
                state.status = AgentStatus.FAILED
                state.error = decision.failure_reason
                state.termination_reason = TerminationReason.ACTIVE_FAILURE
            elif state.current_step >= state.max_steps:
                state.status = AgentStatus.FAILED
                state.error = "达到最大步骤数，任务仍未完成。"
                state.termination_reason = TerminationReason.MAX_STEPS_REACHED

        return state

    def _execute_tool(self, decision: AgentDecision) -> ToolObservation:
        tool_call = decision.tool_call
        if tool_call is None:  # AgentDecision 的 Schema 已保证；保留防御性检查。
            raise LLMError("模型工具调用缺少必要数据。")

        if tool_call.name != self._calculator.name:
            return ToolObservation(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=f"未知工具：{tool_call.name}",
            )

        try:
            arguments, output = self._calculator.execute(tool_call.arguments_json)
        except ToolExecutionError as exc:
            return ToolObservation(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=str(exc),
            )

        return ToolObservation(
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            arguments=self._calculator.arguments_for_log(arguments),
            success=True,
            output=output,
        )

    @staticmethod
    def _terminate_cancelled(state: AgentState) -> None:
        state.status = AgentStatus.CANCELLED
        state.error = "用户取消了任务。"
        state.termination_reason = TerminationReason.USER_CANCELLED
