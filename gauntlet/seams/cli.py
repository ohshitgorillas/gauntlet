# Copyright 2026 oh shit, gorillas!
"""Parse resume arguments and translate typed failures into output and status."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

from gauntlet.core.errors import CapabilityError, GauntletError
from gauntlet.core.records import Action
from gauntlet.seams.resume import resume

if TYPE_CHECKING:
    from collections.abc import Sequence

    from gauntlet.seams.resume import Executor

__all__ = ["exit_code", "main", "render_action", "render_error"]


def render_action(action: Action) -> str:
    """Name the persisted stage and pending operations of an action."""
    state = action.state
    operations = [pending.effect.operation for pending in state.pending]
    return f"stage {state.stage.value}, status {state.status}, pending {operations}"


def render_error(error: GauntletError) -> str:
    """Name the fields of a typed failure."""
    return repr(error)


def exit_code(error: GauntletError | None) -> int:
    """Return the process status for a finished run or a typed failure."""
    return 0 if error is None else 2


def main(
    arguments: Sequence[str] | None = None, *, execute: Executor | None = None
) -> int:
    """Run gauntlet resume <id> against the caller's repository root."""
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(required=True)
    command = commands.add_parser("resume")
    command.add_argument("id", type=_job_folder)
    identity: str = parser.parse_args(arguments).id
    job = Path.cwd() / ".gauntlet" / "jobs" / identity
    try:
        action = _resumed(job, execute)
    except GauntletError as error:
        sys.stderr.write(f"{render_error(error)}\n")
        return exit_code(error)
    sys.stdout.write(f"{render_action(action)}\n")
    return 2 if action.state.status == "stopped" else exit_code(None)


def _job_folder(identity: str) -> str:
    """Accept one job-folder component: no dot, dot-dot or path separator."""
    if identity == os.pardir or PurePath(identity).parts != (identity,):
        raise ValueError
    return identity


def _resumed(job: Path, execute: Executor | None) -> Action:
    """Resume through the supplied executor and return its saved state's pending work."""
    if execute is None:
        raise CapabilityError(resume.__name__)
    state = resume(job, execute=execute)
    return Action(state, tuple(pending.effect for pending in state.pending))
