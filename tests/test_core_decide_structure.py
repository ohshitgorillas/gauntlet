# Copyright 2026 oh shit, gorillas!
"""Structure decisions from M1 Order 28 and the workflow's starting contract."""

from dataclasses import replace

import pytest

from gauntlet.core import decide, records
from gauntlet.core.design import Choice, Design, Home, Step
from gauntlet.core.verdicts import Anchor
from tests.support.answers import candidate, config, design, state

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
    (),
)
_PLAN = records.Plan(
    (records.PlanStep(Step("s1", ("pkg/home.py",), "core-builder"), ("S1", "S2"), ()),)
)
_TESTS = records.TestAnswer(
    (records.TestBinding("S1", (_NEW,)), records.TestBinding("S2", (_OLD,))), ()
)
_JUDGMENT = records.RedJudgment(
    (
        records.RedLine("S1", records.RedVerdict.RED, (_NEW,)),
        records.RedLine("S2", records.RedVerdict.GREEN, (_OLD,)),
    )
)
_SNAPSHOT = records.TestSnapshot(
    _OLD, "@decorator\ndef test_kept():\n    assert preserved\n"
)
_ARTIFACTS: tuple[records.Artifact, ...] = (
    records.Artifact("design", 1, records.RoleAnswer(design())),
    records.Artifact("plan", 1, records.RoleAnswer(_PLAN)),
    records.Artifact("spec", 1, records.RoleAnswer(_SPEC)),
    records.Artifact("tests", 1, records.RoleAnswer(_TESTS)),
)


def _saved(stage: records.Stage) -> records.State:
    """Supply literal approved inputs independently of preceding decisions."""
    return state(
        stage=stage,
        candidate=candidate(keeps=("keep behavior",)),
        artifacts=_ARTIFACTS,
        baselines=(_SNAPSHOT,),
    )


def _answer(
    saved: records.State, role: str, payload: records.Payload
) -> records.Action:
    """Deliver one literal role result with its matching execution envelope."""
    effect = records.Effect(
        "stage-answer", saved.stage, "launch", role, None, None, saved.artifacts
    )
    trace = records.TraceRow(
        "stage-answer.launch.0", role, "model", "medium", None, None, "running"
    )
    pending = records.Pending(
        effect, "started", trace.id, 0, records.RecoveryPoint(0, "checkpoint", None)
    )
    started = replace(saved, pending=(pending,), launches=(trace,))
    return decide.decide(
        started,
        records.Answered(
            effect.id,
            0,
            role,
            records.RoleAnswer(payload),
            replace(trace, outcome="complete"),
        ),
    )


def _owner(saved: records.State, resolved: Design | None = None) -> records.Action:
    """Approve a pending owner request without fabricating a role verdict."""
    pending = next(p for p in saved.pending if p.effect.operation == "owner")
    approval = records.Approved(pending.effect.id, pending.dispatch, ())
    if resolved is not None:
        approval = replace(approval, design=resolved)
    return decide.decide(saved, approval)


def _requested(action: records.Action) -> records.Pending:
    """Read required evidence from the lead-bound CheckSet request protocol."""
    assert any(e.operation == "checks" for e in action.effects)
    pending = next(p for p in action.state.pending if p.effect.operation == "checks")
    assert isinstance(pending.effect.input, records.CheckSet)
    assert pending.effect.input.checks
    return pending


def _rows(pending: records.Pending) -> tuple[records.CheckRow, ...]:
    """Supply PASS verdicts for requested opaque identities, without inference."""
    request = pending.effect.input
    assert isinstance(request, records.CheckSet)
    return tuple(
        records.CheckRow(
            f"{pending.effect.id}.check.{pending.dispatch}.{index}",
            pending.effect.stage,
            0,
            check.id,
            records.Verdict.PASS,
            "executed and passed",
        )
        for index, check in enumerate(request.checks)
    )


