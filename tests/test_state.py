from __future__ import annotations

import pytest
from pydantic import ValidationError

from small_agent.state import AgentDecision, DecisionType


def test_complete_decision_requires_final_answer() -> None:
    with pytest.raises(ValidationError, match="final_answer"):
        AgentDecision(
            decision=DecisionType.COMPLETE,
            action="回答",
            observation="信息充分",
        )


def test_fail_decision_requires_failure_reason() -> None:
    with pytest.raises(ValidationError, match="failure_reason"):
        AgentDecision(
            decision=DecisionType.FAIL,
            action="停止",
            observation="能力不足",
        )


def test_decision_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AgentDecision.model_validate(
            {
                "decision": "continue",
                "action": "继续",
                "observation": "还需处理",
                "hidden_reasoning": "不应进入状态",
            }
        )


def test_decision_rejects_whitespace_only_public_text() -> None:
    with pytest.raises(ValidationError):
        AgentDecision(
            decision="continue",
            action="   ",
            observation="仍需处理",
        )
