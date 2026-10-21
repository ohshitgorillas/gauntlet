"""Red tests for the line the suppression gate gives a case whose pattern spans lines.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: a `match` capture pattern that takes `typing.no_type_check` or
`typing.no_type_check_decorator`, `typing_extensions` included, as its value is a
binding that is the function, and the value is followed when the `match` subject is the
function itself or a list or tuple display written in place, into the targets its items
reach. The line of a `case` whose capture pattern binds either function is a finding, as
an assignment line is, and the line of a `case` is the line its `case` keyword sits on,
however many lines its pattern spans. Any reference to either function is a finding
wherever it appears, so the import line and the match line whose subject names the
function are findings too.

Each seeded pattern puts its capture on a line below its `case` keyword, so a gate that
reports the line the capture name sits on, or the last line of the pattern, reports a
line the documents name as no finding.
"""

from pathlib import Path

import pytest

from tests.support.suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


SPANNING_CASE_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match no_type_check:",
            "    case (",
            "        loose",
            "    ):",
            "        pass",
        ),
        [1, 3, 4],
        id="parenthesized-bare-capture-on-the-next-line",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match no_type_check:",
            "    case \\",
            "        loose:",
            "        pass",
        ),
        [1, 3, 4],
        id="bare-capture-after-a-line-continuation",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            'match ["seeded", no_type_check]:',
            "    case [",
            "        label,",
            "        loose,",
            "    ]:",
            "        pass",
        ),
        [1, 3, 4],
        id="sequence-pattern-over-a-list-display-with-the-capture-two-lines-down",
    ),
    pytest.param(
        _source(
            "from typing_extensions import no_type_check_decorator",
            "",
            "match (print, no_type_check_decorator):",
            "    case (",
            "        other,",
            "        loose,",
            "    ):",
            "        pass",
        ),
        [1, 3, 4],
        id="sequence-pattern-over-a-tuple-display-taking-the-decorator-function",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match no_type_check:",
            "    case 1:",
            "        pass",
            "    case (",
            "        loose",
            "    ):",
            "        pass",
        ),
        [1, 3, 6],
        id="spanning-capture-case-after-a-literal-case",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "",
            "def outer() -> None:",
            "    match [no_type_check]:",
            "        case [",
            "            loose",
            "        ]:",
            "            pass",
        ),
        [1, 5, 6],
        id="spanning-capture-in-a-function-scope",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match no_type_check:",
            "    case (",
            "        loose",
            "    ):",
            "        pass",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 3, 4, 10],
        id="spanning-capture-with-a-later-use",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "spanned.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "finding_lines"), SPANNING_CASE_SOURCES)
def test_spanning_case_is_reported_on_its_case_keyword_line(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the case keyword's line for a capture that takes the function, beside every reference and use line, each once and nothing else."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
