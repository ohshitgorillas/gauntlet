# Copyright 2026 oh shit, gorillas!
"""Read repository configuration from an explicit root."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from gauntlet.core.codec import json_value
from gauntlet.core.config import config_from_json
from gauntlet.core.errors import ConfigError, RecordError, StorageError

if TYPE_CHECKING:
    from pathlib import Path

    from gauntlet.core.records import Config

_MAPPING_NODE: type[MappingNode] = MappingNode
_SEQUENCE_NODE: type[SequenceNode] = SequenceNode
_SCALAR_NODE: type[ScalarNode] = ScalarNode


class _Loader(Protocol):
    """The typed interface used at the safe YAML loader boundary."""

    def get_single_node(self) -> Node | None: ...

    def construct_document(self, node: Node) -> object: ...

    def dispose(self) -> None: ...


def _nodes(node: Node, path: str, ancestors: tuple[Node, ...]) -> None:
    """Check YAML-only constructs before the safe loader builds containers."""
    if node in ancestors:
        raise ConfigError(path, "recursive YAML alias")
    if node.tag not in {
        "tag:yaml.org,2002:map",
        "tag:yaml.org,2002:seq",
        "tag:yaml.org,2002:str",
        "tag:yaml.org,2002:null",
        "tag:yaml.org,2002:bool",
        "tag:yaml.org,2002:int",
        "tag:yaml.org,2002:float",
    }:
        raise ConfigError(path, "expected a JSON-compatible YAML tag")
    parents = (*ancestors, node)
    if isinstance(node, _MAPPING_NODE):
        _mapping_nodes(node, path, parents)
    elif isinstance(node, _SEQUENCE_NODE):
        children: list[Node] = node.value
        for index, child in enumerate(children):
            _nodes(child, f"{path}[{index}]", parents)


def _mapping_nodes(node: MappingNode, path: str, parents: tuple[Node, ...]) -> None:
    """Reject duplicate and non-text YAML keys before dict construction."""
    seen: set[str] = set()
    entries: list[tuple[Node, Node]] = node.value
    for key, child in entries:
        if not isinstance(key, _SCALAR_NODE) or key.tag != "tag:yaml.org,2002:str":
            raise ConfigError(path, "expected a string mapping key")
        location = f"{path}.{key.value}"
        if key.value in seen:
            raise ConfigError(location, "duplicate YAML key")
        seen.add(key.value)
        _nodes(child, location, parents)


def _safe_loader(text: str) -> _Loader:
    """Expose the safe loader through its typed construction interface."""
    return yaml.SafeLoader(text)


def _load(text: str) -> object:
    """Construct only safe YAML after checking its unconstructed nodes."""
    loader = _safe_loader(text)
    try:
        node = loader.get_single_node()
        if node is None:
            return None
        _nodes(node, "$", ())
        return loader.construct_document(node)
    finally:
        loader.dispose()


def read_config(root: Path) -> Config:
    """Read the assigned root's file and delegate its schema to the core."""
    path = root / "gauntlet.yaml"
    location = "$"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise StorageError(str(path), "read", error.errno) from error
    except UnicodeError as error:
        raise ConfigError(location, "expected UTF-8 YAML") from error
    try:
        value = json_value(_load(text))
    except (yaml.YAMLError, KeyError, ValueError) as error:
        raise ConfigError(location, "invalid YAML") from error
    except RecordError as error:
        raise ConfigError(error.location, error.reason) from error
    return config_from_json(value)
