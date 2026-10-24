# Copyright 2026 oh shit, gorillas!
"""Durable JobStore contract, M1 design Order 35."""

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from gauntlet.core import records
from gauntlet.core.errors import GauntletError, StorageError
from gauntlet.seams.job import JobStore
from tests.support.answers import state
from tests.support.capture import captured

_FIRST = records.TraceRow(
    "e1.launch.0", "architect", "model-é", "high", None, None, "interrupted"
)
_SECOND = records.TraceRow(
    "e1.launch.1", "architect", "model-é", "high", 19, "0.004", "complete"
)
_FIRST_TEXT = (
    '{"format":1,"schema":"trace","data":{"id":"e1.launch.0",'
    '"role":"architect","model":"model-é","effort":"high","tokens":null,'
    '"cost":null,"outcome":"interrupted"}}\n'
)
_SECOND_TEXT = (
    '{"format":1,"schema":"trace","data":{"id":"e1.launch.1",'
    '"role":"architect","model":"model-é","effort":"high","tokens":19,'
    '"cost":"0.004","outcome":"complete"}}\n'
)
# Config's last three fields: docs/superpowers/specs/m2-launcher-kinds-design.md:159-161.
_STATE_TEXT = (
    '{"format":1,"schema":"state","data":{"job":"j1","revision":0,'
    '"shape":"structure","stage":"design","status":"active","config":{'
    '"image":".gauntlet/Containerfile","tests":[{"directory":"tests",'
    '"run":"pytest {ids}"}],"gates":"make check","test_policy":"docs/testing.md",'
    '"interface":[{"language":"py","run":"stubgen -o {out} {modules}"}],'
    '"test_helpers":[],"protected":[],"test_lint":null,"implementer_network":false,'
    '"caps":{"design":2,"plan":2,"spec":2,"juror":2,"build":2,"review":2,'
    '"reopen":2},"roles":[],"readiness_timeout_seconds":10,"proxy_limits":{'
    '"header_bytes":65536,"body_bytes":33554432,"connections":8},'
    '"proxy_extra_routes":[]},"candidate":{"concern":"process running",'
    '"payoff":"one runner","risk":"a caller breaks","keeps":[],"why":null},'
    '"copies":[],"artifacts":[],"rounds":[],"steps":[],"owners":[],"cause_rounds":[],'
    '"held":[],"checks":[],"bypasses":[],"amendments":[],"controls":[],"launches":['
    '{"id":"e1.launch.0","role":"architect","model":"model-é","effort":"high",'
    '"tokens":null,"cost":null,"outcome":"interrupted"},'
    '{"id":"e1.launch.1","role":"architect","model":"model-é","effort":"high",'
    '"tokens":19,"cost":"0.004","outcome":"complete"}],"pending":[],"receipts":[],'
    '"baselines":[]}}'
)

_CONTENDER = """
from pathlib import Path
import sys
from gauntlet.core.errors import StorageError
from gauntlet.seams.job import JobStore
try:
    with JobStore(Path(sys.argv[1])):
        print("admitted")
except StorageError as error:
    print(error.operation)
"""


# Writing another filename, losing Unicode or changing ledger order breaks this.
def test_exact_records(tmp_path: Path) -> None:
    """Persist codec text and recover the complete Unicode launch ledger."""
    saved = state(launches=(_FIRST, _SECOND))
    with JobStore(tmp_path) as store:
        store.create(saved)
        loaded = store.load()
    with JobStore(tmp_path) as reopened:
        assert (
            loaded,
            reopened.load(),
            (tmp_path / "state.json").read_text(encoding="utf-8"),
            (tmp_path / "trace.jsonl").read_text(encoding="utf-8"),
        ) == (
            saved,
            saved,
            _STATE_TEXT,
            _FIRST_TEXT + _SECOND_TEXT,
        )


# Recreating an existing job must not overwrite its committed snapshot.
def test_create_never_overwrites(tmp_path: Path) -> None:
    """Reject creation over committed state without changing its bytes."""
    saved = state()
    with JobStore(tmp_path) as store:
        store.create(saved)
        before = (tmp_path / "state.json").read_bytes()
        with pytest.raises(GauntletError):
            store.create(state(revision=1, status="waiting"))
        assert ((tmp_path / "state.json").read_bytes(), store.load()) == (before, saved)


# Ignoring stale expected revisions or accepting a revision jump breaks this.
@pytest.mark.parametrize(
    ("expected", "incoming"), [(3, 4), (0, 0), (0, 2), (0, -1), (3, 1)]
)
def test_revision_rejected(tmp_path: Path, expected: int, incoming: int) -> None:
    """Reject stale writers and non-successor proposed revisions."""
    with JobStore(tmp_path) as store:
        store.create(state())
        before = (tmp_path / "state.json").read_bytes()
        with pytest.raises(GauntletError):
            store.save(state(revision=incoming), expected_revision=expected)
        assert (tmp_path / "state.json").read_bytes() == before


# Incrementing twice or discarding fields while saving breaks this.
def test_revision_advances_once(tmp_path: Path) -> None:
    """Publish successive proposed snapshots without changing their fields."""
    first = state()
    second = replace(
        first, revision=1, launches=(_FIRST,), owners=(("design", "approved"),)
    )
    third = replace(second, revision=2, launches=(_FIRST, _SECOND))
    with JobStore(tmp_path) as store:
        store.create(first)
        store.save(second, expected_revision=0)
        observed = store.load()
        store.save(third, expected_revision=1)
        assert (observed, store.load()) == (second, third)


