"""Red tests for a first-item marker that contains a second-item marker.

Sources: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate":
its opening paragraph (a marker matches anywhere in the comment, ignoring case and the
whitespace around the colon and between its words; a marker of the first item that
contains a marker of the second, as `# pyright: ignore` contains `# pyright:`, carries
both, and its comment is one finding naming both) and its first two items (a
`pyright: ignore` comment; a `# pyright:` comment).
"""

from pathlib import Path

import pytest

from gates.check_suppressions import find_suppressions

NESTED_MARKER_COMMENTS = [
    "# pyright: ignore",
    "value = 1  # pyright: ignore[reportUnknownMemberType]",
    "# PyRight :Ignore",
    "value = 1  # kept as written; pyright:ignore",
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "seeded.py"
    path.write_text(source, encoding="utf-8")
    return path


def _letters(text: str) -> str:
    return "".join(char for char in text.lower() if char.isalpha())


@pytest.mark.parametrize("comment", NESTED_MARKER_COMMENTS)
def test_pyright_ignore_comment_is_one_finding_naming_both_markers(tmp_path: Path, comment: str) -> None:
    """Report a `pyright: ignore` comment as one finding, on its line, naming both `pyright: ignore` and the `# pyright:` it contains."""
    path = _seed(tmp_path, "first = 1\n" + comment + "\n")
    findings = find_suppressions(path)

    assert [(finding.line, _letters(finding.marker).count("pyright") >= 2, "ignore" in _letters(finding.marker)) for finding in findings] == [(2, True, True)]
