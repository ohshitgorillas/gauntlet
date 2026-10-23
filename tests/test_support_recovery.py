# Copyright 2026 oh shit, gorillas!
"""Order 38: literal replies and observations of real durable checkpoints."""

import subprocess
import sys
from pathlib import Path

import pytest

from gauntlet.core import records
from gauntlet.seams.job import JobStore
from gauntlet.seams.resume import Executor
from tests.support.answers import state
from tests.support.capture import captured
from tests.support.lifeline import Beacon, Lifeline
from tests.support.recovery import Replies, RepliesExhaustedError, checkpoint_child

_EFFECT = records.Effect("e1", records.Stage.DESIGN, "owner", None, None, None, ())
_OTHER = records.Effect("e2", records.Stage.PLAN, "owner", None, None, None, ())
_POINT = records.RecoveryPoint(37, "literal-workspace", None)
_ANSWER = records.Failed("different-effect", 91, "literal failure")


# Holding after the parent releases, or swallowing the literal point, fails.
def test_released_checkpoint_continues_with_literal_executor_reply() -> None:
    """A released pipe lets the announced checkpoint continue its injected driver."""
    point = records.RecoveryPoint(0, "checkpoint/e1", None)
    prepared: list[records.RecoveryPoint] = []

    def driver(execute: Executor) -> records.State:
        prepared.append(execute.prepare(_EFFECT, dispatch=0))
        return state()

    with Beacon() as beacon, Lifeline() as line:
        line.release()
        checkpoint_child(
            "unused", beacon.write_fd, line.read_fd, (), points=(point,), run=driver
        )
        announcement = beacon.seen()
    assert (announcement, prepared) == (b"ready\n", [point])


# Deriving dispatch, effect identity or a response instead of returning literals fails.
def test_replies_keep_independent_literal_streams_and_call_history() -> None:
    """Keep all three streams independent, literal and ordered across methods."""
    restored = records.Restored()
    reconciled = records.Reconciled("prepared-oid")
    second = records.Completed("another-effect", 17, "commit-oid")
    point = records.RecoveryPoint(12, None, None)
    replies = Replies(
        (_ANSWER, second), points=(_POINT, point), recoveries=(restored, reconciled)
    )
    before = replies.seen
    recovered = replies.recover(_OTHER, point)
    prepared = replies.prepare(_EFFECT, dispatch=0)
    executed = replies(_OTHER, _POINT)
    middle = replies.seen
    prepared_again = replies.prepare(_OTHER, dispatch=999)
    executed_again = replies(_EFFECT, point)
    recovered_again = replies.recover(_EFFECT, _POINT)
    assert (
        recovered is restored,
        prepared is _POINT,
        executed is _ANSWER,
        prepared_again is point,
        executed_again is second,
        recovered_again is reconciled,
        before,
        middle,
        replies.seen,
    ) == (
        True,
        True,
        True,
        True,
        True,
        True,
        (),
        (_OTHER, _EFFECT, _OTHER),
        (_OTHER, _EFFECT, _OTHER, _OTHER, _EFFECT, _EFFECT),
    )


# Silently synthesizing an exhausted stream or omitting failed calls fails.
@pytest.mark.parametrize("method", ["prepare", "execute", "recover"])
def test_exhaustion_is_typed_and_records_each_attempt(method: str) -> None:
    """Empty streams fail explicitly and preserve the history at each failure."""
    replies = Replies(())

    def invoke(effect: records.Effect) -> None:
        if method == "prepare":
            replies.prepare(effect, dispatch=0)
        elif method == "execute":
            replies(effect, _POINT)
        else:
            replies.recover(effect, _POINT)

    with pytest.raises(RepliesExhaustedError) as first:
        invoke(_EFFECT)
    with pytest.raises(RepliesExhaustedError) as second:
        invoke(_OTHER)
    assert (first.value.seen, second.value.seen, replies.seen) == (
        (_EFFECT,),
        (_EFFECT, _OTHER),
        (_EFFECT, _OTHER),
    )