def _checked(
    action: records.Action,
    pending: records.Pending,
    rows: tuple[records.CheckRow, ...],
) -> records.Action:
    """Return harness evidence for precisely one requested dispatch."""
    started = replace(
        pending,
        status="started",
        recovery=records.RecoveryPoint(pending.dispatch, "check-checkpoint", None),
    )
    saved = replace(
        action.state,
        pending=tuple(
            started if current.effect.id == pending.effect.id else current
            for current in action.state.pending
        ),
    )
    return decide.decide(
        saved, records.Checked(pending.effect.id, pending.dispatch, rows)
    )


# Stopping at the unfinished STRUCTURE row never launches its architect.
def test_design_dispatches_architect() -> None:
    """Start the structure job with architect work and its candidate retained."""
    saved = state(candidate=candidate(keeps=("keep behavior",)))
    action = decide.decide(saved, records.Tick())
    assert any(
        e.operation == "launch" and e.role == "architect" for e in action.effects
    )
    assert action.state.status == "active"
    assert action.state.candidate == saved.candidate


# Accepting an invalid design, absent concern home or unported copy skips DESIGN.
@pytest.mark.parametrize("fault", ["invalid", "home", "copy"])
@pytest.mark.parametrize("cap", [1, 2])
def test_design_problems_spend_only_design_round(fault: str, cap: int) -> None:
    """Retain failed design evidence and stop exactly at the configured cap."""
    proposed = design()
    saved = state(config=config(caps=records.Caps(design=cap)))
    if fault == "invalid":
        proposed = design(modules=())
    elif fault == "home":
        proposed = design(homes=(Home("other concern", "pkg/home.py", "no copies"),))
    else:
        saved = replace(saved, copies=(Anchor("pkg/copy.py", 8),))
    action = _answer(saved, "architect", proposed)
    assert records.Round(records.Loop.DESIGN, 1) in action.state.rounds
    assert any(a.answer.payload == proposed for a in action.state.artifacts)
    assert action.state.stage == _S.DESIGN
    assert action.state.status == ("stopped" if cap == 1 else "active")
    assert not any(e.operation == "owner" for e in action.effects)


# Treating architect success as approval starts PLAN before the owner's ruling.
def test_design_waits_and_approved_resolved_design_reaches_plan() -> None:
    """The owner resolves choices and PLAN receives that exact design."""
    choice = Choice("which home?", "one home", "two homes", "unmeasured")
    proposed = design(choices=(choice,))
    action = _answer(state(), "architect", proposed)
    assert action.state.stage == _S.DESIGN
    assert action.state.status == "waiting"
    assert any(e.operation == "owner" for e in action.effects)
    resolved = design()
    approved = _owner(action.state, resolved)
    assert approved.state.stage == _S.PLAN
    dispatched = decide.decide(approved.state, records.Tick())
    assert any(e.role == "planner" and e.input == resolved for e in dispatched.effects)
    assert any(a.answer.payload == resolved for a in dispatched.state.artifacts)


# Allowing unresolved choices in an approval authorizes an ambiguous plan.
def test_design_approval_cannot_advance_with_unresolved_choices() -> None:
    """An owner event carrying choices still needs a resolved design."""
    proposed = design(choices=(Choice("which?", "one", "two", "unmeasured"),))
    waiting = _answer(state(), "architect", proposed).state
    approved = _owner(waiting, proposed)
    assert approved.state.stage == _S.DESIGN
    assert not any(e.role == "planner" for e in approved.effects)


# Ignoring design-step identity accepts a planner's unauthorized replacement.
@pytest.mark.parametrize("fault", ["path", "implementer", "name"])
def test_plan_matches_approved_design_steps(fault: str) -> None:
    """Reject each changed component of the approved step contract."""
    step = _PLAN.steps[0].step
    if fault == "path":
        step = replace(step, paths=("pkg/other.py",))
    elif fault == "implementer":
        step = replace(step, implementer="seam-builder")
    else:
        step = replace(step, name="another")
    plan = records.Plan((replace(_PLAN.steps[0], step=step),))
    action = _answer(_saved(_S.PLAN), "planner", plan)
    assert action.state.stage == _S.PLAN
    assert records.Round(records.Loop.PLAN, 1) in action.state.rounds
    assert not any(e.operation == "owner" for e in action.effects)


