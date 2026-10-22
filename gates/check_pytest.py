# Copyright 2026 oh shit, gorillas!
"""pytest gate: run the test files among the given Python files under the strict pytest settings in `pyproject.toml`."""

import re
import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path

from defusedxml import ElementTree

from gates.core.checker import (
    UNREAD_CPUS,
    Command,
    Completed,
    cpu_budget,
    environment,
    python_module,
)
from gates.core.project import Project, Source, is_test_module, test_files
from gates.core.report import Finding, GateError, Line, Outcome
from gates.core.runner import Gate, Run, check_with, run_gate
from gates.core.runner import main as run_main

GATE_NAME = "check_pytest"

PYTEST_ENVIRONMENT = "PYTEST_"

SEED_BITS = 32

FAILED_OUTCOMES = frozenset({"failure", "error"})

PY_SUFFIX = re.compile(r"\.py$")

REPORT = "report.xml"

BASETEMP = "basetemp"

JUNIT = "junit"


@dataclass(frozen=True)
class Case:
    """One failed `testcase` of pytest's JUnit XML report: its `classname` and `name` attributes and the `message` of its first failure."""

    classname: str
    name: str
    message: str


@dataclass(frozen=True)
class Failure:
    """One failing test of a module: its id without the module's path, and the message of its first failure."""

    identity: str
    message: str


@dataclass(frozen=True)
class Report:
    """What pytest's JUnit XML report says of one test module: the absolute path it names as its suite, and each failed case in report order."""

    module: str
    cases: list[Case]


def module_classname(module: str, root: Path) -> str:
    """Return the `classname` pytest's JUnit XML report gives a module-level test of the test module at the absolute path `module`.

    pytest's root directory is the project's root, the directory of `pyproject.toml`. pytest names a test module under it
    by its path relative to it, and its JUnit XML report turns that name into a `classname` by writing each `/` as `.`
    and dropping the trailing `.py`. A test module outside it, given by its own path, has an empty name, so its
    `classname` is empty. A test in a class gets the class names appended, each after a `.`.
    """
    path = Path(module)
    if not path.is_relative_to(root):
        return ""
    return PY_SUFFIX.sub("", path.relative_to(root).as_posix().replace("/", "."))


def test_modules(sources: Sequence[Source]) -> list[Source]:
    """Return the test modules among the sources, in their order: each test file but a `conftest.py`."""
    return [source for source in sources if is_test_module(source)]


def identify(case: Case, module: str, root: Path) -> str | None:
    """Return the id of the test `case` names, without the module's path: each class and the test as pytest names them, joined by `::`.

    The case is the module's when its `classname` is the module's own, for a module-level test, or begins with it followed
    by a `.`, for a test in a class. A case that is not the module's has no id.
    """
    classname = module_classname(module, root)
    if case.classname == classname:
        classes: list[str] = []
    elif case.classname.startswith(f"{classname}."):
        classes = case.classname[len(classname) + 1 :].split(".")
    else:
        return None
    return "::".join([*classes, case.name])


def parse_report(text: str) -> Report | None:
    """Read the JUnit XML report pytest wrote, and return `None` when it is no report the gate can read.

    A case failed when it holds a `failure` or an `error` element. A report that is not XML, one whose suite names no
    module, and a failed case or element without the attribute the gate reads, are no report the gate can read.
    """
    try:
        tree = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return None
    suite = tree if tree.tag == "testsuite" else tree.find("testsuite")
    module = None if suite is None else suite.get("name")
    if module is None:
        return None
    cases: list[Case] = []
    for element in tree.iter("testcase"):
        failed = [child for child in element if child.tag in FAILED_OUTCOMES]
        if not failed:
            continue
        classname = element.get("classname")
        name = element.get("name")
        message = failed[0].get("message")
        if (
            classname is None
            or name is None
            or message is None
            or any(child.get("message") is None for child in failed)
        ):
            return None
        cases.append(Case(classname=classname, name=name, message=message))
    return Report(module=module, cases=cases)


