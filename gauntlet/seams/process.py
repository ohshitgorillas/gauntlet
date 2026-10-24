# Copyright 2026 oh shit, gorillas!
"""Run and start child processes through one command record."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NoReturn, Protocol

from gauntlet.seams.readiness import SYSTEM, Clock

if TYPE_CHECKING:
    from pathlib import Path


def _no_outputs() -> dict[str, Path]:
    """Return an empty outputs mapping."""
    return {}


@dataclass(frozen=True)
class Command:
    """One child process to run."""

    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str] | None = None
    timeout: float | None = None
    throttled: bool = False
    outputs: Mapping[str, Path] = field(default_factory=_no_outputs)
    capture: bool = True
    pass_fds: tuple[int, ...] = ()


@dataclass(frozen=True)
class Completed:
    """The result of a finished child process."""

    status: int
    stdout: str
    stderr: str
    timed_out: bool
    outputs: Mapping[str, str | None]

    def output(self) -> str:
        """Return the child's combined output."""
        raise NotImplementedError


type Runner = Callable[[Command], Completed]


class Child(Protocol):
    """A started child process."""

    def wait(self) -> Completed:
        """Wait for the child and return its result."""
        ...

    def close(self) -> None:
        """Release the child's resources."""
        ...


type Starter = Callable[[Command], Child]


def run(command: Command, *, clock: Clock = SYSTEM) -> Completed:
    """Run the command to completion."""
    raise NotImplementedError


def start(command: Command, *, clock: Clock = SYSTEM) -> Child:
    """Start the command and return its child."""
    raise NotImplementedError


def exec_command(argv: tuple[str, ...], env: Mapping[str, str]) -> NoReturn:
    """Replace this process with the command."""
    raise NotImplementedError
