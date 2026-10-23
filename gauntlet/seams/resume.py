# Copyright 2026 oh shit, gorillas!
"""Resume persisted actions through an injected executor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path

    from gauntlet.core.records import (
        Action,
        Effect,
        ExecutionAnswer,
        RecoveryPoint,
        RecoveryResult,
        State,
    )

__all__ = ["Executor", "pending_action", "resume"]


class Executor(Protocol):
    """Prepare, execute and recover a persisted effect."""

    def prepare(self, effect: Effect, *, dispatch: int) -> RecoveryPoint:
        """Prepare a durable checkpoint for this effect's dispatch."""
        raise NotImplementedError

    def __call__(self, effect: Effect, point: RecoveryPoint) -> ExecutionAnswer:
        """Execute an effect against its saved recovery point."""
        raise NotImplementedError

    def recover(self, effect: Effect, point: RecoveryPoint) -> RecoveryResult:
        """Restore or reconcile interrupted work from its saved point."""
        raise NotImplementedError


def pending_action(job: Path) -> Action:
    """Load the persisted job and return its pending action."""
    raise NotImplementedError


def resume(job: Path, *, execute: Executor) -> State:
    """Continue the persisted job through the supplied executor."""
    raise NotImplementedError
