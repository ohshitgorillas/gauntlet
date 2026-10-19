"""Red tests for the suppression gate's no_type_check ban through unpacking assignments.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: any reference to `typing.no_type_check` or `typing.no_type_check_decorator`,
`typing_extensions` included, is a finding wherever it appears, and a use of a name is a
finding when any binding of that name, in the scope Python's scoping rules resolve the
use to, is either function. The value is followed into the targets its items reach when
it is a list, tuple or set display written in place, and the same holds for the targets
of an assignment whose value is such a display; a container reached through another name
is not followed, and the line that puts the function into it is the finding.

Each seeded use spells only the bound name, never `no_type_check`, so only the gate's
resolution of names can report its line. A target that takes another item of the display
is not bound to the function, so a use of it is not a finding.
"""

from pathlib import Path

import pytest

from gates.check_suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


UNPACKING_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            'label, loose = "seeded", no_type_check',
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 3, 6],
        id="tuple-display-without-parentheses",
    ),
    pytest.param(
        _source(
            "from typing_extensions import no_type_check_decorator",
            "",
            "[first, loose] = [print, no_type_check_decorator]",
            "",
            "",
            "unchecked = loose(print)",
        ),
        [1, 3, 6],
        id="list-display-of-the-decorator-function",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "(first, loose) = (print, typing.no_type_check)",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [3, 6],
        id="parenthesized-tuple-holding-the-module-attribute",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "first, (second, loose) = print, (print, no_type_check)",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 3, 6],
        id="nested-target-reached-by-a-nested-display",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "(loose,) = {no_type_check}",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 3, 6],
        id="set-display-of-one-item",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "",
            "def outer() -> None:",
            "    first, loose = print, no_type_check",
            "",
            "    @loose",
            "    def seeded() -> None:",
            "        pass",
        ),
        [1, 5, 7],
        id="unpacking-in-a-function-scope",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "loose, other = no_type_check, print",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
            "",
            "",
            "@other",
            "def checked() -> None:",
            "    pass",
        ),
        [1, 3, 6],
        id="target-taking-another-item-is-not-the-function",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "held = [print, no_type_check]",
            "first, kept = held",
            "spare, loose = print, no_type_check",
            "",
            "",
            "@kept",
            "def checked() -> None:",
            "    pass",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 3, 5, 13],
        id="display-reached-through-another-name-is-not-followed",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "unpacked.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "finding_lines"), UNPACKING_SOURCES)
def test_unpacking_target_taking_the_function_reaches_the_use(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report each reference line and each use of a target bound to the function, each once and nothing else."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
