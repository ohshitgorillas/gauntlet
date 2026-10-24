# Copyright 2026 oh shit, gorillas!
"""Pure repository configuration contract from the M1 records design."""

import os
from collections.abc import Iterator, Mapping
from dataclasses import replace
from typing import override

import pytest

from gauntlet.core import config, records
from gauntlet.core.errors import ConfigError

_LOOPS = ("design", "plan", "spec", "juror", "build", "review", "reopen")
_INVALID_VALUES: list[tuple[str, records.Json]] = [
    ("image", 7),
    ("gates", []),
    ("test_policy", False),
    ("tests", {}),
    ("tests", ["pytest"]),
    ("tests", [{"dir": "tests"}]),
    ("tests", [{"run": "pytest"}]),
    ("tests", [{"dir": 1, "run": "pytest"}]),
    ("tests", [{"dir": "tests", "run": False}]),
    ("interface", "py"),
    ("interface", [None]),
    ("interface", [{"lang": "py"}]),
    ("interface", [{"run": "stubgen"}]),
    ("interface", [{"lang": 1, "run": "stubgen"}]),
    ("interface", [{"lang": "py", "run": []}]),
    ("test_helpers", "tests/support.py"),
    ("test_helpers", [1]),
    ("protected", "conftest.py"),
    ("protected", [False]),
    ("test_lint", 1),
    ("implementer_network", 1),
    ("caps", []),
    ("roles", []),
    ("roles", {"planner": "model"}),
    ("roles", {"planner": {"model": 1}}),
    ("roles", {"planner": {"effort": False}}),
]


def _wire() -> dict[str, records.Json]:
    return {
        "image": ".gauntlet/Containerfile",
        "tests": [{"dir": "tests/py", "run": "pytest {ids}"}],
        "gates": "scripts/gate.sh",
        "test_policy": "docs/testing.md",
        "interface": [{"lang": "py", "run": "stubgen -o {out} {modules}"}],
    }


def _record() -> records.Config:
    return records.Config(
        image=".gauntlet/Containerfile",
        tests=(records.TestCommand("tests/py", "pytest {ids}"),),
        gates="scripts/gate.sh",
        test_policy="docs/testing.md",
        interface=(records.InterfaceCommand("py", "stubgen -o {out} {modules}"),),
    )


# Omitting a default or using the record field names on the wire breaks this.
def test_required_keys_use_every_optional_record_default() -> None:
    """Read the required wire keys with the declared Config and Caps defaults."""
    assert config.config_from_json(_wire()) == _record()


# Rejecting a valid direct record or fabricating a problem breaks validity.
def test_default_record_has_no_problems() -> None:
    """Accept a valid configuration without relying on the JSON reader."""
    assert config.config_problems(_record()) == ()


# Discarding optional values, reordering entries or coercing paths breaks this.
def test_explicit_options_preserve_values_and_order() -> None:
    """Map all documented options into immutable configuration records."""
    value = _wire()
    value.update(
        tests=[
            {"dir": "tests/js", "run": "node --test {ids}"},
            {"dir": " ./tests/py ", "run": "pytest {ids}"},
        ],
        interface=[
            {"lang": "js", "run": "tsc {files}"},
            {"lang": "py", "run": "stubgen {modules}"},
        ],
        test_helpers=[" outside/clock.py ", "tests/support/étude.py"],
        protected=["pyproject.toml", "conftest.py"],
        test_lint="ruff check {files} && mypy {files}",
        implementer_network=True,
        caps={name: index + 1 for index, name in enumerate(_LOOPS)},
        roles={
            "planner": {"model": "claude-opus-5-5", "effort": "high"},
            "juror": {"effort": "medium"},
            "repo-specialist": {"model": "local-model"},
            "reviewer": {},
        },
    )
    expected = replace(
        _record(),
        tests=(
            records.TestCommand("tests/js", "node --test {ids}"),
            records.TestCommand(" ./tests/py ", "pytest {ids}"),
        ),
        interface=(
            records.InterfaceCommand("js", "tsc {files}"),
            records.InterfaceCommand("py", "stubgen {modules}"),
        ),
        test_helpers=(" outside/clock.py ", "tests/support/étude.py"),
        protected=("pyproject.toml", "conftest.py"),
        test_lint="ruff check {files} && mypy {files}",
        implementer_network=True,
        caps=records.Caps(1, 2, 3, 4, 5, 6, 7),
        roles=(
            records.RoleSetting("planner", "claude-opus-5-5", "high"),
            records.RoleSetting("juror", None, "medium"),
            records.RoleSetting("repo-specialist", "local-model", None),
            records.RoleSetting("reviewer", None, None),
        ),
    )
    assert config.config_from_json(value) == expected
    assert config.config_problems(expected) == ()


