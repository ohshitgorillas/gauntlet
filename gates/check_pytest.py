"""pytest gate: run the test files among the given Python files under the strict pytest settings in `pyproject.toml`."""

import fnmatch
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
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

PROCESSES_PER_CPU_PAIR = 2

RUN_PREFIX = f"{GATE}-"

REPORT = "report.xml"

BASETEMP = "basetemp"


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


@dataclass(frozen=True)
class Report:
    """What the gate prints for one test module, its findings or pytest's error in their place, with how many findings it holds and whether pytest finished."""

    text: str
    findings: int
    finished: bool


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


def run(module: str, seed: int, space: Path) -> Run:
    """Run pytest over the test module at `module` from the repository root under the settings in `pyproject.toml` with pytest-randomly's seed `seed`, and read its JUnit XML report.

    pytest reads its settings from the repository's `pyproject.toml` alone, never from a file
    beside the test files, and its root directory is the directory of that file, so a test's id
    and its place in pytest-randomly's order are the same whatever other test modules are given.
    Each test module runs in a pytest of its own, so no other module it imports or runs beside
    changes its verdict. pytest's environment holds no variable whose name begins with `PYTEST_`,
    where pytest and its plugins read options and settings, so none reaches it from outside,
    `PYTEST_ADDOPTS` and `PYTEST_PLUGINS` among them, and pytest-randomly and pytest-timeout load
    as installed.

    `space` is a directory of this module's own inside the run's temp directory, which no other
    process shares: its JUnit XML report is written in it, and pytest's `--basetemp` is a path in
    it that pytest itself makes. `--basetemp` is passed on the command line and changes no
    setting `pyproject.toml` holds.
    """
    environment = {key: value for key, value in os.environ.items() if not key.startswith(PYTEST_ENVIRONMENT)}
    report = space / REPORT
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-c",
        str(CONFIG),
        f"--rootdir={ROOT}",
        f"--junitxml={report}",
        f"--basetemp={space / BASETEMP}",
        f"--randomly-seed={seed}",
        module,
    ]
    completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, check=False)
    return Run(completed=completed, cases=read_report(report))


def unfinished_text(unfinished: Run, given: Path) -> str:
    """Return pytest's own error for a run over the test module given as `given` that it did not finish, then its exit status, one line each.

    pytest writes an error that stops it before any test runs, as a usage error or an unknown
    config key, to its stderr, and one that stops it during collection, as a collection error or
    an internal error, to its JUnit XML report: both are printed, the report's as each failed
    element's message and pytest's whole report of it. A run that collected no test, exit 5, says
    so in a line of its own. The status line names no number of files and says nothing of the
    report, since the count line is the one line that counts files.
    """
    lines = list(unfinished.completed.stderr.splitlines())
    for case in unfinished.cases or []:
        for outcome in case.outcomes:
            lines.append(f"{case.classname}::{case.name}: {one_line(outcome.message)}")
            lines.extend(outcome.text.splitlines())
    if unfinished.completed.returncode == ExitCode.NO_TESTS_COLLECTED:
        lines.append(f"{GATE}: pytest collected no test from {given}")
    lines.append(f"{GATE}: pytest exited {unfinished.completed.returncode} on {given}")
    return "".join(f"{line}\n" for line in lines)


def report(module: str, given: Path, seed: int, space: Path) -> Report:
    """Run pytest over the test module at `module`, given as `given`, with pytest-randomly's seed `seed` and the module's own temp directory `space`, and return what the gate prints for it.

    A run pytest finished prints each failing test as one finding, its id, a colon, a space and
    the message of its failure with every line break replaced by a space. A run it did not finish
    prints pytest's own error in their place.
    """
    finished = run(module, seed, space)
    found = verdict(finished, module, given)
    if found is None:
        return Report(text=unfinished_text(finished, given), findings=0, finished=False)
    text = "".join(f"{identity}: {one_line(message)}\n" for identity, message in found.items())
    return Report(text=text, findings=len(found), finished=True)


def cpus() -> int | None:
    """Return C, the number of CPUs the gate's process may run on, read in this process, or `None` when it cannot be read.

    On a host that keeps an affinity, any but `darwin` and `win32`, C is the number of CPUs
    `os.sched_getaffinity` allows this process; elsewhere, as on macOS, it is the host's CPU
    count, `os.cpu_count()`, which is `None` when the host does not say. No command is run to
    read it.
    """
    if sys.platform != "darwin" and sys.platform != "win32":
        return len(os.sched_getaffinity(0))
    return os.cpu_count()


