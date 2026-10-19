"""pytest gate: run the test files among the given Python files under the strict pytest settings in `pyproject.toml`."""

import fnmatch
import os
import re
import secrets
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from pytest import ExitCode

from gates.check_suppressions import is_python_source

ROOT = Path(__file__).resolve().parent.parent

CONFIG = ROOT / "pyproject.toml"

GATE = "check_pytest"

TESTS_DIRECTORY = "tests"

TEST_MODULE_PATTERNS = ("test_*.py", "*_test.py")

CONFTEST = "conftest.py"

PYTEST_ENVIRONMENT = "PYTEST_"

BLOCKED = 2

SEED_BITS = 32

FAILED_OUTCOMES = frozenset({"failure", "error"})

PY_SUFFIX = re.compile(r"\.py$")


@dataclass(frozen=True)
class Selection:
    """The test files among the given paths: each test module by its absolute path, with the path as it was given, and the `conftest.py` files beside them."""

    modules: dict[str, Path]
    conftests: frozenset[str]


@dataclass(frozen=True)
class Outcome:
    """One `failure` or `error` element of pytest's JUnit XML report: its `message` attribute and its text, pytest's whole report of it."""

    message: str
    text: str


@dataclass(frozen=True)
class Case:
    """One `testcase` element of pytest's JUnit XML report that failed: its `classname` and `name` attributes, and each `failure` or `error` element it holds, in report order."""

    classname: str
    name: str
    outcomes: tuple[Outcome, ...]


@dataclass(frozen=True)
class Run:
    """One pytest run over one test module: pytest's completed process, and each failed case of its JUnit XML report, `None` when it wrote no report the gate can read."""

    completed: subprocess.CompletedProcess[str]
    cases: list[Case] | None


def is_test_module(path: Path) -> bool:
    """Tell whether `path`, as given, has a `tests` directory component and a name pytest collects by default, `test_*.py` or `*_test.py`."""
    return TESTS_DIRECTORY in path.parent.parts and any(fnmatch.fnmatchcase(path.name, pattern) for pattern in TEST_MODULE_PATTERNS)


def select(paths: list[Path]) -> Selection:
    """Pick the test files among the Python files in `paths`: each test module, and each `conftest.py` in the directory of one.

    A file given twice, under one spelling or two, is one file; its first spelling is the one its findings name.
    """
    sources = [path for path in paths if is_python_source(path)]
    modules: dict[str, Path] = {}
    for path in sources:
        if is_test_module(path):
            modules.setdefault(os.path.abspath(path), path)
    directories = {os.path.dirname(module) for module in modules}
    conftests = frozenset(
        os.path.abspath(path) for path in sources if path.name == CONFTEST and os.path.dirname(os.path.abspath(path)) in directories
    )
    return Selection(modules=modules, conftests=conftests)


def module_classname(module: str) -> str:
    """Return the `classname` pytest's JUnit XML report gives a module-level test of the test module at the absolute path `module`.

    pytest's root directory is the repository root, the directory of `pyproject.toml`. pytest
    names a test module under it by its path relative to it, and its JUnit XML report turns that
    name into a `classname` by writing each `/` as `.` and dropping the trailing `.py`. A test
    module outside it, given by its own path, has an empty name, so its `classname` is empty. A
    test in a class gets the class names appended, each after a `.`.
    """
    path = Path(module)
    if not path.is_relative_to(ROOT):
        return ""
    return PY_SUFFIX.sub("", path.relative_to(ROOT).as_posix().replace("/", "."))


def identify(case: Case, module: str, given: Path) -> str | None:
    """Return the id of the test `case` names: `given`, the path the test module at `module` was given as, then `::` and each class and the test as pytest names them.

    The case is the module's when its `classname` is the module's own, for a module-level test,
    or begins with it followed by a `.`, for a test in a class. A case that is not the module's
    has no id.
    """
    classname = module_classname(module)
    if case.classname == classname:
        classes: list[str] = []
    elif case.classname.startswith(f"{classname}."):
        classes = case.classname[len(classname) + 1 :].split(".")
    else:
        return None
    return "::".join([str(given), *classes, case.name])


def read_report(report: Path) -> list[Case] | None:
    """Read each failed `testcase` of the JUnit XML report pytest wrote at `report`, and return `None` when there is no report the gate can read.

    A case failed when it holds a `failure` or an `error` element. A report that is missing or not
    XML, or a failed case or element without the attribute the gate reads, is no report the gate
    can read.
    """
    try:
        tree = ElementTree.parse(report)
    except (OSError, ElementTree.ParseError):
        return None
    cases: list[Case] = []
    for element in tree.iter("testcase"):
        failed = [child for child in element if child.tag in FAILED_OUTCOMES]
        if not failed:
            continue
        classname = element.get("classname")
        name = element.get("name")
        if classname is None or name is None:
            return None
        outcomes: list[Outcome] = []
        for child in failed:
            message = child.get("message")
            if message is None:
                return None
            outcomes.append(Outcome(message=message, text=child.text or ""))
        cases.append(Case(classname=classname, name=name, outcomes=tuple(outcomes)))
    return cases


def one_line(message: str) -> str:
    """Return `message` with every line break in it, each one `str.splitlines` splits on, replaced by a space."""
    lines = message.splitlines()
    ends_in_break = message.splitlines(keepends=True)[-1:] != lines[-1:]
    return " ".join(lines) + (" " if ends_in_break else "")