# Filling omitted cap fields with a chosen constant loses their record defaults.
@pytest.mark.parametrize("loop", _LOOPS)
def test_partial_caps_use_defaults_for_other_loops(loop: str) -> None:
    """Override exactly one cap while retaining the Caps record defaults."""
    value = _wire()
    value["caps"] = {loop: 19}
    expected = replace(_record(), caps=replace(records.Caps(), **{loop: 19}))
    assert config.config_from_json(value) == expected


# Treating a missing required key as optional silently accepts incomplete input.
@pytest.mark.parametrize("key", ["image", "tests", "gates", "test_policy", "interface"])
def test_missing_required_key_identifies_the_key(key: str) -> None:
    """Reject each omitted required field with a typed, located failure."""
    value = _wire()
    del value[key]
    with pytest.raises(ConfigError) as caught:
        config.config_from_json(value)
    assert key in caught.value.key
    assert caught.value.reason


# Accepting a scalar or sequence invents a root mapping that was not supplied.
@pytest.mark.parametrize("value", [None, True, 3, 1.5, "secret-token", []])
def test_nonmapping_root_is_a_safe_config_error(value: records.Json) -> None:
    """Reject invalid roots without echoing their possibly sensitive value."""
    with pytest.raises(ConfigError) as caught:
        config.config_from_json(value)
    assert caught.value.key
    assert caught.value.reason
    assert "secret-token" not in str(caught.value)


# Permitting an empty collection leaves required execution coverage absent.
@pytest.mark.parametrize("key", ["tests", "interface"])
def test_required_command_collections_are_nonempty(key: str) -> None:
    """Reject absent test or interface entries at both public boundaries."""
    value = _wire()
    value[key] = []
    with pytest.raises(ConfigError):
        config.config_from_json(value)
    invalid = (
        replace(_record(), tests=())
        if key == "tests"
        else replace(_record(), interface=())
    )
    assert config.config_problems(invalid)


# Coercing bool, float or text caps accepts a value outside positive integers.
@pytest.mark.parametrize("loop", _LOOPS)
@pytest.mark.parametrize("cap", [0, -1, True, False, 1.5, "2", None])
def test_invalid_cap_values_are_rejected(loop: str, cap: records.Json) -> None:
    """Reject every nonpositive or wrongly typed loop cap."""
    value = _wire()
    value["caps"] = {loop: cap}
    with pytest.raises(ConfigError) as caught:
        config.config_from_json(value)
    assert "caps" in caught.value.key
    assert loop in caught.value.key


# Checking caps only while reading JSON lets invalid direct records through.
@pytest.mark.parametrize("loop", _LOOPS)
@pytest.mark.parametrize("cap", [0, -1, True, False])
def test_record_validator_rejects_invalid_caps(loop: str, cap: int) -> None:
    """Enforce positive integer caps on already constructed records too."""
    invalid = replace(_record(), caps=replace(records.Caps(), **{loop: cap}))
    assert config.config_problems(invalid)


