# Copyright 2026 oh shit, gorillas!
"""Versioned wire contracts from m1-core-records-design, codec."""

import json
import re
from dataclasses import replace

import pytest

from gauntlet.core import codec, records
from gauntlet.core.errors import RecordError
from tests.support.answers import anchor, seed, state

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
_TRACE = records.TraceRow(
    "e1.launch.0", "architect", "模型", "high", 17, "0.0100", "complete"
)
_TRACE_DATA: dict[str, records.Json] = {
    "id": "e1.launch.0",
    "role": "architect",
    "model": "模型",
    "effort": "high",
    "tokens": 17,
    "cost": "0.0100",
    "outcome": "complete",
}


def _json_object(text: str) -> dict[str, records.Json]:
    value: object = json.loads(text)
    validated = codec.json_value(value)
    assert isinstance(validated, dict)
    return validated


def _state_data() -> dict[str, records.Json]:
    return {
        "job": "j1",
        "revision": 0,
        "shape": "structure",
        "stage": "design",
        "status": "active",
        "config": {
            "image": ".gauntlet/Containerfile",
            "tests": [{"directory": "tests", "run": "pytest {ids}"}],
            "gates": "make check",
            "test_policy": "docs/testing.md",
            "interface": [{"language": "py", "run": "stubgen -o {out} {modules}"}],
            "test_helpers": [],
            "protected": [],
            "test_lint": None,
            "implementer_network": False,
            "caps": {
                "design": 2,
                "plan": 2,
                "spec": 2,
                "juror": 2,
                "build": 2,
                "review": 2,
                "reopen": 2,
            },
            "roles": [],
        },
        "candidate": {
            "concern": "process running",
            "payoff": "one runner",
            "risk": "a caller breaks",
            "keeps": [],
            "why": None,
        },
        "copies": [],
        "artifacts": [],
        "rounds": [],
        "steps": [],
        "owners": [],
        "cause_rounds": [],
        "held": [],
        "checks": [],
        "bypasses": [],
        "amendments": [],
        "controls": [],
        "launches": [],
        "pending": [],
        "receipts": [],
        "baselines": [],
    }


def _trace_wire(data: records.Json = None) -> str:
    envelope: dict[str, records.Json] = {
        "format": 1,
        "schema": "trace",
        "data": _TRACE_DATA if data is None else data,
    }
    return json.dumps(envelope)


def _state_wire(**changes: records.Json) -> str:
    data = _state_data()
    data.update(changes)
    envelope: dict[str, records.Json] = {"format": 1, "schema": "state", "data": data}
    return json.dumps(envelope)


def _state_data_wire(data: dict[str, records.Json]) -> str:
    envelope: dict[str, records.Json] = {"format": 1, "schema": "state", "data": data}
    return json.dumps(envelope)


def _error(text: str, *, trace: bool = True) -> RecordError:
    decoder = codec.decode_trace if trace else codec.decode_state
    with pytest.raises(RecordError) as raised:
        decoder(text)
    assert raised.value.location.strip()
    assert raised.value.reason.strip()
    return raised.value


# Dropping a tag, adding a speculative schema or changing FORMAT breaks the catalog.
def test_catalog_and_format() -> None:
    """Expose exactly the documented payload catalog and usable codecs."""
    assert codec.FORMAT == 1
    assert len(codec.SCHEMAS) == len(set(codec.SCHEMAS))
    assert set(codec.SCHEMAS) == set(_TAGS)
    for tag in _TAGS:
        assert codec.decode_document(codec.encode_document(seed(tag)), tag) == seed(tag)


# Losing a payload, defect or nested tuple during answer serialization breaks equality.
@pytest.mark.parametrize("tag", _TAGS)
def test_answer_roundtrip(tag: str) -> None:
    """Preserve every payload and the independently supplied spec defect."""
    defect = records.SpecDefect(
        "S1", "claim", (records.Citation("証拠", anchor("./a/../b.py", 9)),)
    )
    answer = records.RoleAnswer(seed(tag), defect)
    spec = records.RoleSpec("test-reader", records.Kind.READER, (tag,))
    assert codec.decode_answer(codec.encode_answer(answer), spec) == answer


