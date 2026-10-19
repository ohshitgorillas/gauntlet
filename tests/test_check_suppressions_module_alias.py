"""Red tests for the suppression gate on `no_type_check` reached through a name bound to its module by assignment.

Sources: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item (the ban is on the function, not its spelling: it covers `typing.no_type_check`
and `typing.no_type_check_decorator`, `typing_extensions` included, and any reference to
either is a finding wherever it appears: imported, bound to another name, used as a
decorator or called); and "Gates" (exit 1 with one or more findings).
"""

from pathlib import Path

import pytest

from gates.check_suppressions import find_suppressions, main

FINDINGS_STATUS = 1

ALIASED_MODULE_SOURCES = [
    ("import typing\nt = typing\n\n\n@t.no_type_check\ndef seeded() -> None:\n    pass\n", 5),
    ("import typing_extensions\nte = typing_extensions\nloose = te.no_type_check_decorator\n", 3),
    ("import typing as typ\nt = typ\nloose = t.no_type_check\n", 3),
    ("import typing\nt = typing\nu = t\nloose = u.no_type_check_decorator\n", 4),
    ("import typing\n\nt: object = typing\nloose = t.no_type_check\n", 4),
    ("import typing\nt = typing\n\n\ndef seeded() -> None:\n    pass\n\n\nunchecked = t.no_type_check(seeded)\n", 9),
    ("import typing_extensions\n\n\ndef build():\n    te = typing_extensions\n    return te.no_type_check\n", 6),
]

LOOKALIKE_ALIAS_SOURCES = [
    ("import helpers\nimport typing\nh = helpers\nt = typing\n\n\n@h.no_type_check\ndef seeded() -> None:\n    pass\n\n\nloose = t.no_type_check\n", [12]),
    ("import typing\nt = typing\n\n\n@t.final\nclass Seeded:\n    pass\n\n\nloose = t.no_type_check_decorator\n", [10]),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "seeded.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "line"), ALIASED_MODULE_SOURCES)
def test_reference_through_an_assigned_module_name_is_a_finding(tmp_path: Path, source: str, line: int) -> None:
    """Report the line that reaches the function through a name the module was assigned to, as its one finding, and not the lines that import or rebind the module."""
    path = _seed(tmp_path, source)

    assert [finding.line for finding in find_suppressions(path)] == [line]


@pytest.mark.parametrize("source", [source for source, _ in ALIASED_MODULE_SOURCES])
def test_gate_exits_with_findings_status_on_an_assigned_module_name(tmp_path: Path, source: str) -> None:
    """Exit with the findings status on a file that reaches the function through an assigned module name."""
    path = _seed(tmp_path, source)

    assert main([path]) == FINDINGS_STATUS


@pytest.mark.parametrize(("source", "lines"), LOOKALIKE_ALIAS_SOURCES)
def test_only_the_line_reaching_the_function_is_a_finding(tmp_path: Path, source: str, lines: list[int]) -> None:
    """Report the reference through the assigned typing name, not an attribute of a name bound to another module or another typing function."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == lines