class Pytest:
    """pytest as a child process, one per test module, each in a directory of its own in the run's temp space.

    Each test module runs in a pytest of its own, so no other module it imports or runs beside changes its verdict. pytest
    reads its settings from the project's `pyproject.toml` alone, never from a file beside the test files, and its root
    directory is the directory of that file, so a test's id and its place in pytest-randomly's order are the same
    whatever other test modules are given. pytest's environment holds no variable whose name begins with `PYTEST_`, where
    pytest and its plugins read options and settings, so none reaches it from outside, and pytest-randomly and
    pytest-timeout load as installed. The verdict is read from the JUnit XML report pytest writes, never from its console
    output, which a run that did not finish prints whole.
    """

    stopped: frozenset[int] = frozenset()

    def __init__(self, seed: int, spaces: dict[Path, Path], root: Path) -> None:
        """Take the run's seed for pytest-randomly, the directory of each test module by its absolute path, and the project's root."""
        self.seed = seed
        self.spaces = spaces
        self.root = root

    def batches(self, run: Run) -> list[list[Source]]:
        """One pytest per test module; a `conftest.py` beside one gets none."""
        return [[source] for source in test_modules(run.sources)]

    def command(self, run: Run, batch: Sequence[Source]) -> Command:
        """Pytest over the batch's one test module from the project's root, its report and its `--basetemp` in the module's own directory.

        The suite name of the JUnit report is the module's absolute path, which the report is read back by.
        `--basetemp` is passed on the command line and changes no setting `pyproject.toml` holds.
        """
        module = batch[0].absolute
        space = self.spaces[module]
        command = python_module(
            "pytest",
            "-c",
            run.project.config,
            f"--rootdir={self.root}",
            f"--junitxml={space / REPORT}",
            f"--basetemp={space / BASETEMP}",
            f"--randomly-seed={self.seed}",
            "-o",
            f"junit_suite_name={module}",
            module,
            cwd=self.root,
        )
        return replace(
            command,
            env=environment(drop_prefixes=(PYTEST_ENVIRONMENT,)),
            outputs={JUNIT: space / REPORT},
        )

    def read(self, completed: Completed) -> list[Failure]:
        """Read failed cases from pytest's JUnit XML report by id; raise GateError when the report cannot be read.

        A report holding a failed case that is not its module's is no report the gate can read.
        """
        text = completed.outputs.get(JUNIT)
        report = None if text is None else parse_report(text)
        if report is None:
            raise GateError(completed.output())
        failures: list[Failure] = []
        for case in report.cases:
            identity = identify(case, report.module, self.root)
            if identity is None:
                raise GateError(completed.output())
            failures.append(Failure(identity=identity, message=case.message))
        return failures

    def expected_status(self, report: list[Failure]) -> int:
        """Pytest exits 1 when its report holds a failed test and 0 when it holds none; exit 5, no test collected, is no finish."""
        return 1 if report else 0

    def lines(
        self, report: list[Failure], batch: Sequence[Source], *, stopped: bool
    ) -> list[Line]:
        """Each failing test as one finding: the module's path as given, the test's id, a colon, a space and the message of its first failure.

        A test whose call fails and whose teardown fails too is one failing test.
        """
        del stopped
        found: dict[str, str] = {}
        for failure in report:
            found.setdefault(f"{batch[0].given}::{failure.identity}", failure.message)
        return [
            Finding(f"{identity}: {message}") for identity, message in found.items()
        ]


def check(budget: Callable[[], int], run: Run) -> Outcome:
    """Run pytest over each test module in parallel, as many at once as the budget allows, and give the findings under the seed line.

    Each run takes a fresh seed for pytest-randomly, which every test module's run uses, and prints it first, as
    `check_pytest: seed N`. Each module's directory is made before the seed line, so a run whose temp space cannot be made
    prints no seed line and starts no pytest; nor does a run whose budget cannot be read.
    """
    spaces = {
        source.absolute: run.scratch.directory(str(index))
        for index, source in enumerate(test_modules(run.sources))
    }
    seed = secrets.randbits(SEED_BITS)
    read: list[int] = []

    def counted() -> int:
        read.append(budget())
        return read[-1]

    outcome = check_with(Pytest(seed, spaces, run.project.root), budget=counted)(run)
    return replace(outcome, notes=(f"{GATE_NAME}: seed {seed}",) if read else ())


def gate(budget: Callable[[], int] = cpu_budget) -> Gate:
    """Build the gate over the given test files, running as many pytest processes at once as `budget` gives."""
    return Gate(
        name=GATE_NAME,
        check=partial(check, budget),
        select=test_files,
        selects="test file",
    )


GATE: Gate = gate()


def read_budget(read_cpus: Callable[[], int | None]) -> int:
    """Return the CPU budget of the count `read_cpus` gives; raise GateError when the count cannot be read."""
    cpus = read_cpus()
    if cpus is None:
        raise GateError(UNREAD_CPUS)
    return cpu_budget(cpus)


def main(
    paths: Sequence[Path],
    read_cpus: Callable[[], int | None] | None = None,
    scratch_root: Path | None = None,
    project: Project | None = None,
) -> int:
    """Run the gate over the paths, in the working directory's project, and return its exit code.

    The count of CPUs is `read_cpus`'s, or with no reader the host's CPUs this process may run on, read in this process.
    A reader that gives None is a count that cannot be read, a run the checker did not finish.
    """
    return run_gate(
        gate() if read_cpus is None else gate(partial(read_budget, read_cpus)),
        paths,
        project=project,
        scratch_root=scratch_root,
    )


if __name__ == "__main__":
    run_main(GATE)