# Accepting planner prose alone skips the prosecutor's explicit check rows.
def test_plan_requires_prosecutor_and_owner_approval() -> None:
    """A matching plan first requests independent checks."""
    action = _answer(_saved(_S.PLAN), "planner", _PLAN)
    assert action.state.stage == _S.PLAN
    assert any(e.role == "prosecutor" for e in action.effects)
    assert not any(e.operation == "owner" for e in action.effects)


# Empty or unable check collections cannot prove the requested PLAN checks ran.
@pytest.mark.parametrize(
    "verdict", [None, records.Verdict.FAIL, records.Verdict.COULD_NOT_JUDGE]
)
@pytest.mark.parametrize("cap", [1, 2])
def test_plan_nonpassing_checks_fail_capped_round(
    verdict: records.Verdict | None, cap: int
) -> None:
    """Retain objections and stop at cap rather than approve a failed plan."""
    checks = (
        ()
        if verdict is None
        else (
            records.Check(
                "citation", verdict, "unresolved citation", (Anchor("pkg/home.py", 1),)
            ),
        )
    )
    saved = replace(_saved(_S.PLAN), config=config(caps=records.Caps(plan=cap)))
    payload = records.CheckSet(checks, "continue")
    action = _answer(saved, "prosecutor", payload)
    assert records.Round(records.Loop.PLAN, 1) in action.state.rounds
    assert action.state.status == ("stopped" if cap == 1 else "active")
    assert any(a.answer.payload == payload for a in action.state.artifacts)
    assert not any(e.operation == "owner" for e in action.effects)


# Omitting a keeps claim or accepting malformed marks changes owner obligations.
@pytest.mark.parametrize(
    "fault", ["keeps", "duplicate", "claim", "bite", "mark", "green-ids"]
)
def test_spec_requires_keeps_and_explicit_valid_lines(fault: str) -> None:
    """Reject invalid SPEC input before it can be owner approved."""
    first, kept = _SPEC.lines
    if fault == "keeps":
        kept = replace(kept, claim="changed keep behavior")
    elif fault == "duplicate":
        kept = replace(kept, id="S1")
    elif fault == "claim":
        first = replace(first, claim=" ")
    elif fault == "bite":
        first = replace(first, bite=" ")
    elif fault == "mark":
        object.__setattr__(first := replace(first), "start", None)
    else:
        kept = replace(kept, tests=())
    action = _answer(_saved(_S.SPEC), "planner", records.Spec((first, kept), ()))
    assert records.Round(records.Loop.SPEC, 1) in action.state.rounds
    assert not any(e.operation == "owner" for e in action.effects)


# Missing or unable arbiter rulings cannot certify the whole approved spec.
@pytest.mark.parametrize(
    "rulings",
    [
        (),
        (records.SpecRuling("S1", records.Verdict.PASS, "accepted"),),
        (
            records.SpecRuling("S1", records.Verdict.PASS, "accepted"),
            records.SpecRuling("S2", records.Verdict.COULD_NOT_JUDGE, "unknown"),
        ),
    ],
)
def test_spec_requires_every_arbiter_ruling(
    rulings: tuple[records.SpecRuling, ...],
) -> None:
    """Missing and unable rows spend a spec round, never yield approval."""
    action = _answer(_saved(_S.SPEC), "arbiter", records.SpecJudgment(rulings))
    assert records.Round(records.Loop.SPEC, 1) in action.state.rounds
    assert not any(e.operation == "owner" for e in action.effects)