# Silently taking one duplicate directory or language discards a command entry.
@pytest.mark.parametrize("key", ["tests", "interface"])
@pytest.mark.parametrize("conflicting", [False, True])
def test_duplicate_command_identities_fail(key: str, *, conflicting: bool) -> None:
    """Reject identical identities even when their commands differ."""
    value = _wire()
    if key == "tests":
        value[key] = [
            {"dir": "tests/py", "run": "pytest {ids}"},
            {"dir": "tests/py", "run": "other" if conflicting else "pytest {ids}"},
        ]
        invalid = replace(
            _record(),
            tests=(
                records.TestCommand("same", "one"),
                records.TestCommand("same", "two"),
            ),
        )
    else:
        value[key] = [
            {"lang": "py", "run": "stubgen {modules}"},
            {"lang": "py", "run": "other" if conflicting else "stubgen {modules}"},
        ]
        invalid = replace(
            _record(),
            interface=(
                records.InterfaceCommand("py", "one"),
                records.InterfaceCommand("py", "two"),
            ),
        )
    with pytest.raises(ConfigError):
        config.config_from_json(value)
    assert config.config_problems(invalid)


# Treating role settings as a last-write-wins map hides duplicate overrides.
@pytest.mark.parametrize("conflicting", [False, True])
def test_duplicate_role_overrides_fail(*, conflicting: bool) -> None:
    """Reject duplicate role names before execution chooses model settings."""
    first = records.RoleSetting("planner", "one", None)
    second = replace(first, model="two") if conflicting else first
    assert config.config_problems(replace(_record(), roles=(first, second)))


# Ignoring unknown nested fields or reporting only their leaf hides the location.
@pytest.mark.parametrize(
    ("key", "value", "parts"),
    [
        ("unexpected", "secret-token", ("unexpected",)),
        ("caps", {"unexpected": 2}, ("caps", "unexpected")),
        (
            "tests",
            [{"dir": "tests", "run": "pytest", "unexpected": 1}],
            ("tests", "0", "unexpected"),
        ),
        (
            "interface",
            [{"lang": "py", "run": "stubgen", "unexpected": 1}],
            ("interface", "0", "unexpected"),
        ),
        ("roles", {"planner": {"kind": "judge"}}, ("roles", "planner", "kind")),
    ],
)
def test_unknown_keys_report_full_paths_without_values(
    key: str, value: records.Json, parts: tuple[str, ...]
) -> None:
    """Reject extra keys at each schema boundary with their complete location."""
    payload = _wire()
    payload[key] = value
    with pytest.raises(ConfigError) as caught:
        config.config_from_json(payload)
    assert all(part in caught.value.key for part in parts)
    assert "secret-token" not in str(caught.value)


# Accepting schema lookalikes by coercion or dropping incomplete entries is invalid.
@pytest.mark.parametrize(("key", "value"), _INVALID_VALUES)
def test_invalid_field_values_fail_with_config_error(
    key: str, value: records.Json
) -> None:
    """Reject wrong scalar and collection types and missing entry fields."""
    payload = _wire()
    payload[key] = value
    with pytest.raises(ConfigError) as caught:
        config.config_from_json(payload)
    assert key in caught.value.key
    assert caught.value.reason


# Splitting, expanding or filtering shell text changes opaque command strings.
def test_commands_and_placeholders_remain_opaque() -> None:
    """Preserve shell syntax, unknown placeholders and literal variable text."""
    command = "  X=$SECRET tool '{ids}' {unknown} && other | tee out; $(literal)\n"
    value = _wire()
    value.update(
        gates=command,
        tests=[{"dir": "tests/py", "run": command}],
        interface=[{"lang": "py", "run": command}],
        test_lint=command,
    )
    expected = replace(
        _record(),
        gates=command,
        test_lint=command,
        tests=(records.TestCommand("tests/py", command),),
        interface=(records.InterfaceCommand("py", command),),
    )
    assert config.config_from_json(value) == expected
    assert config.config_problems(expected) == ()


