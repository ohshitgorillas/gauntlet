# Copyright 2026 oh shit, gorillas!
"""Encode canonical domain records through a closed, versioned schema catalog."""

from __future__ import annotations

import json
import math
import re
from dataclasses import MISSING, fields, is_dataclass
from functools import singledispatch
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Protocol,
    TypeAliasType,
    get_args,
    get_origin,
    get_type_hints,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from dataclasses import Field
    from enum import StrEnum
    from typing import ClassVar

from gauntlet.core import causes, design, records, verdicts
from gauntlet.core.errors import RecordError
from gauntlet.core.records import Json, Payload, RoleAnswer, RoleSpec, State, TraceRow


class _Dataclass(Protocol):
    """Describe the metadata exposed by every catalog dataclass."""

    __dataclass_fields__: ClassVar[dict[str, Field[object]]]


FORMAT: int = 1
_CLASS: type[object] = type
_ALIAS_CLASS: type[TypeAliasType] = TypeAliasType
_VARIADIC_TUPLE_ARITY = 2
_ROOT = "$"
_DATA = "$.data"
_SCHEMA = "$.schema"
_FORMAT = "$.format"
_PAYLOADS: dict[str, type[Payload]] = {
    "brief": records.Brief,
    "discovery": records.Discovery,
    "outline": records.Outline,
    "design": design.Design,
    "plan": records.Plan,
    "spec": records.Spec,
    "check-set": records.CheckSet,
    "spec-judgment": records.SpecJudgment,
    "evidence": records.Evidence,
    "tests": records.TestAnswer,
    "red-judgment": records.RedJudgment,
    "build": records.BuildAnswer,
    "review": records.ReviewAnswer,
    "causes": records.CausesAnswer,
    "bailiff": records.BailiffAnswer,
    "survey": verdicts.Survey,
    "audit": records.AuditAnswer,
    "epic": records.EpicAnswer,
}
SCHEMAS: tuple[str, ...] = tuple(_PAYLOADS)
_RECORDS: tuple[type[_Dataclass], ...] = (
    *_PAYLOADS.values(),
    verdicts.Anchor,
    verdicts.Finding,
    verdicts.Candidate,
    verdicts.CoreMissing,
    design.Stub,
    design.Module,
    design.Home,
    design.Step,
    design.Choice,
    causes.Cause,
    causes.FixStep,
    causes.DesignChange,
    records.Citation,
    records.PlanStep,
    records.SpecLine,
    records.Collateral,
    records.SpecDefect,
    records.Check,
    records.SpecRuling,
    records.TestBinding,
    records.RedLine,
    records.TestSnapshot,
    records.Pin,
    records.CollateralRuling,
    records.AuditRow,
    records.EpicJob,
    records.RoleAnswer,
    records.Caps,
    records.TestCommand,
    records.InterfaceCommand,
    records.RoleSetting,
    records.Config,
    records.RoleSpec,
    records.StageRule,
    records.CheckRow,
    records.Bypass,
    records.Amendment,
    records.OwnerUse,
    records.TraceRow,
    records.Round,
    records.Artifact,
    records.StepRun,
    records.CauseRound,
    records.Effect,
    records.GitIntent,
    records.RecoveryPoint,
    records.Pending,
    records.State,
    records.Action,
    records.Tick,
    records.Answered,
    records.Checked,
    records.Approved,
    records.Baselined,
    records.Restored,
    records.Reconciled,
    records.Recovered,
    records.Completed,
    records.Failed,
    records.Receipt,
)
_ENUMS: tuple[type[StrEnum], ...] = (
    verdicts.Category,
    records.Stage,
    records.Shape,
    records.Verdict,
    records.Loop,
    records.Kind,
    records.TestStart,
    records.RedVerdict,
    records.BuildStatus,
)
_CHOICES: dict[tuple[type[object], str], tuple[str, ...]] = {
    (records.CheckSet, "disposition"): ("continue", "refuse", "escalate-leave"),
    (records.Pin, "verdict"): ("pin", "unpinned", "could-not-judge"),
    (records.CollateralRuling, "verdict"): ("held", "altered", "could-not-judge"),
    (records.AuditRow, "verdict"): (
        "valid",
        "strike",
        "amend",
        "note",
        "could-not-judge",
    ),
    (records.State, "status"): ("active", "waiting", "stopped", "landed"),
    (records.TraceRow, "outcome"): (
        "starting",
        "running",
        "complete",
        "failed",
        "interrupted",
    ),
}