def processes(modules: int, cpus: int) -> int:
    """Return how many pytest processes run at once over `modules` test modules on a host of `cpus` CPUs: one per module up to floor(`cpus` / 2), and never fewer than one."""
    return max(1, min(modules, cpus // PROCESSES_PER_CPU_PAIR))


def make_spaces(spaces: list[Path]) -> tuple[Path, OSError] | None:
    """Make each directory of `spaces`, in order, and return the first one the OS would not make with its OS error, or `None` when every one was made."""
    for space in spaces:
        try:
            space.mkdir()
        except OSError as error:
            return space, error
    return None


def check(selection: Selection, count: int, spaces: list[Path]) -> tuple[int, bool]:
    """Print the seed line, then run every test module of `selection` in parallel on a host of `count` CPUs and print each module's lines, in the order the modules were given.

    Each module's pytest process takes the directory of `spaces` at its own place in the order
    the modules were given, already made. Return how many findings the modules printed, and
    whether pytest did not finish over some module. On any exception, `KeyboardInterrupt`
    included, no module that has not started is run, and every pytest process already started
    has ended before the exception leaves this function.
    """
    seed = secrets.randbits(SEED_BITS)
    sys.stdout.write(f"{GATE}: seed {seed}\n")
    findings = 0
    unfinished = False
    seeds = [seed] * len(selection.modules)
    pool = ThreadPoolExecutor(max_workers=processes(len(selection.modules), count))
    try:
        for module_report in pool.map(report, selection.modules.keys(), selection.modules.values(), seeds, spaces):
            sys.stdout.write(module_report.text)
            findings += module_report.findings
            unfinished = unfinished or not module_report.finished
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
    return findings, unfinished


def unlock(run_directory: Path) -> None:
    """Make `run_directory` and every directory inside it readable, writable and searchable by its owner, so that nothing a test left read-only keeps it from being deleted.

    A test may leave a directory under its own temp directory without the owner's read, write or
    search permission, which keeps its entries from being listed or removed. Only directories
    inside `run_directory`, itself included, are changed, never a symbolic link or what it points
    to, and never the scratch root above it. A directory whose mode cannot be read or changed is
    left as it is, so that deleting it fails and names the OS error.
    """
    directories = [str(run_directory)]
    while directories:
        directory = directories.pop()
        try:
            mode = os.lstat(directory).st_mode
            if not stat.S_ISDIR(mode):
                continue
            os.chmod(directory, stat.S_IMODE(mode) | stat.S_IRWXU)
            with os.scandir(directory) as entries:
                directories.extend(entry.path for entry in entries if entry.is_dir(follow_symlinks=False))
        except OSError:
            continue


def delete(run_directory: Path) -> OSError | None:
    """Delete `run_directory` and all it holds, a directory a test left read-only included, and return the OS error that left any of it behind, or `None` when nothing is left."""
    unlock(run_directory)
    try:
        shutil.rmtree(run_directory)
    except OSError as error:
        return error
    return None


def main(
    paths: list[Path],
    read_cpus: Callable[[], int | None] = cpus,
    scratch_root: Path | None = None,
) -> int:
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
    error in its place, and every module it did finish still prints its findings. The count line,
    in the same shape whether or not pytest finished, is the last line printed and the one line
    that counts files. When pytest did not finish over some test module, the run exits 2,
    whatever the other modules found.

    Each test module runs in a pytest process of its own, and a `conftest.py` gets none. The
    processes run in parallel, as many at once as there are test modules up to floor(C / 2) and
    never fewer than one, where C is the count `read_cpus` returns, `cpus` by default; a host whose count it cannot read
    runs no test, prints why and the count line, and exits 2. Each module's lines print together,
    in the order the modules were given, whatever the order the processes end in.

    Before its seed line the run makes one temp directory of its own under `scratch_root`, the
    system temp directory as `tempfile` gives it when `None`, and inside it one directory for each
    test module's pytest process. A directory of these the run cannot make prints one line naming
    its path and the OS error, then the count line with no finding, and exits 2, with no seed line
    and no test run. The run's temp directory and all it holds, a directory a test left read-only
    included, are deleted on every exit path, every exception included; a deletion that fails
    prints one line naming the path and the OS error after every module's lines, then the count
    line, and the run exits 2, whatever the modules found.
    """
    selection = select(paths)
    if not selection.modules:
        sys.stdout.write(f"{GATE}: no test file among {len(paths)} path(s); nothing was checked\n")
        return 1
    files = len(selection.modules) + len(selection.conftests)
    count = read_cpus()
    if count is None:
        sys.stdout.write(f"{GATE}: cannot read the number of CPUs this process may run on; no test was run\n")
        sys.stdout.write(f"{GATE}: 0 finding(s) in {files} Python file(s)\n")
        return BLOCKED
    root = Path(tempfile.gettempdir()) if scratch_root is None else scratch_root
    try:
        run_directory = Path(tempfile.mkdtemp(prefix=RUN_PREFIX, dir=root))
    except OSError as error:
        sys.stdout.write(f"{GATE}: cannot make a temp directory in {root}: {error}\n")
        sys.stdout.write(f"{GATE}: 0 finding(s) in {files} Python file(s)\n")
        return BLOCKED
    spaces = [run_directory / str(index) for index in range(len(selection.modules))]
    findings = 0
    unfinished = False
    try:
        unmade = make_spaces(spaces)
        if unmade is None:
            findings, unfinished = check(selection, count, spaces)
        else:
            space, refusal = unmade
            sys.stdout.write(f"{GATE}: cannot make a temp directory {space}: {refusal}\n")
    finally:
        left = delete(run_directory)
        if left is not None:
            sys.stdout.write(f"{GATE}: cannot delete the temp directory {run_directory}: {left}\n")
    sys.stdout.write(f"{GATE}: {findings} finding(s) in {files} Python file(s)\n")
    if unmade is not None or unfinished or left is not None:
        return BLOCKED
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
