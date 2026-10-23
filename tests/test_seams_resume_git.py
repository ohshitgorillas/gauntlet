# Copyright 2026 oh shit, gorillas!
"""Order 39a: durable git intents survive killed resume drivers."""

import contextlib
import subprocess
import sys
from pathlib import Path
from typing import override

import pytest

from gauntlet.core import records
from gauntlet.seams.job import JobStore
from gauntlet.seams.resume import resume
from tests.support.answers import design, seed, state
from tests.support.capture import captured
from tests.support.lifeline import Beacon, Lifeline
from tests.support.recovery import Replies, RepliesExhaustedError

_STAGES = {
    "commit-tests": records.Stage.LOCK,
    "commit-step": records.Stage.BUILD,
    "land": records.Stage.LAND,
}
_INTENT = records.GitIntent("repo", "refs/heads/job", "before", "prepared-after")
_POINT = records.RecoveryPoint(0, "checkpoint/git-e1", _INTENT)
_REPLAY = records.RecoveryPoint(1, "checkpoint/git-e1", _INTENT)
_CHILD = """
import sys
from gauntlet.core import records
from tests.support.recovery import checkpoint_child
from tests.test_seams_resume_git import _POINT
checkpoint_child(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]),
    (records.Completed('git-e1', 0, 'prepared-after'),),
    points=(_POINT,), recoveries=(records.Reconciled('prepared-after'),),
    checkpoint=sys.argv[4])
"""


def _saved(operation: str) -> records.State:
    """Literal approved artifacts and saved results, before git publication."""
    stage = _STAGES[operation]
    artifacts = (
        records.Artifact("design", 1, records.RoleAnswer(design())),
        records.Artifact("plan", 1, records.RoleAnswer(seed("plan"))),
        records.Artifact("spec", 2, records.RoleAnswer(seed("spec"))),
        records.Artifact("tests", 1, records.RoleAnswer(seed("tests"))),
        records.Artifact("build:s1", 1, records.RoleAnswer(seed("build"))),
    )
    effect = records.Effect(
        "git-e1",
        stage,
        operation,
        None,
        "s1" if operation == "commit-step" else None,
        None,
        artifacts,
    )
    return state(
        stage=stage,
        artifacts=artifacts,
        pending=(records.Pending(effect, "ready", None),),
        steps=(records.StepRun("s1", 1, "before", "accepted partial", "running"),)
        if operation == "commit-step"
        else (),
        owners=(("pkg/home.py", "core-builder"),),
        rounds=(records.Round(records.Loop.BUILD, 1),),
        checks=(
            records.CheckRow(
                "saved-check", stage, 0, "gates", records.Verdict.PASS, "saved output"
            ),
        ),
        controls=(
            records.OwnerUse(
                "approve", records.Stage.SPEC, "approved claims and marks"
            ),
        ),
        amendments=(records.Amendment(("S1",), "approved wording"),),
    )


def _kill(job: Path, checkpoint: str) -> None:
    """Kill only after the real resume driver announces its durable boundary."""

    def probe() -> tuple[bytes, int]:
        with Beacon() as beacon, Lifeline() as line:
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    _CHILD,
                    str(job),
                    str(beacon.write_fd),
                    str(line.read_fd),
                    checkpoint,
                ],
                pass_fds=(beacon.write_fd, line.read_fd),
            )
            try:
                announcement = beacon.seen()
                if announcement:
                    child.kill()
                return announcement, child.wait()
            finally:
                child.kill()
                child.wait()

    result = captured(probe)
    assert (result.result, result.out, result.err) == (
        (checkpoint.encode("ascii") + b"\n", -9),
        [],
        [],
    )


def _drive(job: Path, replies: Replies) -> records.State:
    """Stop at an unspecified successor without supplying invented answers."""
    with contextlib.suppress(RepliesExhaustedError):
        resume(job, execute=replies)
    with JobStore(job) as store:
        return store.load()


