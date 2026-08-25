from __future__ import annotations

import pytest

from small_agent.config import (
    ConfigurationError,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    Settings,
)


def test_settings_require_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    monkeypatch.delenv("SILICONFLOW_MODEL", raising=False)
    monkeypatch.delenv("SILICONFLOW_BASE_URL", raising=False)

    with pytest.raises(ConfigurationError, match="SILICONFLOW_API_KEY"):
        Settings.from_env()


def test_settings_use_default_model(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    monkeypatch.delenv("SILICONFLOW_MODEL", raising=False)
    monkeypatch.delenv("SILICONFLOW_BASE_URL", raising=False)

    settings = Settings.from_env()

    assert settings.api_key == "test-key"
    assert settings.model == DEFAULT_MODEL
    assert settings.base_url == DEFAULT_BASE_URL


def test_siliconflow_variables_take_precedence(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SILICONFLOW_API_KEY", "siliconflow-key")
    monkeypatch.setenv("SILICONFLOW_MODEL", "siliconflow-model")
    monkeypatch.setenv("SILICONFLOW_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-key")
    monkeypatch.setenv("OPENAI_MODEL", "legacy-model")

    settings = Settings.from_env()

    assert settings == Settings(
        api_key="siliconflow-key",
        model="siliconflow-model",
        base_url="https://example.test/v1",
    )


def test_settings_do_not_search_parent_directories(monkeypatch, tmp_path) -> None:
    parent_env = tmp_path / ".env"
    child_dir = tmp_path / "child"
    child_dir.mkdir()
    parent_env.write_text("SILICONFLOW_API_KEY=must-not-be-loaded\n", encoding="utf-8")
    monkeypatch.chdir(child_dir)
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ConfigurationError):
        Settings.from_env()
