# Copyright 2026 oh shit, gorillas!
"""Validate repository configuration without I/O."""

from __future__ import annotations

import re
from dataclasses import fields, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataclasses import Field
    from typing import TypeGuard

from gauntlet.core.codec import json_value
from gauntlet.core.errors import ConfigError, RecordError
from gauntlet.core.records import (
    Caps,
    Config,
    InterfaceCommand,
    Json,
    ProxyLimits,
    ProxyRoute,
    RoleSetting,
    TestCommand,
)

_CAPS_KEY = "$.caps"
_LIMITS_KEY = "$.proxy_limits"
_ROUTES_KEY = "$.proxy_extra_routes"
_METHOD = re.compile(r"[!#$%&'*+.^_`|~0-9A-Z-]+")
_SEGMENT = r"(?:[A-Za-z0-9._~!$&'()+,;=:-]|%(?!2[eEfF]|5[cC]|25)[0-9A-Fa-f]{2})+"
_PATH = re.compile(rf"(?:/{_SEGMENT})+")
_QUERY_NAME = re.compile(r"[A-Za-z0-9._~-]+")
_DOT_SEGMENTS = frozenset({".", ".."})


def _mapping(value: Json, key: str) -> dict[str, Json]:
    """Require an object without coercing its contents."""
    if not isinstance(value, dict):
        raise ConfigError(key, "expected an object")
    return value


def _keys(value: dict[str, Json], allowed: set[str], key: str) -> None:
    """Reject unknown fields at their full configuration path."""
    for name in value:
        if name not in allowed:
            path = f"{key}.{name}"
            raise ConfigError(path, "unknown key")


def _required(value: dict[str, Json], name: str, key: str) -> Json:
    """Read a required key with a located failure."""
    if name not in value:
        path = f"{key}.{name}"
        raise ConfigError(path, "missing required key")
    return value[name]


def _text(value: Json, key: str) -> str:
    """Require exact text while leaving commands and paths opaque."""
    if not isinstance(value, str):
        raise ConfigError(key, "expected a string")
    return value


def _array(value: Json, key: str) -> list[Json]:
    """Require an array without inventing entries."""
    if not isinstance(value, list):
        raise ConfigError(key, "expected an array")
    return value


def _strings(value: Json, key: str) -> tuple[str, ...]:
    """Read immutable path lists preserving their order."""
    return tuple(
        _text(child, f"{key}[{index}]")
        for index, child in enumerate(_array(value, key))
    )


def _commands(value: Json, key: str, identity: str) -> tuple[tuple[str, str], ...]:
    """Read the common directory/language and opaque-command entry shape."""
    commands: list[tuple[str, str]] = []
    for index, child in enumerate(_array(value, key)):
        path = f"{key}[{index}]"
        entry = _mapping(child, path)
        _keys(entry, {identity, "run"}, path)
        commands.append(
            (
                _text(_required(entry, identity, path), f"{path}.{identity}"),
                _text(_required(entry, "run", path), f"{path}.run"),
            )
        )
    return tuple(commands)


def _is_positive(value: object) -> TypeGuard[int]:
    """Accept only genuine positive integers, never booleans."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _positive(value: Json, key: str) -> int:
    """Require a positive integer with a located failure."""
    if not _is_positive(value):
        raise ConfigError(key, "expected a positive integer")
    return value


def _overrides[Record: (Caps, ProxyLimits)](
    defaults: Record, value: Json, key: str
) -> Record:
    """Override supplied positive fields of a record's canonical defaults."""
    entry = _mapping(value, key)
    record_fields: tuple[Field[object], ...] = fields(defaults)
    _keys(entry, {field.name for field in record_fields}, key)
    record = defaults
    for name, number in entry.items():
        record = replace(record, **{name: _positive(number, f"{key}.{name}")})
    return record


def _caps(value: Json) -> Caps:
    """Override supplied caps using the canonical record defaults."""
    return _overrides(Caps(), value, _CAPS_KEY)


def proxy_limits_from_json(value: Json) -> ProxyLimits:
    """Override supplied proxy limits using the canonical record defaults."""
    return _overrides(ProxyLimits(), value, _LIMITS_KEY)


def proxy_routes_from_json(value: Json) -> tuple[ProxyRoute, ...]:
    """Read extension routes, then apply the shared route grammar."""
    routes: list[ProxyRoute] = []
    for index, child in enumerate(_array(value, _ROUTES_KEY)):
        path = f"{_ROUTES_KEY}[{index}]"
        entry = _mapping(child, path)
        _keys(entry, {"method", "path", "query_parameters"}, path)
        route = ProxyRoute(
            _text(_required(entry, "method", path), f"{path}.method"),
            _text(_required(entry, "path", path), f"{path}.path"),
        )
        if "query_parameters" in entry:
            names = _strings(entry["query_parameters"], f"{path}.query_parameters")
            route = replace(route, query_parameters=names)
        routes.append(route)
    result = tuple(routes)
    issues = _route_issues(result)
    if issues:
        key, reason = issues[0]
        raise ConfigError(key, reason)
    return result


def _roles(value: Json) -> tuple[RoleSetting, ...]:
    """Read model and effort overrides without interpreting role names."""
    roles: list[RoleSetting] = []
    for name, child in _mapping(value, "$.roles").items():
        path = f"$.roles.{name}"
        entry = _mapping(child, path)
        _keys(entry, {"model", "effort"}, path)
        roles.append(
            RoleSetting(
                name,
                _text(entry["model"], f"{path}.model") if "model" in entry else None,
                _text(entry["effort"], f"{path}.effort") if "effort" in entry else None,
            )
        )
    return tuple(roles)


