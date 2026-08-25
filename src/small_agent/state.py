from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DecisionType(StrEnum):
    CONTINUE = "continue"
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


class AgentDecision(BaseModel):
    """模型在一个循环步骤中返回的、可公开展示的结构化决策。"""

    model_config = ConfigDict(extra="forbid")

    decision: DecisionType
    action: NonEmptyText
    observation: NonEmptyText
    final_answer: NonEmptyText | None = None
    failure_reason: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_result_fields(self) -> AgentDecision:
        if self.decision == DecisionType.COMPLETE and not self.final_answer:
            raise ValueError("complete 决策必须包含 final_answer")
        if self.decision == DecisionType.FAIL and not self.failure_reason:
            raise ValueError("fail 决策必须包含 failure_reason")
        return self


class AgentStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=1)
    decision: DecisionType
    action: NonEmptyText
    observation: NonEmptyText


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
