# Copyright 2026 oh shit, gorillas!
"""Resume real durable checkpoints after killing the harness, Order 39."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from gauntlet.core import records
from gauntlet.seams.job import JobStore
from gauntlet.seams.resume import pending_action, resume
from tests.support.answers import design, state
from tests.support.capture import captured
from tests.support.lifeline import Beacon, Lifeline
from tests.support.recovery import Replies

_INPUT = records.Artifact(
    "brief", 0, records.RoleAnswer(records.Brief("saved logical input"))
)
_EFFECT = records.Effect(
    "e1", records.Stage.DESIGN, "launch", "architect", None, None, (_INPUT,)
)
_POINT = records.RecoveryPoint(0, "workspace/e1", None)
_ROUNDS = (records.Round(records.Loop.DESIGN, 0),)
_CHILD = """
import sys
from gauntlet.core import records
from tests.support.answers import design
from tests.support.recovery import checkpoint_child
checkpoint_child(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]),
    (records.Answered('e1', 0, 'architect', records.RoleAnswer(design()),
        records.TraceRow('e1.launch.0', 'architect', 'model', 'medium',
            17, '0.003', 'complete')),),
    checkpoint=sys.argv[4],
    points=(records.RecoveryPoint(0, 'workspace/e1', None),),
    recoveries=(records.Restored(),))
"""


def _json_object(text: str) -> dict[str, records.Json]:
    """Parse a JSON object without depending on serialization key order."""
    value: records.Json = json.loads(text)
    assert isinstance(value, dict)
    return value


def _seed(job: Path, *, started: bool = False) -> records.State:
    """Persist the literal ready or interrupted input used by the crash probe."""
    saved = state(
        artifacts=(_INPUT,),
        rounds=_ROUNDS,
        pending=(
            records.Pending(
                _EFFECT,
                "started" if started else "ready",
                "e1.launch.0" if started else None,
                0,
                _POINT if started else None,
            ),
        ),
        launches=(
            (
                records.TraceRow(
                    "e1.launch.0", "architect", "", "", None, None, "starting"
                ),
            )
            if started
            else ()
        ),
    )
    with JobStore(job) as store:
        store.create(saved)
    return saved


def _kill_at(job: Path, checkpoint: str) -> bytes:
    """Join the child after its committed-boundary announcement and SIGKILL."""
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
            child.kill()
            child.wait()
            return announcement
        finally:
            child.kill()
            child.wait()


class _Restoring:
    """Observe driver ordering while returning literal protocol replies."""

    def __init__(self, job: Path, dispatch: int) -> None:
        self.job = job
        self.calls: list[tuple[str, records.Effect, records.RecoveryPoint | int]] = []
        self.statuses: list[str] = []
        self.replies = Replies(
            (
                records.Answered(
                    "e1",
                    dispatch,
                    "architect",
                    records.RoleAnswer(design()),
                    records.TraceRow(
                        f"e1.launch.{dispatch}",
                        "architect",
                        "model",
                        "medium",
                        17,
                        "0.003",
                        "complete",
                    ),
                ),
            ),
            points=(records.RecoveryPoint(dispatch, "workspace/e1", None),),
            recoveries=(records.Restored(),),
        )

    def prepare(
        self, effect: records.Effect, *, dispatch: int
    ) -> records.RecoveryPoint:
        """Record the requested unchanged logical input and fresh dispatch."""
        self.calls.append(("prepare", effect, dispatch))
        return self.replies.prepare(effect, dispatch=dispatch)

    def __call__(
        self, effect: records.Effect, point: records.RecoveryPoint
    ) -> records.ExecutionAnswer:
        """Record execution only after unfinished output has been discarded."""
        self.calls.append(("execute", effect, point))
        assert not (self.job / "unfinished").exists()
        return self.replies(effect, point)

    def recover(
        self, effect: records.Effect, point: records.RecoveryPoint
    ) -> records.RecoveryResult:
        """Observe durable recovering before restoring this effect's output."""
        self.calls.append(("recover", effect, point))
        text = (self.job / "state.json").read_text(encoding="utf-8")
        data = _json_object(text)["data"]
        assert isinstance(data, dict)
        pending = data["pending"]
        assert isinstance(pending, list)
        interrupted = pending[0]
        assert isinstance(interrupted, dict)
        self.statuses.append(
            '"status":"recovering"' if interrupted["status"] == "recovering" else text
        )
        (self.job / "unfinished").unlink()
        return self.replies.recover(effect, point)


