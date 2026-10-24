# Copyright 2026 oh shit, gorillas!
"""Literal record builders from m1-core-records-design, shared before consumer ports."""

from dataclasses import replace
from typing import TypedDict, Unpack

from gauntlet.core import records
from gauntlet.core.causes import Cause
from gauntlet.core.design import Choice, Design, Home, Module, Step
from gauntlet.core.verdicts import (
    Anchor,
    Candidate,
    Category,
    CoreMissing,
    Finding,
    Survey,
)


def anchor(path: str = "pkg/a.py", line: int = 1) -> Anchor:
    """Construct the supplied anchor without interpreting its path or line."""
    return Anchor(path, line)


_DEFAULT_ANCHOR = anchor()


def finding(
    *,
    anchor: Anchor = _DEFAULT_ANCHOR,
    scenario: str = "a call fails",
    category: Category = Category.DEFECT,
    blocking: bool = True,
    concern: str | None = None,
    also: tuple[Anchor, ...] = (),
) -> Finding:
    """Construct a finding from literal fields."""
    return Finding(anchor, scenario, category, blocking, concern, also)


def design(
    *,
    modules: tuple[Module, ...] = (Module("pkg/home.py", "one line", (), ()),),
    homes: tuple[Home, ...] = (
        Home("process running", "pkg/home.py", "running a process"),
    ),
    order: tuple[Step, ...] = (Step("s1", ("pkg/home.py",), "core-builder"),),
    choices: tuple[Choice, ...] = (),
) -> Design:
    """Construct the documented design, replacing only supplied fields."""
    return Design(modules, homes, order, choices)


class _CauseIdentity(TypedDict, total=False):
    """Keep the documented id keyword without shadowing the builtin."""

    id: str


def cause(
    *,
    claim: str = "one cause",
    concern: str | None = None,
    findings: tuple[Finding, ...] = (finding(),),
    **identity: Unpack[_CauseIdentity],
) -> Cause:
    """Construct a cause with literal findings."""
    return Cause(identity.get("id", "c1"), claim, concern, findings)


def candidate(
    *,
    concern: str = "process running",
    payoff: str = "one runner",
    risk: str = "a caller breaks",
    keeps: tuple[str, ...] = (),
    why: str | None = None,
) -> Candidate:
    """Construct a candidate without calculating its merits."""
    return Candidate(concern, payoff, risk, keeps, why)


_DEFAULT_CANDIDATE = candidate()


def survey(
    *,
    findings: tuple[Finding, ...] = (),
    candidates: tuple[Candidate, ...] = (),
    sound: tuple[str, ...] = (),
) -> Survey:
    """Construct the supplied survey collections."""
    return Survey(findings, candidates, sound)


def missing(
    *,
    need: str = "one shared policy",
    candidate: Candidate = _DEFAULT_CANDIDATE,
    also: tuple[Anchor, ...] = (),
) -> CoreMissing:
    """Construct a literal missing-core answer."""
    return CoreMissing(need, candidate, also)


class ConfigChanges(TypedDict, total=False):
    """Exact, independently replaceable configuration fields."""

    image: str
    tests: tuple[records.TestCommand, ...]
    gates: str
    test_policy: str
    interface: tuple[records.InterfaceCommand, ...]
    test_helpers: tuple[str, ...]
    protected: tuple[str, ...]
    test_lint: str | None
    implementer_network: bool
    caps: records.Caps
    roles: tuple[records.RoleSetting, ...]
    readiness_timeout_seconds: int
    proxy_limits: records.ProxyLimits
    proxy_extra_routes: tuple[records.ProxyRoute, ...]


class StateChanges(TypedDict, total=False):
    """Exact, independently replaceable workflow state fields."""

    job: str
    revision: int
    shape: records.Shape
    stage: records.Stage
    status: str
    config: records.Config
    candidate: Candidate | None
    copies: tuple[Anchor, ...]
    artifacts: tuple[records.Artifact, ...]
    rounds: tuple[records.Round, ...]
    steps: tuple[records.StepRun, ...]
    owners: tuple[tuple[str, str], ...]
    cause_rounds: tuple[records.CauseRound, ...]
    held: tuple[str, ...]
    checks: tuple[records.CheckRow, ...]
    bypasses: tuple[records.Bypass, ...]
    amendments: tuple[records.Amendment, ...]
    controls: tuple[records.OwnerUse, ...]
    launches: tuple[records.TraceRow, ...]
    pending: tuple[records.Pending, ...]
    receipts: tuple[records.Receipt, ...]
    baselines: tuple[records.TestSnapshot, ...]


