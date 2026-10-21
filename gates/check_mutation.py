"""Mutation gate: stub."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from gates.core.project import Project
from gates.core.report import Finding, Outcome
from gates.core.runner import Gate, Run


@dataclass(frozen=True)
class Mutant:
    """Stub."""

    given: str
    name: str
    status: str
    diff: str


@dataclass(frozen=True)
class Mutated:
    """Stub."""

    mutants: tuple[Mutant, ...] = ()
    at_cap: bool = False
    error: str | None = None


def setting_findings(project: Project) -> list[Finding]:
    """Stub."""
    raise NotImplementedError


def outcome(settings: Sequence[Finding], mutated: Mutated) -> Outcome:
    """Stub."""
    raise NotImplementedError


def check(run: Run) -> Outcome:
    """Stub."""
    raise NotImplementedError


GATE = Gate(name="check_mutation", check=check)


def main(paths: Sequence[Path]) -> int:
    """Stub."""
    raise NotImplementedError
