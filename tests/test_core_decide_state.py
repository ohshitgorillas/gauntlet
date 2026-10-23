# Copyright 2026 oh shit, gorillas!
"""State and recovery contracts from M1 Order 26, before stage dispatch.

spec: docs/superpowers/specs/m1-core-records-design.md
"""

from dataclasses import replace

import pytest

from gauntlet.core import decide, records
from gauntlet.core.errors import StateError
from tests.support.answers import candidate, config, design, state

_STAGE = records.Stage
_SHAPE = records.Shape
_EFFECT = records.Effect("e1", _STAGE.DESIGN, "launch", "architect", None, None, ())
_POINT = records.RecoveryPoint(3, "checkpoint/e1", None)
_TRACE = records.TraceRow(
    "e1.launch.3", "architect", "model", "medium", None, None, "running"
)
_PENDING = records.Pending(_EFFECT, "started", _TRACE.id, 3, _POINT)
_OLD = "tests/test_old.py::test_kept"
_SPEC = records.Spec(
    (records.SpecLine("S1", "keep", "same source", records.TestStart.GREEN, (_OLD,)),),
    (),
)
_ARTIFACT = records.Artifact("spec", 2, records.RoleAnswer(_SPEC))
_SNAPSHOT = records.TestSnapshot(
    _OLD, "@decorator\ndef test_kept():\n    assert True\n"
)
_NEXT_DISPATCH = 4


# Changing the shape routing or omitting stage metadata breaks this table.
def test_stage_table_and_initial_state() -> None:
    """Keep shape entry points, skips, approvals and cap homes explicit."""
    assert decide.FIRST == {
        _SHAPE.JOB: _STAGE.BRIEF,
        _SHAPE.TEST_AUDIT: _STAGE.SPEC,
        _SHAPE.STRUCTURE: _STAGE.DESIGN,
    }
    expected_skips: dict[records.Shape, frozenset[records.Stage]] = {
        _SHAPE.JOB: frozenset(),
        _SHAPE.TEST_AUDIT: frozenset({_STAGE.STUBS, _STAGE.BUILD, _STAGE.REVIEW}),
        _SHAPE.STRUCTURE: frozenset(),
    }
    assert expected_skips == decide.SKIPPED
    assert tuple(row.stage for row in decide.STAGES) == tuple(_STAGE)
    assert tuple(row.successor for row in decide.STAGES) == (*tuple(_STAGE)[1:], None)
    assert {row.stage for row in decide.STAGES if row.approval} == {
        _STAGE.DESIGN,
        _STAGE.PLAN,
        _STAGE.SPEC,
        _STAGE.LAND,
    }
    assert {row.stage: row.loop for row in decide.STAGES if row.loop is not None} == {
        _STAGE.DESIGN: records.Loop.DESIGN,
        _STAGE.PLAN: records.Loop.PLAN,
        _STAGE.SPEC: records.Loop.SPEC,
        _STAGE.RED_RUN: records.Loop.JUROR,
        _STAGE.BUILD: records.Loop.BUILD,
        _STAGE.REVIEW: records.Loop.REVIEW,
    }
    supplied = candidate(keeps=("one behavior",))
    opened = decide.initial(
        "job/unchanged", _SHAPE.STRUCTURE, config(), candidate=supplied
    )
    assert opened == state(job="job/unchanged", candidate=supplied)
    assert decide.state_problems(opened) == ()


# Reallocating effects on Tick loses their durable identity and input revisions.
def test_tick_reproduces_ready_work_without_allocating_ids() -> None:
    """Replay the same immutable effect even when the state revision changes."""
    effect = replace(_EFFECT, input=_SPEC, inputs=(_ARTIFACT,))
    saved = state(
        pending=(records.Pending(effect, "ready", None, 3),), artifacts=(_ARTIFACT,)
    )
    first = decide.decide(saved, records.Tick())
    again = decide.decide(saved, records.Tick())
    revised = decide.decide(replace(saved, revision=41), records.Tick())
    assert first == again
    assert first.effects == revised.effects == (effect,)
    assert first.state.pending == saved.pending
    assert first.state.launches == ()
    assert first.state.rounds == ()


