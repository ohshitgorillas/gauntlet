# Copyright 2026 oh shit, gorillas!
"""Group findings into causes and route each cause to one fix."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from gauntlet.core.design import Design, home_of
from gauntlet.core.verdicts import Category, Finding, Survey


@dataclass(frozen=True)
class Cause:
    """Record one underlying cause and every finding it explains."""

    id: str  # stable across rounds; the grouper reuses it
    claim: str  # the underlying cause, one sentence
    concern: str | None  # None for a cause outside every shared concern
    findings: tuple[Finding, ...]  # every instance


@dataclass(frozen=True)
class FixStep:
    """Record the one fix a cause is routed to."""

    cause: Cause
    implementer: str
    paths: tuple[str, ...]  # the home's module, then every instance's path


@dataclass(frozen=True)
class DesignChange:  # the fix needs a home the design lacks
    """Record a cause whose fix needs a home the design lacks."""

    cause: Cause


class UnownedPathError(Exception):
    """Raise when a path has no owner to route a fix to."""

    def __init__(self, path: str) -> None:
        """Keep the path no owner holds."""
        super().__init__(path)
        self.path = path


UnownedPath = UnownedPathError


def finding_problems(finding: Finding, design: Design | None) -> tuple[str, ...]:
    """Return finding failures in the documented validation order."""
    problems: list[str] = []
    category = finding.category
    if not finding.scenario.strip():
        problems.append("no scenario")
    if category in (Category.COPY, Category.MISSING) and not finding.also:
        problems.append(f"{category} with no also")
    if category != Category.DEFECT and not finding.blocking:
        problems.append(f"{category} not blocking")
    if category == Category.DEFECT and finding.concern is not None:
        problems.append("defect with a concern")
    if category != Category.DEFECT and finding.concern is None:
        problems.append(f"{category} with no concern")
    if category in (Category.OWN_CORE, Category.DRIFT):
        problems.extend(_home_problems(finding, design))
    return tuple(problems)


def _home_problems(finding: Finding, design: Design | None) -> tuple[str, ...]:
    """Check the design requirement for a finding about a declared home."""
    if design is None:
        return (f"{finding.category} with no design",)
    if finding.concern is not None and home_of(design, finding.concern) is None:
        return (f"{finding.category}: no home for {finding.concern}",)
    return ()


def partition_problems(
    findings: Sequence[Finding], causes: Sequence[Cause]
) -> tuple[str, ...]:
    """Check grouping counts before checking each cause's instances."""
    problems: list[str] = []
    for finding in findings:
        count = sum(finding in cause.findings for cause in causes)
        anchor = finding.anchor
        if count == 0:
            problems.append(f"finding {anchor.path}:{anchor.line}: in no cause")
        elif count > 1:
            problems.append(f"finding {anchor.path}:{anchor.line}: in {count} causes")
    for cause in causes:
        if not cause.findings:
            problems.append(f"cause {cause.id}: no finding")
        for finding in cause.findings:
            if finding.category != Category.DEFECT and finding.concern != cause.concern:
                anchor = finding.anchor
                problems.append(
                    f"cause {cause.id}: finding {anchor.path}:{anchor.line} "
                    f"breaks {_concern_text(finding.concern)}, "
                    f"not {_concern_text(cause.concern)}"
                )
    return tuple(problems)


def _concern_text(concern: str | None) -> str:
    """Display an absent concern without changing exact concern strings."""
    return "none" if concern is None else concern


def route(
    cause: Cause, design: Design | None, owners: Mapping[str, str]
) -> FixStep | DesignChange:
    """Route a cause by the first matching concern and ownership rule."""
    paths = tuple(
        dict.fromkeys((finding.anchor.path for finding in cause.findings), False)
    )
    if cause.concern is None:
        return _instance_fix(cause, paths, owners)
    if design is not None:
        home = home_of(design, cause.concern)
        if home is not None:
            writer = next(step for step in design.order if home.module in step.paths)
            return FixStep(
                cause,
                writer.implementer,
                tuple(dict.fromkeys((home.module, *paths), False)),
            )
        if all(
            anchor.path in owners
            for finding in cause.findings
            for anchor in finding.also
        ):
            return DesignChange(cause)
    return _instance_fix(cause, paths, owners)


def _instance_fix(
    cause: Cause, paths: tuple[str, ...], owners: Mapping[str, str]
) -> FixStep:
    """Use the first instance's owner, reporting a missing ownership entry."""
    path = paths[0]
    if path not in owners:
        raise UnownedPath(path)
    return FixStep(cause, owners[path], paths)


def survey_problems(survey: Survey, causes: Sequence[Cause]) -> tuple[str, ...]:
    """Check cause coverage, then each candidate in survey order."""
    candidates = {candidate.concern for candidate in survey.candidates}
    problems = [
        f"cause {cause.id}: no candidate for {_concern_text(cause.concern)}"
        for cause in causes
        if cause.concern not in candidates
    ]
    concerns = {cause.concern for cause in causes}
    seen: set[str] = set()
    for candidate in survey.candidates:
        concern = candidate.concern
        if concern not in concerns:
            problems.append(f"candidate {concern}: no cause")
        if concern in seen:
            problems.append(f"candidate {concern}: named twice")
        seen.add(concern)
        for field, value in (("payoff", candidate.payoff), ("risk", candidate.risk)):
            if not value.strip():
                problems.append(f"candidate {concern}: no {field}")
    return tuple(problems)