# Passing NaN or infinities through a typed field bypasses JSON-value validation.
@pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("key", ["image", "caps", "roles"])
def test_nonfinite_json_values_are_located_config_errors(
    number: float, key: str
) -> None:
    """Reject nonfinite values even inside nested config collections."""
    value = _wire()
    parts: tuple[str, ...]
    if key == "caps":
        value[key] = {"review": number}
        parts = ("caps", "review")
    elif key == "roles":
        value[key] = {"planner": {"model": number}}
        parts = ("roles", "planner", "model")
    else:
        value[key] = number
        parts = ("image",)
    with pytest.raises(ConfigError) as caught:
        config.config_from_json(value)
    assert all(part in caught.value.key for part in parts)
    assert caught.value.reason


# Echoing a rejected collection or nested scalar exposes credential values.
@pytest.mark.parametrize("key", ["image", "tests", "roles"])
def test_nested_invalid_values_do_not_disclose_credentials(key: str) -> None:
    """Keep supplied credential text out of the complete error surface."""
    private_value = "credential-value-private-42"
    value = _wire()
    parts: tuple[str, ...]
    if key == "tests":
        value[key] = [{"dir": "tests", "run": [private_value]}]
        parts = ("tests", "0", "run")
    elif key == "roles":
        value[key] = {"planner": {"model": {"credential": private_value}}}
        parts = ("roles", "planner", "model")
    else:
        value[key] = [private_value]
        parts = ("image",)
    with pytest.raises(ConfigError) as caught:
        config.config_from_json(value)
    error = caught.value
    assert all(part in error.key for part in parts)
    assert error.reason
    assert private_value not in error.key
    assert private_value not in error.reason
    assert private_value not in str(error)
    assert private_value not in repr(error)


class _UnreadableEnvironment(Mapping[str, str]):
    """Fail any attempt to consult the process environment during validation."""

    @override
    def __getitem__(self, key: str) -> str:
        raise AssertionError

    @override
    def __iter__(self) -> Iterator[str]:
        raise AssertionError

    @override
    def __len__(self) -> int:
        raise AssertionError


# Consulting an environment default or expanding shell variables breaks purity.
def test_both_config_boundaries_work_without_environment_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read and validate literal config while every environment read fails."""
    value = _wire()
    value["gates"] = "$PRIVATE_GATE ${PRIVATE_GATE}"
    expected = replace(_record(), gates="$PRIVATE_GATE ${PRIVATE_GATE}")
    with monkeypatch.context() as isolated:
        isolated.setattr(os, "environ", _UnreadableEnvironment())
        result = config.config_from_json(value)
        problems = config.config_problems(expected)
    assert result == expected
    assert problems == ()


_TEN_SECONDS = 10
_LIMIT_FIELDS = ("header_bytes", "body_bytes", "connections")
_ROUTES_KEY = "$.proxy_extra_routes"
_VALID_ROUTE: dict[str, records.Json] = {"method": "GET", "path": "/v1/models"}
_BAD_METHODS: list[str] = ["get", "Get", "", "GE T", "GET/", "GÉT", "GET\n"]
_BAD_PATHS: list[str] = [
    "",
    "v1/models",
    "/v1/models?beta=true",
    "/v1/models#part",
    "/v1/*",
    "/v1/models/*",
    "https://api.example.com/v1/models",
    "https://user:secret@api.example.com/v1/models",
    "//user:secret@api.example.com/v1/models",
    "/v1/../admin",
    "/v1/./models",
    "/v1/%2e%2e/admin",
    "/v1/%2Fmodels",
    "/v1/%zz",
    "/v1/models%",
]
_BAD_QUERY_NAMES: list[str] = [
    "",
    "beta=true",
    "a&b",
    "a?b",
    "a#b",
    "a/b",
    "a%3Db",
    "a\nb",
    "a\x00b",
    "a\x7fb",
]


def _read(value: records.Json) -> records.Config | ConfigError:
    """Return the read record, or the typed failure so equality asserts on it."""
    try:
        return config.config_from_json(value)
    except ConfigError as error:
        return error


def _rejected(value: records.Json) -> ConfigError:
    """Return the typed failure; an accepted value fails the caller's assertion."""
    result = _read(value)
    assert isinstance(result, ConfigError)
    return result