# Skipping ready publication, restoring after replay, charging a round or losing
# interrupted launches breaks the matching killed-harness checkpoint case.
@pytest.mark.parametrize("checkpoint", ["ready", "started", "recovering", "completed"])
def test_killed_checkpoint_resumes_saved_inputs(
    tmp_path: Path, checkpoint: str
) -> None:
    """Recover without an owner prompt, duplicate completion or changed inputs."""
    original = _seed(tmp_path, started=checkpoint == "recovering")
    probe = captured(lambda: _kill_at(tmp_path, checkpoint))
    assert (probe.result, probe.err) == (checkpoint.encode() + b"\n", [])
    with JobStore(tmp_path) as store:
        killed = store.load()
    if checkpoint == "completed":
        receipt = records.Receipt(
            "e1",
            records.Answered(
                "e1",
                0,
                "architect",
                records.RoleAnswer(design()),
                records.TraceRow(
                    "e1.launch.0",
                    "architect",
                    "model",
                    "medium",
                    17,
                    "0.003",
                    "complete",
                ),
            ),
        )
        assert killed.receipts.count(receipt) == 1
        replies = Replies(())
        resumed = resume(tmp_path, execute=replies)
        assert resumed.receipts.count(receipt) == 1
        assert (
            replies.seen,
            resumed.artifacts,
            resumed.launches,
            resumed.receipts,
            resumed.rounds,
            resumed.pending,
        ) == (
            (),
            killed.artifacts,
            killed.launches,
            killed.receipts,
            original.rounds,
            killed.pending,
        )
        assert any(
            artifact.answer.payload == design() for artifact in resumed.artifacts
        )
        return
    interrupted = checkpoint != "ready"
    dispatch = int(interrupted)
    if interrupted:
        (tmp_path / "unfinished").write_text("discard this output", encoding="utf-8")
    execute = _Restoring(tmp_path, dispatch)
    resumed = resume(tmp_path, execute=execute)
    expected_calls: list[tuple[str, records.Effect, records.RecoveryPoint | int]] = []
    if interrupted:
        expected_calls.append(("recover", _EFFECT, _POINT))
    expected_calls.extend(
        [
            ("prepare", _EFFECT, dispatch),
            ("execute", _EFFECT, records.RecoveryPoint(dispatch, "workspace/e1", None)),
        ]
    )
    assert (execute.calls, execute.statuses, resumed.rounds, resumed.status) == (
        expected_calls,
        ['"status":"recovering"'] if interrupted else [],
        original.rounds,
        "waiting",
    )
    assert tuple(
        (row.id, row.outcome, row.tokens, row.cost) for row in resumed.launches
    ) == (
        (
            ("e1.launch.0", "interrupted", None, None),
            ("e1.launch.1", "complete", 17, "0.003"),
        )
        if interrupted
        else (("e1.launch.0", "complete", 17, "0.003"),)
    )
    assert any(artifact.answer.payload == design() for artifact in resumed.artifacts)
    with JobStore(tmp_path) as store:
        assert store.load() == resumed


# Trusting torn trace text instead of the ledger, or dispatching while inspecting,
# would change either authoritative bytes or the pending effect identity.
def test_pending_action_repairs_trace_without_dispatch(tmp_path: Path) -> None:
    """Read the durable next action and repair its trace projection."""
    saved = _seed(tmp_path, started=True)
    before = (tmp_path / "state.json").read_bytes()
    (tmp_path / "trace.jsonl").write_text("{torn", encoding="utf-8")
    action = pending_action(tmp_path)
    assert (
        action.effects,
        action.state.rounds,
        (tmp_path / "state.json").read_bytes(),
    ) == (
        (_EFFECT,),
        saved.rounds,
        before,
    )
    expected_trace = (
        '{"format":1,"schema":"trace","data":{"id":"e1.launch.0",'
        '"role":"architect","model":"","effort":"","tokens":null,'
        '"cost":null,"outcome":"starting"}}\n'
    )
    actual_trace = (tmp_path / "trace.jsonl").read_text(encoding="utf-8")
    assert _json_object(actual_trace) == _json_object(expected_trace)
    assert (
        actual_trace
        == json.dumps(
            _json_object(actual_trace), separators=(",", ":"), ensure_ascii=False
        )
        + "\n"
    )
