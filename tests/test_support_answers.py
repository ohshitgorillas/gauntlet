# Copyright 2026 oh shit, gorillas!
"""Pin the literal defaults and independent overrides in m1-core-records-design §answers."""

from dataclasses import replace

import pytest

from gauntlet.core import records
from gauntlet.core.causes import Cause
from gauntlet.core.design import Choice, Design, Home, Module, Step, Stub
from gauntlet.core.verdicts import (
    Anchor,
    Candidate,
    Category,
    CoreMissing,
    Finding,
    Survey,
)
from tests.support.answers import (
    ConfigChanges,
    StateChanges,
    anchor,
    answer,
    candidate,
    cause,
    config,
    design,
    finding,
    missing,
    seed,
    state,
    survey,
)


# Normalizing paths, changing the default line, or ignoring either override loses literal data.
def test_anchor_defaults_and_overrides() -> None:
    """Pin both defaults and independent positional or keyword overrides."""
    assert anchor() == Anchor("pkg/a.py", 1)
    assert anchor("./pkg/../b.py") == Anchor("./pkg/../b.py", 1)
    assert anchor(line=0) == Anchor("pkg/a.py", 0)
    assert anchor("other.py", -2) == Anchor("other.py", -2)


# Replacing any finding field implicitly, or dropping a supplied field, breaks this contract.
def test_finding_defaults_and_overrides() -> None:
    """Pin all finding fields and each isolated override."""
    expected = Finding(
        Anchor("pkg/a.py", 1),
        "a call fails",
        Category.DEFECT,
        blocking=True,
        concern=None,
        also=(),
    )
    other = Anchor("other.py", 9)
    assert finding() == expected
    assert finding(anchor=other) == replace(expected, anchor=other)
    assert finding(scenario="") == replace(expected, scenario="")
    assert finding(category=Category.COPY) == replace(expected, category=Category.COPY)
    assert finding(blocking=False) == replace(expected, blocking=False)
    assert finding(concern="routing") == replace(expected, concern="routing")
    assert finding(also=(other, other)) == replace(expected, also=(other, other))


# Rebuilding defaults from an override, or treating empty tuples as absent, loses supplied fields.
def test_design_defaults_and_overrides() -> None:
    """Pin the complete default design and independent replacements."""
    expected = Design(
        (Module("pkg/home.py", "one line", (), ()),),
        (Home("process running", "pkg/home.py", "running a process"),),
        (Step("s1", ("pkg/home.py",), "core-builder"),),
        (),
    )
    modules = (
        Module(
            "other.py",
            "different job",
            (Stub("f", "def f(): ..."),),
            (Anchor("old.py", 3),),
        ),
    )
    homes = (Home("routing", "other.py", "another router"),)
    order = (Step("second", ("other.py", "else.py"), "seam-builder"),)
    choices = (Choice("which?", "a", "b", "more work"),)
    assert design() == expected
    assert design(modules=modules) == replace(expected, modules=modules)
    assert design(homes=homes) == replace(expected, homes=homes)
    assert design(order=order) == replace(expected, order=order)
    assert design(choices=choices) == replace(expected, choices=choices)
    assert design(modules=()) == replace(expected, modules=())
    assert design(homes=()) == replace(expected, homes=())
    assert design(order=()) == replace(expected, order=())


# Inferring findings or a concern from the claim would alter fields the caller did not replace.
def test_cause_defaults_and_overrides() -> None:
    """Pin the cause's default finding and all independent fields."""
    expected = Cause(
        "c1",
        "one cause",
        None,
        (
            Finding(
                Anchor("pkg/a.py", 1),
                "a call fails",
                Category.DEFECT,
                blocking=True,
                concern=None,
                also=(),
            ),
        ),
    )
    other = Finding(
        Anchor("other.py", 4),
        "another failure",
        Category.DRIFT,
        blocking=False,
        concern="routing",
        also=(),
    )
    assert cause() == expected
    assert cause(id="c2") == replace(expected, id="c2")
    assert cause(claim="") == replace(expected, claim="")
    assert cause(concern="routing") == replace(expected, concern="routing")
    assert cause(findings=(other, other)) == replace(expected, findings=(other, other))
    assert cause(findings=()) == replace(expected, findings=())


