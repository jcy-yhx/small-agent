from __future__ import annotations

import sys

from small_agent.chat import InputValidationError, ask_once
from small_agent.config import ConfigurationError, Settings
from small_agent.llm import LLMError, SiliconFlowLLMClient, TextGenerator


def main(generator: TextGenerator | None = None) -> int:
    """读取一条命令行输入，调用一次模型并输出回复。"""
    try:
        user_input = input("请输入问题：")
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。", file=sys.stderr)
        return 130

    if not user_input.strip():
        print("错误：问题不能为空。", file=sys.stderr)
        return 2

    try:
        active_generator = generator
        if active_generator is None:
            settings = Settings.from_env()
            active_generator = SiliconFlowLLMClient(settings)

        reply = ask_once(active_generator, user_input)
    except (ConfigurationError, InputValidationError, LLMError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    print(f"助手：{reply}")
    return 0