def _json_scalar(value: object, location: str) -> Json:
    """Validate finite JSON values recursively, retaining exact scalar types."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise RecordError(location, "expected a finite JSON value")


def _json_array(value: list[object], location: str) -> Json:
    """Validate every item of a JSON array."""
    return [_json(child, f"{location}[{i}]") for i, child in enumerate(value)]


def _json_object(value: dict[object, object], location: str) -> Json:
    """Validate JSON object keys and their values."""
    result: dict[str, Json] = {}
    for key, child in value.items():
        if not isinstance(key, str):
            raise RecordError(location, "JSON keys must be strings")
        result[key] = _json(child, f"{location}.{key}")
    return result


def _json_dispatch() -> Callable[[object, str], Json]:
    """Build the runtime dispatcher behind typed JSON validation."""
    dispatch = singledispatch(_json_scalar)
    dispatch.register(list, _json_array)
    dispatch.register(dict, _json_object)
    return dispatch


_json = _json_dispatch()


def json_value(value: object) -> Json:
    """Validate a JSON-compatible value."""
    return _json(value, "$")


def _encode_record(value: object) -> Json:
    """Map canonical records and tuples to their JSON representation."""
    if is_dataclass(value) and not isinstance(value, _CLASS):
        record_fields: tuple[Field[object], ...] = fields(value)
        result: dict[str, Json] = {}
        for field in record_fields:
            child: object = getattr(value, field.name)
            result[field.name] = _encode(child)
        return result
    return json_value(value)


def _encode_tuple(value: tuple[object, ...]) -> Json:
    """Encode record tuples as JSON arrays."""
    return [_encode(child) for child in value]


def _encode_dispatch() -> Callable[[object], Json]:
    """Build the runtime dispatcher behind record encoding."""
    dispatch = singledispatch(_encode_record)
    dispatch.register(tuple, _encode_tuple)
    return dispatch


_encode = _encode_dispatch()


def _hints(cls: type[object]) -> tuple[tuple[str, object], ...]:
    """Resolve trusted source annotations against the canonical domain catalog."""
    localns: dict[str, object] = {"Cause": causes.Cause}
    hints: dict[str, object] = get_type_hints(cls, localns=localns)
    return tuple(hints.items())


def _field_constraints(cls: type[object], name: str) -> dict[str, Json]:
    """Describe field restrictions shared by decoding and schema export."""
    constraints: dict[str, Json] = {}
    choices = _CHOICES.get((cls, name))
    if choices is not None:
        constraints["enum"] = list(choices)
    if name in ("id", "job"):
        constraints["pattern"] = r"\S"
    if cls is verdicts.Anchor and name == "line":
        constraints["minimum"] = 1
    return constraints


def _field_check(cls: type[object], name: str, value: Json, location: str) -> None:
    """Enforce the exported field constraints on incoming wire values."""
    constraints = _field_constraints(cls, name)
    choices = constraints.get("enum")
    if isinstance(choices, list) and value not in choices:
        raise RecordError(location, "unknown literal value")
    pattern = constraints.get("pattern")
    if (
        isinstance(pattern, str)
        and isinstance(value, str)
        and re.search(pattern, value) is None
    ):
        raise RecordError(location, "identifier must not be empty")
    minimum = constraints.get("minimum")
    if isinstance(minimum, int) and isinstance(value, int) and value < minimum:
        raise RecordError(location, "line must be positive")


def _decode(value: Json, annotation: object, location: str) -> object:
    """Decode one trusted catalog type without coercion or dynamic imports."""
    if isinstance(annotation, _ALIAS_CLASS):
        aliased: object = annotation.__value__
        return _decode(value, aliased, location)
    origin: object = get_origin(annotation)
    args: tuple[object, ...] = get_args(annotation)
    if origin is UnionType:
        for member in args:
            try:
                decoded = _decode(value, member, location)
            except RecordError:
                continue
            return decoded
        raise RecordError(location, "value matches no declared variant")
    if origin is tuple:
        if not isinstance(value, list):
            raise RecordError(location, "expected an array")
        if len(args) == _VARIADIC_TUPLE_ARITY and args[1] is Ellipsis:
            return tuple(
                _decode(child, args[0], f"{location}[{i}]")
                for i, child in enumerate(value)
            )
        if len(value) != len(args):
            raise RecordError(location, "wrong tuple length")
        return tuple(
            _decode(child, member, f"{location}[{i}]")
            for i, (child, member) in enumerate(zip(value, args, strict=True))
        )
    enum_cls = next((cls for cls in _ENUMS if annotation is cls), None)
    if enum_cls is not None:
        if not isinstance(value, str):
            raise RecordError(location, "expected an enum string")
        try:
            decoded_enum: object = enum_cls(value)
        except ValueError as error:
            raise RecordError(location, "unknown enum value") from error
        return decoded_enum
    record_cls = next((cls for cls in _RECORDS if annotation is cls), None)
    if record_cls is not None:
        return _decode_record(value, record_cls, location)
    if annotation is type(None) and value is None:
        return None
    if (annotation is str or annotation is int or annotation is bool) and type(
        value
    ) is annotation:
        return value
    raise RecordError(location, "wrong primitive type")


def _decode_record[T: _Dataclass](value: Json, cls: type[T], location: str) -> T:
    """Reconstruct a catalog record, applying only its declared defaults."""
    if not isinstance(value, dict):
        raise RecordError(location, "expected a record object")
    record_fields: tuple[Field[object], ...] = fields(cls)
    names = {field.name for field in record_fields}
    for name in value:
        if name not in names:
            path = f"{location}.{name}"
            raise RecordError(path, "unknown field")
    hints = dict(_hints(cls))
    kwargs: dict[str, object] = {}
    for field in record_fields:
        path = f"{location}.{field.name}"
        if field.name not in value:
            if field.default is MISSING and field.default_factory is MISSING:
                raise RecordError(path, "missing required field")
            continue
        child = value[field.name]
        _field_check(cls, field.name, child, path)
        kwargs[field.name] = _decode(child, hints[field.name], path)
    return cls(**kwargs)


def _pairs(pairs: list[tuple[str, Json]]) -> dict[str, Json]:
    """Reject duplicate keys even in nested JSON objects."""
    result: dict[str, Json] = {}
    for key, value in pairs:
        if key in result:
            location = f"$.{key}"
            raise RecordError(location, "duplicate JSON key")
        result[key] = value
    return result


def _envelope(text: str, permitted: tuple[str, ...]) -> tuple[str, Json]:
    """Validate exact envelope keys, format and requested schema."""
    try:
        parsed: object = json.loads(text, object_pairs_hook=_pairs)
    except ValueError as error:
        raise RecordError(_ROOT, "malformed JSON") from error
    value = json_value(parsed)
    if not isinstance(value, dict) or set(value) != {"format", "schema", "data"}:
        raise RecordError(_ROOT, "expected exactly format, schema and data")
    if type(value["format"]) is not int or value["format"] != FORMAT:
        raise RecordError(_FORMAT, "unknown record format")
    schema = value["schema"]
    if not isinstance(schema, str) or schema not in permitted:
        raise RecordError(_SCHEMA, "unexpected schema tag")
    return schema, value["data"]


def _wire(value: object, schema: str) -> str:
    """Render deterministic compact Unicode JSON."""
    envelope: dict[str, Json] = {
        "format": FORMAT,
        "schema": schema,
        "data": _encode(value),
    }
    return json.dumps(
        envelope,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _tag(payload: Payload) -> str:
    """Find the unique canonical payload tag."""
    return next(tag for tag, cls in _PAYLOADS.items() if type(payload) is cls)


def encode_state(state: State) -> str:
    """Encode a versioned state envelope."""
    return _wire(state, "state")


def decode_state(text: str) -> State:
    """Decode a versioned state envelope."""
    _, data = _envelope(text, ("state",))
    return _decode_record(data, State, _DATA)


def encode_trace(trace: TraceRow) -> str:
    """Encode one newline-terminated trace envelope."""
    return _wire(trace, "trace") + "\n"


def decode_trace(text: str) -> TraceRow:
    """Decode a trace envelope."""
    _, data = _envelope(text, ("trace",))
    return _decode_record(data, TraceRow, _DATA)


def encode_answer(answer: RoleAnswer) -> str:
    """Encode an answer using its payload's canonical schema."""
    return _wire(answer, _tag(answer.payload))


