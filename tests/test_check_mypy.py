# Copyright 2026 oh shit, gorillas!
"""Red tests for the mypy gate's configuration.

Source: the quality gates design spec under docs/superpowers/specs/, "Types", first bullet.
"""

from pathlib import Path

import pytest

from gates.check_mypy import main

UNTYPED_DEF = "def ping():\n    pass\n"

UNREACHABLE = "def pick(value: int) -> int:\n    if isinstance(value, int):\n        return value\n    return 0\n"

EXPLICIT_ANY = "from typing import Any\n\n\ndef keep(value: Any) -> None:\n    pass\n"

ANY_EXPRESSION = (
    "import json\n\n\ndef show(text: str) -> None:\n    print(json.loads(text))\n"
)

EXPLICIT_OVERRIDE = "class Base:\n    def run(self) -> int:\n        return 1\n\n\nclass Child(Base):\n    def run(self) -> int:\n        return 2\n"

POSSIBLY_UNDEFINED = (
    "def pick(flag: bool) -> int:\n    if flag:\n        value = 1\n    return value\n"
)

MUTABLE_OVERRIDE = (
    "class Base:\n    value: float = 0.0\n\n\nclass Child(Base):\n    value: int = 0\n"
)

UNUSED_AWAITABLE = "import asyncio\n\n\nasync def work() -> int:\n    return 1\n\n\nasync def start() -> None:\n    asyncio.ensure_future(work())\n"

TRUTHY_ITERABLE = "from collections.abc import Iterable\n\n\ndef has_items(items: Iterable[int]) -> bool:\n    if items:\n        return True\n    return False\n"

IGNORE_WITHOUT_CODE = "value: str = 1  # type: ignore\n"

NEWER_THAN_312 = "from warnings import deprecated\n"

PEP_695_ALIAS = "type Pair = tuple[int, int]\n\n\ndef first(pair: Pair) -> int:\n    return pair[0]\n"

BARE_GENERIC = "def count(items: list) -> int:\n    return 0\n"

NON_OVERLAPPING_EQUALITY = (
    "def same(left: int, right: str) -> bool:\n    return left == right\n"
)

REDUNDANT_CAST = "from typing import cast\n\nvalue = cast(int, 1)\n"

TRUTHY_BOOL = "class Box:\n    pass\n\n\nbox = Box()\nif box:\n    pass\n"

REDUNDANT_EXPR = "def check(value: int) -> None:\n    if isinstance(value, int) and value > 0:\n        pass\n"

REDUNDANT_SELF = "from typing import Self\n\n\nclass Node:\n    def copy(self: Self) -> Self:\n        return self\n"

UNIMPORTED_REVEAL = "reveal_type(1)\n"

DEPRECATED_CALL = 'from typing_extensions import deprecated\n\n\n@deprecated("use another")\ndef old() -> None:\n    pass\n\n\nold()\n'

NON_EXHAUSTIVE_MATCH = 'from enum import Enum\n\n\nclass Color(Enum):\n    RED = 1\n    BLUE = 2\n\n\ndef label(color: Color) -> str:\n    match color:\n        case Color.RED:\n            return "red"\n    return "other"\n'

UNUSED_IGNORE = "value: int = 1  # type: ignore[assignment]\n"

TYPEDDICT_PARTIAL_UPDATE = "from typing import TypedDict\n\n\nclass Foo(TypedDict):\n    a: int\n\n\nclass Bar(TypedDict):\n    a: int\n    b: int\n\n\ndef merge(foo: Foo, bar: Bar) -> None:\n    bar.update(foo)\n"

REEXPORT_SOURCE = "from json import JSONDecodeError\n"

REEXPORT_USER = "from helper import JSONDecodeError\n"

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "seeded.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(UNTYPED_DEF, id="untyped"),
        pytest.param(UNREACHABLE, id="unreachable"),
        pytest.param(EXPLICIT_ANY, id="any-written"),
        pytest.param(ANY_EXPRESSION, id="any-expr"),
        pytest.param(EXPLICIT_OVERRIDE, id="override"),
        pytest.param(POSSIBLY_UNDEFINED, id="undefined"),
        pytest.param(MUTABLE_OVERRIDE, id="mutable"),
        pytest.param(UNUSED_AWAITABLE, id="awaitable"),
        pytest.param(TRUTHY_ITERABLE, id="truthy-iter"),
        pytest.param(IGNORE_WITHOUT_CODE, id="bare-ignore"),
        pytest.param(NEWER_THAN_312, id="py-version"),
        pytest.param(BARE_GENERIC, id="generics"),
        pytest.param(NON_OVERLAPPING_EQUALITY, id="equality"),
        pytest.param(REDUNDANT_CAST, id="red-cast"),
        pytest.param(TRUTHY_BOOL, id="truthy-bool"),
        pytest.param(REDUNDANT_EXPR, id="red-expr"),
        pytest.param(REDUNDANT_SELF, id="red-self"),
        pytest.param(UNIMPORTED_REVEAL, id="reveal"),
        pytest.param(DEPRECATED_CALL, id="deprecated"),
        pytest.param(NON_EXHAUSTIVE_MATCH, id="exhaustive"),
        pytest.param(UNUSED_IGNORE, id="unused-ign"),
        pytest.param(TYPEDDICT_PARTIAL_UPDATE, id="extra-check"),
    ],
)
def test_rejects(tmp_path: Path, source: str) -> None:
    """Each seeded file breaks exactly one setting the Types bullet requires."""
    path = _seed(tmp_path, source)

    assert main([path]) != 0


def test_rejects_reexport(tmp_path: Path) -> None:
    """Importing a name a sibling module only imported itself breaks strict's no_implicit_reexport."""
    helper = tmp_path / "helper.py"
    helper.write_text(REEXPORT_SOURCE, encoding="utf-8")
    user = tmp_path / "user.py"
    user.write_text(REEXPORT_USER, encoding="utf-8")

    assert main([helper, user]) != 0


def test_passes_clean(tmp_path: Path) -> None:
    """A fully annotated file with no Any passes the gate."""
    path = _seed(tmp_path, CLEAN)

    assert main([path]) == 0


def test_passes_pep695(tmp_path: Path) -> None:
    """A PEP 695 type alias is valid under python_version 3.12."""
    path = _seed(tmp_path, PEP_695_ALIAS)

    assert main([path]) == 0
