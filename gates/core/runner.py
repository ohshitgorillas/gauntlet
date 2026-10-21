"""One gate run, from start to exit: its sources, its scratch space, its checker's batches, its printed lines and exit."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, Protocol

from gates.core.checker import Command, Completed, Runner, run
from gates.core.project import Project, Source
from gates.core.report import Line, Outcome


class Scratch:
    """The run's temp space: one temp dir of its own in the root, made when first asked for, deleted by close."""

    def __init__(self, root: Path | None = None) -> None:
        raise NotImplementedError

    def directory(self, name: str) -> Path:
        raise NotImplementedError

    def copy(self, tree: Path, name: str) -> Path:
        raise NotImplementedError

    def once(self, name: str, make: Callable[[Path], None]) -> Path:
        raise NotImplementedError

    def close(self) -> str | None:
        raise NotImplementedError


@dataclass(frozen=True)
class Run:
    """What a gate's check works with: the project, the selected sources, the run's scratch and its process runner."""

    project: Project
    sources: tuple[Source, ...]
    scratch: Scratch
    process: Runner


@dataclass(frozen=True)
class Gate:
    """A gate: its name, its check, the sources it selects, and what it calls them in an empty run's line."""

    name: str
    check: Callable[[Run], Outcome]
    select: Callable[[Sequence[Source]], list[Source]] = list
    selects: str = "Python file"


class Checker[R](Protocol):
    """A checker process the gate runs in batches, and how its report becomes the gate's lines."""

    stopped: frozenset[int]

    def batches(self, run: Run) -> Sequence[Sequence[Source]]: ...

    def command(self, run: Run, batch: Sequence[Source]) -> Command: ...

    def read(self, completed: Completed) -> R: ...

    def expected_status(self, report: R) -> int: ...

    def lines(self, report: R, batch: Sequence[Source], *, stopped: bool) -> Sequence[Line]: ...


def check_with[R](checker: Checker[R]) -> Callable[[Run], Outcome]:
    raise NotImplementedError


def run_gate(
    gate: Gate,
    paths: Sequence[Path],
    *,
    project: Project | None = None,
    process: Runner = run,
    scratch_root: Path | None = None,
) -> int:
    raise NotImplementedError


def main(gate: Gate) -> NoReturn:
    raise NotImplementedError