# Allocating stop identities from a counter or clock makes the same state differ.
def test_computed_effect_ids_are_deterministic_and_job_specific() -> None:
    """An unavailable row still has reproducible, job-local effect identities."""
    saved = state(shape=_SHAPE.JOB, stage=_STAGE.BRIEF)
    first = decide.decide(saved, records.Tick())
    repeated = decide.decide(saved, records.Tick())
    other = decide.decide(replace(saved, job="j2"), records.Tick())
    assert first.effects
    assert first.effects == repeated.effects
    assert {effect.id for effect in first.effects}.isdisjoint(
        effect.id for effect in other.effects
    )


# Treating ordinary waits as dispatchable work starts unauthorized stages.
@pytest.mark.parametrize("status", ["waiting", "stopped", "landed"])
def test_idle_terminal_or_owner_wait_stays_idle(status: str) -> None:
    """Tick leaves persisted waits and completed jobs alone."""
    saved = state(status=status)
    action = decide.decide(saved, records.Tick())
    assert action.state == saved
    assert action.effects == ()


# Implementing an unavailable row as success fabricates omitted work.
@pytest.mark.parametrize(
    ("shape", "stage"),
    [
        (_SHAPE.JOB, _STAGE.BRIEF),
        (_SHAPE.JOB, _STAGE.DISCOVERY),
        (_SHAPE.JOB, _STAGE.OUTLINE),
        (_SHAPE.TEST_AUDIT, _STAGE.SPEC),
    ],
)
def test_unavailable_rows_stop_explicitly(
    shape: records.Shape, stage: records.Stage
) -> None:
    """Retain the reached row and expose unavailable work without check passes."""
    action = decide.decide(state(shape=shape, stage=stage), records.Tick())
    assert action.state.status == "stopped"
    assert action.state.stage == stage
    assert action.state.checks == ()
    assert any(effect.operation == "stop" for effect in action.effects)


# Dispatching ready siblings before recovering started work violates rollback order.
@pytest.mark.parametrize("status", ["started", "recovering"])
def test_recovery_precedes_ready_dispatch(status: str) -> None:
    """Recover interrupted work before exposing other ready work."""
    interrupted = replace(_PENDING, status=status)
    sibling = records.Pending(replace(_EFFECT, id="e2"), "ready", None)
    saved = state(pending=(sibling, interrupted), launches=(_TRACE,))
    action = decide.decide(saved, records.Tick())
    assert action.effects == (_EFFECT,)
    assert action.state.status != "waiting"
    assert action.state.rounds == saved.rounds
    assert action.state.pending[0] == sibling
    assert action.state.pending[1].status == "recovering"


# Charging a retry round or erasing saved work changes the resumed logical action.
def test_restored_preserves_inputs_rounds_partials_and_other_pending_work() -> None:
    """Only recovery dispatch changes; historical work and metrics survive."""
    step = records.StepRun("s1", 4, "base-oid", "saved diff", "partial")
    sibling = records.Pending(replace(_EFFECT, id="e2"), "ready", None)
    saved = state(
        pending=(_PENDING, sibling),
        launches=(_TRACE,),
        artifacts=(_ARTIFACT,),
        rounds=(records.Round(records.Loop.REVIEW, 1),),
        steps=(step,),
        owners=(("choice", "resolved"),),
        baselines=(_SNAPSHOT,),
    )
    event = records.Recovered("e1", 3, records.Restored())
    action = decide.decide(saved, event)
    restored = action.state
    assert restored.artifacts == saved.artifacts
    assert restored.rounds == saved.rounds
    assert restored.steps == saved.steps
    assert restored.owners == saved.owners
    assert restored.baselines == saved.baselines
    assert restored.pending[1] == sibling
    replay = restored.pending[0]
    assert replay.effect == _EFFECT
    assert replay.status == "ready"
    assert replay.dispatch == _NEXT_DISPATCH
    assert replay.launch_id is None
    assert replay.recovery is None
    assert restored.launches == (replace(_TRACE, outcome="interrupted"),)
    assert records.Receipt("e1", event) in restored.receipts
    assert decide.decide(restored, event).state == restored
    assert decide.decide(restored, event).effects == ()