# Accepting a duplicate launch id skips whole-state validation.
@pytest.mark.parametrize("operation", ["create", "save"])
def test_invalid_state_before_publication(tmp_path: Path, operation: str) -> None:
    """Validate the entire proposed state before creation or replacement."""
    with JobStore(tmp_path) as store:
        if operation == "save":
            store.create(state())
        before = (tmp_path / "state.json").read_bytes() if operation == "save" else None
        invalid = state(revision=int(operation == "save"), launches=(_FIRST, _FIRST))
        if operation == "create":
            with pytest.raises(GauntletError):
                store.create(invalid)
        else:
            with pytest.raises(GauntletError):
                store.save(invalid, expected_revision=0)
        observed = (
            (tmp_path / "state.json").read_bytes()
            if (tmp_path / "state.json").exists()
            else None
        )
        assert observed == before


# A blocking lock or a second admitted writer violates exclusive ownership.
def test_lock_contention_and_release(tmp_path: Path) -> None:
    """Report contention immediately and allow a writer after release."""
    with JobStore(tmp_path) as first:
        first.create(state())
        with pytest.raises(StorageError) as caught, JobStore(tmp_path):
            pass
        result = captured(
            lambda: subprocess.run(
                [sys.executable, "-c", _CONTENDER, str(tmp_path)], check=False
            )
        )
    with JobStore(tmp_path) as successor:
        assert (
            result.result.returncode,
            result.out,
            result.err,
            caught.value.operation,
            successor.load(),
        ) == (0, ["lock\n"], [], "lock", state())


# Failing to release the advisory lock when the context raises breaks this.
def test_lock_released_on_exception(tmp_path: Path) -> None:
    """Release the writer lock even when the context body raises."""

    def interrupted() -> None:
        with JobStore(tmp_path) as store:
            store.create(state())
            raise LookupError

    with pytest.raises(LookupError):
        interrupted()
    with JobStore(tmp_path) as successor:
        assert successor.load() == state()


# Inferring state from a projection, or appending to torn text, breaks this.
@pytest.mark.parametrize("projection", [None, "", "{torn", _SECOND_TEXT])
def test_load_repairs_projection(tmp_path: Path, projection: str | None) -> None:
    """Regenerate missing, stale and torn projections from authoritative state."""
    saved = state(launches=(_FIRST,))
    with JobStore(tmp_path) as store:
        store.create(saved)
    trace = tmp_path / "trace.jsonl"
    if projection is None:
        trace.unlink()
    else:
        trace.write_text(projection, encoding="utf-8")
    committed = (tmp_path / "state.json").read_bytes()
    with JobStore(tmp_path) as store:
        assert (
            store.load(),
            trace.read_text(encoding="utf-8"),
            (tmp_path / "state.json").read_bytes(),
        ) == (saved, _FIRST_TEXT, committed)


# The explicit projection repair must replace stale rows without changing state.
def test_explicit_trace_repair(tmp_path: Path) -> None:
    """Repair the ledger projection without rewriting authoritative state."""
    saved = state(launches=(_FIRST, _SECOND))
    with JobStore(tmp_path) as store:
        store.create(saved)
        (tmp_path / "trace.jsonl").write_text("broken", encoding="utf-8")
        before = (tmp_path / "state.json").read_bytes()
        store.repair_trace(saved)
        assert (
            (tmp_path / "trace.jsonl").read_text(encoding="utf-8"),
            (tmp_path / "state.json").read_bytes(),
        ) == (_FIRST_TEXT + _SECOND_TEXT, before)


# Recovering from trace, an orphan or a backup would conceal corrupt authority.
@pytest.mark.parametrize("text", ["", "{torn", "{}", "[]", "\udcff"])
def test_corrupt_state_stops(tmp_path: Path, text: str) -> None:
    """Stop on corrupt state without replacing it with inferred history."""
    with JobStore(tmp_path) as store:
        store.create(state(launches=(_FIRST,)))
    target = tmp_path / "state.json"
    target.write_bytes(text.encode("utf-8", errors="surrogateescape"))
    before = target.read_bytes()
    with JobStore(tmp_path) as store, pytest.raises(GauntletError):
        store.load()
    assert target.read_bytes() == before


# Returning success on a real temporary-file creation failure breaks this.
def test_failed_state_publication(tmp_path: Path) -> None:
    """Retain committed state when its directory cannot accept writes."""
    old = state()
    new = state(revision=1, launches=(_FIRST,))
    with JobStore(tmp_path) as store:
        store.create(old)
        tmp_path.chmod(0o500)
        try:
            with pytest.raises(StorageError):
                store.save(new, expected_revision=0)
        finally:
            tmp_path.chmod(0o700)
    with JobStore(tmp_path) as store:
        assert store.load() == old


# Trace-first replacement or deleting another invocation's temp breaks this.
def test_failed_trace_publication_and_owned_cleanup(tmp_path: Path) -> None:
    """Commit state first and remove only owned temps after trace failure."""
    orphan = tmp_path / "orphan.tmp"
    orphan.write_text("another invocation", encoding="utf-8")
    new = state(revision=1, launches=(_FIRST,))
    with JobStore(tmp_path) as store:
        store.create(state())
        trace = tmp_path / "trace.jsonl"
        trace.unlink()
        trace.mkdir()
        before = sorted(path.name for path in tmp_path.iterdir())
        with pytest.raises(StorageError):
            store.save(new, expected_revision=0)
    names = sorted(path.name for path in tmp_path.iterdir())
    trace.rmdir()
    with JobStore(tmp_path) as store:
        assert (store.load(), names, orphan.read_text(encoding="utf-8")) == (
            new,
            before,
            "another invocation",
        )