# Losing the payload tag or allowing another requested document tag breaks the contract.
@pytest.mark.parametrize("tag", _TAGS)
def test_document_roundtrip_and_exact_fence(tag: str) -> None:
    """Frame every document with its exact outer schema tag."""
    expected = seed(tag)
    text = codec.encode_document(expected)
    assert text.startswith("```json\n")
    assert text.endswith(("\n```\n", "\n```"))
    envelope = _json_object(text.removeprefix("```json\n").rstrip().removesuffix("```"))
    assert set(envelope) == {"format", "schema", "data"}
    assert envelope["format"] == 1
    assert envelope["schema"] == tag
    assert codec.decode_document(text, tag) == expected
    with pytest.raises(RecordError):
        codec.decode_document(text, "review" if tag != "review" else "brief")


# Changing wire field names, decimal spelling, key ordering or trace framing breaks this.
def test_trace_exact_envelope_and_compact_line() -> None:
    """Pin the complete trace envelope and its compact JSON line."""
    encoded = codec.encode_trace(_TRACE)
    assert _json_object(encoded) == {
        "format": 1,
        "schema": "trace",
        "data": _TRACE_DATA,
    }
    assert encoded.endswith("\n")
    assert encoded.count("\n") == 1
    assert encoded.rstrip() in (
        json.dumps(_json_object(encoded), ensure_ascii=False, separators=(",", ":")),
        json.dumps(_json_object(encoded), ensure_ascii=True, separators=(",", ":")),
    )
    assert codec.encode_trace(_TRACE) == encoded
    assert codec.decode_trace(_trace_wire()) == _TRACE
    assert codec.decode_trace(encoded) == _TRACE


# Defaulting unknown metrics to zero or losing reported values breaks trace identity.
@pytest.mark.parametrize("tokens", [None, 0, 371])
@pytest.mark.parametrize("cost", [None, "0", "0.000100"])
@pytest.mark.parametrize(
    "outcome", ["starting", "running", "complete", "failed", "interrupted"]
)
def test_trace_optional_metrics_and_outcomes(
    tokens: int | None, cost: str | None, outcome: str
) -> None:
    """Keep unknown metrics unknown and all declared outcomes explicit."""
    expected = replace(_TRACE, tokens=tokens, cost=cost, outcome=outcome)
    assert codec.decode_trace(codec.encode_trace(expected)) == expected


# Changing the outer state tag or silently normalizing identifiers loses persisted inputs.
def test_state_exact_envelope_and_literal_decode() -> None:
    """Decode literal persisted state and preserve exact supplied paths."""
    expected = state(copies=(anchor("./pkg/../exact.py", 4), anchor("z.py", 3)))
    encoded = codec.encode_state(expected)
    expected_data = _state_data()
    config_data = expected_data["config"]
    assert isinstance(config_data, dict)
    # m2-launcher-kinds-design.md:159-161: Config carries three defaulted settings.
    config_data["readiness_timeout_seconds"] = 10
    config_data["proxy_limits"] = {
        "header_bytes": 65536,
        "body_bytes": 33554432,
        "connections": 8,
    }
    config_data["proxy_extra_routes"] = []
    expected_data["copies"] = [
        {"path": "./pkg/../exact.py", "line": 4},
        {"path": "z.py", "line": 3},
    ]
    assert _json_object(encoded) == {
        "format": 1,
        "schema": "state",
        "data": expected_data,
    }
    assert codec.decode_state(encoded) == expected
    assert codec.decode_state(_state_wire()) == state()
    assert codec.encode_state(expected) == encoded


# The wire requires exactly these envelope fields regardless of JSON member ordering.
@pytest.mark.parametrize(
    "text",
    [
        "{}",
        "[]",
        "null",
        "1",
        "true",
        '"trace"',
        json.dumps(dict[str, records.Json](schema="trace", data=_TRACE_DATA)),
        json.dumps(dict[str, records.Json](format=1, data=_TRACE_DATA)),
        '{"format":1,"schema":"trace"}',
        *[
            json.dumps(
                dict[str, records.Json](
                    format=version, schema="trace", data=_TRACE_DATA
                )
            )
            for version in (2, True, 1.0)
        ],
        *[
            json.dumps(dict[str, records.Json](format=1, schema=tag, data=_TRACE_DATA))
            for tag in ("unknown", "state")
        ],
        json.dumps(
            dict[str, records.Json](
                format=1, schema="trace", data=_TRACE_DATA, extra=None
            )
        ),
        '{"format":1,' + _trace_wire().removeprefix("{"),
        _trace_wire().replace('"id":', '"id":"e1.launch.0","id":', 1),
        "",
        "{",
        '{"format":1,}',
        '{"format":NaN}',
        '{"format":Infinity}',
        '{"format":-Infinity}',
        "{}{}",
    ],
)
def test_malformed_envelopes(text: str) -> None:
    """Reject malformed, incompatible and duplicate-key JSON envelopes."""
    _error(text)