# Accepting recovery for a different identity can restore another workspace.
@pytest.mark.parametrize(("effect", "dispatch"), [("other", 3), ("e1", 2), ("e1", 4)])
def test_recovery_requires_matching_effect_and_dispatch(
    effect: str, dispatch: int
) -> None:
    """Reject mismatched recovery without accepting a receipt."""
    saved = state(pending=(_PENDING,), launches=(_TRACE,))
    with pytest.raises(StateError):
        decide.decide(saved, records.Recovered(effect, dispatch, records.Restored()))


# Conflating an ordinary completion with recovery skips workspace reconciliation.
def test_started_work_accepts_only_recovery_after_tick() -> None:
    """A recovering effect rejects a late execution answer."""
    saved = state(pending=(replace(_PENDING, status="recovering"),), launches=(_TRACE,))
    with pytest.raises(StateError):
        decide.decide(
            saved,
            records.Answered(
                "e1",
                3,
                "architect",
                records.RoleAnswer(design()),
                replace(_TRACE, outcome="complete"),
            ),
        )


# A matching effect id alone cannot prove a git intent was applied.
@pytest.mark.parametrize("operation", ["commit-tests", "commit-step", "land"])
def test_git_reconciliation_matches_ordinary_completion(operation: str) -> None:
    """The exact prepared oid produces the ordinary durable completion receipt."""
    stage = {
        "commit-tests": _STAGE.LOCK,
        "commit-step": _STAGE.BUILD,
        "land": _STAGE.LAND,
    }[operation]
    effect = records.Effect(
        "git-e1",
        stage,
        operation,
        None,
        "s1" if operation == "commit-step" else None,
        None,
        (),
    )
    intent = records.GitIntent("repo", "refs/heads/job", "before", "prepared-after")
    point = records.RecoveryPoint(3, "checkpoint/git-e1", intent)
    pending = records.Pending(effect, "started", None, 3, point)
    saved = state(stage=stage, pending=(pending,))
    recovering = replace(saved, pending=(replace(pending, status="recovering"),))
    completion = records.Completed(effect.id, 3, "prepared-after")
    ordinary = decide.decide(saved, completion)
    recovery = decide.decide(
        recovering,
        records.Recovered(effect.id, 3, records.Reconciled("prepared-after")),
    )
    assert recovery.state.stage == ordinary.state.stage
    assert recovery.state.status == ordinary.state.status
    assert recovery.state.steps == ordinary.state.steps
    assert recovery.effects == ordinary.effects
    assert records.Receipt(effect.id, completion) in recovery.state.receipts
    assert recovery.state.rounds == saved.rounds
    assert decide.decide(recovery.state, completion).state == recovery.state
    with pytest.raises(StateError):
        decide.decide(
            recovering,
            records.Recovered(effect.id, 3, records.Reconciled("another-oid")),
        )


# Reconciliation is not valid evidence that an agent or check operation finished.
def test_non_git_work_cannot_be_reconciled_as_a_commit() -> None:
    """Reject a git reconciliation attached to ordinary agent work."""
    with pytest.raises(StateError):
        decide.decide(
            state(pending=(_PENDING,), launches=(_TRACE,)),
            records.Recovered("e1", 3, records.Reconciled("oid")),
        )


# Omitting interruption evidence hides an unfinished check from durable state.
def test_interrupted_check_retains_inability_and_requires_current_dispatch() -> None:
    """Restore marks the old run unable to judge and rejects its late results."""
    effect = records.Effect("check-e1", _STAGE.RED_RUN, "checks", None, None, None, ())
    pending = records.Pending(effect, "recovering", None, 3, _POINT)
    prior = records.CheckRow(
        "prior.2", _STAGE.RED_RUN, 0, "tests", records.Verdict.PASS, "earlier evidence"
    )
    saved = state(stage=_STAGE.RED_RUN, pending=(pending,), checks=(prior,))
    restored = decide.decide(
        saved, records.Recovered(effect.id, 3, records.Restored())
    ).state
    assert prior in restored.checks
    interruptions = tuple(row for row in restored.checks if row.id != prior.id)
    assert interruptions
    assert all(row.verdict == records.Verdict.COULD_NOT_JUDGE for row in interruptions)
    assert all("interrupt" in row.evidence.lower() for row in interruptions)
    assert all("3" in row.id for row in interruptions)
    assert restored.rounds == saved.rounds
    current = restored.pending[0]
    assert current.dispatch == _NEXT_DISPATCH
    started = replace(
        restored,
        pending=(
            replace(
                current,
                status="started",
                recovery=replace(_POINT, dispatch=_NEXT_DISPATCH),
            ),
        ),
    )
    assert decide.state_problems(started) == ()
    late = records.CheckRow(
        "check-e1.check.3",
        _STAGE.RED_RUN,
        0,
        "tests",
        records.Verdict.PASS,
        "late result",
    )
    with pytest.raises(StateError):
        decide.decide(started, records.Checked(effect.id, 3, (late,)))


