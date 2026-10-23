# Copyright 2026 oh shit, gorillas!
"""Review, bailiff and landing decisions from approved M1 Order 32."""

from dataclasses import replace

import pytest

from gauntlet.core import decide, records
from gauntlet.core.causes import Cause
from gauntlet.core.errors import UnownedPathError
from gauntlet.core.verdicts import Anchor, Category
from tests.support.answers import candidate, config, design, finding, state, survey

_S = records.Stage
_OLD = "tests/test_old.py::test_kept"
_NEW = "tests/test_new.py::test_added"
_SPEC = records.Spec(
    (
        records.SpecLine("S1", "new behavior", "new value", records.TestStart.RED),
        records.SpecLine(
            "S2", "keep behavior", "same value", records.TestStart.GREEN, (_OLD,)
        ),
    ),
    (records.Collateral("retired", "assert old_value", "altered"),),
)
_PLAN = records.Plan(
    tuple(records.PlanStep(step, ("S1", "S2"), ()) for step in design().order)
)
_TESTS = records.TestAnswer(
    (records.TestBinding("S1", (_NEW,)), records.TestBinding("S2", (_OLD,))), ()
)
_SNAPSHOT = records.TestSnapshot(_OLD, "@mark\ndef test_kept():\n    assert kept\n")
_ARTIFACTS = (
    records.Artifact("design", 1, records.RoleAnswer(design())),
    records.Artifact("plan", 1, records.RoleAnswer(_PLAN)),
    records.Artifact("spec", 1, records.RoleAnswer(_SPEC)),
    records.Artifact("tests", 1, records.RoleAnswer(_TESTS)),
)
_BAILIFF = records.BailiffAnswer(
    (records.Pin("S1", "pin", "pinned"), records.Pin("S2", "pin", "pinned")),
    (records.CollateralRuling("retired", "altered", "assertion survives"),),
)


def _saved(stage: records.Stage = _S.REVIEW) -> records.State:
    """Supply approved inputs and an independently committed completed step."""
    return state(
        stage=stage,
        candidate=candidate(keeps=("keep behavior",)),
        artifacts=_ARTIFACTS,
        baselines=(_SNAPSHOT,),
        steps=(records.StepRun("s1", 1, "locked", None, "complete"),),
        owners=(("pkg/home.py", "core-builder"),),
    )


def _answer(
    saved: records.State, role: str, payload: records.Payload
) -> records.Action:
    """Supply a literal completed role launch, independently of dispatch policy."""
    effect = records.Effect(
        f"reply-{role}", saved.stage, "launch", role, None, None, saved.artifacts
    )
    trace = records.TraceRow(
        f"{effect.id}.launch.0", role, "model", "medium", None, None, "running"
    )
    pending = records.Pending(
        effect, "started", trace.id, 0, records.RecoveryPoint(0, "checkpoint", None)
    )
    return decide.decide(
        replace(saved, pending=(pending,), launches=(*saved.launches, trace)),
        records.Answered(
            effect.id,
            0,
            role,
            records.RoleAnswer(payload),
            replace(trace, outcome="complete"),
        ),
    )


def _request(action: records.Action, operation: str) -> records.Pending:
    """Require requested work before extracting it, so omissions fail assertions."""
    matches = tuple(p for p in action.state.pending if p.effect.operation == operation)
    assert matches
    return matches[0]


def _checked(action: records.Action, fault: str = "complete") -> records.Action:
    """Reply to a nonempty check request with explicit dispatch-bound evidence."""
    pending = _request(action, "checks")
    request = pending.effect.input
    assert isinstance(request, records.CheckSet)
    assert request.checks
    rows = tuple(
        records.CheckRow(
            f"{pending.effect.id}.check.{pending.dispatch}.{index}",
            pending.effect.stage,
            0,
            check.id,
            records.Verdict.PASS,
            "executed",
        )
        for index, check in enumerate(request.checks)
    )
    if fault == "missing":
        rows = rows[:-1]
    elif fault == "duplicate":
        rows = (*rows, replace(rows[0], id="duplicate"))
    elif fault == "unexpected":
        rows = (*rows, replace(rows[0], id="extra", check="unrequested"))
    elif fault in {"fail", "unable"}:
        verdict = (
            records.Verdict.FAIL if fault == "fail" else records.Verdict.COULD_NOT_JUDGE
        )
        rows = (replace(rows[0], verdict=verdict), *rows[1:])
    started = replace(
        pending,
        status="started",
        recovery=records.RecoveryPoint(pending.dispatch, "checks", None),
    )
    saved = replace(
        action.state,
        pending=tuple(started if p == pending else p for p in action.state.pending),
    )
    return decide.decide(
        saved, records.Checked(pending.effect.id, pending.dispatch, rows)
    )


