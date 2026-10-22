# Copyright 2026 oh shit, gorillas!
"""Pin the literal defaults and independent overrides in m1-core-records-design §answers."""

from dataclasses import replace

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
    anchor,
    candidate,
    cause,
    design,
    finding,
    missing,
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