# Accepting a conflicting duplicate lets a late answer overwrite durable evidence.
def test_receipts_are_exact_duplicate_safe_and_conflicts_fail() -> None:
    """No pending effect is needed for exact replay, but its payload must match."""
    accepted = records.Baselined("baseline-e1", 3, (_SNAPSHOT,))
    saved = state(
        receipts=(records.Receipt("baseline-e1", accepted),), baselines=(_SNAPSHOT,)
    )
    replay = decide.decide(saved, accepted)
    assert replay.state == saved
    assert replay.effects == ()
    with pytest.raises(StateError):
        decide.decide(
            saved, replace(accepted, tests=(replace(_SNAPSHOT, source="different"),))
        )
    with pytest.raises(StateError):
        decide.decide(saved, replace(accepted, dispatch=2))


# Baseline acceptance must not infer source snapshots from approved test ids.
def test_baselined_records_exact_harness_sources_and_receipt() -> None:
    """Store approved preserved sources before later stage work can run."""
    effect = records.Effect(
        "baseline-e1", _STAGE.SPEC, "baseline", None, None, _SPEC, (_ARTIFACT,)
    )
    saved = state(
        stage=_STAGE.SPEC,
        artifacts=(_ARTIFACT,),
        pending=(records.Pending(effect, "started", None, 3, _POINT),),
    )
    event = records.Baselined(effect.id, 3, (_SNAPSHOT,))
    action = decide.decide(saved, event)
    assert action.state.baselines == (_SNAPSHOT,)
    assert action.state.artifacts == saved.artifacts
    assert records.Receipt(effect.id, event) in action.state.receipts
    assert all(p.effect.id != effect.id for p in action.state.pending)


# Missing, added, duplicated or blank snapshot data cannot certify preservation.
@pytest.mark.parametrize(
    "snapshots",
    [
        (),
        (_SNAPSHOT, _SNAPSHOT),
        (replace(_SNAPSHOT, test_id="other"),),
        (replace(_SNAPSHOT, source=" "),),
    ],
)
def test_baselined_requires_exact_approved_ids(
    snapshots: tuple[records.TestSnapshot, ...],
) -> None:
    """Reject invalid harness baseline evidence at its event boundary."""
    effect = records.Effect(
        "baseline-e1", _STAGE.SPEC, "baseline", None, None, _SPEC, (_ARTIFACT,)
    )
    saved = state(
        stage=_STAGE.SPEC,
        artifacts=(_ARTIFACT,),
        pending=(records.Pending(effect, "started", None, 3, _POINT),),
    )
    with pytest.raises(StateError):
        decide.decide(saved, records.Baselined(effect.id, 3, snapshots))


# A baseline event cannot create its own authorization or effect identity.
def test_baselined_requires_a_pending_baseline_operation() -> None:
    """Reject unsolicited baseline sources even with a matching launch id."""
    with pytest.raises(StateError):
        decide.decide(
            state(pending=(_PENDING,), launches=(_TRACE,)),
            records.Baselined("e1", 3, (_SNAPSHOT,)),
        )


# Wrong role, trace or dispatch associations cannot close another launch attempt.
@pytest.mark.parametrize(
    "change", ["effect", "dispatch", "role", "trace-id", "trace-role"]
)
def test_answered_association_is_exact(change: str) -> None:
    """Reject mismatched answer identities before stage-specific interpretation."""
    answer = records.Answered(
        "e1",
        3,
        "architect",
        records.RoleAnswer(design()),
        replace(_TRACE, outcome="complete"),
    )
    if change == "effect":
        answer = replace(answer, effect="other")
    elif change == "dispatch":
        answer = replace(answer, dispatch=2)
    elif change == "role":
        answer = replace(answer, role="planner")
    elif change == "trace-id":
        answer = replace(answer, trace=replace(answer.trace, id="other.launch.3"))
    else:
        answer = replace(answer, trace=replace(answer.trace, role="planner"))
    with pytest.raises(StateError):
        decide.decide(state(pending=(_PENDING,), launches=(_TRACE,)), answer)