def _routes_wire(*entries: records.Json) -> dict[str, records.Json]:
    value = _wire()
    value["proxy_extra_routes"] = list(entries)
    return value


def _direct_route(route: records.ProxyRoute) -> records.Config:
    return replace(_record(), proxy_extra_routes=(route,))


# Ignoring or rejecting the readiness key loses the configured startup bound.
def test_readiness_timeout_override_is_read() -> None:
    """Read a positive readiness timeout into the Config record."""
    value = _wire()
    value["readiness_timeout_seconds"] = 30
    expected = replace(_record(), readiness_timeout_seconds=30)
    assert _read(value) == expected
    assert config.config_problems(expected) == ()


# Accepting zero, bool or text as a timeout, or blaming the key, breaks this.
@pytest.mark.parametrize("timeout", [0, -1, True, False, 1.5, "10", None])
def test_invalid_readiness_timeout_is_rejected_at_its_path(
    timeout: records.Json,
) -> None:
    """Reject each nonpositive or noninteger timeout while accepting one."""
    valid = _wire()
    valid["readiness_timeout_seconds"] = 1
    assert _read(valid) == replace(_record(), readiness_timeout_seconds=1)
    value = _wire()
    value["readiness_timeout_seconds"] = timeout
    error = _rejected(value)
    assert error.key == "$.readiness_timeout_seconds"
    assert error.reason


# Validating the timeout only while reading JSON lets direct records through.
@pytest.mark.parametrize("timeout", [0, -1, True, False])
def test_record_validator_rejects_invalid_readiness_timeout(timeout: int) -> None:
    """Report a nonpositive or boolean timeout on a constructed record."""
    invalid = replace(_record(), readiness_timeout_seconds=timeout)
    assert config.config_problems(invalid)


# Dropping, swapping or capping a configured limit changes sidecar transport.
def test_every_proxy_limit_override_is_read() -> None:
    """Read each proxy limit into its own ProxyLimits field."""
    value = _wire()
    value["proxy_limits"] = {"header_bytes": 1, "body_bytes": 2, "connections": 3}
    expected = replace(_record(), proxy_limits=records.ProxyLimits(1, 2, 3))
    assert _read(value) == expected
    assert config.config_problems(expected) == ()


# Accepting a nonpositive, boolean or noninteger limit admits an unusable proxy.
@pytest.mark.parametrize("field", _LIMIT_FIELDS)
@pytest.mark.parametrize("limit", [0, -1, True, False, 1.5, "8", None])
def test_invalid_proxy_limit_is_rejected_at_its_field(
    field: str, limit: records.Json
) -> None:
    """Locate each invalid limit at its member of proxy_limits."""
    value = _wire()
    value["proxy_limits"] = {field: limit}
    error = _rejected(value)
    assert error.key == f"$.proxy_limits.{field}"
    assert error.reason


# Checking limits only while reading JSON lets invalid direct records through.
@pytest.mark.parametrize("field", _LIMIT_FIELDS)
@pytest.mark.parametrize("limit", [0, -1, True, False])
def test_record_validator_rejects_invalid_proxy_limits(field: str, limit: int) -> None:
    """Report a nonpositive or boolean limit on a constructed record."""
    limits = replace(records.ProxyLimits(), **{field: limit})
    assert config.config_problems(replace(_record(), proxy_limits=limits))


# Ignoring an unknown limit member hides a misspelled override.
def test_unknown_proxy_limit_member_is_rejected() -> None:
    """Reject a member ProxyLimits does not declare, naming its location."""
    value = _wire()
    value["proxy_limits"] = {"connections": 2, "unexpected": 4}
    error = _rejected(value)
    assert "proxy_limits" in error.key
    assert "unexpected" in error.key