# The adjacent walk shares these literal inputs and executor reply machinery.
BAILIFF = _BAILIFF
PLAN = _PLAN
SNAPSHOT = _SNAPSHOT
SPEC = _SPEC
TESTS = _TESTS
checked = _checked


# Skipping a reviewer or the current-tree survey treats absent work as success.
def test_review_dispatches_every_required_role() -> None:
    """Explicitly execute both review contracts and the STRUCTURE survey."""
    action = decide.decide(_saved(), records.Tick())
    assert {e.role for e in action.effects} >= {
        "reviewer",
        "structure-reviewer",
        "surveyor",
    }
    assert action.state.stage == _S.REVIEW
    assert all(e.inputs == _ARTIFACTS for e in action.effects)


# Empty reviewer output cannot stand in for the other required executions.
def test_empty_review_is_recorded_without_skipping_other_roles() -> None:
    """One empty but executed review leaves the remaining work outstanding."""
    action = _answer(_saved(), "reviewer", records.ReviewAnswer(()))
    assert action.state.stage == _S.REVIEW
    assert any(
        a.answer.payload == records.ReviewAnswer(()) for a in action.state.artifacts
    )
    assert {e.role for e in action.effects} >= {"structure-reviewer", "surveyor"}


# Invalid findings must be retained with problems and excluded from grouping.
def test_review_rejects_invalid_findings_before_grouping() -> None:
    """A blank scenario is recorded but cannot become a routed cause."""
    invalid = finding(scenario=" ")
    valid = finding(anchor=Anchor("pkg/home.py", 2))
    action = _answer(_saved(), "reviewer", records.ReviewAnswer((invalid, valid)))
    assert any(
        a.answer.payload == records.ReviewAnswer((invalid, valid))
        for a in action.state.artifacts
    )
    assert any("no scenario" in row.evidence for row in action.state.checks)
    assert action.state.stage == _S.REVIEW
    action = _answer(action.state, "structure-reviewer", records.ReviewAnswer(()))
    action = _answer(action.state, "surveyor", survey())
    groupers = tuple(e for e in action.effects if e.role == "grouper")
    assert len(groupers) == 1
    assert groupers[0].input == records.ReviewAnswer((valid,))


# Invalid partitions cannot authorize fixes; all failure rounds spend the cap.
@pytest.mark.parametrize("cap", [1, 2])
@pytest.mark.parametrize("partition", ["missing", "duplicate", "empty"])
def test_invalid_cause_partition_consumes_review_round(
    cap: int, partition: str
) -> None:
    """Missing, repeated and empty cause assignments fail explicitly."""
    item = finding(anchor=Anchor("pkg/home.py", 2))
    saved = replace(
        _saved(),
        config=config(caps=records.Caps(review=cap)),
        artifacts=(
            *_ARTIFACTS,
            records.Artifact(
                "reviewer", 1, records.RoleAnswer(records.ReviewAnswer((item,)))
            ),
        ),
    )
    causes = (
        ()
        if partition == "missing"
        else (Cause("c1", "one cause", None, () if partition == "empty" else (item,)),)
    )
    if partition == "duplicate":
        causes = (*causes, Cause("c2", "same finding", None, (item,)))
    action = _answer(saved, "grouper", records.CausesAnswer(causes))
    assert records.Round(records.Loop.REVIEW, 1) in action.state.rounds
    assert any(
        row.verdict == records.Verdict.COULD_NOT_JUDGE for row in action.state.checks
    )
    assert not any(e.operation == "build" for e in action.effects)
    assert (action.state.status == "stopped") == (cap == 1)