def decode_answer(text: str, spec: RoleSpec) -> RoleAnswer:
    """Decode only the role's permitted payload schemas."""
    schema, data = _envelope(text, spec.schemas)
    if schema not in _PAYLOADS or not isinstance(data, dict):
        raise RecordError(_DATA, "expected role answer")
    if set(data) - {"payload", "spec_defect"} or "payload" not in data:
        raise RecordError(_DATA, "invalid answer fields")
    payload = _decode_record(data["payload"], _PAYLOADS[schema], "$.data.payload")
    defect_data = data.get("spec_defect")
    defect = (
        None
        if defect_data is None
        else _decode_record(defect_data, records.SpecDefect, "$.data.spec_defect")
    )
    return RoleAnswer(payload, defect)


def _schema(annotation: object) -> Json:
    """Export the same trusted type tree used by decoding."""
    if isinstance(annotation, _ALIAS_CLASS):
        aliased: object = annotation.__value__
        return _schema(aliased)
    origin: object = get_origin(annotation)
    args: tuple[object, ...] = get_args(annotation)
    if origin is UnionType:
        return {"anyOf": [_schema(member) for member in args]}
    if origin is tuple:
        if len(args) == _VARIADIC_TUPLE_ARITY and args[1] is Ellipsis:
            return {"type": "array", "items": _schema(args[0])}
        return {
            "type": "array",
            "prefixItems": [_schema(member) for member in args],
            "minItems": len(args),
            "maxItems": len(args),
        }
    enum_cls = next((cls for cls in _ENUMS if annotation is cls), None)
    if enum_cls is not None:
        return {"type": "string", "enum": [member.value for member in enum_cls]}
    record_cls = next((cls for cls in _RECORDS if annotation is cls), None)
    if record_cls is not None:
        hints = dict(_hints(record_cls))
        properties: dict[str, Json] = {}
        required: list[Json] = []
        record_fields: tuple[Field[object], ...] = fields(record_cls)
        for field in record_fields:
            properties[field.name] = {
                "allOf": [
                    _schema(hints[field.name]),
                    _field_constraints(record_cls, field.name),
                ]
            }
            if field.default is MISSING and field.default_factory is MISSING:
                required.append(field.name)
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }
    primitives: dict[object, str] = {
        str: "string",
        int: "integer",
        bool: "boolean",
        type(None): "null",
    }
    return {"type": primitives[annotation]}