# Calculating merits or ignoring empty overrides changes the literal candidate.
def test_candidate_defaults_and_overrides() -> None:
    """Pin every candidate default and independent override."""
    expected = Candidate("process running", "one runner", "a caller breaks", (), None)
    assert candidate() == expected
    assert candidate(concern="") == replace(expected, concern="")
    assert candidate(payoff="shared") == replace(expected, payoff="shared")
    assert candidate(risk="none known") == replace(expected, risk="none known")
    assert candidate(keeps=("same output", "same output")) == replace(
        expected, keeps=("same output", "same output")
    )
    assert candidate(why="measured") == replace(expected, why="measured")


# Filling a survey with inferred findings or sorting its supplied tuples loses literal observations.
def test_survey_defaults_and_overrides() -> None:
    """Pin the empty survey and independently supplied collections."""
    expected = Survey((), (), ())
    item = Finding(
        Anchor("b.py", 2),
        "failure",
        Category.COPY,
        blocking=True,
        concern=None,
        also=(),
    )
    proposal = Candidate("routing", "shared", "callers", ("same output",), "measured")
    assert survey() == expected
    assert survey(findings=(item, item)) == replace(expected, findings=(item, item))
    assert survey(candidates=(proposal,)) == replace(expected, candidates=(proposal,))
    assert survey(sound=("z", "a", "z")) == replace(expected, sound=("z", "a", "z"))


# Deriving a candidate from the need or discarding repeated anchors changes supplied fields.
def test_missing_defaults_and_overrides() -> None:
    """Pin the missing-core default candidate and independent replacements."""
    expected = CoreMissing(
        "one shared policy",
        Candidate("process running", "one runner", "a caller breaks", (), None),
        (),
    )
    proposal = Candidate("routing", "shared", "callers", ("same output",), "measured")
    other = Anchor("other.py", 8)
    assert missing() == expected
    assert missing(need="") == replace(expected, need="")
    assert missing(candidate=proposal) == replace(expected, candidate=proposal)
    assert missing(also=(other, other)) == replace(expected, also=(other, other))


# Changing any configuration seed field breaks the documented literal contract.
def test_config_defaults() -> None:
    """Pin the configuration seed including every optional default."""
    assert config() == records.Config(
        ".gauntlet/Containerfile",
        (records.TestCommand("tests", "pytest {ids}"),),
        "make check",
        "docs/testing.md",
        (records.InterfaceCommand("py", "stubgen -o {out} {modules}"),),
        (),
        (),
        None,
        implementer_network=False,
        caps=records.Caps(2, 2, 2, 2, 2, 2, 2),
        roles=(),
    )


# Ignoring an override or changing a second field violates independent replacement.
@pytest.mark.parametrize(
    "changes",
    [
        {"image": "other"},
        {"tests": ()},
        {"gates": "other"},
        {"test_policy": "other"},
        {"interface": ()},
        {"test_helpers": ("a", "a")},
        {"protected": ("b",)},
        {"test_lint": "lint"},
        {"implementer_network": True},
        {"caps": records.Caps(build=7)},
        {"roles": (records.RoleSetting("architect", "other", "high"),)},
        {"readiness_timeout_seconds": 1},
        {"proxy_limits": records.ProxyLimits(connections=1)},
        {
            "proxy_extra_routes": (
                records.ProxyRoute("GET", "/v1/models"),
                records.ProxyRoute("GET", "/v1/models"),
            )
        },
    ],
)
def test_config_independent_overrides(changes: ConfigChanges) -> None:
    """Each supplied field replaces only that field."""
    assert config(**changes) == replace(config(), **changes)


# Seeding a local readiness, limit or route default instead of Config's breaks this.
def test_config_launcher_setting_defaults() -> None:
    """Omitted settings keep ten seconds, canonical limits and no routes."""
    value = config()
    readiness_seconds = 10
    assert value.readiness_timeout_seconds == readiness_seconds
    assert value.proxy_limits == records.ProxyLimits(65536, 33554432, 8)
    assert value.proxy_extra_routes == ()