# Accepting wrong primitive types, missing fields or undeclared outcomes violates the schema.
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", ""),
        ("id", None),
        ("id", 3),
        ("role", False),
        ("model", []),
        ("effort", {}),
        ("tokens", True),
        ("tokens", 1.5),
        ("tokens", "17"),
        ("cost", 0.1),
        ("cost", []),
        ("outcome", "unknown"),
    ],
)
def test_malformed_trace_fields(field: str, value: records.Json) -> None:
    """Identify the malformed trace field rather than coercing its value."""
    data = dict(_TRACE_DATA)
    data[field] = value
    failure = _error(_trace_wire(data))
    assert field in failure.location


# Supplying constructor fields as optional would silently repair truncated persisted traces.
@pytest.mark.parametrize("field", tuple(_TRACE_DATA))
def test_missing_trace_fields(field: str) -> None:
    """Require every trace constructor field, including nullable fields."""
    data = dict(_TRACE_DATA)
    del data[field]
    failure = _error(_trace_wire(data))
    assert field in failure.location


# Silently retaining unknown fields or coercing container types accepts incompatible data.
@pytest.mark.parametrize("data", [[], True, "trace", 2, {**_TRACE_DATA, "extra": 1}])
def test_wrong_trace_data_shapes(data: records.Json) -> None:
    """Reject nonobjects and unknown members in trace data."""
    _error(_trace_wire(data))


# Invalid persisted enum, tuple, identifier and integer fields must fail where supplied.
@pytest.mark.parametrize(
    ("field", "value", "path"),
    [
        ("job", "", ("job",)),
        ("job", None, ("job",)),
        ("revision", True, ("revision",)),
        ("revision", "1", ("revision",)),
        ("shape", "unknown", ("shape",)),
        ("stage", "unknown", ("stage",)),
        ("status", "unknown", ("status",)),
        ("copies", {}, ("copies",)),
        ("owners", [["a.py"]], ("owners", "0")),
        ("copies", [{"path": "a.py", "line": True}], ("copies", "0", "line")),
        ("copies", [{"path": "a.py", "line": "1"}], ("copies", "0", "line")),
        ("copies", [{"path": "a.py", "line": 0}], ("copies", "0", "line")),
        (
            "copies",
            [{"path": "a.py", "line": 1, "extra": 2}],
            ("copies", "0", "extra"),
        ),
        ("rounds", [{"loop": "unknown", "used": 0}], ("rounds", "0", "loop")),
        ("rounds", [{"loop": "design", "used": True}], ("rounds", "0", "used")),
    ],
)
def test_malformed_state_fields(
    field: str, value: records.Json, path: tuple[str, ...]
) -> None:
    """Locate malformed state values at their supplied field."""
    failure = _error(_state_wire(**{field: value}), trace=False)
    assert field in failure.location
    tokens = tuple(
        match.group(0) for match in re.finditer(r"[A-Za-z_]+|\d+", failure.location)
    )
    assert tokens[-len(path) :] == path


# Container validation must descend into nested JSON and reject nonfinite scalars.
@pytest.mark.parametrize(
    "value",
    [
        object(),
        {1: "value"},
        ("tuple",),
        {"a": object()},
        float("nan"),
        float("inf"),
        float("-inf"),
        {"a": [float("nan")]},
    ],
)
def test_json_value_rejects_non_json(value: object) -> None:
    """Reject incompatible objects and nonfinite values at every depth."""
    with pytest.raises(RecordError) as failure:
        codec.json_value(value)
    assert failure.value.location.strip()
    assert failure.value.reason.strip()