def verdict(finished: Run, module: str, given: Path) -> dict[str, str] | None:
    """Return each failing test of the run over the test module at `module` with the `message` of its first failure, in report order, or `None` when the run did not finish.

    A test whose call fails and whose teardown fails too is one failing test. A run did not finish
    when pytest wrote no report the gate can read, when a failed case is not the module's, or when
    pytest's exit status is not the one its report calls for: 1 when the report holds a failed
    test, and 0 when it holds none. A run in which pytest collected no test from the module, exit
    5, did not finish either, so the module's verdict never depends on what other modules hold.
    """
    if finished.cases is None:
        return None
    failing: dict[str, str] = {}
    for case in finished.cases:
        identity = identify(case, module, given)
        if identity is None:
            return None
        failing.setdefault(identity, case.outcomes[0].message)
    returncode = finished.completed.returncode
    agrees = returncode == ExitCode.TESTS_FAILED if failing else returncode == ExitCode.OK
    return failing if agrees else None


def run(module: str, seed: int) -> Run:
    """Run pytest over the test module at `module` from the repository root under the settings in `pyproject.toml` with pytest-randomly's seed `seed`, and read its JUnit XML report.

    pytest reads its settings from the repository's `pyproject.toml` alone, never from a file
    beside the test files, and its root directory is the directory of that file, so a test's id
    and its place in pytest-randomly's order are the same whatever other test modules are given.
    Each test module runs in a pytest of its own, so no other module it imports or runs beside
    changes its verdict. pytest's environment holds no variable whose name begins with `PYTEST_`,
    where pytest and its plugins read options and settings, so none reaches it from outside,
    `PYTEST_ADDOPTS` and `PYTEST_PLUGINS` among them, and pytest-randomly and pytest-timeout load
    as installed.
    """
    environment = {key: value for key, value in os.environ.items() if not key.startswith(PYTEST_ENVIRONMENT)}
    with tempfile.TemporaryDirectory() as scratch:
        report = Path(scratch) / "report.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(CONFIG),
            f"--rootdir={ROOT}",
            f"--junitxml={report}",
            f"--randomly-seed={seed}",
            module,
        ]
        completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, check=False)
        return Run(completed=completed, cases=read_report(report))


def print_unfinished(unfinished: Run, given: Path) -> None:
    """Print pytest's own error for a run over the test module given as `given` that it did not finish, then what its exit status and report were.

    pytest writes an error that stops it before any test runs, as a usage error or an unknown
    config key, to its stderr, and one that stops it during collection, as a collection error or
    an internal error, to its JUnit XML report: both are printed, the report's as each failed
    element's message and pytest's whole report of it. A run that collected no test, exit 5, says
    so in a line of its own.
    """
    sys.stdout.write("".join(f"{line}\n" for line in unfinished.completed.stderr.splitlines()))
    for case in unfinished.cases or []:
        for outcome in case.outcomes:
            sys.stdout.write(f"{case.classname}::{case.name}: {one_line(outcome.message)}\n")
            sys.stdout.write("".join(f"{line}\n" for line in outcome.text.splitlines()))
    if unfinished.completed.returncode == ExitCode.NO_TESTS_COLLECTED:
        sys.stdout.write(f"{GATE}: pytest collected no test from {given}\n")
    held = "no JUnit XML report the gate can read" if unfinished.cases is None else f"a JUnit XML report of {len(unfinished.cases)} failed test(s)"
    sys.stdout.write(f"{GATE}: pytest exited {unfinished.completed.returncode} with {held} on {given}\n")


def main(paths: list[Path]) -> int:
    """Run pytest over the test files among the Python files in `paths` and print each failing test.

    A test file is a test module, a file whose path as given has a `tests` directory component
    and whose name is `test_*.py` or `*_test.py`, or a `conftest.py` beside one; other files are
    neither run nor counted, and a run given no test module checked nothing and exits 1. Each
    run takes a fresh seed for pytest-randomly, which every test module's run uses, and prints it
    first, as `check_pytest: seed N`. The verdict is read from pytest's JUnit XML reports, never
    from its console output, which a finished run does not print. Each failing test is one
    finding, printed as its id, a colon, a space and the message of its failure with every line
    break replaced by a space; then the count line, with the failing tests and the test files run,
    and exit 1 on any finding and 0 on none. Each test module's verdict is its own: a module
    pytest did not finish, one from which it collected no test included, prints pytest's own
    error in its place, and every module it did finish still prints its findings. When pytest did
    not finish over some test module, the count line says over how many of the test files and
    with how many findings, and the run exits 2, whatever the other modules found.
    """
    selection = select(paths)
    if not selection.modules:
        sys.stdout.write(f"{GATE}: no test file among {len(paths)} path(s); nothing was checked\n")
        return 1
    files = len(selection.modules) + len(selection.conftests)
    seed = secrets.randbits(SEED_BITS)
    sys.stdout.write(f"{GATE}: seed {seed}\n")
    findings = 0
    unfinished = 0
    for module, given in selection.modules.items():
        finished = run(module, seed)
        found = verdict(finished, module, given)
        if found is None:
            print_unfinished(finished, given)
            unfinished += 1
        else:
            sys.stdout.write("".join(f"{identity}: {one_line(message)}\n" for identity, message in found.items()))
            findings += len(found)
    if unfinished:
        sys.stdout.write(f"{GATE}: pytest could not finish on {unfinished} of {files} Python file(s), with {findings} finding(s)\n")
        return BLOCKED
    sys.stdout.write(f"{GATE}: {findings} finding(s) in {files} Python file(s)\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
