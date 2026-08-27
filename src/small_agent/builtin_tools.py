from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from small_agent.calculator import Calculator
from small_agent.tooling import BaseTool, ToolExecutionError, ToolRegistry


class CurrentTimeArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone: Literal["UTC"] = "UTC"


class CurrentTimeTool(BaseTool[CurrentTimeArguments]):
    name = "current_time"
    description = "返回当前 UTC 时间，ISO 8601 格式。"
    arguments_model = CurrentTimeArguments
    parameters_schema = {
        "type": "object",
        "properties": {"timezone": {"type": "string", "enum": ["UTC"]}},
        "additionalProperties": False,
    }

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(self, arguments: CurrentTimeArguments) -> str:
        current = self._clock()
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        return current.astimezone(UTC).isoformat()


TextValue = Annotated[
    str, StringConstraints(strip_whitespace=False, min_length=1, max_length=10_000)
]


class TextStatsArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: TextValue


class TextStatsTool(BaseTool[TextStatsArguments]):
    name = "text_stats"
    description = "统计给定文本的字符数、空白分词数和行数。"
    arguments_model = TextStatsArguments
    parameters_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "minLength": 1, "maxLength": 10_000}
        },
        "required": ["text"],
        "additionalProperties": False,
    }

    def execute(self, arguments: TextStatsArguments) -> str:
        return json.dumps(
            {
                "characters": len(arguments.text),
                "words": len(arguments.text.split()),
                "lines": len(arguments.text.splitlines()) or 1,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )


FilePathValue = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class ReadTextFileArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: FilePathValue


class ReadTextFileTool(BaseTool[ReadTextFileArguments]):
    name = "read_text_file"
    description = "读取工作区内非隐藏的 UTF-8 .txt 或 .md 文件，最大 64 KiB。"
    arguments_model = ReadTextFileArguments
    parameters_schema = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "工作区相对路径"}},
        "required": ["path"],
        "additionalProperties": False,
    }

    def __init__(self, workspace: Path, max_bytes: int = 64 * 1024) -> None:
        self._workspace = workspace.resolve()
        self._max_bytes = max_bytes

    def execute(self, arguments: ReadTextFileArguments) -> str:
        relative = Path(arguments.path)
        if relative.is_absolute() or any(
            part.startswith(".") for part in relative.parts
        ):
            raise ToolExecutionError("只允许工作区内的非隐藏相对路径。")
        if relative.suffix.lower() not in {".txt", ".md"}:
            raise ToolExecutionError("只允许读取 .txt 或 .md 文件。")

        if (
            not hasattr(os, "O_NOFOLLOW")
            or not hasattr(os, "O_NONBLOCK")
            or os.open not in os.supports_dir_fd
        ):
            raise ToolExecutionError("当前平台不支持安全文件读取。")

        directory_flags = (
            os.O_RDONLY
            | os.O_DIRECTORY
            | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0)
        )
        file_flags = (
            os.O_RDONLY
            | os.O_NONBLOCK
            | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0)
        )
        directory_fds: list[int] = []
        file_fd: int | None = None
        try:
            directory_fds.append(os.open(self._workspace, directory_flags))
            for part in relative.parts[:-1]:
                directory_fds.append(
                    os.open(part, directory_flags, dir_fd=directory_fds[-1])
                )
            file_fd = os.open(
                relative.parts[-1],
                file_flags,
                dir_fd=directory_fds[-1],
            )
            file_info = os.fstat(file_fd)
            if not stat.S_ISREG(file_info.st_mode):
                raise ToolExecutionError("目标文件不存在或不是普通文件。")
            if file_info.st_size > self._max_bytes:
                raise ToolExecutionError(
                    f"目标文件超过 {self._max_bytes} 字节限制。"
                )

            with os.fdopen(file_fd, "rb") as opened_file:
                file_fd = None
                content = opened_file.read(self._max_bytes + 1)
            if len(content) > self._max_bytes:
                raise ToolExecutionError(
                    f"目标文件超过 {self._max_bytes} 字节限制。"
                )
            return content.decode("utf-8")
        except UnicodeError as exc:
            raise ToolExecutionError("文件无法按 UTF-8 安全读取。") from exc
        except OSError as exc:
            raise ToolExecutionError("文件不存在、不是普通文件或无法安全打开。") from exc
        finally:
            if file_fd is not None:
                os.close(file_fd)
            for directory_fd in reversed(directory_fds):
                os.close(directory_fd)


def build_default_registry(workspace: Path) -> ToolRegistry:
    return ToolRegistry(
        [
            Calculator(),
            CurrentTimeTool(),
            TextStatsTool(),
            ReadTextFileTool(workspace),
        ]
    )