# Starting stub work on spec acceptance edits preserved tests before capture.
@pytest.mark.parametrize("marks", ["red", "mixed"])
def test_spec_approval_captures_green_baselines_before_edits(marks: str) -> None:
    """Owner approval covers marks and ids; only GREEN schedules capture."""
    spec = (
        _SPEC
        if marks == "mixed"
        else replace(
            _SPEC,
            lines=(
                _SPEC.lines[0],
                replace(_SPEC.lines[1], start=records.TestStart.RED, tests=()),
            ),
        )
    )
    saved = replace(
        _saved(_S.SPEC),
        artifacts=(
            *_ARTIFACTS[:2],
            records.Artifact("spec", 2, records.RoleAnswer(spec)),
        ),
        baselines=(),
    )
    judgment = records.SpecJudgment(
        tuple(
            records.SpecRuling(line.id, records.Verdict.PASS, "accepted")
            for line in spec.lines
        )
    )
    waiting = _answer(saved, "arbiter", judgment)
    assert waiting.state.status == "waiting"
    approved = _owner(waiting.state)
    if marks == "mixed":
        assert approved.effects
        assert all(e.operation == "baseline" for e in approved.effects)
        assert any(e.input == spec for e in approved.effects)
        assert approved.state.baselines == ()
    else:
        assert approved.state.stage == _S.STUBS
        assert not any(e.operation == "baseline" for e in approved.effects)


# Substituting approved GREEN ids or dropping bindings silently changes coverage.
@pytest.mark.parametrize("fault", ["missing", "substitute", "untestable"])
def test_tests_bind_exact_approved_ids(fault: str) -> None:
    """Binding validation stops incomplete and rewritten preserved-test sets."""
    supplied = _TESTS
    if fault == "missing":
        supplied = replace(supplied, bindings=(_TESTS.bindings[0],))
    elif fault == "substitute":
        supplied = replace(
            supplied,
            bindings=(_TESTS.bindings[0], records.TestBinding("S2", ("replacement",))),
        )
    else:
        supplied = replace(supplied, untestable=("S1",))
    action = _answer(_saved(_S.TESTS), "scrivener", supplied)
    assert action.state.stage != _S.LOCK
    assert not any(e.operation == "commit-tests" for e in action.effects)
    assert any(e.role == "arbiter" or e.operation == "stop" for e in action.effects)


# Advancing TESTS without binding validation never schedules the starting runs.
def test_valid_bindings_advance_to_red_run_without_changing_baselines() -> None:
    """Keep approved spec and harness sources while starting the runners."""
    saved = _saved(_S.TESTS)
    action = _answer(saved, "scrivener", _TESTS)
    assert action.state.stage == _S.RED_RUN
    assert action.state.baselines == saved.baselines
    assert _ARTIFACTS[2] in action.state.artifacts


# Running only one configured language leaves the other starting verdict unknown.
def test_red_run_requests_every_configured_runner() -> None:
    """Expose both opaque configured commands to the harness check work."""
    commands = (
        records.TestCommand("python", "pytest {ids}"),
        records.TestCommand("web", "npm test -- {ids}"),
    )
    saved = replace(_saved(_S.RED_RUN), config=config(tests=commands))
    action = decide.decide(saved, records.Tick())
    assert any(e.operation == "checks" for e in action.effects)
    assert action.state.config.tests == commands
    assert not any(e.operation == "commit-tests" for e in action.effects)


# Ignoring a runner's absent or nonpassing row advances on partial work.
@pytest.mark.parametrize(
    "fault",
    ["none", "missing", "duplicate", "unexpected", "fail", "unable", "complete"],
)
def test_runner_receipts_require_every_requested_check(fault: str) -> None:
    """Only exact explicit PASS evidence for all runners dispatches the juror."""
    commands = (
        records.TestCommand("python", "pytest {ids}"),
        records.TestCommand("web", "npm test -- {ids}"),
    )
    saved = replace(_saved(_S.RED_RUN), config=config(tests=commands))
    action = decide.decide(saved, records.Tick())
    pending = _requested(action)
    request = pending.effect.input
    assert isinstance(request, records.CheckSet)
    assert len(request.checks) == len(commands)
    assert tuple(check.reason for check in request.checks) == tuple(
        command.run for command in commands
    )
    assert all(c.verdict == records.Verdict.COULD_NOT_JUDGE for c in request.checks)
    rows = _rows(pending)
    if fault == "none":
        rows = ()
    elif fault == "missing":
        rows = rows[:1]
    elif fault == "duplicate":
        rows = (*rows, replace(rows[0], id="duplicate-run"))
    elif fault == "unexpected":
        rows = (*rows, replace(rows[0], id="unexpected-run", check="unrequested"))
    elif fault == "fail":
        rows = (rows[0], replace(rows[1], verdict=records.Verdict.FAIL))
    elif fault == "unable":
        rows = (rows[0], replace(rows[1], verdict=records.Verdict.COULD_NOT_JUDGE))
    checked = _checked(action, pending, rows)
    if fault == "complete":
        assert any(e.role == "juror" for e in checked.effects)
        assert all(row in checked.state.checks for row in rows)
    else:
        assert not any(e.role == "juror" for e in checked.effects)
    assert not any(e.operation == "commit-tests" for e in checked.effects)


