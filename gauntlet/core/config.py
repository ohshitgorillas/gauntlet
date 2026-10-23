# Copyright 2026 oh shit, gorillas!
"""Validate repository configuration without I/O."""

from __future__ import annotations

from dataclasses import fields, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataclasses import Field

from gauntlet.core.codec import json_value
from gauntlet.core.errors import ConfigError, RecordError
from gauntlet.core.records import (
    Caps,
    Config,
    InterfaceCommand,
    Json,
    RoleSetting,
    TestCommand,
)


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


def _caps(value: Json) -> Caps:
    """Override supplied caps using the canonical record defaults."""
    caps = Caps()
    entry = _mapping(value, "$.caps")
    cap_fields: tuple[Field[object], ...] = fields(caps)
    _keys(entry, {field.name for field in cap_fields}, "$.caps")
    for name, cap in entry.items():
        if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
            path = f"$.caps.{name}"
            raise ConfigError(path, "expected a positive integer")
        caps = replace(caps, **{name: cap})
    return caps


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
    )


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
    cap_fields: tuple[Field[object], ...] = fields(config.caps)
    for field in cap_fields:
        cap: int = getattr(config.caps, field.name)
        if isinstance(cap, bool) or cap <= 0:
            issues.append((f"$.caps.{field.name}", "expected a positive integer"))
    return tuple(issues)


def config_problems(config: Config) -> tuple[str, ...]:
    """Return semantic problems in an already constructed config record."""
    return tuple(f"{key}: {reason}" for key, reason in _issues(config))
