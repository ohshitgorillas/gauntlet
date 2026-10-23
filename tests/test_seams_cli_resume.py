# Copyright 2026 oh shit, gorillas!
"""Resume CLI entry point, id validation, output and status, Order 42."""

import json
import os
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

import pytest

from gauntlet.core import errors, records
from gauntlet.seams.cli import exit_code, render_action, render_error
from gauntlet.seams.job import JobStore
from tests.support.answers import design, state

_ROOT = Path(__file__).resolve().parents[1]
_INPUT = records.Artifact(
    "brief", 0, records.RoleAnswer(records.Brief("saved logical input"))
)
_EFFECT = records.Effect(
    "e1", records.Stage.DESIGN, "launch", "architect", None, None, (_INPUT,)
)
_ROUNDS = (records.Round(records.Loop.DESIGN, 0),)
_MAIN = """
import json, sys
from gauntlet.core import records
from gauntlet.seams.cli import main
from tests.support.answers import design
from tests.support.recovery import Replies
arguments = json.loads(sys.argv[1])
if sys.argv[2] == "none":
    sys.exit(main(arguments))
replies = Replies(
    (records.Answered('e1', 0, 'architect', records.RoleAnswer(design()),
        records.TraceRow('e1.launch.0', 'architect', 'model', 'medium',
            17, '0.003', 'complete')),)
    if sys.argv[2] == "design" else (),
    points=(records.RecoveryPoint(0, 'workspace/e1', None),),
)
code = main(arguments, execute=replies)
print(f"executor saw {len(replies.seen)}", flush=True)
sys.exit(code)
"""
_SCRIPT = """
import sys
from importlib.metadata import entry_points
(point,) = entry_points(group="console_scripts", name="gauntlet")
sys.argv = ["gauntlet", *sys.argv[1:]]
sys.exit(point.load()())
"""


def _seed(job: Path, saved: records.State | None = None) -> records.State:
    """Persist the literal ready job, or the supplied state, in a real job folder."""
    if saved is None:
        saved = state(
            artifacts=(_INPUT,),
            rounds=_ROUNDS,
            pending=(records.Pending(_EFFECT, "ready", None, 0, None),),
        )
    job.mkdir(parents=True, exist_ok=True)
    with JobStore(job) as store:
        store.create(saved)
    return saved


def _load(job: Path) -> records.State:
    with JobStore(job) as store:
        return store.load()


def _argv(*words: str) -> str:
    """Encode the CLI arguments as the JSON list the child script reads."""
    arguments: list[str] = list(words)
    return json.dumps(arguments)