# Treating a scalar or list as an empty mapping silently applies the defaults.
@pytest.mark.parametrize("limits", [[], 8, "header_bytes", True])
def test_nonobject_proxy_limits_is_rejected(limits: records.Json) -> None:
    """Reject a proxy_limits value that is not a mapping while accepting one."""
    valid = _wire()
    valid["proxy_limits"] = {"connections": 2}
    assert _read(valid) == replace(
        _record(), proxy_limits=records.ProxyLimits(connections=2)
    )
    value = _wire()
    value["proxy_limits"] = limits
    assert _rejected(value).key == "$.proxy_limits"


# Dropping, reordering or merging extension routes loses declared permissions.
def test_valid_extra_routes_are_read_in_order() -> None:
    """Read exact routes; one path under two methods is not a duplicate."""
    value = _routes_wire(
        {"method": "GET", "path": "/v1/models"},
        {"method": "POST", "path": "/v1/models", "query_parameters": ["beta", "x"]},
        {"method": "PROPFIND", "path": "/v1/files/file_01"},
    )
    expected = replace(
        _record(),
        proxy_extra_routes=(
            records.ProxyRoute("GET", "/v1/models"),
            records.ProxyRoute("POST", "/v1/models", ("beta", "x")),
            records.ProxyRoute("PROPFIND", "/v1/files/file_01"),
        ),
    )
    assert _read(value) == expected
    assert config.config_problems(expected) == ()


# Folding case or accepting nontoken text admits a method no route names.
@pytest.mark.parametrize("method", [*_BAD_METHODS, 1, None, ["GET"]])
def test_invalid_route_method_is_rejected_at_its_index(method: records.Json) -> None:
    """Locate a bad method at its entry's method field."""
    value = _routes_wire(_VALID_ROUTE, {"method": method, "path": "/v1/files"})
    error = _rejected(value)
    assert error.key == f"{_ROUTES_KEY}[1].method"
    assert error.reason


# Accepting a prefix, query, wildcard or traversal widens the proxy grant.
@pytest.mark.parametrize("path", [*_BAD_PATHS, 1, None, ["/v1/models"]])
def test_invalid_route_path_is_rejected_at_its_index(path: records.Json) -> None:
    """Locate a path that is not one exact origin-form path at its field."""
    value = _routes_wire(_VALID_ROUTE, {"method": "POST", "path": path})
    error = _rejected(value)
    assert error.key == f"{_ROUTES_KEY}[1].path"
    assert error.reason


# Accepting delimiters or controls in a query name smuggles extra parameters.
@pytest.mark.parametrize(
    "names", [*([name] for name in _BAD_QUERY_NAMES), "beta", [1], {"beta": 1}]
)
def test_invalid_query_parameters_are_rejected_at_their_field(
    names: records.Json,
) -> None:
    """Locate bad query names or a non-list of names at query_parameters."""
    value = _routes_wire(
        _VALID_ROUTE,
        {"method": "POST", "path": "/v1/files", "query_parameters": names},
    )
    error = _rejected(value)
    assert error.key.startswith(f"{_ROUTES_KEY}[1].query_parameters")
    assert error.reason


# Treating method or path as optional invents a route nobody declared.
@pytest.mark.parametrize("field", ["method", "path"])
def test_missing_route_field_is_rejected_at_its_index(field: str) -> None:
    """Require both method and path on every extension entry."""
    entry: dict[str, records.Json] = {"method": "POST", "path": "/v1/files"}
    del entry[field]
    error = _rejected(_routes_wire(_VALID_ROUTE, entry))
    assert error.key == f"{_ROUTES_KEY}[1].{field}"


# Ignoring an unknown route field silently drops an origin or wildcard request.
def test_unknown_route_field_is_rejected_at_its_index() -> None:
    """Reject a field ProxyRoute does not declare, naming its location."""
    entry: dict[str, records.Json] = {
        "method": "POST",
        "path": "/v1/files",
        "origin": "https://example.com",
    }
    error = _rejected(_routes_wire(_VALID_ROUTE, entry))
    assert error.key == f"{_ROUTES_KEY}[1].origin"


