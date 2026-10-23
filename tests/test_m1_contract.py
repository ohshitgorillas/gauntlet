# Copyright 2026 oh shit, gorillas!
"""A literal mixed RED/GREEN STRUCTURE job through the injected core protocol."""

from dataclasses import replace

from gauntlet.core import decide, records
from gauntlet.core.verdicts import Anchor
from tests.support.answers import candidate, config, design, survey
from tests.test_core_decide_review import (
    BAILIFF as _BAILIFF,
)
from tests.test_core_decide_review import (
    PLAN as _PLAN,
)
from tests.test_core_decide_review import (
    SNAPSHOT as _SNAPSHOT,
)
from tests.test_core_decide_review import (
    SPEC as _SPEC,
)
from tests.test_core_decide_review import (
    TESTS as _TESTS,
)
from tests.test_core_decide_review import (
    checked as _checked,
)

_S = records.Stage
_MAX_EVENTS = 60
_JUROR = records.RedJudgment(
    (
        records.RedLine(
            "S1", records.RedVerdict.RED, ("tests/test_new.py::test_added",)
        ),
        records.RedLine(
            "S2", records.RedVerdict.GREEN, ("tests/test_old.py::test_kept",)
        ),
    )
)


def _role_payload(effect: records.Effect) -> records.Payload:
    """Choose literal role replies from the approved walk, never compute verdicts."""
    if effect.role == "architect":
        return design()
    if effect.role == "planner":
        return _PLAN if effect.stage == _S.PLAN else _SPEC
    if effect.role == "prosecutor":
        return records.CheckSet(
            (
                records.Check(
                    "citation",
                    records.Verdict.PASS,
                    "citation verified",
                    (Anchor("pkg/home.py", 1),),
                ),
            ),
            "continue",
        )
    if effect.role == "arbiter":
        return records.SpecJudgment(
            (
                records.SpecRuling("S1", records.Verdict.PASS, "accepted"),
                records.SpecRuling("S2", records.Verdict.PASS, "accepted"),
            )
        )
    if effect.role == "scrivener":
        return _TESTS
    if effect.role == "juror":
        return _JUROR
    if effect.role in {"reviewer", "structure-reviewer"}:
        return records.ReviewAnswer(())
    if effect.role == "surveyor":
        return survey()
    if effect.role == "grouper":
        return records.CausesAnswer(())
    if effect.role == "bailiff":
        return _BAILIFF
    assert effect.operation == "build"
    return records.BuildAnswer("s1", records.BuildStatus.COMPLETE, "implemented")


def _execute(action: records.Action, pending: records.Pending) -> records.Action:
    """Supply one explicit executor reply with its matching checkpoint and trace."""
    effect = pending.effect
    if effect.operation == "owner":
        return decide.decide(
            action.state,
            records.Approved(
                effect.id,
                pending.dispatch,
                (),
                design() if effect.stage == _S.DESIGN else None,
            ),
        )
    if effect.operation == "checks":
        return _checked(action)
    git = (
        records.GitIntent("repo", "job", "before", "prepared-oid")
        if effect.operation in {"commit-tests", "commit-step", "land"}
        else None
    )
    trace = records.TraceRow(
        f"{effect.id}.launch.{pending.dispatch}",
        effect.role or "harness",
        "model",
        "medium",
        None,
        None,
        "running",
    )
    started = replace(
        pending,
        status="started",
        launch_id=trace.id if effect.role else None,
        recovery=records.RecoveryPoint(pending.dispatch, "workspace", git),
    )
    saved = replace(
        action.state,
        pending=tuple(started if p == pending else p for p in action.state.pending),
        launches=(*action.state.launches, trace)
        if effect.role
        else action.state.launches,
    )
    if effect.operation == "baseline":
        return decide.decide(
            saved, records.Baselined(effect.id, pending.dispatch, (_SNAPSHOT,))
        )
    if effect.operation in {"launch", "build"}:
        event: records.Answer = records.Answered(
            effect.id,
            pending.dispatch,
            effect.role or "core-builder",
            records.RoleAnswer(_role_payload(effect)),
            replace(trace, outcome="complete"),
        )
    else:
        event = records.Completed(
            effect.id, pending.dispatch, "prepared-oid" if git else None
        )
    return decide.decide(saved, event)


