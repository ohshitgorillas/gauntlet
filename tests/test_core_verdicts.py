# Copyright 2026 oh shit, gorillas!
"""Verdict schemas from structure-first-design.md, Modules: verdicts.py."""

import pytest

from gauntlet.core.verdicts import (
    Candidate,
    Category,
    CoreMissing,
    core_missing_problems,
)


def test_category_has_exactly_the_documented_values() -> None:
    """Breaks when a category is added, removed or given a different value."""
    assert {category.value for category in Category} == {
        "defect",
        "copy",
        "own-core",
        "drift",
        "missing",
    }


def _missing(why: str | None) -> CoreMissing:
    return CoreMissing(
        need="The step needs one policy for grouping causes.",
        candidate=Candidate(
            concern="Cause grouping",
            payoff="Every reviewer uses the same cause boundaries.",
            risk="Distinct causes could be grouped together.",
            keeps=("Distinct causes remain distinct.",),
            why=why,
        ),
        also=(),
    )


@pytest.mark.parametrize(
    "why", ["Correctness requires the shared policy.", "  needed  "]
)
def test_blocked_with_a_nonblank_why_has_no_problems(why: str) -> None:
    """Breaks when a blocked step with a substantive why is rejected."""
    assert core_missing_problems(_missing(why), blocked=True) == ()


@pytest.mark.parametrize("why", [None, "", " \t\n"])
def test_blocked_without_a_nonblank_why_has_a_problem(why: str | None) -> None:
    """Breaks when absent, empty or whitespace-only why passes a blocked step."""
    assert core_missing_problems(_missing(why), blocked=True) == (
        "blocked with no why",
    )


@pytest.mark.parametrize(
    "why", ["Correctness requires the shared policy.", "  needed  "]
)
def test_not_blocked_with_a_nonblank_why_has_a_problem(why: str) -> None:
    """Breaks when a substantive why is accepted on a step that is not blocked."""
    assert core_missing_problems(_missing(why), blocked=False) == (
        "why set on a step not blocked",
    )


@pytest.mark.parametrize("why", [None, "", " \t\n"])
def test_not_blocked_without_a_nonblank_why_has_no_problems(why: str | None) -> None:
    """Breaks when an absent, empty or whitespace-only why requires blocking."""
    assert core_missing_problems(_missing(why), blocked=False) == ()
