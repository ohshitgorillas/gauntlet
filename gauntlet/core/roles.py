# Copyright 2026 oh shit, gorillas!
"""Associate fixed roles with kinds and the shared answer schema catalog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gauntlet.core.codec import SCHEMAS
from gauntlet.core.records import Kind, RoleSpec

if TYPE_CHECKING:
    from collections.abc import Sequence

ROLES: tuple[RoleSpec, ...] = (
    RoleSpec("brief-writer", Kind.READER, ("brief",)),
    RoleSpec("detective", Kind.READER, ("discovery",)),
    RoleSpec("planner", Kind.READER, ("outline", "plan", "spec")),
    RoleSpec("architect", Kind.READER, ("design",)),
    RoleSpec("prosecutor", Kind.READER, ("check-set",)),
    RoleSpec("examiner", Kind.SCRATCH, ("evidence",)),
    RoleSpec("arbiter", Kind.JUDGE, ("spec-judgment",)),
    RoleSpec("scrivener", Kind.TESTER, ("tests",)),
    RoleSpec("juror", Kind.JUDGE, ("red-judgment",)),
    RoleSpec("implementer", Kind.IMPLEMENTER, ("build",)),
    RoleSpec("reviewer", Kind.READER, ("review",)),
    RoleSpec("structure-reviewer", Kind.READER, ("review",)),
    RoleSpec("grouper", Kind.JUDGE, ("causes",)),
    RoleSpec("bailiff", Kind.JUDGE, ("bailiff",)),
    RoleSpec("surveyor", Kind.READER, ("survey",)),
    RoleSpec("auditor", Kind.JUDGE, ("audit",)),
    RoleSpec("coordinator", Kind.COORDINATOR, ("epic",)),
)
_BY_NAME = {spec.name: spec for spec in ROLES}


def role(name: str) -> RoleSpec:
    """Return the fixed contract, raising KeyError for an unknown name."""
    return _BY_NAME[name]


def registry_problems(roles: Sequence[RoleSpec]) -> tuple[str, ...]:
    """Report invalid rows in input order and tags in schema order."""
    problems: list[str] = []
    seen: set[str] = set()
    for spec in roles:
        if spec.name in seen:
            problems.append(f"duplicate role name: {spec.name}")
        seen.add(spec.name)
        if not spec.schemas:
            problems.append(f"empty schema set: {spec.name}")
        problems.extend(
            f"unknown schema tag: {spec.name}: {tag}"
            for tag in spec.schemas
            if tag not in SCHEMAS
        )
        if spec.kind != _BY_NAME.get(spec.name, spec).kind:
            problems.append(f"wrong fixed role kind: {spec.name}")
    return tuple(problems)
