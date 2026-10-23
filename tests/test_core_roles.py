# Copyright 2026 oh shit, gorillas!
"""Fixed role contracts from m1-core-records-design, roles."""

from dataclasses import replace

import pytest

from gauntlet.core import codec, records, roles
from gauntlet.core.errors import RecordError
from tests.support.answers import seed

_EXPECTED = (
    records.RoleSpec("brief-writer", records.Kind.READER, ("brief",)),
    records.RoleSpec("detective", records.Kind.READER, ("discovery",)),
    records.RoleSpec("planner", records.Kind.READER, ("outline", "plan", "spec")),
    records.RoleSpec("architect", records.Kind.READER, ("design",)),
    records.RoleSpec("prosecutor", records.Kind.READER, ("check-set",)),
    records.RoleSpec("examiner", records.Kind.SCRATCH, ("evidence",)),
    records.RoleSpec("arbiter", records.Kind.JUDGE, ("spec-judgment",)),
    records.RoleSpec("scrivener", records.Kind.TESTER, ("tests",)),
    records.RoleSpec("juror", records.Kind.JUDGE, ("red-judgment",)),
    records.RoleSpec("implementer", records.Kind.IMPLEMENTER, ("build",)),
    records.RoleSpec("reviewer", records.Kind.READER, ("review",)),
    records.RoleSpec("structure-reviewer", records.Kind.READER, ("review",)),
    records.RoleSpec("grouper", records.Kind.JUDGE, ("causes",)),
    records.RoleSpec("bailiff", records.Kind.JUDGE, ("bailiff",)),
    records.RoleSpec("surveyor", records.Kind.READER, ("survey",)),
    records.RoleSpec("auditor", records.Kind.JUDGE, ("audit",)),
    records.RoleSpec("coordinator", records.Kind.COORDINATOR, ("epic",)),
)
_CONTRACTS = tuple((spec.name, tag) for spec in _EXPECTED for tag in spec.schemas)
_NAMES = tuple(spec.name for spec in _EXPECTED)


# Adding, losing or duplicating a registry row breaks the fixed role set.
def test_registry_has_exact_fixed_roles() -> None:
    """Expose the documented roles, kinds and exact schema tuples."""
    assert isinstance(roles.ROLES, tuple)
    assert len(roles.ROLES) == len(_EXPECTED)
    assert set(roles.ROLES) == set(_EXPECTED)


# Returning another role, kind or schema tuple breaks this independent oracle.
@pytest.mark.parametrize("expected", _EXPECTED, ids=_NAMES)
def test_lookup_preserves_fixed_role_contract(expected: records.RoleSpec) -> None:
    """Look up every fixed role with its documented kind and schemas."""
    assert roles.role(expected.name) == expected


# Rejecting the fixed registry or relying on its iteration order breaks validity.
def test_fixed_registry_is_valid() -> None:
    """Accept the full valid registry as either tuple or reordered sequence."""
    assert roles.registry_problems(roles.ROLES) == ()
    assert roles.registry_problems(list(reversed(_EXPECTED))) == ()


# Silently replacing a duplicate name loses a supplied contract.
@pytest.mark.parametrize("expected", _EXPECTED, ids=_NAMES)
@pytest.mark.parametrize("conflicting", [False, True])
def test_registry_rejects_duplicate_names(
    expected: records.RoleSpec, *, conflicting: bool
) -> None:
    """Reject identical and conflicting rows with an already used name."""
    duplicate = replace(expected, schemas=("brief",)) if conflicting else expected
    assert roles.registry_problems((*_EXPECTED, duplicate))


# Accepting a role without any answer schema breaks its registered contract.
@pytest.mark.parametrize("expected", _EXPECTED, ids=_NAMES)
def test_registry_rejects_empty_schema_sets(expected: records.RoleSpec) -> None:
    """Reject an empty schema tuple for every fixed role."""
    invalid = tuple(
        replace(spec, schemas=()) if spec.name == expected.name else spec
        for spec in _EXPECTED
    )
    assert roles.registry_problems(invalid)


# Checking only the first tag permits an unknown trailing schema.
@pytest.mark.parametrize("expected", _EXPECTED, ids=_NAMES)
@pytest.mark.parametrize("retain_known", [False, True])
def test_registry_rejects_unknown_schema_tags(
    expected: records.RoleSpec, *, retain_known: bool
) -> None:
    """Reject unknown tags alone and alongside documented schema tags."""
    tags = (
        (*expected.schemas, "unknown-schema") if retain_known else ("unknown-schema",)
    )
    invalid = tuple(
        replace(spec, schemas=tags) if spec.name == expected.name else spec
        for spec in _EXPECTED
    )
    assert roles.registry_problems(invalid)


# Allowing any alternate kind lets role overrides change visibility and authority.
@pytest.mark.parametrize("expected", _EXPECTED, ids=_NAMES)
@pytest.mark.parametrize("kind", tuple(records.Kind))
def test_registry_rejects_fixed_role_wrong_kind(
    expected: records.RoleSpec, kind: records.Kind
) -> None:
    """Reject every different kind for each fixed role."""
    if kind == expected.kind:
        assert roles.registry_problems(_EXPECTED) == ()
        return
    invalid = tuple(
        replace(spec, kind=kind) if spec.name == expected.name else spec
        for spec in _EXPECTED
    )
    assert roles.registry_problems(invalid)


# A missing catalog tag or narrowed role schema rejects its documented specimen.
@pytest.mark.parametrize(("name", "tag"), _CONTRACTS)
def test_registered_schema_accepts_documented_seed(name: str, tag: str) -> None:
    """Connect every registered answer tag to the shared codec catalog."""
    spec = roles.role(name)
    expected = records.RoleAnswer(seed(tag))
    assert tag in codec.SCHEMAS
    assert codec.decode_answer(codec.encode_answer(expected), spec) == expected


# Widening a role's accepted payload set lets an unrelated answer pass.
@pytest.mark.parametrize(("name", "tag"), _CONTRACTS)
def test_registered_schema_rejects_different_payload(name: str, tag: str) -> None:
    """Reject a valid payload outside each registered role's schema set."""
    spec = roles.role(name)
    other = "review" if tag != "review" else "brief"
    text = codec.encode_answer(records.RoleAnswer(seed(other)))
    with pytest.raises(RecordError):
        codec.decode_answer(text, spec)