# Trusting any juror success accepts contrary marks, wrong ids or absent rows.
@pytest.mark.parametrize("fault", ["missing", "ids", "opposite", "unable"])
@pytest.mark.parametrize("cap", [1, 2])
def test_juror_mismatch_goes_to_arbiter_under_cap(fault: str, cap: int) -> None:
    """Preserve approval and baselines while escalating a starting mismatch."""
    first, kept = _JUDGMENT.lines
    if fault == "missing":
        judgment = records.RedJudgment((first,))
    else:
        if fault == "ids":
            kept = replace(kept, tests=("replacement",))
        elif fault == "opposite":
            kept = replace(kept, verdict=records.RedVerdict.RED)
        else:
            kept = replace(kept, verdict=records.RedVerdict.COULD_NOT_JUDGE)
        judgment = records.RedJudgment((first, kept))
    saved = replace(_saved(_S.RED_RUN), config=config(caps=records.Caps(juror=cap)))
    action = _answer(saved, "juror", judgment)
    assert records.Round(records.Loop.JUROR, 1) in action.state.rounds
    assert action.state.baselines == saved.baselines
    assert _ARTIFACTS[2] in action.state.artifacts
    assert not any(e.operation == "commit-tests" for e in action.effects)
    if cap == 1:
        assert action.state.status == "stopped"
    else:
        assert any(e.role == "arbiter" for e in action.effects)


# Committing after juror success without a source check loses GREEN preservation.
def test_matching_juror_requires_explicit_source_check_before_lock() -> None:
    """Starting verdicts alone never authorize the test commit."""
    saved = _saved(_S.RED_RUN)
    action = _answer(saved, "juror", _JUDGMENT)
    assert any(e.operation == "checks" for e in action.effects)
    assert not any(e.operation == "commit-tests" for e in action.effects)
    assert action.state.baselines == saved.baselines


# Empty, failed or unable source evidence cannot authorize committing the tests.
@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "unexpected", "fail", "unable", "complete"]
)
def test_lock_requires_exact_passing_source_receipts(fault: str) -> None:
    """Only complete durable source-equality PASS evidence permits LOCK."""
    action = _answer(_saved(_S.RED_RUN), "juror", _JUDGMENT)
    pending = _requested(action)
    request = pending.effect.input
    assert isinstance(request, records.CheckSet)
    assert tuple((check.id, check.reason) for check in request.checks) == (
        (_SNAPSHOT.test_id, _SNAPSHOT.source),
    )
    rows = _rows(pending)
    if fault == "missing":
        rows = ()
    elif fault == "duplicate":
        rows = (*rows, replace(rows[0], id="duplicate-source-run"))
    elif fault == "unexpected":
        rows = (
            *rows,
            replace(rows[0], id="unexpected-source-run", check="unrequested"),
        )
    elif fault == "fail":
        rows = tuple(replace(row, verdict=records.Verdict.FAIL) for row in rows)
    elif fault == "unable":
        rows = tuple(
            replace(row, verdict=records.Verdict.COULD_NOT_JUDGE) for row in rows
        )
    checked = _checked(action, pending, rows)
    if fault == "complete":
        assert checked.state.stage == _S.LOCK
        assert any(e.operation == "commit-tests" for e in checked.effects)
        assert all(row in checked.state.checks for row in rows)
    else:
        assert not any(e.operation == "commit-tests" for e in checked.effects)
    assert checked.state.baselines == (_SNAPSHOT,)