# Coercing bools, numbers, null, Unicode or collection order changes JSON-compatible inputs.
@pytest.mark.parametrize(
    "value", [None, False, True, 7, 0.25, "雪", ["z", "a"], {"雪": [None, True, 3]}]
)
def test_json_value_preserves_json(value: records.Json) -> None:
    """Preserve JSON-compatible scalars and ordered containers."""
    assert codec.json_value(value) == value
    assert type(codec.json_value(value)) is type(value)


# Decoding an unframed object or extracting a convenient fence from prose accepts another format.
@pytest.mark.parametrize(
    "text",
    [
        '{"format":1,"schema":"brief","data":{"text":"x"}}',
        '```\n{"format":1,"schema":"brief","data":{"text":"x"}}\n```',
        'before\n```json\n{"format":1,"schema":"brief","data":{"text":"x"}}\n```',
        '```json\n{"format":1,"schema":"brief","data":{"text":"x"}}\n```\nafter',
    ],
)
def test_document_rejects_wrong_framing(text: str) -> None:
    """Require a standalone JSON fence rather than extracting embedded JSON."""
    with pytest.raises(RecordError):
        codec.decode_document(text, "brief")


# Accepting undeclared string verdicts, enums or nested field shapes violates each answer contract.
_MALFORMED_DOCUMENTS: list[tuple[str, records.Json, tuple[str, ...]]] = [
    ("brief", {}, ("text",)),
    ("brief", {"text": 3}, ("text",)),
    ("brief", {"text": "x", "extra": 1}, ("extra",)),
    ("check-set", {"checks": [], "disposition": "unknown"}, ("disposition",)),
    (
        "bailiff",
        {
            "pins": [{"line": "S1", "verdict": "unknown", "reason": "r"}],
            "collateral": [],
        },
        ("pins", "0", "verdict"),
    ),
    (
        "bailiff",
        {
            "pins": [],
            "collateral": [{"test_id": "t", "verdict": "unknown", "reason": "r"}],
        },
        ("collateral", "0", "verdict"),
    ),
    (
        "audit",
        {"rows": [{"test_id": "t", "verdict": "unknown", "reason": "r"}]},
        ("rows", "0", "verdict"),
    ),
    ("build", {"step": "s1", "status": "unknown", "reason": "r"}, ("status",)),
    (
        "spec",
        {
            "lines": [{"id": "S1", "claim": "c", "bite": "b", "start": "unknown"}],
            "collateral": [],
        },
        ("lines", "0", "start"),
    ),
    (
        "review",
        {
            "findings": [
                {
                    "anchor": {"path": "x", "line": 1},
                    "scenario": "s",
                    "category": "unknown",
                    "blocking": True,
                    "concern": None,
                }
            ]
        },
        ("findings", "0", "category"),
    ),
    (
        "review",
        {
            "findings": [
                {
                    "anchor": {"path": "x", "line": 1},
                    "scenario": "s",
                    "category": "defect",
                    "blocking": 1,
                    "concern": None,
                }
            ]
        },
        ("findings", "0", "blocking"),
    ),
    (
        "red-judgment",
        {"lines": [{"line": "S1", "verdict": "unknown", "tests": []}]},
        ("lines", "0", "verdict"),
    ),
    (
        "discovery",
        {"citations": [{"claim": "c", "anchor": {"path": False, "line": 1}}]},
        ("citations", "0", "anchor", "path"),
    ),
]


@pytest.mark.parametrize(("tag", "data", "path"), _MALFORMED_DOCUMENTS)
def test_malformed_document_fields(
    tag: str, data: records.Json, path: tuple[str, ...]
) -> None:
    """Reject incompatible values in every declared string-verdict family."""
    envelope = {"format": 1, "schema": tag, "data": data}
    text = "```json\n" + json.dumps(envelope) + "\n```"
    with pytest.raises(RecordError) as failure:
        codec.decode_document(text, tag)
    assert failure.value.location.strip()
    assert failure.value.reason.strip()
    tokens = tuple(
        match.group(0)
        for match in re.finditer(r"[A-Za-z_]+|\d+", failure.value.location)
    )
    assert tokens[-len(path) :] == path