# This literal writer stands in for the later resume build, not its state machine.
_CHILD = """
import sys
from dataclasses import replace
from pathlib import Path
from gauntlet.core import records
from gauntlet.seams.job import JobStore
from tests.support import recovery

def writer(execute):
    with JobStore(Path(sys.argv[1])) as store:
        saved = store.load()
        effect = saved.pending[0].effect
        point = execute.prepare(effect, dispatch=0)
        saved = replace(saved, revision=1,
            pending=(records.Pending(effect, 'started', None, 0, point),))
        store.save(saved, expected_revision=0)
        if sys.argv[4] == 'recovering' or len(sys.argv) > 5:
            saved = replace(saved, revision=2,
                pending=(records.Pending(effect, 'recovering', None, 0, point),))
            store.save(saved, expected_revision=1)
            result = execute.recover(effect, point)
            if not isinstance(result, records.Reconciled):
                return saved
            event = records.Completed(effect.id, 0, result.commit)
        else:
            event = execute(effect, point)
        saved = replace(saved, revision=saved.revision + 1, pending=(),
            receipts=(records.Receipt(effect.id, event),))
        store.save(saved, expected_revision=saved.revision - 1)
        return saved

recovery.checkpoint_child(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]),
    (records.Completed('e1', 0, None),),
    points=(records.RecoveryPoint(0, 'checkpoint/e1', None),),
    recoveries=(records.Reconciled('prepared-oid')
        if len(sys.argv) > 5 and sys.argv[5] == 'reconciled'
        else records.Restored(),), checkpoint=sys.argv[4], run=writer)
"""


# Announcing before save, observing the wrong boundary, or failing to hold fails.
@pytest.mark.parametrize("checkpoint", ["ready", "started", "recovering", "completed"])
def test_probe_holds_after_committed_checkpoint(
    tmp_path: Path, checkpoint: str
) -> None:
    """Kill only after a pipe announcement and reload the announced durable state."""
    original = state(pending=(records.Pending(_EFFECT, "ready", None),))
    with JobStore(tmp_path) as store:
        store.create(original)

    def probe() -> tuple[bytes, int]:
        with Beacon() as beacon, Lifeline() as line:
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    _CHILD,
                    str(tmp_path),
                    str(beacon.write_fd),
                    str(line.read_fd),
                    checkpoint,
                ],
                pass_fds=(beacon.write_fd, line.read_fd),
            )
            try:
                announcement = beacon.seen()
                child.kill()
                return announcement, child.wait()
            finally:
                child.kill()
                child.wait()

    output = captured(probe)
    with JobStore(tmp_path) as store:
        loaded = store.load()
    event = records.Completed("e1", 0, None)
    expected_pending = (
        ()
        if checkpoint == "completed"
        else (
            records.Pending(
                _EFFECT,
                checkpoint,
                None,
                0,
                None
                if checkpoint == "ready"
                else records.RecoveryPoint(0, "checkpoint/e1", None),
            ),
        )
    )

    assert (
        output.result,
        output.out,
        output.err,
        loaded.pending,
        loaded.receipts,
        loaded.revision,
    ) == (
        (checkpoint.encode("ascii") + b"\n", -9),
        [],
        [],
        expected_pending,
        (records.Receipt("e1", event),) if checkpoint == "completed" else (),
        {"ready": 0, "started": 1, "recovering": 2, "completed": 2}[checkpoint],
    )


# A reconciled receipt completes an effect; a restored workspace alone does not.
@pytest.mark.parametrize("result", ["reconciled", "restored"])
def test_completed_probe_distinguishes_reconciliation_from_restoration(
    tmp_path: Path, result: str
) -> None:
    """Hold after a saved reconciled receipt and leave restoration unannounced."""
    with JobStore(tmp_path) as store:
        store.create(state(pending=(records.Pending(_EFFECT, "ready", None),)))

    def probe() -> tuple[bytes, int]:
        with Beacon() as beacon, Lifeline() as line:
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    _CHILD,
                    str(tmp_path),
                    str(beacon.write_fd),
                    str(line.read_fd),
                    "completed",
                    result,
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

    output = captured(probe)
    with JobStore(tmp_path) as store:
        loaded = store.load()
    expected: tuple[tuple[bytes, int], tuple[records.Receipt, ...]] = (
        (
            (b"completed\n", -9),
            (records.Receipt("e1", records.Completed("e1", 0, "prepared-oid")),),
        )
        if result == "reconciled"
        else ((b"", 0), ())
    )
    empty_errors: list[str] = []
    assert (output.result, loaded.receipts, output.err) == (
        expected[0],
        expected[1],
        empty_errors,
    )
