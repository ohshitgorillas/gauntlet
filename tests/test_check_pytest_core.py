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

import errno
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from gates.check_pytest import GATE
from gates.core.checker import Command, environment
from gates.core.runner import run_gate
from tests.support.capture import captured
from tests.support.fake import FakeRunner, completed
from tests.support.project import scaffold

REPO_ROOT = Path(__file__).parents[1]

SEED_LINE = re.compile(r"check_pytest: seed \d+")

# The two variables the spec says pytest's environment is without.
SEEDED_VARIABLES = ("PYTEST_ADDOPTS", "PYTEST_PLUGINS")

# A child interpreter that runs `_run` under the tmp path it is given, then writes whether the one pytest command got an
# environment of its own and which of the variables it is given that environment still holds.
ENVIRONMENT_CHILD = (
    "import sys\n"
    "from pathlib import Path\n\n"
    "from tests.test_check_pytest_core import _junit, _run\n\n"
    "_, _, runner = _run(Path(sys.argv[1]), 0, '', _junit(Path('MODULE'), classname='tests.test_seeded', message=None))\n"
    "(command,) = runner.commands\n"
    "env = command.env or {}\n"
    "sys.stdout.write(repr((command.env is not None, [name for name in sys.argv[2:] if name in env])))\n"
)

# What the child writes when the command has an environment of its own holding neither variable.
NOTHING_LEAKED: tuple[bool, list[str]] = (True, [])

PASSING = "def test_seeded():\n    pass\n"

COLLECTED_NOTHING = (
    "collected 0 items\n\n============ no tests ran in 0.01s ============\n"
)

# The JUnit XML of a run over MODULE that collected no test: one suite holding no case.
EMPTY_JUNIT = '<?xml version="1.0"?><testsuites><testsuite name="MODULE" tests="0"></testsuite></testsuites>'


def _junit(module: Path, *, classname: str, message: str | None) -> str:
    """The JUnit XML of a run over `module` holding one test named `test_seeded`, failing with `message` when given."""
    failure = "" if message is None else f'<failure message="{message}"/>'
    return (
        f'<?xml version="1.0"?><testsuites><testsuite name="{module}" tests="1">'
        f'<testcase classname="{classname}" name="test_seeded">{failure}</testcase></testsuite></testsuites>'
    )


def _run(
    tmp_path: Path, status: int, stdout: str, junit: str | None
) -> tuple[int, list[str], FakeRunner]:
    """Run the gate over the one test module of a scaffolded project, its pytest answered by the seeded reply."""
    project = scaffold(tmp_path / "project", {"tests/test_seeded.py": PASSING})
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    module = project.root / "tests/test_seeded.py"
    seeded = junit if junit is None else junit.replace("MODULE", str(module))
    runner = FakeRunner([completed(status, stdout, outputs={"junit": seeded})])
    output = captured(
        lambda: run_gate(
            GATE, [module], project=project, process=runner, scratch_root=scratch
        )
    )
    return output.result, [line.rstrip("\n") for line in output.merged], runner


def test_seed_then_finding(tmp_path: Path) -> None:
    """A failing test is one finding after the seed line: its given path, `::`, its name, a colon and the message, one line."""
    junit = _junit(
        Path("MODULE"), classname="tests.test_seeded", message="First&#10;Second"
    )
    status, lines, _ = _run(tmp_path, 1, "", junit)

    assert (
        status,
        len(lines),
        SEED_LINE.fullmatch(lines[0]) is not None,
        lines[1:],
    ) == (
        1,
        3,
        True,
        [
            f"{tmp_path / 'project/tests/test_seeded.py'}::test_seeded: First Second",
            "check_pytest: 1 finding(s) in 1 Python file(s)",
        ],
    )


def _named(command: Command, modules: Sequence[Path]) -> list[str]:
    """The modules among `modules` that an argument of `command` names, read from the command's working directory."""
    named = {command.cwd / argument for argument in command.argv}
    return [str(module) for module in modules if module in named]


def test_one_pytest_per_module(tmp_path: Path) -> None:
    """The one module is run by one pytest, named on its command line, with the JUnit report as an output file, read back by the gate."""
    junit = _junit(Path("MODULE"), classname="tests.test_seeded", message=None)
    status, _, runner = _run(tmp_path, 0, "", junit)
    module = tmp_path / "project/tests/test_seeded.py"

    (command,) = runner.commands
    assert (
        status,
        "pytest" in {Path(argument).name for argument in command.argv},
        _named(command, [module]),
        set(command.outputs),
    ) == (
        0,
        True,
        [str(module)],
        {"junit"},
    )


