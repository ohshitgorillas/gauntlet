"""Red tests for the pyright gate's mode.

Source: the quality gates design spec under docs/superpowers/specs/, "Types", second bullet.

Each rejected source passes pyright's standard mode and breaks one rule that
strict mode raises to an error, so only a gate running pyright in strict mode
rejects all of them.
"""

from pathlib import Path

import pytest

from gates.check_pyright import main

MISSING_PARAMETER_TYPE = "def double(value) -> int:\n    return value * 2\n"

UNKNOWN_VARIABLE = "def make() -> None:\n    items = []\n    print(items)\n"

MISSING_TYPE_ARGUMENT = "def count(items: list) -> int:\n    return len(items)\n"

UNUSED_IMPORT = "import os\n"

UNUSED_VARIABLE = "def run() -> None:\n    value = 1\n"

UNUSED_FUNCTION = "def _helper() -> None:\n    pass\n"

UNUSED_EXPRESSION = "def show(value: int) -> None:\n    value + 1\n"

DUPLICATE_IMPORT = "import os\nimport os\n\nprint(os.sep)\n"

CONSTANT_REDEFINITION = "LIMIT = 1\nLIMIT = 2\n"

TYPE_COMMENT = "value = 1  # type: int\n"

UNNECESSARY_ISINSTANCE = "def pick(value: int) -> int:\n    if isinstance(value, int):\n        return value\n    return 0\n"

UNNECESSARY_COMPARISON = (
    "def same(left: int, right: str) -> bool:\n    return left == right\n"
)

UNNECESSARY_CONTAINS = 'def has(value: int) -> bool:\n    return value in ("a", "b")\n'

UNNECESSARY_CAST = "from typing import cast\n\n\ndef keep(value: int) -> int:\n    return cast(int, value)\n"

NON_EXHAUSTIVE_MATCH = 'from enum import Enum\n\n\nclass Color(Enum):\n    RED = 1\n    BLUE = 2\n\n\ndef label(color: Color) -> str:\n    match color:\n        case Color.RED:\n            return "red"\n    return "other"\n'

DEPRECATED_CALL = 'from typing_extensions import deprecated\n\n\n@deprecated("use another")\ndef old() -> None:\n    pass\n\n\nold()\n'

PRIVATE_SOURCE = "_secret = 1\n"

PRIVATE_USER = "from helper import _secret\n\nprint(_secret)\n"

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "seeded.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(MISSING_PARAMETER_TYPE, id="param-type"),
        pytest.param(UNKNOWN_VARIABLE, id="unknown-var"),
        pytest.param(MISSING_TYPE_ARGUMENT, id="type-arg"),
        pytest.param(UNUSED_IMPORT, id="unused-import"),
        pytest.param(UNUSED_VARIABLE, id="unused-var"),
        pytest.param(UNUSED_FUNCTION, id="unused-func"),
        pytest.param(UNUSED_EXPRESSION, id="unused-expr"),
        pytest.param(DUPLICATE_IMPORT, id="dup-import"),
        pytest.param(CONSTANT_REDEFINITION, id="constant"),
        pytest.param(TYPE_COMMENT, id="type-comment"),
        pytest.param(UNNECESSARY_ISINSTANCE, id="isinstance"),
        pytest.param(UNNECESSARY_COMPARISON, id="comparison"),
        pytest.param(UNNECESSARY_CONTAINS, id="contains"),
        pytest.param(UNNECESSARY_CAST, id="cast"),
        pytest.param(NON_EXHAUSTIVE_MATCH, id="exhaustive"),
        pytest.param(DEPRECATED_CALL, id="deprecated"),
    ],
)
def test_rejects(tmp_path: Path, source: str) -> None:
    """Each seeded file breaks one rule only pyright's strict mode makes an error."""
    path = _seed(tmp_path, source)

    assert main([path]) != 0


def test_rejects_private_usage(tmp_path: Path) -> None:
    """Importing a sibling module's private name breaks strict's reportPrivateUsage."""
    helper = tmp_path / "helper.py"
    helper.write_text(PRIVATE_SOURCE, encoding="utf-8")
    user = tmp_path / "user.py"
    user.write_text(PRIVATE_USER, encoding="utf-8")

    assert main([helper, user]) != 0


def test_passes_clean(tmp_path: Path) -> None:
    """A fully annotated file with nothing unknown or unused passes the gate."""
    path = _seed(tmp_path, CLEAN)

    assert main([path]) == 0
