# Copyright 2026 oh shit, gorillas!
"""Literal record builders from m1-core-records-design, shared before consumer ports."""

from typing import TypedDict, Unpack

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