# Inferring state from configuration or populating history alters the literal seed.
def test_state_defaults() -> None:
    """Pin all state seed fields without running a decision function."""
    assert state() == records.State(
        job="j1",
        revision=0,
        shape=records.Shape.STRUCTURE,
        stage=records.Stage.DESIGN,
        status="active",
        config=config(),
        candidate=Candidate(
            "process running", "one runner", "a caller breaks", (), None
        ),
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
    )


# Dropping any field's override or deriving another field changes literal caller data.
@pytest.mark.parametrize(
    "changes",
    [
        {"job": "j2"},
        {"revision": 3},
        {"shape": records.Shape.JOB},
        {"stage": records.Stage.BRIEF},
        {"status": "stopped"},
        {"config": config(image="other")},
        {"candidate": None},
        {"copies": (Anchor("other.py", 0),)},
        {
            "artifacts": (
                records.Artifact("brief", 1, records.RoleAnswer(records.Brief("x"))),
            )
        },
        {"rounds": (records.Round(records.Loop.DESIGN, 1),)},
        {"steps": (records.StepRun("s1", 1, "base", None, "pending"),)},
        {"owners": (("x.py", "core-builder"),)},
        {"cause_rounds": (records.CauseRound("c1", 1),)},
        {"held": ("S1",)},
        {
            "checks": (
                records.CheckRow(
                    "c1", records.Stage.DESIGN, 1, "x", records.Verdict.PASS, "e"
                ),
            )
        },
        {"bypasses": (records.Bypass(records.Stage.DESIGN, "owner", "detail"),)},
        {"amendments": (records.Amendment(("S1",), "reason"),)},
        {"controls": (records.OwnerUse("stop", records.Stage.DESIGN, "detail"),)},
        {
            "launches": (
                records.TraceRow(
                    "e2.launch.1", "architect", "m", "high", 1, "0.1", "complete"
                ),
            )
        },
        {
            "pending": (
                records.Pending(
                    records.Effect(
                        "e2", records.Stage.DESIGN, "owner", None, None, None, ()
                    ),
                    "ready",
                    None,
                ),
            )
        },
        {"receipts": (records.Receipt("e1", records.Completed("e1", 0, "commit")),)},
        {
            "baselines": (
                records.TestSnapshot("tests/test_a.py::test_a", "def test_a(): pass"),
            )
        },
    ],
)
def test_state_independent_overrides(changes: StateChanges) -> None:
    """Every state field is independently replaceable."""
    assert state(**changes) == replace(state(), **changes)


# Deriving traces, discarding defects, or replacing payloads loses supplied answer fields.
def test_answer_defaults_and_overrides() -> None:
    """Pin default answer fields and explicit matching trace replacements."""
    default_trace = records.TraceRow(
        "e1.launch.0", "architect", "model", "medium", None, None, "complete"
    )
    expected = records.Answered(
        "e1", 0, "architect", records.RoleAnswer(design()), default_trace
    )
    defect = records.SpecDefect(
        "S1", "one claim", (records.Citation("evidence", Anchor("a", 1)),)
    )
    other_trace = records.TraceRow(
        "e1.launch.0", "architect", "other", "high", 5, "0.2", "complete"
    )
    effect_trace = replace(default_trace, id="e2.launch.0")
    dispatch_trace = replace(default_trace, id="e1.launch.2")
    role_trace = replace(default_trace, role="planner")
    assert answer() == expected
    assert answer(records.Brief("other")) == replace(
        expected, answer=records.RoleAnswer(records.Brief("other"))
    )
    assert answer(spec_defect=defect) == replace(
        expected, answer=records.RoleAnswer(design(), defect)
    )
    assert answer(trace=other_trace) == replace(expected, trace=other_trace)
    assert answer(effect="e2", trace=effect_trace) == replace(
        expected, effect="e2", trace=effect_trace
    )
    assert answer(dispatch=2, trace=dispatch_trace) == replace(
        expected, dispatch=2, trace=dispatch_trace
    )
    assert answer(role="planner", trace=role_trace) == replace(
        expected, role="planner", trace=role_trace
    )


