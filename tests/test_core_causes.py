# Copyright 2026 oh shit, gorillas!
"""Cause checks from structure-first-design.md, Modules: core/causes.py."""

from dataclasses import replace

import pytest

from gauntlet.core.causes import (
    Cause,
    DesignChange,
    FixStep,
    UnownedPath,
    finding_problems,
    partition_problems,
    route,
    survey_problems,
)
from gauntlet.core.design import Design, Home, Module, Step
from gauntlet.core.verdicts import Anchor, Candidate, Category, Finding, Survey


def _finding(category: Category = Category.COPY) -> Finding:
    return Finding(
        Anchor("z.py", 7),
        "Copies diverge",
        category,
        blocking=True,
        concern="running",
        also=(Anchor("other.py", 9),),
    )


def _design() -> Design:
    return Design(
        (Module("home.py", "Run processes", (), ()),),
        (Home("running", "home.py", "process execution"),),
        (Step("home", ("home.py",), "core-builder"),),
        (),
    )


@pytest.mark.parametrize("blank", ["", " \t\n"])
def test_finding_reports_scenario_before_other_problems(blank: str) -> None:
    """Breaks when blank scenarios pass or check order changes."""
    finding = replace(_finding(), scenario=blank, also=(), blocking=False, concern=None)
    assert finding_problems(finding, None) == (
        "no scenario",
        "copy with no also",
        "copy not blocking",
        "copy with no concern",
    )


@pytest.mark.parametrize("category", [Category.COPY, Category.MISSING])
def test_copy_and_missing_require_also(category: Category) -> None:
    """Breaks when either copying category accepts no other anchor."""
    assert finding_problems(replace(_finding(category), also=()), None) == (
        f"{category.value} with no also",
    )


@pytest.mark.parametrize(
    "category", [Category.COPY, Category.MISSING, Category.OWN_CORE, Category.DRIFT]
)
def test_nondefect_requires_blocking_and_concern(category: Category) -> None:
    """Breaks when any structural category accepts nonblocking or no concern."""
    assert finding_problems(replace(_finding(category), blocking=False), _design()) == (
        f"{category.value} not blocking",
    )
    assert finding_problems(replace(_finding(category), concern=None), None)[:1] == (
        f"{category.value} with no concern",
    )


def test_defect_has_no_concern_and_need_not_block_or_have_also() -> None:
    """Breaks when defects require structural fields or allow a concern."""
    finding = replace(_finding(Category.DEFECT), also=(), blocking=False)
    assert finding_problems(finding, None) == ("defect with a concern",)
    assert finding_problems(replace(finding, concern=None), None) == ()


@pytest.mark.parametrize("category", [Category.OWN_CORE, Category.DRIFT])
def test_design_categories_need_design_and_exact_home(category: Category) -> None:
    """Breaks when design categories pass without a design or matching home."""
    finding = _finding(category)
    assert finding_problems(finding, None) == (f"{category.value} with no design",)
    absent = replace(_design(), homes=(Home("Running", "home.py", "copies"),))
    assert finding_problems(finding, absent) == (
        f"{category.value}: no home for running",
    )
    assert finding_problems(replace(finding, also=()), _design()) == ()


@pytest.mark.parametrize("design", [None, Design((), (), (), ()), _design()])
@pytest.mark.parametrize("category", [Category.COPY, Category.MISSING])
def test_copy_and_missing_stand_independently_of_design(
    category: Category,
    design: Design | None,
) -> None:
    """Breaks when audit categories are incorrectly tied to design homes."""
    assert finding_problems(_finding(category), design) == ()


def test_partition_lists_findings_then_empty_and_mismatched_causes() -> None:
    """Breaks when partition checks omit or reorder any failure kind."""
    absent = _finding()
    repeated = replace(absent, anchor=Anchor("a.py", 2), concern="parsing")
    causes = (
        Cause("empty", "No instances", None, ()),
        Cause("first", "Wrong home", "running", (repeated,)),
        Cause("second", "Wrong home", None, (repeated,)),
        Cause("third", "Another home", "parsing", (repeated,)),
    )
    assert partition_problems((absent, repeated), causes) == (
        "finding z.py:7: in no cause",
        "finding a.py:2: in 3 causes",
        "cause empty: no finding",
        "cause first: finding a.py:2 breaks parsing, not running",
        "cause second: finding a.py:2 breaks parsing, not none",
    )


def test_partition_accepts_one_cause_each_and_ignores_defect_concern() -> None:
    """Breaks when valid partitions fail or defects get structural checks."""
    structural = _finding()
    defect = replace(_finding(Category.DEFECT), concern=None)
    causes = (Cause("shared", "One cause", "running", (structural, defect)),)
    assert partition_problems((structural, defect), causes) == ()


def test_empty_partition_has_no_problem() -> None:
    """Breaks when an empty review invents partition problems."""
    assert partition_problems((), ()) == ()


