# Copyright 2026 oh shit, gorillas!
"""BUILD decisions from approved M1 Order 30 and its persisted phase contract."""

from dataclasses import replace

import pytest

from gauntlet.core import decide, records
from gauntlet.core.design import Step
from tests.support.answers import candidate, config, design, missing, state

_BUILD = records.Stage.BUILD
_PARALLEL_STEPS = 2
_ORDER = (
    Step("s1", ("pkg/a.py",), "core-builder"),
    Step("s2", ("pkg/a.py",), "seam-builder"),
    Step("s3", ("pkg/b.py",), "core-builder"),
)
_PLAN = records.Plan(tuple(records.PlanStep(step, ("S1",), ()) for step in _ORDER))
_ARTIFACTS: tuple[records.Artifact, ...] = (
    records.Artifact("design", 1, records.RoleAnswer(design(order=_ORDER))),
    records.Artifact("plan", 1, records.RoleAnswer(_PLAN)),
    records.Artifact(
        "spec",
        1,
        records.RoleAnswer(
            records.Spec(
                (
                    records.SpecLine(
                        "S1", "one behavior", "one value", records.TestStart.RED
                    ),
                ),
                (),
            )
        ),
    ),
    records.Artifact(
        "tests",
        1,
        records.RoleAnswer(
            records.TestAnswer(
                (records.TestBinding("S1", ("tests/test_a.py::test_a",)),), ()
            )
        ),
    ),
)


def _saved() -> records.State:
    """Supply independently recorded branch bases and approved build inputs."""
    return state(
        stage=_BUILD,
        artifacts=_ARTIFACTS,
        steps=tuple(
            records.StepRun(step.name, 0, "locked-base", None, "pending")
            for step in _ORDER
        ),
        config=config(
            tests=(
                records.TestCommand("py", "pytest {ids}"),
                records.TestCommand("web", "node --test {ids}"),
            )
        ),
    )


def _started(saved: records.State, pending: records.Pending) -> records.State:
    """Install the executor's literal checkpoint for a requested operation."""
    effect = pending.effect
    trace = records.TraceRow(
        f"{effect.id}.launch.{pending.dispatch}",
        effect.role or "harness",
        "model",
        "medium",
        None,
        None,
        "running",
    )
    point = records.RecoveryPoint(
        pending.dispatch,
        f"workspace/{effect.id}",
        records.GitIntent("repo", "job", "locked-base", "step-commit")
        if effect.operation == "commit-step"
        else None,
    )
    active = replace(
        pending,
        status="started",
        recovery=point,
        launch_id=trace.id if effect.role is not None else None,
    )
    return replace(
        saved,
        pending=tuple(active if p == pending else p for p in saved.pending),
        launches=(*saved.launches, trace)
        if effect.role is not None
        else saved.launches,
    )


def _result(action: records.Action, payload: records.BuildAnswer) -> records.Action:
    """Return the named step's build answer, preserving other pending steps."""
    assert any(
        p.effect.step == payload.step and p.effect.operation == "build"
        for p in action.state.pending
    )
    pending = next(
        p
        for p in action.state.pending
        if p.effect.step == payload.step and p.effect.operation == "build"
    )
    saved = _started(action.state, pending)
    trace = next(
        t
        for t in saved.launches
        if t.id == f"{pending.effect.id}.launch.{pending.dispatch}"
    )
    return decide.decide(
        saved,
        records.Answered(
            pending.effect.id,
            pending.dispatch,
            pending.effect.role or "core-builder",
            records.RoleAnswer(payload),
            replace(trace, outcome="complete"),
        ),
    )


def _checks(action: records.Action) -> records.Pending:
    """Require a real requested check batch for the completed build step."""
    pending = next(
        p
        for p in action.state.pending
        if p.effect.operation == "checks" and p.effect.step == "s1"
    )
    assert isinstance(pending.effect.input, records.CheckSet)
    assert pending.effect.input.checks
    return pending


def _rows(pending: records.Pending) -> tuple[records.CheckRow, ...]:
    """Literal successful harness replies use requested opaque check identities."""
    request = pending.effect.input
    assert isinstance(request, records.CheckSet)
    return tuple(
        records.CheckRow(
            f"{pending.effect.id}.check.{pending.dispatch}.{index}",
            _BUILD,
            0,
            check.id,
            records.Verdict.PASS,
            "executed and passed",
        )
        for index, check in enumerate(request.checks)
    )


