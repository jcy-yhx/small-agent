from __future__ import annotations

import sys
from pathlib import Path

from small_agent.agent import AgentRunner, DecisionMaker
from small_agent.builtin_tools import build_default_registry
from small_agent.config import ConfigurationError, Settings
from small_agent.llm import SiliconFlowLLMClient
from small_agent.state import AgentStatus
from small_agent.tooling import ToolRegistry


def main(
    decision_maker: DecisionMaker | None = None,
    max_steps: int | None = None,
    registry: ToolRegistry | None = None,
) -> int:
    """读取任务目标，运行最小 Agent 循环并展示公开步骤。"""
    try:
        goal = input("请输入任务目标：")
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。", file=sys.stderr)
        return 130

    if not goal.strip():
        print("错误：任务目标不能为空。", file=sys.stderr)
        return 2

    try:
        active_decision_maker = decision_maker
        active_max_steps = max_steps
        active_registry = registry or build_default_registry(Path.cwd())
        if active_decision_maker is None:
            settings = Settings.from_env()
            active_decision_maker = SiliconFlowLLMClient(settings)
            if active_max_steps is None:
                active_max_steps = settings.max_steps
        if active_max_steps is None:
            active_max_steps = 3

        state = AgentRunner(
            active_decision_maker,
            active_registry,
            active_max_steps,
        ).run(goal)
    except (ConfigurationError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    for step in state.steps:
        print(f"步骤 {step.index}")
        print(f"决策：{step.decision.value}")
        print(f"行动：{step.action}")
        print(f"观察：{step.observation}")
        if step.tool_call is not None:
            print(f"工具调用意图：{step.tool_call.name}")
        if step.tool_observation is not None:
            print("工具执行：成功" if step.tool_observation.success else "工具执行：失败")
            if step.tool_observation.arguments is not None:
                print(f"工具参数：{step.tool_observation.arguments}")
            if step.tool_observation.output is not None:
                print(f"工具结果：{step.tool_observation.output}")
            if step.tool_observation.error is not None:
                print(f"工具错误：{step.tool_observation.error}")

    if state.termination_reason is not None:
        print(f"终止原因：{state.termination_reason.value}")

    if state.status == AgentStatus.COMPLETED:
        print(f"助手：{state.final_answer}")
        return 0

    if state.error:
        print(f"错误：{state.error}", file=sys.stderr)
    return 130 if state.status == AgentStatus.CANCELLED else 1