@pytest.mark.parametrize("concern", [None, "unhomed"])
@pytest.mark.parametrize("design", [None, _design()])
def test_route_uses_first_instance_owner_and_unique_instance_paths(
    concern: str | None,
    design: Design | None,
) -> None:
    """Breaks when routing uses also anchors, sorts paths or repeats a path."""
    first = _finding()
    second = replace(first, anchor=Anchor("a.py", 1))
    third = replace(first, anchor=Anchor("z.py", 8))
    cause = Cause("copies", "Repeated execution", concern, (first, second, third))
    assert route(cause, design, {"z.py": "first", "a.py": "second"}) == FixStep(
        cause,
        "first",
        ("z.py", "a.py"),
    )


def test_homed_route_uses_first_writer_and_module_then_instances() -> None:
    """Breaks when home routing uses owners, last writer or duplicate paths."""
    first = _finding()
    cause = Cause(
        "copies",
        "Repeated execution",
        "running",
        (
            first,
            replace(first, anchor=Anchor("home.py", 1)),
            replace(first, anchor=Anchor("a.py", 2)),
            first,
        ),
    )
    design = replace(
        _design(),
        order=(
            Step("unrelated", ("else.py",), "other"),
            Step("first", ("home.py",), "first-builder"),
            Step("second", ("home.py",), "last-builder"),
        ),
    )
    assert route(cause, design, {}) == FixStep(
        cause,
        "first-builder",
        ("home.py", "z.py", "a.py"),
    )


def test_unhomed_route_changes_design_when_all_also_paths_are_owned() -> None:
    """Breaks when instance ownership replaces the every-also ownership rule."""
    first = _finding()
    second = replace(first, also=(Anchor("more.py", 4),))
    cause = Cause("copies", "Repeated execution", "unhomed", (first, second))
    assert route(cause, _design(), {"other.py": "one", "more.py": "two"}) == (
        DesignChange(cause)
    )


def test_unhomed_route_with_no_also_changes_design() -> None:
    """Breaks when every-also incorrectly requires a nonempty anchor list."""
    cause = Cause(
        "gap", "Missing structure", "unhomed", (replace(_finding(), also=()),)
    )
    assert route(cause, _design(), {}) == DesignChange(cause)


def test_one_external_also_path_forces_instance_owner_route() -> None:
    """Breaks when any owned also path is enough to reopen a design."""
    first = _finding()
    second = replace(first, also=(Anchor("external.py", 4),))
    cause = Cause("copies", "Repeated execution", "unhomed", (first, second))
    assert route(cause, _design(), {"z.py": "fixer", "other.py": "other"}) == (
        FixStep(cause, "fixer", ("z.py",))
    )


def test_no_concern_rule_precedes_design_change() -> None:
    """Breaks when owned also paths reopen a design for a concernless cause."""
    cause = Cause("bug", "Incorrect result", None, (_finding(),))
    assert route(cause, _design(), {"z.py": "fixer", "other.py": "other"}) == (
        FixStep(cause, "fixer", ("z.py",))
    )


@pytest.mark.parametrize("concern", [None, "unhomed"])
def test_unowned_first_instance_raises_with_its_path(concern: str | None) -> None:
    """Breaks when missing ownership is hidden or reports an also path."""
    cause = Cause("copies", "Repeated execution", concern, (_finding(),))
    with pytest.raises(UnownedPath) as caught:
        route(cause, None, {"other.py": "other"})
    assert caught.value.path == "z.py"


@pytest.mark.parametrize("blank", ["", " \t\n"])
def test_survey_reports_causes_then_candidates_in_order(blank: str) -> None:
    """Breaks when any survey failure is missed, reordered or deduplicated."""
    causes = (
        Cause("missing", "No proposal", "absent", (_finding(),)),
        Cause("covered", "Has proposals", "running", (_finding(),)),
    )
    unknown = Candidate("unknown", blank, blank, ())
    known = Candidate("running", "One home", "Porting risk", ())
    survey = Survey((), (unknown, known, known, unknown, known), ())
    assert survey_problems(survey, causes) == (
        "cause missing: no candidate for absent",
        "candidate unknown: no cause",
        "candidate unknown: no payoff",
        "candidate unknown: no risk",
        "candidate running: named twice",
        "candidate unknown: no cause",
        "candidate unknown: named twice",
        "candidate unknown: no payoff",
        "candidate unknown: no risk",
        "candidate running: named twice",
    )


def test_survey_accepts_complete_candidates_for_every_cause() -> None:
    """Breaks when shared-concern causes require separate candidate records."""
    causes = (
        Cause("first", "One instance", "running", (_finding(),)),
        Cause("second", "Another instance", "running", (_finding(),)),
    )
    candidate = Candidate("running", "One home", "Porting risk", ())
    assert survey_problems(Survey((), (candidate,), ()), causes) == ()


def test_empty_survey_and_causes_have_no_problems() -> None:
    """Breaks when an empty audit invents missing candidates or causes."""
    assert survey_problems(Survey((), (), ()), ()) == ()
