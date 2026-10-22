# Copyright 2026 oh shit, gorillas!
"""Red tests for the pyright gate on the gates core.

Source: the gates core design spec under docs/superpowers/specs/, section 2, "A gate on the core", the C2 row of
section 4, and decision 2 (iii) and (iv), 14 and 22; the quality gates design spec, "Gates", intro, for the count line,
the exit status 2, the pin and the parse rules.

An empty run prints the nothing-checked line and the count line for no file, then exits 1. A file given twice is one
file in M. A checker run counts as finished only when its exit status is the one its report calls for: pyright exits 1
when its report holds an error and 0 when it holds none, so an exit 0 over an error is not a finished run. A checker
whose output holds no report the gate can read ends the run unfinished, printing the checker's whole output, then the
count line. The pin error is the gate's own line, and pyright is not run. A diagnostic pyright reports with no rule in
a file that cannot be parsed is printed as the checker's report of not finishing it, and is no finding; a warning raised by a parse is printed too.
The gate runs pyright in the project's directory with the project's own settings file.
"""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from gates.check_pyright import GATE, main
from gates.core.checker import Completed
from gates.core.runner import run_gate
from tests.support.capture import captured
from tests.support.fake import FakeRunner, completed
from tests.support.project import scaffold

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

INVALID_ESCAPE = 'PATTERN = "\\d"\n'

UNPARSEABLE = "def broken(:\n    return\n"

COUNT_ONE = "check_pyright: 1 finding(s) in 1 Python file(s)\n"

COUNT_NONE = "check_pyright: 0 finding(s) in 1 Python file(s)\n"


def _entry(
    path: Path, severity: str = "error", rule: str | None = "reportAssignmentType"
) -> dict[str, object]:
    entry: dict[str, object] = {
        "file": str(path.resolve()),
        "severity": severity,
        "message": "bad type",
        "range": {
            "start": {"line": 2, "character": 4},
            "end": {"line": 2, "character": 9},
        },
    }
    if rule is not None:
        entry["rule"] = rule
    return entry


def _line(
    path: Path, severity: str = "error", rule: str | None = "reportAssignmentType"
) -> str:
    suffix = "" if rule is None else f" ({rule})"
    return f"{path.resolve()}:3:5 - {severity}: bad type{suffix}\n"


def _report(entries: Sequence[Mapping[str, object]], analyzed: int = 1) -> str:
    summary: dict[str, object] = {"filesAnalyzed": analyzed}
    document: dict[str, object] = {
        "generalDiagnostics": list(entries),
        "summary": summary,
    }
    return json.dumps(document)


def _run(
    tmp_path: Path,
    files: Mapping[str, str],
    paths: Sequence[str],
    reply: Completed,
    pyproject: str | None = None,
) -> tuple[int, list[str], FakeRunner]:
    """Run the gate over the named files of a scaffolded project against one canned pyright reply."""
    project = scaffold(tmp_path, files, pyproject=pyproject)
    fake = FakeRunner([reply])
    output = captured(
        lambda: run_gate(
            GATE, [tmp_path / name for name in paths], project=project, process=fake
        )
    )
    return output.result, output.merged, fake


def test_empty_run_prints_both_lines(tmp_path: Path) -> None:
    """A run with no Python file among the paths prints the nothing-checked line, then the count line, and exits 1."""
    note = tmp_path / "notes.txt"
    note.write_text("text\n", encoding="utf-8")

    output = captured(lambda: main([note]))

    assert (output.result, output.merged) == (
        1,
        [
            "check_pyright: nothing checked: no Python file among the 1 file(s) given\n",
            "check_pyright: 0 finding(s) in 0 Python file(s)\n",
        ],
    )


def test_a_file_given_twice_is_one_file(tmp_path: Path) -> None:
    """The same file named twice counts once in M, and pyright is handed it once."""
    status, lines, fake = _run(
        tmp_path,
        {"clean.py": CLEAN},
        ["clean.py", "clean.py"],
        completed(0, _report([])),
    )

    (command,) = fake.commands
    assert (
        status,
        lines,
        command.argv.count(str((tmp_path / "clean.py").resolve())),
    ) == (0, [COUNT_NONE], 1)


def test_a_finding_prints_with_the_count_line(tmp_path: Path) -> None:
    """An error diagnostic with a rule in a given file prints as one line with its place and rule, and exits 1."""
    path = tmp_path / "typed.py"
    status, lines, _ = _run(
        tmp_path,
        {"typed.py": CLEAN},
        ["typed.py"],
        completed(1, _report([_entry(path)])),
    )

    assert (status, lines) == (1, [_line(path), COUNT_ONE])


def test_a_warning_is_a_finding(tmp_path: Path) -> None:
    """A diagnostic of any severity is a finding; pyright exits 0 when it holds no error."""
    path = tmp_path / "typed.py"
    status, lines, _ = _run(
        tmp_path,
        {"typed.py": CLEAN},
        ["typed.py"],
        completed(0, _report([_entry(path, "warning")])),
    )

    assert (status, lines) == (1, [_line(path, "warning"), COUNT_ONE])


def test_a_diagnostic_in_another_file_is_not_shown(tmp_path: Path) -> None:
    """A diagnostic in a file that was not given is neither printed nor counted, though pyright exits 1 for it."""
    other = tmp_path / "other.py"
    status, lines, _ = _run(
        tmp_path,
        {"typed.py": CLEAN, "other.py": CLEAN},
        ["typed.py"],
        completed(1, _report([_entry(other)])),
    )

    assert (status, lines) == (0, [COUNT_NONE])