def config_from_json(value: Json) -> Config:
    """Read repository configuration through the shared JSON-value validator."""
    try:
        validated = json_value(value)
    except RecordError as error:
        raise ConfigError(error.location, error.reason) from error
    entry = _mapping(validated, "$")
    config_fields: tuple[Field[object], ...] = fields(Config)
    _keys(entry, {field.name for field in config_fields}, "$")
    config = Config(
        image=_text(_required(entry, "image", "$"), "$.image"),
        tests=tuple(
            TestCommand(directory, run)
            for directory, run in _commands(
                _required(entry, "tests", "$"), "$.tests", "dir"
            )
        ),
        gates=_text(_required(entry, "gates", "$"), "$.gates"),
        test_policy=_text(_required(entry, "test_policy", "$"), "$.test_policy"),
        interface=tuple(
            InterfaceCommand(language, run)
            for language, run in _commands(
                _required(entry, "interface", "$"), "$.interface", "lang"
            )
        ),
    )
    config = _options(config, entry)
    issues = _issues(config)
    if issues:
        key, reason = issues[0]
        raise ConfigError(key, reason)
    return config


def _options(config: Config, entry: dict[str, Json]) -> Config:
    """Apply only supplied options to the record's own defaults."""
    network = entry.get("implementer_network", config.implementer_network)
    if not isinstance(network, bool):
        path = "$.implementer_network"
        raise ConfigError(path, "expected a boolean")
    return replace(
        config,
        test_helpers=(
            _strings(entry["test_helpers"], "$.test_helpers")
            if "test_helpers" in entry
            else config.test_helpers
        ),
        protected=(
            _strings(entry["protected"], "$.protected")
            if "protected" in entry
            else config.protected
        ),
        test_lint=(
            _text(entry["test_lint"], "$.test_lint")
            if "test_lint" in entry
            else config.test_lint
        ),
        implementer_network=network,
        caps=_caps(entry["caps"]) if "caps" in entry else config.caps,
        roles=_roles(entry["roles"]) if "roles" in entry else config.roles,
        readiness_timeout_seconds=(
            _positive(entry["readiness_timeout_seconds"], "$.readiness_timeout_seconds")
            if "readiness_timeout_seconds" in entry
            else config.readiness_timeout_seconds
        ),
        proxy_limits=(
            proxy_limits_from_json(entry["proxy_limits"])
            if "proxy_limits" in entry
            else config.proxy_limits
        ),
        proxy_extra_routes=(
            proxy_routes_from_json(entry["proxy_extra_routes"])
            if "proxy_extra_routes" in entry
            else config.proxy_extra_routes
        ),
    )


def _positive_issues(
    prefix: str, record: Caps | ProxyLimits
) -> tuple[tuple[str, str], ...]:
    """Locate every non-positive integer among a record's own fields."""
    record_fields: tuple[Field[object], ...] = fields(record)
    issues: list[tuple[str, str]] = []
    for field in record_fields:
        value: object = getattr(record, field.name)
        if not _is_positive(value):
            issues.append((f"{prefix}.{field.name}", "expected a positive integer"))
    return tuple(issues)


def _route_issues(routes: tuple[ProxyRoute, ...]) -> tuple[tuple[str, str], ...]:
    """Locate route grammar problems and repeated method/path pairs."""
    issues: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, route in enumerate(routes):
        base = f"{_ROUTES_KEY}[{index}]"
        if _METHOD.fullmatch(route.method) is None:
            issues.append((f"{base}.method", "expected an uppercase HTTP method"))
        segments = set(route.path.split("/"))
        if _PATH.fullmatch(route.path) is None or segments & _DOT_SEGMENTS:
            issues.append((f"{base}.path", "expected one exact origin-form path"))
        for position, name in enumerate(route.query_parameters):
            if _QUERY_NAME.fullmatch(name) is None:
                key = f"{base}.query_parameters[{position}]"
                issues.append((key, "expected a literal query name"))
        identity = (route.method, route.path)
        if identity in seen:
            issues.append((base, "duplicate method and path"))
        seen.add(identity)
    return tuple(issues)


def _issues(config: Config) -> tuple[tuple[str, str], ...]:
    """Locate semantic problems shared by wire and direct record validation."""
    issues: list[tuple[str, str]] = []
    for key, identities in (
        ("tests", tuple(command.directory for command in config.tests)),
        ("interface", tuple(command.language for command in config.interface)),
    ):
        if not identities:
            issues.append((f"$.{key}", "expected at least one entry"))
        if len(set(identities)) != len(identities):
            issues.append((f"$.{key}", "duplicate identity"))
    names = tuple(role.name for role in config.roles)
    if len(set(names)) != len(names):
        issues.append(("$.roles", "duplicate role override"))
    issues.extend(_positive_issues(_CAPS_KEY, config.caps))
    if not _is_positive(config.readiness_timeout_seconds):
        issues.append(("$.readiness_timeout_seconds", "expected a positive integer"))
    issues.extend(_positive_issues(_LIMITS_KEY, config.proxy_limits))
    issues.extend(_route_issues(config.proxy_extra_routes))
    return tuple(issues)


def config_problems(config: Config) -> tuple[str, ...]:
    """Return semantic problems in an already constructed config record."""
    return tuple(f"{key}: {reason}" for key, reason in _issues(config))