def test_each_module_gets_its_own_pytest(tmp_path: Path) -> None:
    """Two test modules are two pytest processes, each naming its own module and not the other."""
    project = scaffold(
        tmp_path / "project",
        {"tests/test_first.py": PASSING, "tests/test_second.py": PASSING},
    )
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    modules = [
        project.root / "tests/test_first.py",
        project.root / "tests/test_second.py",
    ]
    replies = [
        completed(
            0,
            "",
            outputs={
                "junit": _junit(module, classname=f"tests.{module.stem}", message=None)
            },
        )
        for module in modules
    ]
    runner = FakeRunner(replies)
    captured(
        lambda: run_gate(
            GATE, modules, project=project, process=runner, scratch_root=scratch
        )
    )

    assert sorted(_named(command, modules) for command in runner.commands) == [
        [str(modules[0])],
        [str(modules[1])],
    ]


def test_environment_drops_pytest_variables(tmp_path: Path) -> None:
    """A gate started with PYTEST_ADDOPTS and PYTEST_PLUGINS set hands its pytest an environment of its own without them."""
    result = subprocess.run(  # A child interpreter is the one way to start the gate with the two variables set.
        [sys.executable, "-c", ENVIRONMENT_CHILD, str(tmp_path), *SEEDED_VARIABLES],
        cwd=REPO_ROOT,
        env={**environment(), **dict.fromkeys(SEEDED_VARIABLES, "seeded")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert (result.returncode, result.stdout) == (0, repr(NOTHING_LEAKED))


def test_exit_five_is_unfinished(tmp_path: Path) -> None:
    """Exit 5 with the empty report of a run that collected no test is no finish: pytest's whole output prints, exit 2, no finding."""
    status, lines, _ = _run(tmp_path, 5, COLLECTED_NOTHING, EMPTY_JUNIT)

    assert (status, lines[1:-1], lines[-1]) == (
        2,
        COLLECTED_NOTHING.splitlines(),
        "check_pytest: 0 finding(s) in 1 Python file(s)",
    )


def test_exit_zero_with_a_failure_is_unfinished(tmp_path: Path) -> None:
    """A report holding a failed test calls for exit 1, so an exit 0 is no finish: pytest's whole output, exit 2."""
    junit = _junit(Path("MODULE"), classname="tests.test_seeded", message="Seeded")
    status, lines, _ = _run(tmp_path, 0, "seeded console output\n", junit)

    assert (status, lines[1:-1]) == (2, ["seeded console output"])


def test_no_report_is_unfinished(tmp_path: Path) -> None:
    """A pytest that wrote no report prints its whole output, exit 2."""
    status, lines, _ = _run(tmp_path, 4, "usage: pytest\n", None)

    assert (status, lines[1:-1]) == (2, ["usage: pytest"])


def test_signal_death_is_unfinished(tmp_path: Path) -> None:
    """A pytest a signal ended, status 137 as a shell reports it, prints its whole output, exit 2, though its report reads.

    The report is readable and passing, so only the signal rule makes the run unfinished: a gate that took 137 as a finish
    would exit 0, and one that took it as a stop whose report stands would print that report, not the whole output.
    """
    junit = _junit(Path("MODULE"), classname="tests.test_seeded", message=None)
    status, lines, _ = _run(tmp_path, 137, "seeded console output\n", junit)

    assert (status, lines[1:-1]) == (2, ["seeded console output"])


def test_foreign_case_is_unfinished(tmp_path: Path) -> None:
    """A failed case that is not the module's makes the run unfinished: pytest's whole output, exit 2."""
    junit = _junit(Path("MODULE"), classname="tests.test_other", message="Seeded")
    status, lines, _ = _run(tmp_path, 1, "seeded console output\n", junit)

    assert (status, lines[1:-1]) == (2, ["seeded console output"])


def test_no_seed_when_no_temp_space(tmp_path: Path) -> None:
    """A scratch root that does not exist is temp space the run cannot make: no seed line, no pytest run, exit 2.

    It prints one error line naming the path and the OS error, then the count line with N 0 and M the test files given.
    """
    project = scaffold(tmp_path / "project", {"tests/test_seeded.py": PASSING})
    runner = FakeRunner([])
    absent = tmp_path / "absent"
    output = captured(
        lambda: run_gate(
            GATE,
            [project.root / "tests/test_seeded.py"],
            project=project,
            process=runner,
            scratch_root=absent,
        )
    )
    lines = [line.rstrip("\n") for line in output.merged]

    assert (
        output.result,
        runner.commands,
        [line for line in lines if SEED_LINE.fullmatch(line)],
        len(lines),
        str(absent) in lines[0],
        os.strerror(errno.ENOENT) in lines[0],
        lines[-1],
    ) == (2, [], [], 2, True, True, "check_pytest: 0 finding(s) in 1 Python file(s)")
