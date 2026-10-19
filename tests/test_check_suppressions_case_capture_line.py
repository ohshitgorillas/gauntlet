"""Red tests for the suppression gate's finding on the case line of a match capture.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: a `match` capture pattern that takes `typing.no_type_check` or
`typing.no_type_check_decorator`, `typing_extensions` included, as its value is a
binding that is the function. The value is followed when the `match` subject is the
function itself, or a list, tuple or set display written in place, into the targets its
items reach; a container reached through another name is not followed, and the line
that puts the function into it is the finding. The line of a `case` whose capture
pattern binds either function is a finding, as an assignment line is. Any reference to
either function is a finding wherever it appears, so the import line and the match line
whose subject names the function are findings too.

A case line that binds no name to either function is not one: a literal pattern, a
capture that takes another value, the wildcard `_`, and a capture whose subject reaches
the function only through another name.
"""

from pathlib import Path

import pytest

from gates.check_suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


BINDING_CASE_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match no_type_check:",
            "    case loose:",
            "        pass",
        ),
        [1, 3, 4],
        id="bare-capture-of-the-function",
    ),
    pytest.param(
        _source(
            "from typing_extensions import no_type_check_decorator",
            "",
            "match [no_type_check_decorator]:",
            "    case [loose]:",
            "        pass",
        ),
        [1, 3, 4],
        id="capture-inside-a-sequence-pattern-over-a-list-display",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            'match ("seeded", no_type_check):',
            "    case (label, loose):",
            "        pass",
        ),
        [1, 3, 4],
        id="capture-of-the-later-item-of-a-tuple-display",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "match typing.no_type_check:",
            "    case loose:",
            "        pass",
        ),
        [3, 4],
        id="capture-of-the-module-attribute",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "",
            "def outer() -> None:",
            "    match no_type_check:",
            "        case loose:",
            "            pass",
        ),
        [1, 5, 6],
        id="capture-in-a-function-scope",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match no_type_check:",
            "    case loose:",
            "        pass",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 3, 4, 8],
        id="capture-with-a-later-use",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match no_type_check:",
            "    case 1:",
            "        pass",
            "    case loose:",
            "        pass",
        ),
        [1, 3, 6],
        id="capture-case-after-a-literal-case",
    ),
]

MIXED_CASE_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match print:",
            "    case loose:",
            "        pass",
            "",
            "match no_type_check:",
            "    case caught:",
            "        pass",
        ),
        [1, 7, 8],
        id="capture-of-another-value-beside-a-capture-of-the-function",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match (print, no_type_check):",
            "    case (loose, _):",
            "        pass",
            "    case (other, caught):",
            "        pass",
        ),
        [1, 3, 6],
        id="function-item-reaches-the-wildcard-then-a-capture",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "checks = [no_type_check]",
            "match checks:",
            "    case [loose]:",
            "        pass",
            "",
            "match [no_type_check]:",
            "    case [caught]:",
            "        pass",
        ),
        [1, 3, 8, 9],
        id="container-through-another-name-beside-a-display-written-in-place",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "cased.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "finding_lines"), BINDING_CASE_SOURCES)
def test_case_line_whose_capture_binds_the_function_is_a_finding(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the case line whose capture takes the function, beside every reference and use line, each once and nothing else."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines


@pytest.mark.parametrize(("source", "finding_lines"), MIXED_CASE_SOURCES)
def test_only_the_case_line_whose_capture_binds_the_function_is_a_finding(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the case line whose capture takes the function and leave out a case line whose captures take no function, each line once and nothing else."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
