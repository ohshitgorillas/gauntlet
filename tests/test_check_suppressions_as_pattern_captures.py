"""Red tests for the suppression gate's no_type_check ban through match `as` patterns.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: the name an `as` pattern binds is a capture, and binds the function when
what its pattern matched is `typing.no_type_check` or `typing.no_type_check_decorator`,
`typing_extensions` included. The value is followed when the `match` subject is the
function itself or a list, tuple or set display written in place, into the targets its
items reach. The line of a `case` whose capture pattern binds either function is a
finding, as an assignment line is, and the line of a `case` is the line its `case`
keyword sits on, however many lines its pattern spans. A use of a name is a finding when
any binding of that name, in the scope the use resolves to, is either function. Any
reference to either function is a finding wherever it appears, so the import line and
the match line whose subject names the function are findings too.

An `as` pattern whose pattern matched a display holding the function, rather than the
function, binds that display, never the function, so a use of its name is no finding;
nor is a use of the name of an `as` pattern over a subject that is another value.

Each seeded use spells only the bound name, never `no_type_check`, so only the gate's
resolution of names can report its line.
"""

from pathlib import Path

import pytest

from gates.check_suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


BINDING_AS_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match no_type_check:",
            "    case _ as loose:",
            "        pass",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 3, 4, 8],
        id="wildcard-as-over-the-function-with-a-later-use",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match no_type_check:",
            "    case loose as alias:",
            "        pass",
            "",
            "",
            "unchecked = alias(print)",
        ),
        [1, 3, 4, 8],
        id="as-around-a-capture-with-a-use-of-the-as-name",
    ),
    pytest.param(
        _source(
            "from typing_extensions import no_type_check_decorator",
            "",
            "match [no_type_check_decorator]:",
            "    case [_ as loose]:",
            "        pass",
        ),
        [1, 3, 4],
        id="as-inside-a-sequence-pattern-over-a-list-display",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match (print, no_type_check):",
            "    case (_ as other, _ as caught):",
            "        pass",
            "",
            "",
            "unchecked = other(print)",
            "checked = caught(print)",
        ),
        [1, 3, 4, 9],
        id="as-on-the-later-item-of-a-tuple-display-only-that-name-is-the-function",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "match typing.no_type_check:",
            "    case _ as loose:",
            "        pass",
        ),
        [3, 4],
        id="as-over-the-module-attribute",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "",
            "def outer() -> None:",
            "    match no_type_check:",
            "        case _ as loose:",
            "            pass",
            "",
            "    @loose",
            "    def seeded() -> None:",
            "        pass",
        ),
        [1, 5, 6, 9],
        id="as-in-a-function-scope-with-a-later-use",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match [no_type_check]:",
            "    case [",
            "        _ as loose",
            "    ]:",
            "        pass",
        ),
        [1, 3, 4],
        id="as-in-a-pattern-spanning-lines-reports-the-case-keyword-line",
    ),
]

MIXED_AS_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match [no_type_check]:",
            "    case [_ as item] as whole:",
            "        pass",
            "",
            "",
            "checks = whole",
            "unchecked = item(print)",
        ),
        [1, 3, 4, 9],
        id="as-around-a-sequence-pattern-binds-the-list-display-not-the-function",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            'match ("seeded", no_type_check):',
            "    case (label, _ as caught) as pair:",
            "        pass",
            "",
            "",
            "checks = pair",
            "checked = caught(print)",
        ),
        [1, 3, 4, 9],
        id="as-around-a-sequence-pattern-binds-the-tuple-display-not-the-function",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match print:",
            "    case _ as loose:",
            "        pass",
            "",
            "match no_type_check:",
            "    case _ as caught:",
            "        pass",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
            "",
            "",
            "@caught",
            "def other() -> None:",
            "    pass",
        ),
        [1, 7, 8, 17],
        id="as-over-another-value-beside-an-as-over-the-function",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "aliased.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "finding_lines"), BINDING_AS_SOURCES)
def test_as_name_whose_pattern_matched_the_function_is_a_capture_of_it(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the case line whose as name takes the function, beside every reference and use line, each once and nothing else."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines


@pytest.mark.parametrize(("source", "finding_lines"), MIXED_AS_SOURCES)
def test_only_the_as_name_whose_pattern_matched_the_function_binds_it(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the case line and use of the as name that takes the function and leave out every use of an as name that takes a display or another value."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
