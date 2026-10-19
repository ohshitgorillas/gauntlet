"""Red tests for the suppression gate's no_type_check ban across the control flow bindings pass through.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: a use of a name is a finding when any binding of that name, in the scope
Python's scoping rules resolve the use to, is `typing.no_type_check` or
`typing.no_type_check_decorator`, with no path or reachability condition. A binding
counts whether it is conditional, deleted on some or every path, or behind code that
never runs, and a binding made through `global` or `nonlocal`, in a class body, a
comprehension or by an assignment expression counts whether or not its body ever runs.
Any reference to either function is a finding wherever it appears, so the import line is
a finding too; a line that binds, deletes or declares the name with no reference to the
function is not a use and not a finding.

Each seeded use spells only the bound name, never `no_type_check`, so only the gate's
resolution of names can report its line.
"""

from pathlib import Path

import pytest

from gates.check_suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


BRANCH_SOURCES = [
    pytest.param(
        _source(
            "flag = False",
            "if flag:",
            "    from typing import no_type_check as loose",
            "else:",
            "    loose = print",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [3, 8],
        id="if-body-with-other-binding-in-else",
    ),
    pytest.param(
        _source(
            "flag = False",
            "match flag:",
            "    case True:",
            "        from typing import no_type_check as loose",
            "    case _:",
            "        loose = print",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [4, 9],
        id="match-case-with-other-binding-in-later-case",
    ),
]

REMOVED_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check as loose",
            "",
            "del loose",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 6],
        id="deleted-on-every-path",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check as loose",
            "",
            "flag = False",
            "if flag:",
            "    del loose",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 8],
        id="deleted-on-some-path",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check as loose",
            "",
            "loose = print",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 6],
        id="overwritten-before-the-use",
    ),
]

UNREACHABLE_SOURCES = [
    pytest.param(
        _source(
            "def outer() -> None:",
            "    @loose",
            "    def seeded() -> None:",
            "        pass",
            "",
            "    return",
            "    from typing import no_type_check as loose",
        ),
        [2, 7],
        id="after-return-in-the-same-function",
    ),
    pytest.param(
        _source(
            "def seeded() -> None:",
            "    pass",
            "",
            "",
            "unchecked = loose(seeded)",
            "raise SystemExit",
            "from typing import no_type_check as loose",
        ),
        [5, 7],
        id="after-raise-at-module-level",
    ),
]

ORDER_SOURCES = [
    pytest.param(
        _source(
            "@loose",
            "def seeded() -> None:",
            "    pass",
            "",
            "",
            "from typing import no_type_check as loose",
        ),
        [1, 6],
        id="module-binding-after-the-use",
    ),
    pytest.param(
        _source(
            "def outer() -> None:",
            "    @loose",
            "    def seeded() -> None:",
            "        pass",
            "",
            "    from typing import no_type_check as loose",
        ),
        [2, 6],
        id="function-binding-after-the-use",
    ),
]

UNRUN_BODY_SOURCES = [
    pytest.param(
        _source(
            "def install() -> None:",
            "    global loose",
            "    from typing import no_type_check as loose",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [3, 6],
        id="global-in-a-function-never-called",
    ),
    pytest.param(
        _source(
            "def outer() -> None:",
            "    loose = print",
            "",
            "    def inner() -> None:",
            "        nonlocal loose",
            "        from typing import no_type_check as loose",
            "",
            "    @loose",
            "    def seeded() -> None:",
            "        pass",
        ),
        [6, 8],
        id="nonlocal-in-a-function-never-called",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "flow.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "finding_lines"), BRANCH_SOURCES)
def test_binding_in_any_branch_reaches_the_use(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the import line and the use line, each once and nothing else, when no_type_check is bound in one branch and another name in a later one."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines


@pytest.mark.parametrize(("source", "finding_lines"), REMOVED_SOURCES)
def test_deleted_or_overwritten_binding_still_reaches_the_use(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the import line and the use line, each once and nothing else, when the no_type_check binding is deleted or rebound before the use."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines


@pytest.mark.parametrize(("source", "finding_lines"), UNREACHABLE_SOURCES)
def test_binding_behind_code_that_never_runs_reaches_the_use(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the use line and the import line, each once and nothing else, when the no_type_check binding sits after a return or raise."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines


@pytest.mark.parametrize(("source", "finding_lines"), ORDER_SOURCES)
def test_binding_after_the_use_reaches_it(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the use line and the import line, each once and nothing else, when the no_type_check binding comes after the use in the same scope."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines


@pytest.mark.parametrize(("source", "finding_lines"), UNRUN_BODY_SOURCES)
def test_binding_in_a_body_that_never_runs_reaches_the_use(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the import line and the use line, each once and nothing else, when no_type_check is bound through global or nonlocal in a function never called."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