# Serializing disjoint work or ignoring earlier overlap violates startable selection.
def test_build_selects_all_disjoint_steps_with_independent_pending_identity() -> None:
    """Start s1 and s3 with their exact roles, inputs, bases and durable ids."""
    action = decide.decide(_saved(), records.Tick())
    builds = tuple(e for e in action.effects if e.operation == "build")
    assert tuple(e.step for e in builds) == ("s1", "s3")
    assert tuple(e.role for e in builds) == ("core-builder", "core-builder")
    assert len({e.id for e in builds}) == _PARALLEL_STEPS
    assert all(e.inputs == _ARTIFACTS for e in builds)
    assert all(
        any(p.effect == e and p.status == "ready" for p in action.state.pending)
        for e in builds
    )
    assert all(run.base_commit == "locked-base" for run in action.state.steps)
    again = decide.decide(action.state, records.Tick())
    assert {e.id for e in again.effects} == {e.id for e in builds}


# Ignoring held paths, done or running statuses schedules unauthorized work.
@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("held", ("s3",)),
        ("done", ("s2", "s3")),
        ("running", ("s3",)),
        ("empty", ("s1",)),
    ],
)
def test_build_delegates_schedule_constraints(
    mode: str, expected: tuple[str, ...]
) -> None:
    """Honor held files, running files, completion and unknown empty file sets."""
    saved = _saved()
    if mode == "held":
        saved = replace(saved, held=("pkg/a.py",))
    elif mode in {"done", "running"}:
        status = "complete" if mode == "done" else "running"
        saved = replace(
            saved, steps=(replace(saved.steps[0], status=status), *saved.steps[1:])
        )
    else:
        plan = records.Plan(
            (
                replace(_PLAN.steps[0], step=replace(_ORDER[0], paths=())),
                *_PLAN.steps[1:],
            )
        )
        saved = replace(
            saved,
            artifacts=(
                *_ARTIFACTS[:1],
                records.Artifact("plan", 2, records.RoleAnswer(plan)),
                *_ARTIFACTS[2:],
            ),
        )
    action = decide.decide(saved, records.Tick())
    assert tuple(e.step for e in action.effects if e.operation == "build") == expected


# Trusting implementer COMPLETE skips the harness's configured tests and gate.
def test_complete_build_requests_tests_and_gate_before_commit() -> None:
    """Persist the answer while explicitly requiring every configured command."""
    payload = records.BuildAnswer("s1", records.BuildStatus.COMPLETE, "implemented")
    action = _result(decide.decide(_saved(), records.Tick()), payload)
    pending = _checks(action)
    request = pending.effect.input
    assert isinstance(request, records.CheckSet)
    assert {command.run for command in action.state.config.tests} | {
        action.state.config.gates
    } == {
        "pytest {ids}",
        "node --test {ids}",
        "make check",
    }
    assert len(request.checks) == len(action.state.config.tests) + 1
    assert len({check.id for check in request.checks}) == len(request.checks)
    assert all(
        command in repr(pending.effect)
        for command in ("pytest {ids}", "node --test {ids}", "make check")
    )
    assert all(c.verdict == records.Verdict.COULD_NOT_JUDGE for c in request.checks)
    assert any(a.answer.payload == payload for a in action.state.artifacts)
    assert next(s for s in action.state.steps if s.name == "s1").status != "complete"
    assert not any(e.operation == "commit-step" for e in action.effects)
    assert any(p.effect.step == "s3" for p in action.state.pending)


# Missing, duplicated or nonpassing rows must never authorize a step commit.
@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "unexpected", "fail", "unable", "pass"]
)
def test_commit_requires_exact_passing_test_and_gate_receipts(fault: str) -> None:
    """Only complete explicit harness PASS rows prepare a separate git phase."""
    action = _result(
        decide.decide(_saved(), records.Tick()),
        records.BuildAnswer("s1", records.BuildStatus.COMPLETE, "implemented"),
    )
    pending = _checks(action)
    rows = _rows(pending)
    if fault == "missing":
        rows = rows[:-1]
    elif fault == "duplicate":
        rows = (*rows, replace(rows[0], id="duplicate-run"))
    elif fault == "unexpected":
        rows = (*rows, replace(rows[0], id="unexpected-run", check="unrequested"))
    elif fault in {"fail", "unable"}:
        verdict = (
            records.Verdict.FAIL if fault == "fail" else records.Verdict.COULD_NOT_JUDGE
        )
        rows = (*rows[:-1], replace(rows[-1], verdict=verdict))
    checked = decide.decide(
        _started(action.state, pending),
        records.Checked(pending.effect.id, pending.dispatch, rows),
    )
    commits = tuple(e for e in checked.effects if e.operation == "commit-step")
    assert bool(commits) == (fault == "pass")
    assert next(s for s in checked.state.steps if s.name == "s1").status != "complete"
    if fault == "pass":
        assert all(row in checked.state.checks for row in rows)
        commit = next(
            p for p in checked.state.pending if p.effect.operation == "commit-step"
        )
        completed = decide.decide(
            _started(checked.state, commit),
            records.Completed(commit.effect.id, commit.dispatch, "step-commit"),
        )
        assert (
            next(s for s in completed.state.steps if s.name == "s1").status
            == "complete"
        )
        assert any(r.effect == commit.effect.id for r in completed.state.receipts)
        assert any(p.effect.step == "s3" for p in completed.state.pending)


