"""Red tests for a comment that carries more than one suppression marker.

Sources: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate":
its opening paragraph (markers are found by tokenizing and match only inside a comment
token; a marker matches anywhere in the comment, ignoring case and the whitespace around
the colon and between its words; a comment that carries more than one marker is one
finding that names every marker it carries) and its first two items (a `noqa`,
`type: ignore`, `pyright: ignore`, `pragma: no cover` or `pragma: no mutate` comment; a
`# mypy:`, `# pyright:`, `# fmt: off` or `# fmt: skip` comment); and "Gates" (the count
line `<gate>: N finding(s) in M Python file(s)` is the last line a finished run prints).
"""

from pathlib import Path

import pytest

from gates.check_suppressions import find_suppressions, main

SEVERAL_MARKER_COMMENTS = [
    ("value = 1  # noqa  type: ignore", ("noqa", "typeignore")),
    ("value = 1  # type: ignore  # noqa", ("typeignore", "noqa")),
    ("# pragma: no cover; pragma: no mutate", ("pragmanocover", "pragmanomutate")),
    ("value = 1  # NOQA fmt:skip", ("noqa", "fmtskip")),
    ("# Pragma : No  Cover  mypy: strict", ("pragmanocover", "mypy")),
    ("value = 1  # noqa  type: ignore  fmt: skip", ("noqa", "typeignore", "fmtskip")),
]

COUNT_LINE = "check_suppressions: 1 finding(s) in 1 Python file(s)"


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "seeded.py"
    path.write_text(source, encoding="utf-8")
    return path


def _letters(text: str) -> str:
    return "".join(char for char in text.lower() if char.isalpha())


@pytest.mark.parametrize(("comment", "names"), SEVERAL_MARKER_COMMENTS)
def test_comment_with_several_markers_is_one_finding_naming_every_marker(tmp_path: Path, comment: str, names: tuple[str, ...]) -> None:
    """Report a comment carrying more than one marker as a single finding, on its line, that names every marker."""
    path = _seed(tmp_path, "first = 1\n" + comment + "\n")
    findings = find_suppressions(path)

    assert [(finding.line, [name in _letters(finding.marker) for name in names]) for finding in findings] == [(2, [True] * len(names))]


def test_several_marker_comments_on_separate_lines_are_separate_findings(tmp_path: Path) -> None:
    """Report each several-marker comment as its own finding, one per comment."""
    path = _seed(tmp_path, "value = 1  # noqa  type: ignore\nother = 2\n# pragma: no cover  fmt: off\n")

    assert [finding.line for finding in find_suppressions(path)] == [1, 3]


def test_gate_counts_a_several_marker_comment_as_one_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Count a comment carrying more than one marker as one finding in the gate's count line."""
    path = _seed(tmp_path, "value = 1  # noqa  type: ignore  fmt: skip\n")
    main([path])

    assert capsys.readouterr().out.splitlines()[-1] == COUNT_LINE
