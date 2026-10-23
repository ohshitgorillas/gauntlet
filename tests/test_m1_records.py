# Copyright 2026 oh shit, gorillas!
"""Decoded record contracts from m1-core-records-design, Modules and codec."""

import re
from dataclasses import FrozenInstanceError
from enum import StrEnum
from typing import ClassVar, Protocol, TypeGuard, runtime_checkable

import pytest

from gauntlet.core import codec, records
from gauntlet.core.design import Choice, Home, Module, Step, Stub
from gauntlet.core.verdicts import Category
from tests.support.answers import (
    anchor,
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

_TAGS = (
    "brief",
    "discovery",
    "outline",
    "design",
    "plan",
    "spec",
    "check-set",
    "spec-judgment",
    "evidence",
    "tests",
    "red-judgment",
    "build",
    "review",
    "causes",
    "bailiff",
    "survey",
    "audit",
    "epic",
)


@runtime_checkable
class _Record(Protocol):
    __dataclass_fields__: ClassVar[dict[str, object]]


def _is_tuple(value: object) -> TypeGuard[tuple[object, ...]]:
    return isinstance(value, tuple)


def _preserved(actual: object, expected: object) -> None:
    """Check exact nested types and payloads, including every frozen field."""
    assert type(actual) is type(expected)
    assert actual == expected
    if isinstance(expected, _Record):
        for name in expected.__dataclass_fields__:
            actual_field: object = getattr(actual, name)
            expected_field: object = getattr(expected, name)
            _preserved(actual_field, expected_field)
            with pytest.raises(FrozenInstanceError):
                setattr(actual, name, None)
            with pytest.raises(FrozenInstanceError):
                delattr(actual, name)
    elif _is_tuple(expected):
        assert _is_tuple(actual)
        for left, right in zip(actual, expected, strict=True):
            _preserved(left, right)


# Dropping a seed field, decoding tuples as lists, or returning mutable records breaks this.
@pytest.mark.parametrize("tag", _TAGS)
def test_decoded_seed_preserves_fields_defaults_and_frozen_records(tag: str) -> None:
    """Every documented specimen survives document decoding in its canonical type."""
    expected = seed(tag)
    actual = codec.decode_document(codec.encode_document(expected), tag)
    _preserved(actual, expected)


# Silently replacing nondefault nested fields with specimen defaults breaks these answers.
@pytest.mark.parametrize(
    ("tag", "payload"),
    [
        ("brief", records.Brief("请求\nwith exact whitespace  ")),
        (
            "discovery",
            records.Discovery(
                (records.Citation("claim two", anchor("./a/../b.py", 9)),)
            ),
        ),
        (
            "outline",
            records.Outline(
                (Step("s2", ("./b.py", "a.py"), "seam-builder"),),
                ("z", "a"),
                shared_structure=True,
            ),
        ),
        (
            "design",
            design(
                modules=(
                    Module(
                        "./a/../b.py",
                        "a distinct job",
                        (Stub("f", "def f(): raise NotImplementedError"),),
                        (anchor("old.py", 7),),
                    ),
                ),
                homes=(Home("ownership", "./a/../b.py", "a second owner"),),
                order=(Step("s2", ("./a/../b.py",), "core-builder"),),
                choices=(Choice("Which?", "one", "two", "port callers"),),
            ),
        ),
        (
            "plan",
            records.Plan(
                (
                    records.PlanStep(
                        Step("s2", ("b.py",), "core-builder"),
                        ("S2", "S1"),
                        (Stub("f", "def f(): raise NotImplementedError"),),
                    ),
                )
            ),
        ),
        (
            "spec",
            records.Spec(
                (
                    records.SpecLine(
                        "S2",
                        "kept claim",
                        "observed bite",
                        records.TestStart.GREEN,
                        ("tests/test_b.py::test_b",),
                    ),
                ),
                (
                    records.Collateral(
                        "tests/test_a.py::test_a", "old assertion", "altered"
                    ),
                ),
            ),
        ),
        (
            "check-set",
            records.CheckSet(
                (
                    records.Check(
                        "c2",
                        records.Verdict.COULD_NOT_JUDGE,
                        "no evidence",
                        (anchor("b.py", 8),),
                    ),
                ),
                "escalate-leave",
            ),
        ),
        (
            "spec-judgment",
            records.SpecJudgment(
                (records.SpecRuling("S2", records.Verdict.FAIL, "claim differs"),)
            ),
        ),
        (
            "evidence",
            records.Evidence((records.Citation("measured twice", anchor("b.py", 8)),)),
        ),
        (
            "tests",
            records.TestAnswer(
                (
                    records.TestBinding(
                        "S2", ("tests/test_b.py::test_b", "tests/test_a.py::test_a")
                    ),
                ),
                ("S3",),
            ),
        ),
        (
            "red-judgment",
            records.RedJudgment(
                (
                    records.RedLine(
                        "S2",
                        records.RedVerdict.COULD_NOT_JUDGE,
                        ("tests/test_b.py::test_b",),
                    ),
                )
            ),
        ),
        (
            "build",
            records.BuildAnswer(
                "s2",
                records.BuildStatus.BLOCKED,
                "shared policy missing",
                missing(
                    candidate=candidate(keeps=("one behavior",), why="required"),
                    also=(anchor("b.py", 8),),
                ),
            ),
        ),
        (
            "review",
            records.ReviewAnswer(
                (finding(concern="ownership", also=(anchor("b.py", 8),)),)
            ),
        ),
        (
            "causes",
            records.CausesAnswer(
                (
                    cause(
                        id="c2",
                        concern="ownership",
                        findings=(finding(concern="ownership"),),
                    ),
                )
            ),
        ),
        (
            "bailiff",
            records.BailiffAnswer(
                (records.Pin("S2", "could-not-judge", "no proof"),),
                (
                    records.CollateralRuling(
                        "tests/test_a.py::test_a", "altered", "approved change"
                    ),
                ),
            ),
        ),
        (
            "survey",
            survey(
                findings=(finding(),),
                candidates=(candidate(why="required"),),
                sound=("one retained home",),
            ),
        ),
        (
            "audit",
            records.AuditAnswer(
                (
                    records.AuditRow(
                        "tests/test_b.py::test_b", "amend", "weaker assertion"
                    ),
                )
            ),
        ),
        (
            "epic",
            records.EpicAnswer(
                (records.EpicJob("j2", "second request", ("j1",), ("z", "a")),),
                "owner decision",
            ),
        ),
    ],
)
def test_decoded_answer_preserves_complete_nondefault_payload(
    tag: str, payload: records.Payload
) -> None:
    """Optional payload fields and spec defects survive alongside primary answers."""
    expected = records.RoleAnswer(
        payload,
        records.SpecDefect(
            "S2", "a different claim", (records.Citation("proof", anchor("b.py", 8)),)
        ),
    )
    spec = records.RoleSpec("reader", records.Kind.READER, (tag,))
    actual = codec.decode_answer(codec.encode_answer(expected), spec)
    _preserved(actual, expected)


# Dropping any persisted state/recovery/event field or inferring unknown metrics breaks this.
def test_decoded_state_preserves_complete_recovery_and_history() -> None:
    """Persisted state includes approvals, artifacts, checkpoints and all event variants."""
    payload = seed("spec")
    answer = records.RoleAnswer(payload)
    artifact = records.Artifact("spec", 3, answer)
    effect = records.Effect(
        "e1", records.Stage.BUILD, "build", "implementer", "s1", payload, (artifact,)
    )
    trace = records.TraceRow(
        "e1.launch.2", "implementer", "model-b", "high", None, "0.012300", "interrupted"
    )
    check = records.CheckRow(
        "check.2",
        records.Stage.BUILD,
        1,
        "unit tests",
        records.Verdict.COULD_NOT_JUDGE,
        "interrupted",
    )
    snapshot = records.TestSnapshot(
        "tests/test_a.py::test_a", "@decorator\ndef test_a():\n    assert True\n"
    )
    events: tuple[records.Answer, ...] = (
        records.Tick(),
        records.Answered("e1", 2, "implementer", answer, trace),
        records.Checked("e1", 2, (check,)),
        records.Approved("e1", 2, (("choice", "one"),), design()),
        records.Approved("e1", 2, (), None),
        records.Baselined("e1", 2, (snapshot,)),
        records.Recovered("e1", 2, records.Restored()),
        records.Recovered("e1", 2, records.Reconciled("abc123")),
        records.Completed("e1", 2, "abc123"),
        records.Completed("e1", 2, None),
        records.Failed("e1", 2, "startup failed"),
    )
    expected = state(
        job="j2",
        revision=7,
        shape=records.Shape.JOB,
        stage=records.Stage.BUILD,
        status="waiting",
        config=config(
            image="./Containerfile",
            tests=(records.TestCommand("unit", "pytest {ids}"),),
            gates="make verify",
            test_policy="docs/policy.md",
            interface=(records.InterfaceCommand("py", "stubgen {modules}"),),
            test_helpers=("tests/support",),
            protected=("policy.txt",),
            test_lint="lint tests",
            implementer_network=True,
            caps=records.Caps(1, 3, 4, 5, 6, 7, 8),
            roles=(
                records.RoleSetting("implementer", "model-b", "high"),
                records.RoleSetting("reviewer", None, None),
            ),
        ),
        candidate=candidate(keeps=("one behavior",), why="required"),
        copies=(anchor("./a/../b.py", 8),),
        artifacts=(artifact,),
        rounds=(records.Round(records.Loop.BUILD, 1),),
        steps=(records.StepRun("s1", 2, "abc123", "diff --git a/b b/b\n", "partial"),),
        owners=(("ownership", "./a/../b.py"),),
        cause_rounds=(records.CauseRound("c1", 1),),
        held=("s2",),
        checks=(check,),
        bypasses=(records.Bypass(records.Stage.REVIEW, "owner", "approved omission"),),
        amendments=(records.Amendment(("S2", "S1"), "owner amended"),),
        controls=(records.OwnerUse("retry", records.Stage.BUILD, "explicit request"),),
        launches=(trace,),
        pending=(
            records.Pending(
                effect,
                "recovering",
                trace.id,
                2,
                records.RecoveryPoint(
                    2,
                    "opaque workspace",
                    records.GitIntent("./repo", "refs/heads/work", "abc123", "def456"),
                ),
            ),
            records.Pending(
                records.Effect("e2", records.Stage.BUILD, "stop", None, None, None, ()),
                "ready",
                None,
            ),
        ),
        receipts=tuple(records.Receipt("e1", event) for event in events),
        baselines=(snapshot,),
    )
    actual = codec.decode_state(codec.encode_state(expected))
    _preserved(actual, expected)
    expected_revision = 7
    expected_artifact_revision = 3
    expected_attempt = 2
    assert actual.revision == expected_revision
    assert actual.shape is records.Shape.JOB
    assert actual.stage is records.Stage.BUILD
    assert actual.artifacts[0].revision == expected_artifact_revision
    assert actual.rounds[0].loop is records.Loop.BUILD
    assert actual.rounds[0].used == 1
    assert actual.steps[0].attempt == expected_attempt
    assert actual.steps[0].base_commit == "abc123"
    assert actual.steps[0].partial_diff == "diff --git a/b b/b\n"
    assert actual.cause_rounds == (records.CauseRound("c1", 1),)
    assert actual.checks[0].stage is records.Stage.BUILD
    assert actual.checks[0].round == 1
    assert actual.checks[0].verdict is records.Verdict.COULD_NOT_JUDGE
    assert actual.checks[0].evidence == "interrupted"
    assert actual.bypasses[0].stage is records.Stage.REVIEW
    assert actual.bypasses[0].detail == "approved omission"
    assert actual.amendments == (records.Amendment(("S2", "S1"), "owner amended"),)
    assert actual.controls[0].stage is records.Stage.BUILD
    assert actual.controls[0].detail == "explicit request"
    assert actual.launches[0].model == "model-b"
    assert actual.launches[0].effort == "high"
    assert actual.pending[0].effect.stage is records.Stage.BUILD
    assert actual.pending[0].effect.input == payload
    assert actual.pending[0].effect.inputs == (artifact,)
    assert actual.pending[0].launch_id == "e1.launch.2"
    recovery = actual.pending[0].recovery
    assert recovery is not None
    assert recovery.workspace == "opaque workspace"
    assert recovery.git is not None
    assert recovery.git.repository == "./repo"
    checked = actual.receipts[2].event
    assert isinstance(checked, records.Checked)
    assert checked.rows == (check,)
    recovered = actual.receipts[7].event
    assert isinstance(recovered, records.Recovered)
    assert isinstance(recovered.result, records.Reconciled)
    assert recovered.result.commit == "abc123"
    completed = actual.receipts[8].event
    assert isinstance(completed, records.Completed)
    assert completed.commit == "abc123"


# Replacing optional constructor defaults or enum members during decoding breaks this.
def test_decoded_default_state_retains_literal_defaults() -> None:
    """Default caps remain two, optional collections empty and unknown fields absent."""
    actual = codec.decode_state(codec.encode_state(state()))
    assert actual.config.caps == records.Caps(2, 2, 2, 2, 2, 2, 2)
    assert actual.config.test_helpers == ()
    assert actual.config.protected == ()
    assert actual.config.test_lint is None
    assert actual.config.implementer_network is False
    assert actual.config.roles == ()
    assert actual.receipts == ()
    assert actual.baselines == ()
    _preserved(actual, state())


def _literal_json(value: object) -> records.Json:
    """Translate spec-pinned input records independently of the product encoder."""
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if _is_tuple(value):
        return [_literal_json(item) for item in value]
    assert isinstance(value, _Record)
    result: dict[str, records.Json] = {}
    for name in value.__dataclass_fields__:
        field: object = getattr(value, name)
        result[name] = _literal_json(field)
    return result


def _intersect_bounds(
    bounds: tuple[tuple[records.Json, ...] | None, ...],
) -> tuple[records.Json, ...] | None:
    """Unknown bounds are universal sets, so finite conjuncts still bound a value."""
    finite = tuple(bound for bound in bounds if bound is not None)
    if not finite:
        return None
    return tuple(item for item in finite[0] if all(item in bound for bound in finite))


def _finite_field_bound(
    schema: records.Json, path: tuple[str, ...], root: records.Json
) -> tuple[records.Json, ...] | None:
    """Overapproximate possible field values; None means no finite bound is proved.

    Alternatives use union even for oneOf: complete-instance validation decides
    exclusive membership afterward, keeping other fields' discriminators intact.
    """
    if isinstance(schema, bool):
        return None if schema else ()
    assert isinstance(schema, dict)
    bounds: list[tuple[records.Json, ...] | None] = []
    reference = schema.get("$ref")
    if isinstance(reference, str):
        assert reference.startswith("#/")
        target = root
        for component in reference.removeprefix("#/").split("/"):
            assert isinstance(target, dict)
            target = target[component.replace("~1", "/").replace("~0", "~")]
        bounds.append(_finite_field_bound(target, path, root))
    if not path:
        enumeration = schema.get("enum")
        if isinstance(enumeration, list):
            bounds.append(tuple(enumeration))
        if "const" in schema:
            bounds.append((schema["const"],))
    elif path[0] == "[]":
        bounds.append(_finite_field_bound(schema.get("items", True), path[1:], root))
    else:
        properties = schema.get("properties", {})
        assert isinstance(properties, dict)
        child = properties.get(path[0], schema.get("additionalProperties", True))
        bounds.append(_finite_field_bound(child, path[1:], root))
    for keyword in ("allOf", "anyOf", "oneOf"):
        branches = schema.get(keyword)
        if not isinstance(branches, list):
            continue
        alternatives = tuple(
            _finite_field_bound(branch, path, root) for branch in branches
        )
        if keyword == "allOf":
            bounds.append(_intersect_bounds(alternatives))
        elif any(bound is None for bound in alternatives):
            bounds.append(None)
        else:
            bounds.append(
                tuple(
                    item
                    for bound in alternatives
                    if bound is not None
                    for item in bound
                )
            )
    return _intersect_bounds(tuple(bounds))


def _schema_accepts(
    schema: records.Json, value: records.Json, root: records.Json
) -> bool:
    """Evaluate complete instances; never project away a branch discriminator."""
    if isinstance(schema, bool):
        return schema
    assert isinstance(schema, dict)
    reference = schema.get("$ref")
    if isinstance(reference, str):
        assert reference.startswith("#/")
        target = root
        for component in reference.removeprefix("#/").split("/"):
            assert isinstance(target, dict)
            target = target[component.replace("~1", "/").replace("~0", "~")]
        if not _schema_accepts(target, value, root):
            return False
    kind = schema.get("type")
    kinds = kind if isinstance(kind, list) else [kind]
    actual = (
        "null"
        if value is None
        else "boolean"
        if isinstance(value, bool)
        else "string"
        if isinstance(value, str)
        else "object"
        if isinstance(value, dict)
        else "array"
        if isinstance(value, list)
        else "integer"
        if isinstance(value, int)
        else "number"
    )
    if (
        kind is not None
        and actual not in kinds
        and not (actual == "integer" and "number" in kinds)
    ):
        return False
    enumeration = schema.get("enum")
    if isinstance(enumeration, list) and value not in enumeration:
        return False
    if "const" in schema and value != schema["const"]:
        return False
    for keyword in ("allOf", "anyOf", "oneOf"):
        branches = schema.get(keyword)
        if isinstance(branches, list):
            matches = tuple(_schema_accepts(branch, value, root) for branch in branches)
            if keyword == "allOf" and not all(matches):
                return False
            if keyword == "anyOf" and not any(matches):
                return False
            if keyword == "oneOf" and sum(matches) != 1:
                return False
    if "if" in schema:
        branch = "then" if _schema_accepts(schema["if"], value, root) else "else"
        if not _schema_accepts(schema.get(branch, True), value, root):
            return False
    if "not" in schema and _schema_accepts(schema["not"], value, root):
        return False
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        assert isinstance(properties, dict)
        assert isinstance(required, list)
        if any(name not in value for name in required if isinstance(name, str)):
            return False
        additional = schema.get("additionalProperties", True)
        if any(
            not _schema_accepts(properties.get(name, additional), child, root)
            for name, child in value.items()
        ):
            return False
    if isinstance(value, list):
        prefix = schema.get("prefixItems", [])
        assert isinstance(prefix, list)
        if any(
            not _schema_accepts(
                prefix[index] if index < len(prefix) else schema.get("items", True),
                child,
                root,
            )
            for index, child in enumerate(value)
        ):
            return False
    if isinstance(value, (str, list)):
        minimum = schema.get("minLength" if isinstance(value, str) else "minItems")
        maximum = schema.get("maxLength" if isinstance(value, str) else "maxItems")
        if isinstance(minimum, int) and len(value) < minimum:
            return False
        if isinstance(maximum, int) and len(value) > maximum:
            return False
    pattern = schema.get("pattern")
    if (
        isinstance(value, str)
        and isinstance(pattern, str)
        and re.search(pattern, value) is None
    ):
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        for keyword in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
            bound = schema.get(keyword)
            if isinstance(bound, (int, float)) and (
                (keyword == "minimum" and value < bound)
                or (keyword == "maximum" and value > bound)
                or (keyword == "exclusiveMinimum" and value <= bound)
                or (keyword == "exclusiveMaximum" and value >= bound)
            ):
                return False
    return True


def _schema_probe(tag: str) -> dict[str, records.Json]:
    """Use documented constructors and pinned specimens, including nonempty rows."""
    payload = seed(tag)
    if tag == "review":
        payload = records.ReviewAnswer((finding(),))
    elif tag == "survey":
        payload = survey(findings=(finding(),))
    elif tag == "bailiff":
        payload = records.BailiffAnswer(
            (records.Pin("S1", "pin", "one reason"),),
            (records.CollateralRuling("test_a", "held", "one reason"),),
        )
    return {
        "format": 1,
        "schema": tag,
        "data": _literal_json(records.RoleAnswer(payload)),
    }


def _probe_field(value: records.Json, path: tuple[str, ...]) -> dict[str, records.Json]:
    """Find the containing record without projecting the schema."""
    if len(path) == 1:
        assert isinstance(value, dict)
        return value
    if path[0] == "[]":
        assert isinstance(value, list)
        return _probe_field(value[0], path[1:])
    assert isinstance(value, dict)
    return _probe_field(value[path[0]], path[1:])


# Exporting a missing, misspelled or extra member in a payload enum breaks this.
@pytest.mark.parametrize(
    ("tag", "field", "expected"),
    [
        ("spec", ("lines", "[]", "start"), frozenset({"red", "green"})),
        (
            "check-set",
            ("checks", "[]", "verdict"),
            frozenset({"pass", "fail", "could-not-judge"}),
        ),
        (
            "spec-judgment",
            ("rulings", "[]", "verdict"),
            frozenset({"pass", "fail", "could-not-judge"}),
        ),
        (
            "red-judgment",
            ("lines", "[]", "verdict"),
            frozenset({"red", "error", "green", "invalid", "could-not-judge"}),
        ),
        ("build", ("status",), frozenset({"complete", "partial", "blocked"})),
        (
            "review",
            ("findings", "[]", "category"),
            frozenset({"defect", "copy", "own-core", "drift", "missing"}),
        ),
        (
            "causes",
            ("causes", "[]", "findings", "[]", "category"),
            frozenset({"defect", "copy", "own-core", "drift", "missing"}),
        ),
        (
            "survey",
            ("findings", "[]", "category"),
            frozenset({"defect", "copy", "own-core", "drift", "missing"}),
        ),
        (
            "bailiff",
            ("pins", "[]", "verdict"),
            frozenset({"pin", "unpinned", "could-not-judge"}),
        ),
        (
            "bailiff",
            ("collateral", "[]", "verdict"),
            frozenset({"held", "altered", "could-not-judge"}),
        ),
        (
            "audit",
            ("rows", "[]", "verdict"),
            frozenset({"valid", "strike", "amend", "note", "could-not-judge"}),
        ),
        (
            "check-set",
            ("disposition",),
            frozenset({"continue", "refuse", "escalate-leave"}),
        ),
    ],
)
def test_answer_schema_exports_exact_payload_enums(
    tag: str, field: tuple[str, ...], expected: frozenset[str]
) -> None:
    """Schema constraints carry exactly the design's enum and literal verdict choices."""
    exported = codec.answer_schema(
        records.RoleSpec("reader", records.Kind.READER, (tag,))
    )
    probe = _schema_probe(tag)
    path = ("data", "payload", *field)
    target = _probe_field(probe, path)
    choices = _finite_field_bound(exported, path, exported)
    assert choices is not None
    accepted: set[str] = set()
    for choice in (*choices, *expected):
        target[path[-1]] = choice
        if _schema_accepts(exported, probe, exported):
            assert isinstance(choice, str)
            accepted.add(choice)
    assert accepted == expected


# Enum identities and wire values are durable persisted record contracts.
@pytest.mark.parametrize(
    ("members", "values"),
    [
        (
            (
                Category.DEFECT,
                Category.COPY,
                Category.OWN_CORE,
                Category.DRIFT,
                Category.MISSING,
            ),
            (
                "defect",
                "copy",
                "own-core",
                "drift",
                "missing",
            ),
        ),
        (
            (
                records.Stage.BRIEF,
                records.Stage.DISCOVERY,
                records.Stage.OUTLINE,
                records.Stage.DESIGN,
                records.Stage.PLAN,
                records.Stage.SPEC,
                records.Stage.STUBS,
                records.Stage.TESTS,
                records.Stage.RED_RUN,
                records.Stage.LOCK,
                records.Stage.BUILD,
                records.Stage.REVIEW,
                records.Stage.BAILIFF,
                records.Stage.LAND,
            ),
            (
                "brief",
                "discovery",
                "outline",
                "design",
                "plan",
                "spec",
                "stubs",
                "tests",
                "red-run",
                "lock",
                "build",
                "review",
                "bailiff",
                "land",
            ),
        ),
        (
            (
                records.Shape.JOB,
                records.Shape.TEST_AUDIT,
                records.Shape.STRUCTURE,
            ),
            (
                "job",
                "test-audit",
                "structure",
            ),
        ),
        (
            (
                records.Verdict.PASS,
                records.Verdict.FAIL,
                records.Verdict.COULD_NOT_JUDGE,
            ),
            (
                "pass",
                "fail",
                "could-not-judge",
            ),
        ),
        (
            (
                records.Loop.DESIGN,
                records.Loop.PLAN,
                records.Loop.SPEC,
                records.Loop.JUROR,
                records.Loop.BUILD,
                records.Loop.REVIEW,
                records.Loop.REOPEN,
            ),
            (
                "design",
                "plan",
                "spec",
                "juror",
                "build",
                "review",
                "reopen",
            ),
        ),
        (
            (
                records.Kind.JUDGE,
                records.Kind.READER,
                records.Kind.COORDINATOR,
                records.Kind.SCRATCH,
                records.Kind.TESTER,
                records.Kind.IMPLEMENTER,
            ),
            (
                "judge",
                "reader",
                "coordinator",
                "scratch",
                "tester",
                "implementer",
            ),
        ),
        (
            (
                records.TestStart.RED,
                records.TestStart.GREEN,
            ),
            (
                "red",
                "green",
            ),
        ),
        (
            (
                records.RedVerdict.RED,
                records.RedVerdict.ERROR,
                records.RedVerdict.GREEN,
                records.RedVerdict.INVALID,
                records.RedVerdict.COULD_NOT_JUDGE,
            ),
            (
                "red",
                "error",
                "green",
                "invalid",
                "could-not-judge",
            ),
        ),
        (
            (
                records.BuildStatus.COMPLETE,
                records.BuildStatus.PARTIAL,
                records.BuildStatus.BLOCKED,
            ),
            (
                "complete",
                "partial",
                "blocked",
            ),
        ),
    ],
)
def test_record_enum_wire_values(
    members: tuple[StrEnum, ...], values: tuple[str, ...]
) -> None:
    """Pin every documented member spelling against its stable wire value."""
    assert tuple(member.value for member in members) == values


# Direct field checks expose field swaps even when a record's equality hides them.
def test_decoded_discovery_citation_fields() -> None:
    """Keep citations in order with their exact claim and anchor."""
    value = records.Discovery((records.Citation("proof", anchor("b.py", 8)),))
    actual = codec.decode_document(codec.encode_document(value), "discovery")
    assert isinstance(actual, records.Discovery)
    assert actual.citations == (records.Citation("proof", anchor("b.py", 8)),)


def test_decoded_outline_and_plan_fields() -> None:
    """Retain area ordering, shared structure and each step's coverage/stubs."""
    step = Step("s2", ("b.py",), "core-builder")
    outline = records.Outline((step,), ("z", "a"), shared_structure=True)
    actual = codec.decode_document(codec.encode_document(outline), "outline")
    assert isinstance(actual, records.Outline)
    assert actual.areas == ("z", "a")
    assert actual.shared_structure is True
    stub = Stub("f", "def f(): raise NotImplementedError")
    plan = records.Plan((records.PlanStep(step, ("S2", "S1"), (stub,)),))
    decoded = codec.decode_document(codec.encode_document(plan), "plan")
    assert isinstance(decoded, records.Plan)
    assert decoded.steps[0].serves == ("S2", "S1")


def test_decoded_spec_and_defect_fields() -> None:
    """Retain measured bites and collateral assertions/dispositions."""
    payload = records.Spec(
        (records.SpecLine("S2", "claim", "measured bite", records.TestStart.RED),),
        (records.Collateral("test_a", "old assertion", "altered"),),
    )
    expected = records.RoleAnswer(
        payload,
        records.SpecDefect("S2", "defect", (records.Citation("proof", anchor()),)),
    )
    actual = codec.decode_answer(
        codec.encode_answer(expected),
        records.RoleSpec("reader", records.Kind.READER, ("spec",)),
    )
    assert isinstance(actual.payload, records.Spec)
    assert actual.payload.lines[0].bite == "measured bite"
    assert actual.payload.collateral[0].assertion == "old assertion"
    assert actual.payload.collateral[0].disposition == "altered"
    assert actual.spec_defect is not None
    assert actual.spec_defect.evidence == (records.Citation("proof", anchor()),)


def test_decoded_check_and_judgment_fields() -> None:
    """Retain an explicit inability and its cited evidence."""
    check = records.Check("c2", records.Verdict.COULD_NOT_JUDGE, "unknown", (anchor(),))
    value = records.CheckSet((check,), "escalate-leave")
    actual = codec.decode_document(codec.encode_document(value), "check-set")
    assert isinstance(actual, records.CheckSet)
    assert actual.checks[0].verdict is records.Verdict.COULD_NOT_JUDGE
    assert actual.checks[0].citations == (anchor(),)
    assert actual.disposition == "escalate-leave"
    judgment = records.SpecJudgment(
        (records.SpecRuling("S2", records.Verdict.FAIL, "differs"),)
    )
    decoded = codec.decode_document(codec.encode_document(judgment), "spec-judgment")
    assert isinstance(decoded, records.SpecJudgment)
    assert decoded.rulings[0].verdict is records.Verdict.FAIL


def test_decoded_evidence_and_test_binding_fields() -> None:
    """Keep measurement citations, bound test order and untestable claims."""
    value = records.Evidence((records.Citation("measured", anchor()),))
    actual = codec.decode_document(codec.encode_document(value), "evidence")
    assert isinstance(actual, records.Evidence)
    assert actual.measurements == (records.Citation("measured", anchor()),)
    tests = records.TestAnswer(
        (records.TestBinding("S2", ("test_b", "test_a")),), ("S3",)
    )
    decoded = codec.decode_document(codec.encode_document(tests), "tests")
    assert isinstance(decoded, records.TestAnswer)
    assert decoded.bindings[0].ids == ("test_b", "test_a")
    assert decoded.untestable == ("S3",)


def test_decoded_red_judgment_fields() -> None:
    """Keep the red-run verdict rather than inferring it from test names."""
    value = records.RedJudgment(
        (records.RedLine("S2", records.RedVerdict.ERROR, ("test_b",)),)
    )
    actual = codec.decode_document(codec.encode_document(value), "red-judgment")
    assert isinstance(actual, records.RedJudgment)
    assert actual.lines[0].verdict is records.RedVerdict.ERROR


def test_decoded_bailiff_and_audit_fields() -> None:
    """Keep each distinct pin, collateral ruling and audit verdict."""
    value = records.BailiffAnswer(
        (records.Pin("S2", "could-not-judge", "no proof"),),
        (records.CollateralRuling("test_a", "altered", "changed"),),
    )
    actual = codec.decode_document(codec.encode_document(value), "bailiff")
    assert isinstance(actual, records.BailiffAnswer)
    assert actual.pins[0].verdict == "could-not-judge"
    assert actual.collateral[0].verdict == "altered"
    audit = records.AuditAnswer((records.AuditRow("test_a", "amend", "weaker"),))
    decoded = codec.decode_document(codec.encode_document(audit), "audit")
    assert isinstance(decoded, records.AuditAnswer)
    assert decoded.rows[0].verdict == "amend"


def test_decoded_epic_job_fields() -> None:
    """Preserve dependencies and exact area order with the job brief."""
    value = records.EpicAnswer(
        (records.EpicJob("j2", "request", ("j1",), ("z", "a")),), None
    )
    actual = codec.decode_document(codec.encode_document(value), "epic")
    assert isinstance(actual, records.EpicAnswer)
    assert actual.jobs[0].brief == "request"
    assert actual.jobs[0].depends == ("j1",)
    assert actual.jobs[0].areas == ("z", "a")


def test_stage_rule_fields() -> None:
    """Keep stage succession, loop and required approval as supplied."""
    rule = records.StageRule(
        records.Stage.DESIGN, records.Stage.PLAN, records.Loop.DESIGN, approval=True
    )
    assert rule.stage is records.Stage.DESIGN
    assert rule.successor is records.Stage.PLAN
    assert rule.loop is records.Loop.DESIGN
    assert rule.approval is True
