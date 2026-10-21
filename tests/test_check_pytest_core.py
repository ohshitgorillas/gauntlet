"""Red tests for the pytest gate on the gates core: one pytest per test module, its JUnit report read from the Completed.

Source: the gates core design spec under docs/superpowers/specs/, section 2 ("pytest (G3, already built). A Checker with
one batch per test module and `outputs={"junit": ...}`; the seed line is an Outcome note"), section 1 (runner.py: an exit
status that is not the one the report calls for, or no readable report, is unfinished and prints the checker's whole
output), report.py's `render`, and the quality gates design spec,
"Tests", the "pytest strictness" bullet: a finding is a failing test's id, a colon, a space and its message with every
line break a space; the seed line is `check_pytest: seed N` and comes first; a module pytest did not finish prints
pytest's whole console output; exit 1 on a failing test and 0 on none; no seed line when the run's temp directory cannot
be made.

Each pytest run is answered by a FakeRunner that seeds pytest's whole output and the JUnit XML it wrote, so the gate is
judged by what it prints for that report alone. The XML names the module's absolute path as its suite name, as pytest
does under the `junit_suite_name` setting the gate passes.
"""

import re
from pathlib import Path

from gates.check_pytest import GATE
from gates.core.runner import run_gate
from tests.support.capture import captured
from tests.support.fake import FakeRunner, completed
from tests.support.project import scaffold

SEED_LINE = re.compile(r"check_pytest: seed \d+")

PASSING = "def test_seeded():\n    pass\n"

COLLECTED_NOTHING = "collected 0 items\n\n============ no tests ran in 0.01s ============\n"


def _junit(module: Path, *, classname: str, message: str | None) -> str:
    """The JUnit XML of a run over `module` holding one test named `test_seeded`, failing with `message` when given."""
    failure = "" if message is None else f'<failure message="{message}"/>'
    return (
        f'<?xml version="1.0"?><testsuites><testsuite name="{module}" tests="1">'
        f'<testcase classname="{classname}" name="test_seeded">{failure}</testcase></testsuite></testsuites>'
    )


def _run(tmp_path: Path, status: int, stdout: str, junit: str | None) -> tuple[int, list[str], FakeRunner]:
    """Run the gate over the one test module of a scaffolded project, its pytest answered by the seeded reply."""
    project = scaffold(tmp_path / "project", {"tests/test_seeded.py": PASSING})
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    module = project.root / "tests/test_seeded.py"
    seeded = junit if junit is None else junit.replace("MODULE", str(module))
    runner = FakeRunner([completed(status, stdout, outputs={"junit": seeded})])
    output = captured(lambda: run_gate(GATE, [module], project=project, process=runner, scratch_root=scratch))
    return output.result, [line.rstrip("\n") for line in output.merged], runner


def test_seed_then_finding(tmp_path: Path) -> None:
    """A failing test is one finding after the seed line: its given path, `::`, its name, a colon and the message, one line."""
    junit = _junit(Path("MODULE"), classname="tests.test_seeded", message="First&#10;Second")
    status, lines, _ = _run(tmp_path, 1, "", junit)

    assert (status, len(lines), SEED_LINE.fullmatch(lines[0]) is not None, lines[1:]) == (
        1,
        3,
        True,
        [f"{tmp_path / 'project/tests/test_seeded.py'}::test_seeded: First Second", "check_pytest: 1 finding(s) in 1 Python file(s)"],
    )


def test_one_pytest_per_module(tmp_path: Path) -> None:
    """The one module is run by one pytest, with the JUnit report as an output file, read back by the gate."""
    junit = _junit(Path("MODULE"), classname="tests.test_seeded", message=None)
    status, _, runner = _run(tmp_path, 0, "", junit)

    (command,) = runner.commands
    assert (status, "pytest" in command.argv, set(command.outputs)) == (0, True, {"junit"})


def test_environment_drops_pytest_variables(tmp_path: Path) -> None:
    """The pytest process gets no variable whose name begins with PYTEST_."""
    junit = _junit(Path("MODULE"), classname="tests.test_seeded", message=None)
    _, _, runner = _run(tmp_path, 0, "", junit)

    (command,) = runner.commands
    assert command.env is not None
    assert [name for name in command.env if name.startswith("PYTEST_")] == []


def test_exit_five_is_unfinished(tmp_path: Path) -> None:
    """Exit 5, no test collected, calls for no report with 0: pytest's whole output prints, exit 2, no finding."""
    junit = _junit(Path("MODULE"), classname="tests.test_seeded", message=None)
    status, lines, _ = _run(tmp_path, 5, COLLECTED_NOTHING, junit)

    assert (status, lines[1:-1], lines[-1]) == (2, COLLECTED_NOTHING.splitlines(), "check_pytest: 0 finding(s) in 1 Python file(s)")


def test_exit_zero_with_a_failure_is_unfinished(tmp_path: Path) -> None:
    """A report holding a failed test calls for exit 1, so an exit 0 is no finish: pytest's whole output, exit 2."""
    junit = _junit(Path("MODULE"), classname="tests.test_seeded", message="Seeded")
    status, lines, _ = _run(tmp_path, 0, "seeded console output\n", junit)

    assert (status, lines[1:-1]) == (2, ["seeded console output"])


def test_no_report_is_unfinished(tmp_path: Path) -> None:
    """A pytest that wrote no report prints its whole output, exit 2."""
    status, lines, _ = _run(tmp_path, 4, "usage: pytest\n", None)

    assert (status, lines[1:-1]) == (2, ["usage: pytest"])


def test_foreign_case_is_unfinished(tmp_path: Path) -> None:
    """A failed case that is not the module's makes the run unfinished: pytest's whole output, exit 2."""
    junit = _junit(Path("MODULE"), classname="tests.test_other", message="Seeded")
    status, lines, _ = _run(tmp_path, 1, "seeded console output\n", junit)

    assert (status, lines[1:-1]) == (2, ["seeded console output"])


def test_no_seed_when_no_temp_space(tmp_path: Path) -> None:
    """A scratch root that does not exist is temp space the run cannot make: no seed line, no pytest run, exit 2."""
    project = scaffold(tmp_path / "project", {"tests/test_seeded.py": PASSING})
    runner = FakeRunner([])
    output = captured(
        lambda: run_gate(GATE, [project.root / "tests/test_seeded.py"], project=project, process=runner, scratch_root=tmp_path / "absent")
    )

    assert (output.result, runner.commands, [line for line in output.merged if SEED_LINE.fullmatch(line.rstrip("\n"))]) == (2, [], [])
