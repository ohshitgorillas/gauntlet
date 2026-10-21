"""Red tests for the suppression gate's no_type_check ban through starred unpacking targets.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: any reference to `typing.no_type_check` or `typing.no_type_check_decorator`,
`typing_extensions` included, is a finding wherever it appears. The value of a list, tuple
or set display written in place is followed into the targets its items reach, for an
assignment and a `match` subject alike, and a set display, having no
item order, gives each target its items reach every one of them. A starred target is
bound to a list, never to the function, so a use of it is no finding; the line that puts
the function into the display is the finding.

The spec makes an assignment line a finding, as a `case` line is, but says where a `case`
line sits and not where the line of an assignment spanning several lines sits. So for such
an assignment the line its statement starts on may be reported or not, and each case lists
that line apart from the lines it must report.

Each seeded use spells only the bound name, never `no_type_check`, so only the gate's
resolution of names can report its line.
"""

from pathlib import Path

import pytest

from tests.support.suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


STARRED_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "loose, *rest = [",
            "    no_type_check,",
            "    no_type_check,",
            "]",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
            "",
            "",
            "chosen = rest",
        ),
        [1, 4, 5, 9],
        [3],
        id="starred-target-after-a-plain-one",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "*rest, loose = print, no_type_check",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
            "",
            "",
            "chosen = rest",
        ),
        [1, 3, 6],
        [],
        id="plain-target-after-the-starred-one-takes-the-function",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "[*rest, loose] = [",
            "    no_type_check,",
            "    no_type_check,",
            "    no_type_check,",
            "]",
            "",
            "",
            "chosen = rest[0]",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 4, 5, 6, 13],
        [3],
        id="starred-target-taking-every-item-but-the-last",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "first, *rest = {print, no_type_check}",
            "",
            "",
            "@first",
            "def seeded() -> None:",
            "    pass",
            "",
            "",
            "chosen = rest",
        ),
        [1, 3, 6],
        [],
        id="set-display-gives-the-plain-target-every-item",
    ),
    pytest.param(
        _source(
            "from typing_extensions import no_type_check_decorator",
            "",
            "first, (*rest, last) = print, (",
            "    no_type_check_decorator,",
            "    no_type_check_decorator,",
            ")",
            "",
            "",
            "chosen = rest",
            "unchecked = last(print)",
        ),
        [1, 4, 5, 10],
        [3],
        id="nested-starred-target-of-the-decorator-function",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "",
            "def outer() -> None:",
            "    loose, *rest = (",
            "        typing.no_type_check,",
            "        typing.no_type_check,",
            "    )",
            "    chosen = rest",
            "",
            "    @loose",
            "    def seeded() -> None:",
            "        pass",
        ),
        [6, 7, 11],
        [5],
        id="starred-target-in-a-function-scope",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match (",
            "    no_type_check,",
            "    no_type_check,",
            "):",
            "    case loose, *rest:",
            "        chosen = rest",
            "        unchecked = loose(print)",
        ),
        [1, 4, 5, 7, 9],
        [],
        id="starred-match-pattern",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "starred.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("source", "finding_lines", "statement_lines"), STARRED_SOURCES
)
def test_starred_target_is_bound_to_a_list_not_the_function(
    tmp_path: Path, source: str, finding_lines: list[int], statement_lines: list[int]
) -> None:
    """Report each reference line and each use of a plain target bound to the function, never a use of a starred one.

    A multi-line assignment's statement line may be reported too, since the spec does not say which line it has.
    """
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) in (
        finding_lines,
        sorted([*finding_lines, *statement_lines]),
    )
