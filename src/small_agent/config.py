from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash"
DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"


class ConfigurationError(RuntimeError):
    """本地配置不完整或无效。"""


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def from_env(cls) -> Settings:
        """从环境变量和本地 .env 文件加载阶段 0 配置。"""
        # 使用明确路径，避免测试或子项目意外向父目录搜索并加载真实 Secret。
        load_dotenv(dotenv_path=".env")

        api_key = (
            os.getenv("SILICONFLOW_API_KEY", "").strip()
            or os.getenv("OPENAI_API_KEY", "").strip()
        )
        if not api_key:
            raise ConfigurationError(
                "缺少 SILICONFLOW_API_KEY。请参考 .env.example 在本地配置。"
            )

        model = (
            os.getenv("SILICONFLOW_MODEL", "").strip()
            or os.getenv("OPENAI_MODEL", "").strip()
            or DEFAULT_MODEL
        )
        if not model:
            model = DEFAULT_MODEL

        base_url = os.getenv("SILICONFLOW_BASE_URL", DEFAULT_BASE_URL).strip()
        if not base_url:
            base_url = DEFAULT_BASE_URL

        return cls(api_key=api_key, model=model, base_url=base_url)