# Skipping final rows or source preservation prevents this literal job landing.
def test_mixed_structure_walk_preserves_tests_and_runs_final_gates() -> None:
    """Run all stages with literal external replies and explicit final PASS rows."""
    opened = decide.initial(
        "mixed-walk",
        records.Shape.STRUCTURE,
        config(),
        candidate=candidate(keeps=("keep behavior",)),
    )
    action = decide.decide(opened, records.Tick())
    seen: list[records.Effect] = []
    sources: list[records.TestSnapshot] = []
    stages = [action.state.stage]
    for _ in range(_MAX_EVENTS):
        if action.state.status == "landed":
            break
        assert action.state.status != "stopped", (
            action.state.stage,
            action.state.checks,
        )
        if not action.state.pending:
            action = decide.decide(action.state, records.Tick())
        assert action.state.pending, (action.state.stage, action.state.artifacts)
        pending = action.state.pending[0]
        assert pending.effect.operation != "stop"
        if pending.effect.stage == _S.BAILIFF and pending.effect.role == "bailiff":
            ready = action.state
            variants: list[records.Payload | None] = []
            for changed in (
                replace(
                    ready,
                    config=config(
                        tests=(records.TestCommand("tests", "other-tests {ids}"),)
                    ),
                ),
                replace(
                    ready,
                    baselines=(
                        replace(
                            _SNAPSHOT, source="def test_kept():\n    assert preserved\n"
                        ),
                    ),
                ),
                replace(ready, config=config(gates="project-final-gates")),
            ):
                other = _execute(replace(action, state=changed), pending)
                requests = tuple(
                    e.input for e in other.effects if e.operation == "checks"
                )
                variants.append(requests[0] if requests else None)
            actual = _execute(action, pending)
            requests = tuple(e.input for e in actual.effects if e.operation == "checks")
            assert requests
            assert all(item is not None and item != requests[0] for item in variants)
        seen.append(pending.effect)
        action = _execute(action, pending)
        if action.state.baselines:
            assert action.state.baselines == (_SNAPSHOT,)
            sources.extend(action.state.baselines)
        if action.state.stage != stages[-1]:
            stages.append(action.state.stage)
    assert action.state.status == "landed"
    assert stages == [
        _S.DESIGN,
        _S.PLAN,
        _S.SPEC,
        _S.STUBS,
        _S.TESTS,
        _S.RED_RUN,
        _S.LOCK,
        _S.BUILD,
        _S.REVIEW,
        _S.BAILIFF,
        _S.LAND,
    ]
    assert sources
    assert {e.role for e in seen} >= {
        "reviewer",
        "structure-reviewer",
        "surveyor",
        "bailiff",
    }
    baseline = next(
        index for index, effect in enumerate(seen) if effect.operation == "baseline"
    )
    first_edit = next(
        index for index, effect in enumerate(seen) if effect.stage == _S.STUBS
    )
    assert baseline < first_edit
    final = tuple(e for e in seen if e.stage == _S.LAND and e.operation == "checks")
    assert final
    requested = tuple(
        check
        for e in final
        if isinstance(e.input, records.CheckSet)
        for check in e.input.checks
    )
    assert requested
    assert all(
        any(
            row.stage == _S.LAND
            and row.check == check.id
            and row.verdict == records.Verdict.PASS
            for row in action.state.checks
        )
        for check in requested
    )
    assert any(a.answer.payload == _SPEC for a in action.state.artifacts)
    assert action.state.baselines == (_SNAPSHOT,)
