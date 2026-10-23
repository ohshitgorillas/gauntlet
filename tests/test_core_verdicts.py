# Copyright 2026 oh shit, gorillas!
"""Verdict schemas from structure-first-design.md, Modules: verdicts.py."""

from typing import TypedDict

import pytest

from gauntlet.core.verdicts import (
    Anchor,
    Category,
    core_missing_problems,
)
from tests.support.answers import candidate as c
from tests.support.answers import missing as m


def test_category_has_exactly_the_documented_values() -> None:
    """Breaks when a category is added, removed or given a different value."""
    assert {category.value for category in Category} == {
        "defect",
        "copy",
        "own-core",
        "drift",
        "missing",
    }


class CandidateFields(TypedDict):
    """Document the shared candidate fields used by these tests."""

    concern: str
    payoff: str
    risk: str
    keeps: tuple[str, ...]


class MissingFields(TypedDict):
    """Document the shared missing-core fields used by these tests."""

    need: str
    also: tuple[Anchor, ...]


C: CandidateFields = {
    "concern": "Cause grouping",
    "payoff": "Every reviewer uses the same cause boundaries.",
    "risk": "Distinct causes could be grouped together.",
    "keeps": ("Distinct causes remain distinct.",),
}
M: MissingFields = {
    "need": "The step needs one policy for grouping causes.",
    "also": (),
}


@pytest.mark.parametrize(
    "why", ["Correctness requires the shared policy.", "  needed  "]
)
def test_blocked_with_a_nonblank_why_has_no_problems(why: str) -> None:
    """Breaks when a blocked step with a substantive why is rejected."""
    assert core_missing_problems(m(candidate=c(**C, why=why), **M), blocked=True) == ()


@pytest.mark.parametrize("why", [None, "", " \t\n"])
def test_blocked_without_a_nonblank_why_has_a_problem(why: str | None) -> None:
    """Breaks when absent, empty or whitespace-only why passes a blocked step."""
    assert core_missing_problems(m(candidate=c(**C, why=why), **M), blocked=True) == (
        "blocked with no why",
    )


@pytest.mark.parametrize(
    "why", ["Correctness requires the shared policy.", "  needed  "]
)
def test_not_blocked_with_a_nonblank_why_has_a_problem(why: str) -> None:
    """Breaks when a substantive why is accepted on a step that is not blocked."""
    assert core_missing_problems(m(candidate=c(**C, why=why), **M), blocked=False) == (
        "why set on a step not blocked",
    )


@pytest.mark.parametrize("why", [None, "", " \t\n"])
def test_not_blocked_without_a_nonblank_why_has_no_problems(why: str | None) -> None:
    """Breaks when an absent, empty or whitespace-only why requires blocking."""
    assert core_missing_problems(m(candidate=c(**C, why=why), **M), blocked=False) == ()