# Retrying on top of a partial workspace or changing its base loses accepted work.
def test_partial_retries_fresh_effect_from_saved_base_and_diff() -> None:
    """A new attempt preserves the recorded base and accepted partial checkpoint."""
    saved = _saved()
    saved = replace(
        saved,
        steps=(
            replace(saved.steps[0], partial_diff="accepted diff"),
            *saved.steps[1:],
        ),
    )
    running = decide.decide(saved, records.Tick())
    assert any(p.effect.step == "s1" for p in running.state.pending)
    old = next(p for p in running.state.pending if p.effect.step == "s1")
    partial = _result(
        running,
        records.BuildAnswer("s1", records.BuildStatus.PARTIAL, "remaining work"),
    )
    retried = decide.decide(partial.state, records.Tick())
    fresh = next(p for p in retried.state.pending if p.effect.step == "s1")
    run = next(s for s in retried.state.steps if s.name == "s1")
    before = next(s for s in running.state.steps if s.name == "s1")
    assert fresh.effect.id != old.effect.id
    assert fresh.status == "ready"
    assert fresh.launch_id is None
    assert run.attempt == before.attempt + 1
    assert run.base_commit == "locked-base"
    assert run.partial_diff == "accepted diff"
    assert not any(e.operation == "commit-step" for e in partial.effects)


# M1 cannot turn BLOCKED into a successful build or silently spawn an M8 job.
@pytest.mark.parametrize("with_missing", [False, True])
def test_blocked_stops_and_retains_answer_without_spawn(*, with_missing: bool) -> None:
    """Keep the implementer's reason and optional valid CoreMissing intact."""
    report = (
        missing(candidate=candidate(why="required to implement correctly"))
        if with_missing
        else None
    )
    payload = records.BuildAnswer(
        "s1", records.BuildStatus.BLOCKED, "needs core", report
    )
    action = _result(decide.decide(_saved(), records.Tick()), payload)
    assert action.state.status == "stopped"
    assert next(s for s in action.state.steps if s.name == "s1").status == "blocked"
    assert any(a.answer.payload == payload for a in action.state.artifacts)
    assert all(e.operation == "stop" for e in action.effects)


# Skipping core_missing_problems accepts a why on offers or no why on blockers.
@pytest.mark.parametrize(
    ("status", "why", "valid"),
    [
        (records.BuildStatus.COMPLETE, None, True),
        (records.BuildStatus.PARTIAL, None, True),
        (records.BuildStatus.COMPLETE, "must have", False),
        (records.BuildStatus.PARTIAL, "must have", False),
        (records.BuildStatus.BLOCKED, None, False),
    ],
)
def test_core_missing_validation_precedes_usual_build_course(
    status: records.BuildStatus, why: str | None, *, valid: bool
) -> None:
    """Validate and retain the core report without starting a structure job."""
    payload = records.BuildAnswer(
        "s1", status, "result", missing(candidate=candidate(why=why))
    )
    action = _result(decide.decide(_saved(), records.Tick()), payload)
    assert any(a.answer.payload == payload for a in action.state.artifacts)
    assert not any(e.stage == records.Stage.DESIGN for e in action.effects)
    if valid and status == records.BuildStatus.COMPLETE:
        assert any(e.operation == "checks" for e in action.effects)
    elif valid:
        retried = decide.decide(action.state, records.Tick())
        assert any(
            p.effect.step == "s1" and p.effect.operation == "build"
            for p in retried.state.pending
        )
    else:
        assert records.Round(records.Loop.BUILD, 1) in action.state.rounds
        assert not any(e.operation in {"checks", "commit-step"} for e in action.effects)
