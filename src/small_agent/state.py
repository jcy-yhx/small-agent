from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DecisionType(StrEnum):
    CONTINUE = "continue"
    TOOL_CALL = "tool_call"
    COMPLETE = "complete"
    FAIL = "fail"


class AgentStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ERROR = "error"


class TerminationReason(StrEnum):
    TASK_COMPLETED = "task_completed"
    ACTIVE_FAILURE = "active_failure"
    MAX_STEPS_REACHED = "max_steps_reached"
    USER_CANCELLED = "user_cancelled"
    UNRECOVERABLE_ERROR = "unrecoverable_error"


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    ]
    name: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
            max_length=64,
            pattern=r"^[a-z][a-z0-9_]*$",
        ),
    ]
    arguments_json: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=2000)
    ]


class AgentDecision(BaseModel):
    """模型在一个循环步骤中返回的、可公开展示的结构化决策。"""

    model_config = ConfigDict(extra="forbid")

    decision: DecisionType
    action: NonEmptyText
    observation: NonEmptyText
    final_answer: NonEmptyText | None = None
    failure_reason: NonEmptyText | None = None
    tool_call: ToolCallRequest | None = None

    @model_validator(mode="after")
    def validate_result_fields(self) -> AgentDecision:
        if self.decision == DecisionType.COMPLETE and not self.final_answer:
            raise ValueError("complete 决策必须包含 final_answer")
        if self.decision == DecisionType.FAIL and not self.failure_reason:
            raise ValueError("fail 决策必须包含 failure_reason")
        if self.decision == DecisionType.TOOL_CALL and self.tool_call is None:
            raise ValueError("tool_call 决策必须包含 tool_call")
        if self.decision != DecisionType.COMPLETE and self.final_answer is not None:
            raise ValueError("只有 complete 决策可以包含 final_answer")
        if self.decision != DecisionType.FAIL and self.failure_reason is not None:
            raise ValueError("只有 fail 决策可以包含 failure_reason")
        if self.decision != DecisionType.TOOL_CALL and self.tool_call is not None:
            raise ValueError("只有 tool_call 决策可以包含 tool_call")
        return self


class ToolObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_call_id: str
    tool_name: str
    arguments: str | None = None
    success: bool
    output: NonEmptyText | None = None
    error: NonEmptyText | None = None
    error_code: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_result(self) -> ToolObservation:
        if self.success and (
            self.output is None or self.error is not None or self.error_code is not None
        ):
            raise ValueError("成功的工具观察必须只包含 output")
        if not self.success and (self.error is None or self.output is not None):
            raise ValueError("失败的工具观察必须只包含 error")
        return self


class AgentStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=1)
    decision: DecisionType
    action: NonEmptyText
    observation: NonEmptyText
    tool_call: ToolCallRequest | None = None
    tool_observation: ToolObservation | None = None

    @model_validator(mode="after")
    def validate_tool_fields(self) -> AgentStep:
        has_tool_data = self.tool_call is not None or self.tool_observation is not None
        if self.decision == DecisionType.TOOL_CALL and not (
            self.tool_call is not None and self.tool_observation is not None
        ):
            raise ValueError("tool_call 步骤必须包含请求和执行观察")
        if self.decision != DecisionType.TOOL_CALL and has_tool_data:
            raise ValueError("非 tool_call 步骤不能包含工具数据")
        return self


class AgentState(BaseModel):
    """一次 Agent 运行的显式状态。"""

    model_config = ConfigDict(validate_assignment=True)

    goal: NonEmptyText
    max_steps: int = Field(ge=1, le=10)
    current_step: int = Field(default=0, ge=0)
    status: AgentStatus = AgentStatus.RUNNING
    steps: list[AgentStep] = Field(default_factory=list)
    final_answer: str | None = None
    error: str | None = None
    termination_reason: TerminationReason | None = None