# Cause routing must preserve identities and cannot reset the global review cap.
@pytest.mark.parametrize("recurrent", [False, True])
def test_blocking_cause_routes_once_and_retains_history(*, recurrent: bool) -> None:
    """Send a valid owned defect back to BUILD as one cause-level fix."""
    item = finding(anchor=Anchor("pkg/home.py", 2))
    grouped = Cause("c1", "one defect", None, (item,))
    saved = replace(
        _saved(),
        rounds=(records.Round(records.Loop.REVIEW, 1),),
        cause_rounds=(records.CauseRound("c1" if recurrent else "prior", 1),),
        config=config(caps=records.Caps(review=3)),
        artifacts=(
            *_ARTIFACTS,
            records.Artifact(
                "reviewer", 1, records.RoleAnswer(records.ReviewAnswer((item,)))
            ),
        ),
    )
    action = _answer(saved, "grouper", records.CausesAnswer((grouped,)))
    assert action.state.stage == _S.BUILD
    assert records.Round(records.Loop.REVIEW, 2) in action.state.rounds
    assert records.CauseRound("c1", 2 if recurrent else 1) in action.state.cause_rounds
    assert any(
        a.answer.payload == records.CausesAnswer((grouped,))
        for a in action.state.artifacts
    )
    builds = tuple(e for e in action.effects if e.operation == "build")
    assert len(builds) == 1
    assert builds[0].role == "core-builder"


# A missing shared home requires M8 design change, never an invented builder.
def test_design_change_stops_with_cause_retained() -> None:
    """Retain an unhomed structural cause for the unavailable M8 decision."""
    item = finding(
        anchor=Anchor("pkg/home.py", 2),
        category=Category.COPY,
        concern="unhomed",
        also=(Anchor("pkg/home.py", 3),),
    )
    grouped = Cause("c1", "missing home", "unhomed", (item,))
    saved = replace(
        _saved(),
        artifacts=(
            *_ARTIFACTS,
            records.Artifact(
                "reviewer", 1, records.RoleAnswer(records.ReviewAnswer((item,)))
            ),
        ),
    )
    action = _answer(saved, "grouper", records.CausesAnswer((grouped,)))
    assert action.state.status == "stopped"
    assert any(
        a.answer.payload == records.CausesAnswer((grouped,))
        for a in action.state.artifacts
    )
    assert not any(e.operation == "build" for e in action.effects)


# Current surveyed copies at separate lines cannot collapse to a single path.
def test_surveyed_copies_join_review_and_block_exit() -> None:
    """Keep both current anchors in the grouper's immutable input selection."""
    copies = tuple(
        finding(
            anchor=Anchor("pkg/home.py", line),
            category=Category.COPY,
            concern="process running",
            also=(Anchor("pkg/old.py", 9),),
        )
        for line in (4, 8)
    )
    saved = replace(
        _saved(),
        artifacts=(
            *_ARTIFACTS,
            records.Artifact(
                "reviewer", 1, records.RoleAnswer(records.ReviewAnswer(()))
            ),
            records.Artifact(
                "structure-reviewer", 1, records.RoleAnswer(records.ReviewAnswer(()))
            ),
        ),
    )
    action = _answer(saved, "surveyor", survey(findings=copies))
    assert action.state.stage == _S.REVIEW
    assert not any(e.role == "bailiff" for e in action.effects)
    groupers = tuple(e for e in action.effects if e.role == "grouper")
    assert groupers
    assert any(a.answer.payload == survey(findings=copies) for a in groupers[0].inputs)


# Routing an unowned defect must retain the domain's typed error boundary.
def test_unowned_cause_raises_typed_error() -> None:
    """Do not guess an implementer for an unowned first instance."""
    item = finding(anchor=Anchor("unowned.py", 2))
    saved = replace(
        _saved(),
        artifacts=(
            *_ARTIFACTS,
            records.Artifact(
                "reviewer", 1, records.RoleAnswer(records.ReviewAnswer((item,)))
            ),
        ),
    )
    with pytest.raises(UnownedPathError):
        _answer(
            saved,
            "grouper",
            records.CausesAnswer((Cause("c1", "unowned", None, (item,)),)),
        )