# A role's decoder may accept only its supplied schema set, even for an empty review.
def test_answer_envelope_and_schema_restriction() -> None:
    """Accept empty successful reviews only for a permitted payload schema."""
    expected = records.RoleAnswer(records.ReviewAnswer(()))
    text = codec.encode_answer(expected)
    envelope = _json_object(text)
    assert set(envelope) == {"format", "schema", "data"}
    assert envelope["format"] == 1
    data = envelope["data"]
    assert isinstance(data, dict)
    assert "payload" in data
    spec = records.RoleSpec("reviewer", records.Kind.READER, ("review",))
    assert codec.decode_answer(text, spec) == expected
    with pytest.raises(RecordError):
        codec.decode_answer(text, replace(spec, schemas=("brief",)))


# Treating declared Config/Caps/Candidate defaults as required breaks omitted-field decoding.
@pytest.mark.parametrize(
    "field",
    ["test_helpers", "protected", "test_lint", "implementer_network", "caps", "roles"],
)
def test_omitted_config_defaults(field: str) -> None:
    """Use the declared default of each omitted optional configuration field."""
    data = _state_data()
    config_data = data["config"]
    assert isinstance(config_data, dict)
    del config_data[field]
    text = _state_data_wire(data)
    assert codec.decode_state(text) == state()


# Requiring optional nested defaults or inventing nondefault values changes the state.
def test_omitted_nested_defaults() -> None:
    """Default every omitted cap and the candidate's optional explanation."""
    data = _state_data()
    config_data = data["config"]
    candidate_data = data["candidate"]
    assert isinstance(config_data, dict)
    assert isinstance(candidate_data, dict)
    config_data["caps"] = {}
    del candidate_data["why"]
    text = _state_data_wire(data)
    assert codec.decode_state(text) == state()


# Requiring a declared optional document field rejects a valid compact payload.
@pytest.mark.parametrize(
    ("tag", "data"),
    [
        (
            "outline",
            {
                "steps": [
                    {
                        "name": "s1",
                        "paths": ["pkg/home.py"],
                        "implementer": "core-builder",
                    }
                ],
                "areas": ["pkg"],
            },
        ),
        (
            "spec",
            {
                "lines": [
                    {
                        "id": "S1",
                        "claim": "one claim",
                        "bite": "one measured value",
                        "start": "red",
                    }
                ],
                "collateral": [],
            },
        ),
        ("build", {"step": "s1", "status": "complete", "reason": "one result"}),
    ],
)
def test_omitted_document_defaults(tag: str, data: records.Json) -> None:
    """Decode omitted Outline, SpecLine and BuildAnswer defaults."""
    envelope: dict[str, records.Json] = {"format": 1, "schema": tag, "data": data}
    text = "```json\n" + json.dumps(envelope) + "\n```"
    assert codec.decode_document(text, tag) == seed(tag)


# Requiring the optional defect field prevents decoding an ordinary role answer.
def test_omitted_answer_defect() -> None:
    """Default an omitted spec defect to None."""
    expected = records.RoleAnswer(records.Brief("one request"))
    envelope = _json_object(codec.encode_answer(expected))
    data = envelope["data"]
    assert isinstance(data, dict)
    data.pop("spec_defect", None)
    spec = records.RoleSpec("reader", records.Kind.READER, ("brief",))
    assert codec.decode_answer(json.dumps(envelope), spec) == expected


# Supplying inferred state fields would silently repair an incomplete persisted record.
@pytest.mark.parametrize("field", tuple(_state_data()))
def test_missing_required_state_fields(field: str) -> None:
    """Require every State field even when its specimen is empty or nullable."""
    data = _state_data()
    del data[field]
    text = _state_data_wire(data)
    failure = _error(text, trace=False)
    assert field in failure.location


# Filling required Config fields from helper seeds would accept incomplete persisted config.
@pytest.mark.parametrize(
    "field", ["image", "tests", "gates", "test_policy", "interface"]
)
def test_missing_required_config_fields(field: str) -> None:
    """Require Config constructor fields rather than borrowing fixture values."""
    data = _state_data()
    config_data = data["config"]
    assert isinstance(config_data, dict)
    del config_data[field]
    text = _state_data_wire(data)
    failure = _error(text, trace=False)
    assert field in failure.location


def _proxy_state_data() -> dict[str, records.Json]:
    data = _state_data()
    config_data = data["config"]
    assert isinstance(config_data, dict)
    config_data["readiness_timeout_seconds"] = 30
    config_data["proxy_limits"] = {
        "header_bytes": 1024,
        "body_bytes": 2048,
        "connections": 3,
    }
    config_data["proxy_extra_routes"] = [
        {
            "method": "GET",
            "path": "/v1/models",
            "query_parameters": ["limit", "after_id"],
        },
        {"method": "POST", "path": "/v1/messages", "query_parameters": []},
    ]
    return data