def _run(
    cwd: Path, *argv: str, script: str = _MAIN
) -> subprocess.CompletedProcess[str]:
    """Run the CLI in a child whose process cwd is the repository root."""
    path = os.environ.get("PYTHONPATH")
    search = os.pathsep.join(filter(None, (str(_ROOT), path)))
    env = {**os.environ, "PYTHONPATH": search}
    return subprocess.run(
        [sys.executable, "-c", script, *argv],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


# Breaks when the entry point stops naming cli:main, main ignores sys.argv or
# the job is looked up anywhere but the cwd's .gauntlet/jobs/<id>.
def test_entry_point_resumes_job_under_cwd(tmp_path: Path) -> None:
    """Gauntlet resume <id> reaches the cwd's job and reports the missing executor."""
    job = tmp_path / ".gauntlet" / "jobs" / "j1"
    saved = _seed(job)
    points = entry_points(group="console_scripts", name="gauntlet")
    names = tuple(point.value for point in points)
    done = _run(tmp_path, "resume", "j1", script=_SCRIPT)
    assert (names, done.returncode, "CapabilityError" in done.stdout + done.stderr) == (
        ("gauntlet.seams.cli:main",),
        2,
        True,
    )
    assert tuple(pending.effect for pending in _load(job).pending) == tuple(
        pending.effect for pending in saved.pending
    )


# Breaks when main searches parent directories for an enclosing .gauntlet.
def test_job_is_not_discovered_above_cwd(tmp_path: Path) -> None:
    """A job above the cwd is not found, resumed or rewritten."""
    job = tmp_path / ".gauntlet" / "jobs" / "j1"
    _seed(job)
    before = (job / "state.json").read_bytes()
    below = tmp_path / "below"
    below.mkdir()
    done = _run(below, _argv("resume", "j1"), "design")
    assert (done.returncode, (job / "state.json").read_bytes()) == (2, before)


# Breaks when an id is joined onto .gauntlet/jobs without rejecting dot,
# dot-dot or a path separator: each target holds a resumable job.
@pytest.mark.parametrize("form", ["dot", "dot-dot", "nested", "absolute"])
def test_invalid_id_is_refused(tmp_path: Path, form: str) -> None:
    """An id that is not one job-folder component resumes nothing."""
    jobs = tmp_path / ".gauntlet" / "jobs"
    targets = {
        "dot": (".", jobs),
        "dot-dot": ("..", tmp_path / ".gauntlet"),
        "nested": ("a/b", jobs / "a" / "b"),
        "absolute": (str(tmp_path / "elsewhere"), tmp_path / "elsewhere"),
    }
    identity, target = targets[form]
    _seed(target)
    before = (target / "state.json").read_bytes()
    done = _run(tmp_path, _argv("resume", identity), "design")
    assert (done.returncode, (target / "state.json").read_bytes()) == (2, before)


# Breaks when render_error drops any field of the typed failure.
@pytest.mark.parametrize(
    ("error", "fields"),
    [
        (errors.UnownedPathError("pkg/unowned.py"), ("pkg/unowned.py",)),
        (
            errors.RecordError("data.pending[0].status", "unknown value"),
            ("data.pending[0].status", "unknown value"),
        ),
        (
            errors.ConfigError("caps.review", "not positive"),
            ("caps.review", "not positive"),
        ),
        (errors.StateError("e42", "stale dispatch"), ("e42", "stale dispatch")),
        (
            errors.StorageError("jobs/j1/state.json", "lock", 11),
            ("jobs/j1/state.json", "lock", "11"),
        ),
        (
            errors.RecoveryError(("e7", "e9"), "contradictory git evidence"),
            ("e7", "e9", "contradictory git evidence"),
        ),
        (errors.CapabilityError("launch"), ("launch",)),
    ],
)
def test_error_output_names_fields(
    error: errors.GauntletError, fields: tuple[str, ...]
) -> None:
    """The typed failure's output carries every one of its fields."""
    text = render_error(error)
    assert tuple(field for field in fields if field not in text) == ()


# Breaks when render_action omits the persisted stage or a pending operation.
@pytest.mark.parametrize(
    ("stage", "operation"),
    [(records.Stage.SPEC, "baseline"), (records.Stage.LAND, "land")],
)
def test_action_output_names_stage_and_pending(
    stage: records.Stage, operation: str
) -> None:
    """The action's output names its persisted stage and pending operation."""
    effect = records.Effect("e5", stage, operation, None, None, None, ())
    action = records.Action(
        state(stage=stage, pending=(records.Pending(effect, "ready", None),)),
        (effect,),
    )
    text = render_action(action)
    assert (stage.value in text, operation in text) == (True, True)


# Breaks when success is not 0.
def test_no_error_exits_zero() -> None:
    """Without a typed failure the status is 0."""
    assert exit_code(None) == 0


# Breaks when any typed failure maps to a status other than 2.
@pytest.mark.parametrize(
    "error",
    [
        errors.UnownedPathError("pkg/unowned.py"),
        errors.RecordError("data", "malformed"),
        errors.ConfigError("image", "missing"),
        errors.StateError("e1", "stale"),
        errors.StorageError("state.json", "lock", None),
        errors.RecoveryError(("e1",), "corrupt checkpoint"),
        errors.CapabilityError("launch"),
    ],
)
def test_typed_failure_exits_two(error: errors.GauntletError) -> None:
    """Every typed failure has status 2."""
    assert (exit_code(error),) == (2,)


# Breaks when bad syntax is accepted or exits with a status other than argparse's 2.
@pytest.mark.parametrize("arguments", [[], ["resume"], ["resume", "j1", "j2"]])
def test_bad_syntax_exits_two(tmp_path: Path, arguments: list[str]) -> None:
    """Missing or extra arguments follow argparse's status."""
    _seed(tmp_path / ".gauntlet" / "jobs" / "j1")
    assert (_run(tmp_path, json.dumps(arguments), "design").returncode,) == (2,)


# Breaks when a stopped job returns 0 or is dispatched.
def test_stopped_work_exits_two(tmp_path: Path) -> None:
    """Resuming stopped work dispatches nothing and returns 2."""
    job = tmp_path / ".gauntlet" / "jobs" / "j1"
    stopped = state(
        status="stopped",
        artifacts=(_INPUT,),
        rounds=_ROUNDS,
        pending=(records.Pending(_EFFECT, "ready", None, 0, None),),
    )
    _seed(job, stopped)
    before = (job / "state.json").read_bytes()
    done = _run(tmp_path, _argv("resume", "j1"), "empty")
    assert (done.returncode, "executor saw 0" in done.stdout) == (2, True)
    assert (job / "state.json").read_bytes() == before


# Breaks when main ignores the injected executor or does not dispatch through it.
def test_injected_executor_dispatches_pending(tmp_path: Path) -> None:
    """Main resumes through the supplied executor to the owner wait, status 0."""
    job = tmp_path / ".gauntlet" / "jobs" / "j1"
    _seed(job)
    done = _run(tmp_path, _argv("resume", "j1"), "design")
    saved = _load(job)
    assert (
        done.returncode,
        "executor saw 2" in done.stdout,
        "design" in done.stdout.replace("executor saw 2", ""),
        saved.status,
    ) == (0, True, True, "waiting")
    assert any(artifact.answer.payload == design() for artifact in saved.artifacts)


# Breaks when a missing executor completes, drops or silently skips pending work.
def test_missing_executor_preserves_pending(tmp_path: Path) -> None:
    """Without an executor, CapabilityError is reported and pending work stays."""
    job = tmp_path / ".gauntlet" / "jobs" / "j1"
    saved = _seed(job)
    done = _run(tmp_path, _argv("resume", "j1"), "none")
    after = _load(job)
    reported = "CapabilityError" in done.stdout + done.stderr
    assert (done.returncode, reported) == (2, True)
    assert (
        tuple(pending.effect for pending in after.pending),
        after.receipts,
        after.artifacts,
    ) == (tuple(pending.effect for pending in saved.pending), (), saved.artifacts)
    assert after == saved