def config(**changes: Unpack[ConfigChanges]) -> records.Config:
    """Replace only supplied fields of the documented configuration seed."""
    return replace(
        records.Config(
            ".gauntlet/Containerfile",
            (records.TestCommand("tests", "pytest {ids}"),),
            "make check",
            "docs/testing.md",
            (records.InterfaceCommand("py", "stubgen -o {out} {modules}"),),
        ),
        **changes,
    )


def state(**changes: Unpack[StateChanges]) -> records.State:
    """Replace only supplied fields of the documented state seed."""
    return replace(
        records.State(
            job="j1",
            revision=0,
            shape=records.Shape.STRUCTURE,
            stage=records.Stage.DESIGN,
            status="active",
            config=config(),
            candidate=candidate(),
            copies=(),
            artifacts=(),
            rounds=(),
            steps=(),
            owners=(),
            cause_rounds=(),
            held=(),
            checks=(),
            bypasses=(),
            amendments=(),
            controls=(),
            launches=(),
            pending=(),
            receipts=(),
            baselines=(),
        ),
        **changes,
    )


_DEFAULT_PAYLOAD = design()
_DEFAULT_TRACE = records.TraceRow(
    "e1.launch.0", "architect", "model", "medium", None, None, "complete"
)


def answer(
    payload: records.Payload = _DEFAULT_PAYLOAD,
    *,
    effect: str = "e1",
    dispatch: int = 0,
    role: str = "architect",
    spec_defect: records.SpecDefect | None = None,
    trace: records.TraceRow = _DEFAULT_TRACE,
) -> records.Answered:
    """Wrap literal payload and trace fields without deriving either."""
    return records.Answered(
        effect, dispatch, role, records.RoleAnswer(payload, spec_defect), trace
    )


def seed(schema: str) -> records.Payload:
    """Return the specimen pinned by the design's schema table."""
    specimens: dict[str, records.Payload] = {
        "brief": records.Brief("one request"),
        "discovery": records.Discovery((records.Citation("one claim", anchor()),)),
        "outline": records.Outline(
            (Step("s1", ("pkg/home.py",), "core-builder"),),
            ("pkg",),
            shared_structure=False,
        ),
        "design": design(),
        "plan": records.Plan(
            (
                records.PlanStep(
                    Step("s1", ("pkg/home.py",), "core-builder"), ("S1",), ()
                ),
            )
        ),
        "spec": records.Spec(
            (
                records.SpecLine(
                    "S1", "one claim", "one measured value", records.TestStart.RED
                ),
            ),
            (),
        ),
        "check-set": records.CheckSet(
            (records.Check("c1", records.Verdict.PASS, "one reason", (anchor(),)),),
            "continue",
        ),
        "spec-judgment": records.SpecJudgment(
            (records.SpecRuling("S1", records.Verdict.PASS, "one reason"),)
        ),
        "evidence": records.Evidence((records.Citation("one measurement", anchor()),)),
        "tests": records.TestAnswer(
            (records.TestBinding("S1", ("tests/test_a.py::test_a",)),), ()
        ),
        "red-judgment": records.RedJudgment(
            (
                records.RedLine(
                    "S1", records.RedVerdict.RED, ("tests/test_a.py::test_a",)
                ),
            )
        ),
        "build": records.BuildAnswer("s1", records.BuildStatus.COMPLETE, "one result"),
        "review": records.ReviewAnswer(()),
        "causes": records.CausesAnswer((cause(),)),
        "bailiff": records.BailiffAnswer((records.Pin("S1", "pin", "one reason"),), ()),
        "survey": survey(),
        "audit": records.AuditAnswer(
            (records.AuditRow("tests/test_a.py::test_a", "valid", "one reason"),)
        ),
        "epic": records.EpicAnswer(
            (records.EpicJob("j1", "one request", (), ("pkg",)),), None
        ),
    }
    return specimens[schema]