# Reexecuting an applied commit, losing saved approvals, or changing the point fails.
@pytest.mark.parametrize("operation", ["commit-tests", "commit-step", "land"])
def test_applied_intent_reconciles_after_another_recovery_crash(
    tmp_path: Path,
    operation: str,
) -> None:
    """Two killed drivers retain one intent and recover its ordinary receipt."""
    saved = _saved(operation)
    effect = saved.pending[0].effect
    with JobStore(tmp_path) as store:
        store.create(saved)
    _kill(tmp_path, "started")
    with JobStore(tmp_path) as store:
        started = store.load()
    assert started.pending == (records.Pending(effect, "started", None, 0, _POINT),)
    _kill(tmp_path, "recovering")
    with JobStore(tmp_path) as store:
        recovering = store.load()
    assert recovering.pending == (
        records.Pending(effect, "recovering", None, 0, _POINT),
    )
    replies = Replies((), recoveries=(records.Reconciled("prepared-after"),))
    completed = _drive(tmp_path, replies)
    receipt = records.Receipt(
        "git-e1", records.Completed("git-e1", 0, "prepared-after")
    )
    assert completed.receipts.count(receipt) == 1
    assert replies.seen.count(effect) == 1
    assert (
        completed.artifacts,
        completed.checks,
        completed.controls,
        completed.amendments,
        completed.owners,
        completed.rounds,
    ) == (
        saved.artifacts,
        saved.checks,
        saved.controls,
        saved.amendments,
        saved.owners,
        saved.rounds,
    )
    if operation == "commit-step":
        assert completed.steps == (
            records.StepRun("s1", 1, "before", None, "complete"),
        )
    if operation == "land":
        assert completed.status == "landed"
    again = _drive(tmp_path, Replies(()))
    assert again.receipts.count(receipt) == 1
    assert all(p.effect.id != "git-e1" for p in again.pending)


class _Observed(Replies):
    """Observe protocol ordering while returning only supplied literal replies."""

    def __init__(self) -> None:
        super().__init__(
            (records.Completed("git-e1", 1, "prepared-after"),),
            points=(_REPLAY,),
            recoveries=(records.Restored(),),
        )
        self.calls: list[tuple[str, records.Effect, records.RecoveryPoint | int]] = []

    @override
    def prepare(
        self, effect: records.Effect, *, dispatch: int
    ) -> records.RecoveryPoint:
        self.calls.append(("prepare", effect, dispatch))
        return super().prepare(effect, dispatch=dispatch)

    @override
    def __call__(
        self, effect: records.Effect, point: records.RecoveryPoint
    ) -> records.ExecutionAnswer:
        self.calls.append(("execute", effect, point))
        return super().__call__(effect, point)

    @override
    def recover(
        self, effect: records.Effect, point: records.RecoveryPoint
    ) -> records.RecoveryResult:
        self.calls.append(("recover", effect, point))
        return super().recover(effect, point)


# Treating an unreferenced prepared object as success, or replay before restore, fails.
@pytest.mark.parametrize("operation", ["commit-tests", "commit-step", "land"])
def test_unapplied_intent_restores_before_replaying_exact_intent(
    tmp_path: Path,
    operation: str,
) -> None:
    """Restored means replay with a fresh dispatch and the same logical inputs."""
    saved = _saved(operation)
    effect = saved.pending[0].effect
    with JobStore(tmp_path) as store:
        store.create(saved)
    _kill(tmp_path, "started")
    replies = _Observed()
    completed = _drive(tmp_path, replies)
    assert replies.calls[:3] == [
        ("recover", effect, _POINT),
        ("prepare", effect, 1),
        ("execute", effect, _REPLAY),
    ]
    assert (
        records.Receipt("git-e1", records.Completed("git-e1", 1, "prepared-after"))
        in completed.receipts
    )
    assert not any(
        r.event == records.Completed("git-e1", 0, "prepared-after")
        for r in completed.receipts
    )
    assert (
        completed.artifacts,
        completed.checks,
        completed.controls,
        completed.amendments,
        completed.rounds,
    ) == (
        saved.artifacts,
        saved.checks,
        saved.controls,
        saved.amendments,
        saved.rounds,
    )