# Omitting or misruling any bailiff obligation must stop rather than land.
@pytest.mark.parametrize(
    "fault",
    [
        "missing-pin",
        "duplicate-pin",
        "unknown-pin",
        "unpinned",
        "unable",
        "missing-collateral",
        "wrong-collateral",
        "duplicate-collateral",
    ],
)
def test_bailiff_requires_exact_pins_and_collateral(fault: str) -> None:
    """Validate every final line and required collateral disposition."""
    pins, collateral = _BAILIFF.pins, _BAILIFF.collateral
    if fault == "missing-pin":
        pins = pins[:-1]
    elif fault == "duplicate-pin":
        pins = (*pins, pins[0])
    elif fault == "unknown-pin":
        pins = (*pins, records.Pin("unknown", "pin", "unrequested"))
    elif fault in {"unpinned", "unable"}:
        pins = (
            replace(
                pins[0],
                verdict="unpinned" if fault == "unpinned" else "could-not-judge",
            ),
            pins[1],
        )
    elif fault == "missing-collateral":
        collateral = ()
    elif fault == "wrong-collateral":
        collateral = (replace(collateral[0], verdict="held"),)
    else:
        collateral = (*collateral, collateral[0])
    action = _answer(
        _saved(_S.BAILIFF), "bailiff", records.BailiffAnswer(pins, collateral)
    )
    assert action.state.status == "stopped"
    assert not any(e.operation in {"owner", "land"} for e in action.effects)


# Omitting final gates must fail even when runners and preserved sources pass.
@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "unexpected", "fail", "unable", "complete"]
)
def test_land_requires_fresh_exact_final_checks_and_gates(fault: str) -> None:
    """All runners, gates and unchanged sources need explicit PASS rows."""
    saved = _saved(_S.BAILIFF)
    action = _answer(saved, "bailiff", _BAILIFF)
    assert action.state.stage == _S.LAND
    pending = _request(action, "checks")
    request = pending.effect.input
    assert isinstance(request, records.CheckSet)
    alternatives: list[records.Payload | None] = []
    for changed in (
        replace(
            saved,
            config=config(tests=(records.TestCommand("tests", "other-tests {ids}"),)),
        ),
        replace(
            saved,
            baselines=(
                replace(_SNAPSHOT, source="def test_kept():\n    assert preserved\n"),
            ),
        ),
        replace(saved, config=config(gates="project-final-gates")),
    ):
        other = _answer(changed, "bailiff", _BAILIFF)
        alternatives.append(_request(other, "checks").effect.input)
    assert all(item != request for item in alternatives)
    assert all(
        check.verdict == records.Verdict.COULD_NOT_JUDGE for check in request.checks
    )
    checked = _checked(action, fault)
    assert not any(e.operation == "land" for e in checked.effects)
    assert any(e.operation == "owner" for e in checked.effects) == (fault == "complete")
    assert checked.state.baselines == (_SNAPSHOT,)


# Owner approval authorizes a land operation but is never its success receipt.
def test_land_approval_and_success_receipt_are_distinct() -> None:
    """Only the prepared git operation's matching completion marks landed."""
    saved = replace(
        _saved(_S.BAILIFF),
        bypasses=(records.Bypass(_S.DISCOVERY, "owner", "recorded omission"),),
        amendments=(records.Amendment(("S1",), "approved change"),),
        controls=(records.OwnerUse("accept", _S.SPEC, "recorded ruling"),),
    )
    checked = _checked(_answer(saved, "bailiff", _BAILIFF))
    owner = _request(checked, "owner")
    approved = decide.decide(
        checked.state, records.Approved(owner.effect.id, owner.dispatch, ())
    )
    assert approved.state.status != "landed"
    land = _request(approved, "land")
    started = replace(
        land,
        status="started",
        recovery=records.RecoveryPoint(
            land.dispatch,
            "landing",
            records.GitIntent("repo", "main", "before", "landed-oid"),
        ),
    )
    landed = decide.decide(
        replace(approved.state, pending=(started,)),
        records.Completed(land.effect.id, land.dispatch, "landed-oid"),
    )
    assert landed.state.status == "landed"
    assert landed.state.bypasses == saved.bypasses
    assert landed.state.amendments == saved.amendments
    assert landed.state.controls == saved.controls
    assert landed.state.checks == checked.state.checks
    assert landed.state.launches == checked.state.launches