def test_exit_zero_over_an_error_is_unfinished(tmp_path: Path) -> None:
    """Pyright exits 1 with an error, so an exit 0 over a report that holds one is no finished run: exit 2."""
    path = tmp_path / "typed.py"
    report = _report([_entry(path)])
    status, lines, _ = _run(
        tmp_path, {"typed.py": CLEAN}, ["typed.py"], completed(0, report)
    )

    assert (status, lines) == (2, [report + "\n", COUNT_NONE])


def test_exit_one_with_no_error_is_unfinished(tmp_path: Path) -> None:
    """Pyright exits 0 when its report holds no error, so an exit 1 over an empty report is no finished run: exit 2."""
    report = _report([])
    status, lines, _ = _run(
        tmp_path, {"clean.py": CLEAN}, ["clean.py"], completed(1, report)
    )

    assert (status, lines) == (2, [report + "\n", COUNT_NONE])


def test_unreadable_report_prints_the_whole_output(tmp_path: Path) -> None:
    """Output that is no report ends the run at exit 2: the checker's output line by line, then the count line."""
    status, lines, _ = _run(
        tmp_path,
        {"clean.py": CLEAN},
        ["clean.py"],
        completed(1, "garbage\n", "No module named pyright\n"),
    )

    assert (status, lines) == (
        2,
        ["garbage\n", "No module named pyright\n", COUNT_NONE],
    )


def test_a_report_of_another_shape_is_unreadable(tmp_path: Path) -> None:
    """A report whose summary holds no `filesAnalyzed` number is no report the gate can read: exit 2."""
    document: dict[str, object] = {"generalDiagnostics": [], "summary": {}}
    report = json.dumps(document)
    status, lines, _ = _run(
        tmp_path, {"clean.py": CLEAN}, ["clean.py"], completed(0, report)
    )

    assert (status, lines) == (2, [report + "\n", COUNT_NONE])


def test_pyright_runs_in_the_project_with_its_settings(tmp_path: Path) -> None:
    """The command runs from the project's root, takes its settings file, reports JSON and is handed each file resolved."""
    status, _, fake = _run(
        tmp_path, {"clean.py": CLEAN}, ["clean.py"], completed(0, _report([]))
    )

    (command,) = fake.commands
    argv = command.argv
    assert (status, command.cwd, "--outputjson" in argv) == (0, tmp_path, True)
    assert argv[argv.index("--project") + 1] == str(tmp_path / "pyproject.toml")
    assert argv[-1] == str((tmp_path / "clean.py").resolve())


def test_a_missing_pin_is_the_gates_own_line(tmp_path: Path) -> None:
    """A pyproject.toml with no pythonVersion ends the run at exit 2 with the error naming the key; pyright is not run."""
    config = tmp_path / "pyproject.toml"
    status, lines, fake = _run(
        tmp_path,
        {"clean.py": CLEAN},
        ["clean.py"],
        completed(0, _report([])),
        "[tool.pyright]\n",
    )

    assert (status, lines, fake.commands) == (
        2,
        [f"{config}: tool.pyright.pythonVersion: not set\n", COUNT_NONE],
        [],
    )


def test_a_parse_warning_is_printed_and_ends_unfinished(tmp_path: Path) -> None:
    """A file whose parse raises a warning is one pyright did not finish: the warning prints as its report, exit 2."""
    status, lines, _ = _run(
        tmp_path,
        {"warned.py": INVALID_ESCAPE},
        ["warned.py"],
        completed(0, _report([])),
    )

    assert (
        status,
        len(lines),
        lines[0].startswith(f"{tmp_path / 'warned.py'}:1: SyntaxWarning: "),
        lines[-1],
    ) == (2, 2, True, COUNT_NONE)


def test_an_unparsed_file_prints_pyrights_report_and_no_finding(tmp_path: Path) -> None:
    """A rule-less diagnostic in a file that cannot be parsed is pyright's report of not finishing it: printed, not counted, exit 2."""
    path = tmp_path / "broken.py"
    entries = [_entry(path, rule=None), _entry(path)]
    status, lines, _ = _run(
        tmp_path,
        {"broken.py": UNPARSEABLE},
        ["broken.py"],
        completed(1, _report(entries)),
    )

    assert (status, lines[:2], lines[-1]) == (
        2,
        [_line(path, rule=None), _line(path)],
        COUNT_ONE,
    )


def test_a_rule_less_diagnostic_in_a_parsed_file_is_a_finding(tmp_path: Path) -> None:
    """An error pyright's binder raises in a file that parses has no rule and is a finding."""
    path = tmp_path / "bound.py"
    status, lines, _ = _run(
        tmp_path,
        {"bound.py": CLEAN},
        ["bound.py"],
        completed(1, _report([_entry(path, rule=None)])),
    )

    assert (status, lines) == (1, [_line(path, rule=None), COUNT_ONE])


def test_a_file_pyright_left_out_is_unfinished(tmp_path: Path) -> None:
    """When the report's `filesAnalyzed` counts fewer files than were given, a line says so, before the count line, exit 2."""
    status, lines, _ = _run(
        tmp_path,
        {"clean.py": CLEAN},
        ["clean.py"],
        completed(0, _report([], analyzed=0)),
    )

    assert (status, lines) == (
        2,
        [
            "check_pyright: pyright left some of the given Python files out of its analysis\n",
            COUNT_NONE,
        ],
    )
