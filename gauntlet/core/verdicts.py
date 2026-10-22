# Copyright 2026 oh shit, gorillas!
"""Hold the records every role's answer is built from."""

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class Anchor:  # one place in the job tree
    """Name one place in the job tree."""

    path: str  # relative to the tree root
    line: int  # 1-based


class Category(StrEnum):
    """Name the kind of a finding."""

    DEFECT = "defect"  # wrong behavior, no design concern
    COPY = "copy"  # the same logic in two or more places
    OWN_CORE = "own-core"  # a piece writes what a design home holds
    DRIFT = "drift"  # code departs from a design stub or home
    MISSING = "missing"  # audit only: a shared concern with no home


@dataclass(frozen=True)
class Finding:
    """Record one finding at one anchor."""

    anchor: Anchor
    scenario: str  # the failure scenario
    category: Category
    blocking: bool
    concern: str | None  # the shared concern it breaks; None only for DEFECT
    also: tuple[
        Anchor, ...
    ] = ()  # every other place the logic sits, for COPY and MISSING


@dataclass(frozen=True)
class Candidate:  # one structure job put to the owner
    """Record one structure job put to the owner."""

    concern: str
    payoff: str  # what the core saves, one sentence
    risk: str  # what porting the copies could break, one sentence
    keeps: tuple[
        str, ...
    ]  # hard-won behaviors the copies carry, one line each, for the spec (decision 9)
    why: str | None = (
        None  # set only when the request cannot be done correctly without it (decision 8)
    )


@dataclass(frozen=True)
class CoreMissing:  # carried by an implementer's `blocked`, `complete` or `partial`
    """Record what a step needs from a core that lacks it."""

    need: str  # what the step needs from the core, one sentence
    candidate: Candidate  # its why set on `blocked` and only there
    also: tuple[
        Anchor, ...
    ]  # every copy or caller of the concern the implementer found


@dataclass(frozen=True)
class Survey:  # the surveyor's answer
    """Record the surveyor's answer."""

    findings: tuple[Finding, ...]  # categories COPY and MISSING
    candidates: tuple[
        Candidate, ...
    ]  # one per concern, ranked best payoff for its risk first (decision 9)
    sound: tuple[str, ...]  # what is sound enough to keep as it is, one line each


def core_missing_problems(missing: CoreMissing, *, blocked: bool) -> tuple[str, ...]:
    """Check that a substantive why is present exactly when the step is blocked."""
    has_why = bool((missing.candidate.why or "").strip())
    if blocked and not has_why:
        return ("blocked with no why",)
    if not blocked and has_why:
        return ("why set on a step not blocked",)
    return ()
