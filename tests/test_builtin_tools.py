from __future__ import annotations

from datetime import UTC, datetime

import pytest

from small_agent.builtin_tools import (
    CurrentTimeTool,
    ReadTextFileTool,
    TextStatsTool,
    build_default_registry,
)
from small_agent.tooling import ToolErrorCode


def test_current_time_tool_uses_injected_clock() -> None:
    tool = CurrentTimeTool(lambda: datetime(2026, 8, 25, 12, 30, tzinfo=UTC))

    result = tool.invoke("{}")

    assert result.output == "2026-08-25T12:30:00+00:00"


def test_text_stats_tool_returns_normalized_counts() -> None:
    result = TextStatsTool().invoke('{"text":"hello world\\n第二行"}')

    assert result.output == '{"characters":15,"words":3,"lines":2}'


def test_read_text_file_reads_allowed_workspace_file(tmp_path) -> None:
    target = tmp_path / "notes.md"
    target.write_text("阶段 3 测试", encoding="utf-8")

    result = ReadTextFileTool(tmp_path).invoke('{"path":"notes.md"}')

    assert result.success is True
    assert result.output == "阶段 3 测试"


@pytest.mark.parametrize(
    "path",
    ["../outside.md", "/tmp/outside.md", ".env", "data.json", ".hidden.md"],
)
def test_read_text_file_rejects_disallowed_paths(tmp_path, path: str) -> None:
    result = ReadTextFileTool(tmp_path).invoke(f'{{"path":"{path}"}}')

    assert result.success is False
    assert result.error_code == ToolErrorCode.EXECUTION_ERROR


def test_read_text_file_rejects_symlink_escape(tmp_path) -> None:
    outside = tmp_path.parent / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    (tmp_path / "link.md").symlink_to(outside)

    result = ReadTextFileTool(tmp_path).invoke('{"path":"link.md"}')

    assert result.success is False
    assert "超出工作区" in result.error  # type: ignore[operator]


def test_read_text_file_rejects_oversized_file(tmp_path) -> None:
    (tmp_path / "large.txt").write_text("x" * 11, encoding="utf-8")

    result = ReadTextFileTool(tmp_path, max_bytes=10).invoke(
        '{"path":"large.txt"}'
    )

    assert result.success is False
    assert "64 KiB" in result.error  # type: ignore[operator]


def test_default_registry_contains_only_stage_three_tools(tmp_path) -> None:
    registry = build_default_registry(tmp_path)

    assert registry.names == (
        "calculator",
        "current_time",
        "text_stats",
        "read_text_file",
    )