# Accepting a scalar entry or a non-list collection invents route objects.
@pytest.mark.parametrize(
    ("routes", "prefix"),
    [
        (["GET /v1/files"], f"{_ROUTES_KEY}[0]"),
        ([_VALID_ROUTE, None], f"{_ROUTES_KEY}[1]"),
        (_VALID_ROUTE, _ROUTES_KEY),
        ("GET /v1/files", _ROUTES_KEY),
    ],
)
def test_nonobject_routes_are_rejected(routes: records.Json, prefix: str) -> None:
    """Reject non-object entries and a non-list value while accepting a list."""
    assert _read(_routes_wire(_VALID_ROUTE)) == replace(
        _record(), proxy_extra_routes=(records.ProxyRoute("GET", "/v1/models"),)
    )
    value = _wire()
    value["proxy_extra_routes"] = routes
    assert _rejected(value).key.startswith(prefix)


# Last-write-wins on a repeated method/path hides a conflicting declaration.
@pytest.mark.parametrize("names", [[], ["beta"]])
def test_duplicate_extra_route_is_rejected(names: list[records.Json]) -> None:
    """Reject a second entry for the same method and path within the list."""
    value = _routes_wire(
        {"method": "GET", "path": "/v1/files"},
        _VALID_ROUTE,
        {"method": "GET", "path": "/v1/files", "query_parameters": names},
    )
    assert _rejected(value).key.startswith(f"{_ROUTES_KEY}[2]")
    duplicated = (
        records.ProxyRoute("GET", "/v1/files"),
        records.ProxyRoute("GET", "/v1/files", ("beta",)),
    )
    assert config.config_problems(replace(_record(), proxy_extra_routes=duplicated))


# Validating routes only while reading JSON lets direct records through.
@pytest.mark.parametrize(
    "route",
    [
        *(records.ProxyRoute(method, "/v1/files") for method in _BAD_METHODS),
        *(records.ProxyRoute("POST", path) for path in _BAD_PATHS),
        *(
            records.ProxyRoute("POST", "/v1/files", (name,))
            for name in _BAD_QUERY_NAMES
        ),
    ],
)
def test_record_validator_rejects_invalid_routes(route: records.ProxyRoute) -> None:
    """Apply the same route grammar to a constructed record."""
    assert config.config_problems(_direct_route(route))


# Substituting other defaults or default routes, or requiring query_parameters,
# breaks this.
def test_omitted_settings_and_members_use_canonical_defaults() -> None:
    """Fill absent settings, limit members and query names with the defaults."""
    assert records.DEFAULT_READINESS_TIMEOUT_SECONDS == _TEN_SECONDS
    default_routes = records.DEFAULT_PROXY_ROUTES
    assert default_routes == (
        records.ProxyRoute("POST", "/v1/messages", ("beta",)),
        records.ProxyRoute("POST", "/v1/messages/count_tokens", ("beta",)),
    )
    assert records.ProxyRoute("GET", "/v1/models").query_parameters == ()
    omitted = config.config_from_json(_wire())
    assert omitted.readiness_timeout_seconds == _TEN_SECONDS
    assert omitted.proxy_limits == records.ProxyLimits(65536, 33554432, 8)
    assert omitted.proxy_extra_routes == ()
    value = _routes_wire(_VALID_ROUTE)
    value["proxy_limits"] = {}
    assert _read(value) == replace(
        _record(), proxy_extra_routes=(records.ProxyRoute("GET", "/v1/models", ()),)
    )


# Filling an omitted limit with a constant other than its default breaks this.
@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("header_bytes", records.ProxyLimits(7, 33554432, 8)),
        ("body_bytes", records.ProxyLimits(65536, 7, 8)),
        ("connections", records.ProxyLimits(65536, 33554432, 7)),
    ],
)
def test_partial_proxy_limits_keep_other_defaults(
    field: str, expected: records.ProxyLimits
) -> None:
    """Override exactly one limit while the others keep their literal defaults."""
    value = _wire()
    value["proxy_limits"] = {field: 7}
    assert _read(value) == replace(_record(), proxy_limits=expected)