def answer_schema(spec: RoleSpec) -> Json:
    """Describe complete versioned answers for the role's permitted tags."""
    variants: list[Json] = []
    for tag in spec.schemas:
        if tag not in _PAYLOADS:
            raise RecordError(_SCHEMA, "unknown schema tag")
        variants.append(
            {
                "type": "object",
                "properties": {
                    "format": {"const": FORMAT},
                    "schema": {"const": tag},
                    "data": {
                        "type": "object",
                        "properties": {
                            "payload": _schema(_PAYLOADS[tag]),
                            "spec_defect": _schema(records.SpecDefect | None),
                        },
                        "required": ["payload"],
                        "additionalProperties": False,
                    },
                },
                "required": ["format", "schema", "data"],
                "additionalProperties": False,
            }
        )
    return {"anyOf": variants}


def encode_document(payload: Payload) -> str:
    """Encode a payload in one standalone JSON fence."""
    return "```json\n" + _wire(payload, _tag(payload)) + "\n```\n"


def decode_document(text: str, schema: str) -> Payload:
    """Require exact fence framing and the supplied payload tag."""
    framed = text.removesuffix("\n")
    if not framed.startswith("```json\n") or not framed.endswith("\n```"):
        raise RecordError(_ROOT, "expected standalone JSON fence")
    _, data = _envelope(framed[len("```json\n") : -len("\n```")], (schema,))
    if schema not in _PAYLOADS:
        raise RecordError(_SCHEMA, "unknown schema tag")
    return _decode_record(data, _PAYLOADS[schema], _DATA)