# Changing or omitting a schema specimen breaks its independently pinned wire-test input.
@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ("brief", records.Brief("one request")),
        (
            "discovery",
            records.Discovery((records.Citation("one claim", Anchor("pkg/a.py", 1)),)),
        ),
        (
            "outline",
            records.Outline(
                (Step("s1", ("pkg/home.py",), "core-builder"),),
                ("pkg",),
                shared_structure=False,
            ),
        ),
        (
            "design",
            Design(
                (Module("pkg/home.py", "one line", (), ()),),
                (Home("process running", "pkg/home.py", "running a process"),),
                (Step("s1", ("pkg/home.py",), "core-builder"),),
                (),
            ),
        ),
        (
            "plan",
            records.Plan(
                (
                    records.PlanStep(
                        Step("s1", ("pkg/home.py",), "core-builder"), ("S1",), ()
                    ),
                )
            ),
        ),
        (
            "spec",
            records.Spec(
                (
                    records.SpecLine(
                        "S1", "one claim", "one measured value", records.TestStart.RED
                    ),
                ),
                (),
            ),
        ),
        (
            "check-set",
            records.CheckSet(
                (
                    records.Check(
                        "c1",
                        records.Verdict.PASS,
                        "one reason",
                        (Anchor("pkg/a.py", 1),),
                    ),
                ),
                "continue",
            ),
        ),
        (
            "spec-judgment",
            records.SpecJudgment(
                (records.SpecRuling("S1", records.Verdict.PASS, "one reason"),)
            ),
        ),
        (
            "evidence",
            records.Evidence(
                (records.Citation("one measurement", Anchor("pkg/a.py", 1)),)
            ),
        ),
        (
            "tests",
            records.TestAnswer(
                (records.TestBinding("S1", ("tests/test_a.py::test_a",)),), ()
            ),
        ),
        (
            "red-judgment",
            records.RedJudgment(
                (
                    records.RedLine(
                        "S1", records.RedVerdict.RED, ("tests/test_a.py::test_a",)
                    ),
                )
            ),
        ),
        (
            "build",
            records.BuildAnswer("s1", records.BuildStatus.COMPLETE, "one result"),
        ),
        ("review", records.ReviewAnswer(())),
        (
            "causes",
            records.CausesAnswer(
                (
                    Cause(
                        "c1",
                        "one cause",
                        None,
                        (
                            Finding(
                                Anchor("pkg/a.py", 1),
                                "a call fails",
                                Category.DEFECT,
                                blocking=True,
                                concern=None,
                                also=(),
                            ),
                        ),
                    ),
                )
            ),
        ),
        (
            "bailiff",
            records.BailiffAnswer((records.Pin("S1", "pin", "one reason"),), ()),
        ),
        ("survey", Survey((), (), ())),
        (
            "audit",
            records.AuditAnswer(
                (records.AuditRow("tests/test_a.py::test_a", "valid", "one reason"),)
            ),
        ),
        (
            "epic",
            records.EpicAnswer(
                (records.EpicJob("j1", "one request", (), ("pkg",)),), None
            ),
        ),
    ],
)
def test_schema_literal_specimens(schema: str, expected: records.Payload) -> None:
    """Pin every schema specimen before downstream codec tests consume it."""
    assert seed(schema) == expected


# Defaults are literal caller data, including config commands and every loop cap.
def test_config_default_fields() -> None:
    """Pin command strings and cap fields without dataclass equality alone."""
    value = config()
    assert value.image == ".gauntlet/Containerfile"
    assert value.gates == "make check"
    assert value.test_policy == "docs/testing.md"
    assert value.interface[0].language == "py"
    assert value.interface[0].run == "stubgen -o {out} {modules}"
    default_cap = 2
    assert value.caps.plan == default_cap
    assert value.caps.juror == default_cap
    assert value.caps.review == default_cap
    assert value.caps.reopen == default_cap
    role = records.RoleSetting("architect", "other", "high")
    assert role.model == "other"
    assert role.effort == "high"