# Discarding the completion trace loses reported metrics or fabricates unknown ones.
@pytest.mark.parametrize(
    ("tokens", "cost"), [(17, "0.0042"), (None, None), (17, None), (None, "0.0042")]
)
def test_answered_closes_matching_trace_with_reported_metrics(
    tokens: int | None, cost: str | None
) -> None:
    """Close this launch alone and preserve every supplied completion field."""
    prior = replace(_TRACE, id="prior.launch.2", outcome="interrupted")
    saved = state(pending=(_PENDING,), launches=(prior, _TRACE))
    reported = replace(
        _TRACE,
        model="reported-model",
        effort="high",
        tokens=tokens,
        cost=cost,
        outcome="complete",
    )
    event = records.Answered(
        "e1", 3, "architect", records.RoleAnswer(design()), reported
    )
    action = decide.decide(saved, event)
    assert action.state.launches == (prior, reported)
    assert all(p.effect.id != "e1" for p in action.state.pending)
    assert records.Receipt("e1", event) in action.state.receipts


# Permissive state validation lets contradictory checkpoints reach the executor.
@pytest.mark.parametrize(
    "fault",
    [
        "candidate",
        "duplicate-effect",
        "duplicate-trace",
        "ready-launch",
        "missing-point",
        "wrong-dispatch",
        "missing-workspace",
        "launch-role",
        "launch-step",
        "git-intent",
        "duplicate-check",
        "duplicate-receipt",
        "step-status",
    ],
)
def test_state_validation_rejects_contradictory_identity_and_checkpoints(
    fault: str,
) -> None:
    """Reject malformed persisted state before recovery or fresh dispatch."""
    saved = state(pending=(_PENDING,), launches=(_TRACE,))
    if fault == "candidate":
        saved = replace(saved, candidate=None)
    elif fault == "duplicate-effect":
        saved = replace(saved, pending=(_PENDING, _PENDING))
    elif fault == "duplicate-trace":
        saved = replace(saved, launches=(_TRACE, _TRACE))
    elif fault == "ready-launch":
        saved = replace(saved, pending=(replace(_PENDING, status="ready"),))
    elif fault == "missing-point":
        saved = replace(saved, pending=(replace(_PENDING, recovery=None),))
    elif fault == "wrong-dispatch":
        saved = replace(
            saved, pending=(replace(_PENDING, recovery=replace(_POINT, dispatch=2)),)
        )
    elif fault == "missing-workspace":
        saved = replace(
            saved,
            pending=(replace(_PENDING, recovery=replace(_POINT, workspace=None)),),
        )
    elif fault == "launch-role":
        saved = replace(
            saved, pending=(replace(_PENDING, effect=replace(_EFFECT, role=None)),)
        )
    elif fault == "launch-step":
        saved = replace(
            saved, pending=(replace(_PENDING, effect=replace(_EFFECT, step="s1")),)
        )
    elif fault == "git-intent":
        saved = replace(
            saved,
            stage=_STAGE.LOCK,
            pending=(
                replace(
                    _PENDING,
                    launch_id=None,
                    effect=replace(
                        _EFFECT, stage=_STAGE.LOCK, operation="commit-tests", role=None
                    ),
                ),
            ),
            launches=(),
        )
    elif fault == "duplicate-check":
        row = records.CheckRow(
            "run.3", _STAGE.DESIGN, 0, "one-check", records.Verdict.PASS, "evidence"
        )
        saved = replace(saved, checks=(row, row))
    elif fault == "duplicate-receipt":
        receipt = records.Receipt("old", records.Completed("old", 0, None))
        saved = replace(saved, receipts=(receipt, receipt))
    else:
        saved = replace(
            saved, steps=(records.StepRun("s1", 1, "base", "partial diff", "complete"),)
        )
    assert decide.state_problems(saved)
    with pytest.raises(StateError):
        decide.decide(saved, records.Tick())
