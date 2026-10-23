# Copyright 2026 oh shit, gorillas!
"""Resume persisted actions through an injected executor."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Protocol

from gauntlet.core.decide import decide
from gauntlet.core.errors import RecoveryError, StateError
from gauntlet.core.records import Recovered, Tick, TraceRow
from gauntlet.seams.job import JobStore

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
    with JobStore(job) as store:
        return decide(store.load(), Tick())


def resume(job: Path, *, execute: Executor) -> State:
    """Continue the persisted job through the supplied executor."""
    with JobStore(job) as store:
        state = store.load()
        while True:
            action = decide(state, Tick())
            state = _publish(store, state, action.state)
            if state.status != "active" or not action.effects:
                return state
            effect = action.effects[0]
            pending = next(p for p in state.pending if p.effect.id == effect.id)
            if pending.status == "recovering":
                point = pending.recovery
                if point is None:
                    raise RecoveryError((effect.id,), "missing recovery point")
                result = execute.recover(effect, point)
                answer = Recovered(effect.id, pending.dispatch, result)
                try:
                    state = _publish(store, state, decide(state, answer).state)
                except StateError as error:
                    raise RecoveryError((effect.id,), error.reason) from error
                continue
            point = execute.prepare(effect, dispatch=pending.dispatch)
            launch_id = None
            launches = state.launches
            if effect.operation in {"launch", "build"}:
                launch_id = f"{effect.id}.launch.{pending.dispatch}"
                launches = (
                    *launches,
                    TraceRow(
                        launch_id, effect.role or "", "", "", None, None, "starting"
                    ),
                )
            started = replace(
                pending, status="started", recovery=point, launch_id=launch_id
            )
            try:
                state = _publish(
                    store,
                    state,
                    replace(
                        state,
                        launches=launches,
                        pending=tuple(
                            started if p == pending else p for p in state.pending
                        ),
                    ),
                )
            except StateError as error:
                raise RecoveryError((effect.id,), error.reason) from error
            event = execute(effect, point)
            state = _publish(store, state, decide(state, event).state)


def _publish(store: JobStore, before: State, after: State) -> State:
    """Assign a storage revision to a changed core or dispatch checkpoint."""
    if after == before:
        return before
    saved = replace(after, revision=before.revision + 1)
    store.save(saved, expected_revision=before.revision)
    return saved