def _accepted(data: dict[str, records.Json]) -> records.State:
    try:
        decoded: records.State | RecordError = codec.decode_state(
            _state_data_wire(data)
        )
    except RecordError as error:
        decoded = error
    assert isinstance(decoded, records.State), decoded
    return decoded


def _proxy_settings(decoded: records.State) -> tuple[object, ...]:
    config = decoded.config
    limits = config.proxy_limits
    return (
        config.readiness_timeout_seconds,
        (limits.header_bytes, limits.body_bytes, limits.connections),
        [
            (route.method, route.path, route.query_parameters)
            for route in config.proxy_extra_routes
        ],
    )


# Dropping, renaming or reshaping any startup/proxy setting loses persisted configuration.
def test_proxy_settings_roundtrip() -> None:
    """Carry the three settings inside State.config through the state envelope."""
    data = _proxy_state_data()
    decoded = _accepted(data)
    assert _proxy_settings(decoded) == (
        30,
        (1024, 2048, 3),
        [
            ("GET", "/v1/models", ("limit", "after_id")),
            ("POST", "/v1/messages", ()),
        ],
    )
    encoded = codec.encode_state(decoded)
    assert _json_object(encoded) == {"format": 1, "schema": "state", "data": data}
    assert codec.decode_state(encoded) == decoded


_OMITTED_PROXY_SETTINGS: list[tuple[str, tuple[object, ...], records.Json]] = [
    (
        "readiness_timeout_seconds",
        (
            10,
            (1024, 2048, 3),
            [
                ("GET", "/v1/models", ("limit", "after_id")),
                ("POST", "/v1/messages", ()),
            ],
        ),
        10,
    ),
    (
        "proxy_limits",
        (
            30,
            (65536, 33554432, 8),
            [
                ("GET", "/v1/models", ("limit", "after_id")),
                ("POST", "/v1/messages", ()),
            ],
        ),
        {"header_bytes": 65536, "body_bytes": 33554432, "connections": 8},
    ),
    ("proxy_extra_routes", (30, (1024, 2048, 3), []), []),
]


# Requiring an omitted setting, or inventing a nondefault value, breaks older state.
@pytest.mark.parametrize(("field", "expected", "wire"), _OMITTED_PROXY_SETTINGS)
def test_omitted_proxy_settings_defaults(
    field: str, expected: tuple[object, ...], wire: records.Json
) -> None:
    """Default each omitted setting to its declared value and persist it."""
    data = _proxy_state_data()
    config_data = data["config"]
    assert isinstance(config_data, dict)
    del config_data[field]
    decoded = _accepted(data)
    assert _proxy_settings(decoded) == expected
    encoded = codec.encode_state(decoded)
    config_data[field] = wire
    assert _json_object(encoded) == {"format": 1, "schema": "state", "data": data}
    assert codec.decode_state(encoded) == decoded


# Requiring optional nested members rejects a partial limits mapping or a bare route.
def test_omitted_proxy_nested_defaults() -> None:
    """Default omitted limit members and an omitted route query list."""
    data = _proxy_state_data()
    config_data = data["config"]
    assert isinstance(config_data, dict)
    config_data["proxy_limits"] = {"body_bytes": 2048}
    config_data["proxy_extra_routes"] = [{"method": "GET", "path": "/v1/models"}]
    decoded = _accepted(data)
    assert _proxy_settings(decoded) == (
        30,
        (65536, 2048, 8),
        [("GET", "/v1/models", ())],
    )


# Filling a route's method or path would accept an incomplete persisted permission.
@pytest.mark.parametrize("field", ["method", "path"])
def test_missing_required_proxy_route_fields(field: str) -> None:
    """Require each ProxyRoute constructor field in persisted config."""
    data = _proxy_state_data()
    config_data = data["config"]
    assert isinstance(config_data, dict)
    routes = config_data["proxy_extra_routes"]
    assert isinstance(routes, list)
    route = routes[0]
    assert isinstance(route, dict)
    del route[field]
    failure = _error(_state_data_wire(data), trace=False)
    assert field in failure.location
