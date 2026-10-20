"""pytest gate: run the test files among the given Python files under the strict pytest settings in `pyproject.toml`."""

import fnmatch
import functools
import os
import re
import secrets
import select as multiplexing
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from concurrent.futures import CancelledError, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
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

DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY

STDOUT = "stdout"

STDERR = "stderr"

OUTPUT_ENCODING = "locale"

ENDING_SIGNALS = frozenset({signal.SIGHUP, signal.SIGQUIT, signal.SIGTERM})


@dataclass(frozen=True)
class Selection:
    """The test files among the given paths: each test module by its absolute path, with the path as it was given, and the `conftest.py` files beside them."""

    modules: dict[str, Path]
    conftests: frozenset[str]


@dataclass(frozen=True)
class Outcome:
    """One `failure` or `error` element of pytest's JUnit XML report: its `message` attribute."""

    message: str


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


def kill_group(process: subprocess.Popen[bytes]) -> None:
    """Kill the pytest process `process` and every process in its process group, each process a test started included, unless `process` has been reaped.

    Each pytest process leads a process group of its own, which every process a test starts joins
    unless it leaves it, so the kill reaches them all. A reaped process's ID may name another
    process, so it is never signalled. A group with no process left, and one the OS will not let
    the gate signal, as macOS will not a group whose every process has exited and waits to be
    reaped, are left as they are.
    """
    if process.returncode is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        return


def await_exit(process: subprocess.Popen[bytes]) -> None:
    """Wait until the process `process` has exited, without reaping it, so that its ID still names it and its process group.

    The wait waits on `process` alone, never on anything a process it started holds open. On Linux it waits on a pidfd of `process`; elsewhere, as on macOS, on a kqueue event for
    its exit, whose registration the OS refuses with `ESRCH` for a process that has exited already
    and waits to be reaped.
    """
    if sys.platform == "linux":
        descriptor = os.pidfd_open(process.pid)
        try:
            multiplexing.select([descriptor], [], [])
        finally:
            os.close(descriptor)
        return
    queue = multiplexing.kqueue()
    try:
        exit_event = multiplexing.kevent(
            process.pid,
            multiplexing.KQ_FILTER_PROC,
            multiplexing.KQ_EV_ADD | multiplexing.KQ_EV_ONESHOT,
            multiplexing.KQ_NOTE_EXIT,
        )
        try:
            queue.control([exit_event], 0, 0)
        except ProcessLookupError:
            return
        queue.control(None, 1, None)
    finally:
        queue.close()


def finish(process: subprocess.Popen[bytes]) -> None:
    """Wait until the pytest process `process` has exited, then kill every process left in its process group.

    A process a test started and left running, while pytest itself exits, is killed as soon as
    pytest has exited and before it is reaped, so none in pytest's group outlives the run or
    writes into its temp directory while it is deleted. The wait ends when pytest exits, whatever
    a process that left pytest's group holds open, since pytest's output goes to files, never to
    a pipe the gate reads to its end. On any exception, `process` and every process in its group
    are killed too.
    """
    try:
        await_exit(process)
    finally:
        kill_group(process)


class Started:
    """The pytest processes one check has started and not yet reaped, each of which it can end at once with every process in its process group; once ended, it starts no other."""

    def __init__(self) -> None:
        """Hold no process, and start one on request."""
        self.lock = threading.Lock()
        self.live: set[subprocess.Popen[bytes]] = set()
        self.ended = False

    def run(self, command: list[str], environment: dict[str, str], space: Path) -> subprocess.CompletedProcess[str]:
        """Run `command` from the repository root in `environment` and return its completed process with its output as text, as `subprocess.run` would, or raise `CancelledError` when this set was already ended.

        The process writes its stdout and its stderr each to a file of its own that this call makes
        new in the directory `space`, and both are read once it has exited, decoded as
        `subprocess.run` decodes text. Any OS error met making the files, starting the process or
        reading the files is raised.
        """
        out_path, err_path = space / STDOUT, space / STDERR
        with open(out_path, "xb") as out, open(err_path, "xb") as err, self.lock:
            if self.ended:
                raise CancelledError
            process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=out, stderr=err, process_group=0)
            self.live.add(process)
        with process:
            try:
                finish(process)
            finally:
                with self.lock:
                    self.live.discard(process)
        stdout = out_path.read_text(encoding=OUTPUT_ENCODING)
        stderr = err_path.read_text(encoding=OUTPUT_ENCODING)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)

    def end(self) -> None:
        """Kill every process this set started and has not reaped, with every process in its process group, and start no other."""
        with self.lock:
            self.ended = True
            for process in self.live:
                kill_group(process)


class Ended(BaseException):
    """Raised in the main thread in place of a hangup, quit or terminate signal whose action was the OS default, so that the run cleans up before the signal ends the gate."""


class Deferral:
    """The Python-level signal handlers of one run, and the OS default of each signal sent to end a process, each answered in its place, so that a signal that arrives while the run cleans up is held until it has cleaned up.

    Python runs a signal's handler in the main thread alone, between two bytecode instructions,
    whichever thread the signal reached, so a handler's exception, `KeyboardInterrupt` among them,
    can land at any point of the main thread's code. While `holding` is set, the handler this run
    installs records the signal and returns, so no handler's exception stops the run's cleanup
    partway; while it is clear, the signal goes on to the handler it replaced. `holding` starts
    set, and each block that cleans up sets it in its first statement, a bare attribute store,
    which runs no handler, so a signal that arrived before the block is held too.

    A signal of `ENDING_SIGNALS`, sent to end a process as a closing terminal, the quit key and
    `kill` send theirs, whose action is the OS default, would end the gate at once and pass over
    its cleanup, leaving every pytest process group, which a signal sent to the gate's group no
    longer reaches, running in a temp directory never deleted. It is answered too: once let
    through, it is recorded and raised as `Ended`, so the run cleans up, and `restore` raises it
    again once its default is back, so it ends the gate as the default would have. A signal the
    gate ignores stays ignored.
    """

    def __init__(self) -> None:
        """Replace no handler yet, and hold every signal that arrives."""
        self.holding = True
        self.replaced: dict[int, Callable[[int, FrameType | None], object] | signal.Handlers] = {}
        self.arrived: list[int] = []

    def install(self) -> None:
        """Answer every signal that has a Python-level handler, and every signal of `ENDING_SIGNALS` whose action is the OS default, when this thread is the main thread; in any other thread no handler can be set, so none is replaced."""
        if threading.current_thread() is not threading.main_thread():
            return
        for signum in sorted(signal.valid_signals()):
            handler = signal.getsignal(signum)
            if callable(handler):
                self.replaced[signum] = handler
            elif signum in ENDING_SIGNALS and handler == signal.SIG_DFL:
                self.replaced[signum] = signal.SIG_DFL
            else:
                continue
            signal.signal(signum, self.answer)

    def record(self, signum: int) -> None:
        """Record that the signal `signum` arrived, once however often it arrives, so that it is raised again later."""
        if signum not in self.arrived:
            self.arrived.append(signum)

    def answer(self, signum: int, frame: FrameType | None) -> None:
        """Record the signal `signum` while `holding` is set, and otherwise hand it and `frame` on to the handler it replaced, or, for a signal whose action was the OS default, record it and raise `Ended`."""
        if self.holding:
            self.record(signum)
            return
        handler = self.replaced[signum]
        if callable(handler):
            handler(signum, frame)
            return
        self.record(signum)
        raise Ended(signal.Signals(signum).name)

    def raise_arrived(self) -> None:
        """Raise again, in the order they arrived, each signal held so far, until one's handler raises."""
        arrived, self.arrived = self.arrived, []
        for signum in arrived:
            signal.raise_signal(signum)

    def release(self) -> None:
        """Clear `holding`, and raise again each signal held so far, so it reaches the handler it was held from."""
        self.holding = False
        self.raise_arrived()

    def restore(self) -> None:
        """Put back every handler this run replaced, then raise again each signal held so far, which its own handler now answers.

        Called with `holding` set, so a signal that arrives while the handlers are put back is held.
        Should a handler already put back raise before the rest are, `holding` is cleared, so each
        handler still replaced hands its signal on as if it were not.
        """
        try:
            for signum, handler in self.replaced.items():
                signal.signal(signum, handler)
        finally:
            self.holding = False
        self.raise_arrived()


class Unlocked(Exception):
    """Raised by `unlock` once it has given a directory back its owner's permissions, so that the deletion starts again."""


class Left(Exception):
    """Raised by `unlock` with the OS error that leaves temp space behind, so that the deletion stops on that error as it is."""

    def __init__(self, error: OSError) -> None:
        """Carry `error`, the OS error that leaves temp space behind."""
        super().__init__(error)
        self.error = error


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
            outcomes.append(Outcome(message=message))
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


def run(module: str, seed: int, space: Path, started: Started) -> Run:
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
    process shares: its JUnit XML report and its stdout and stderr are written in it, and pytest's `--basetemp` is a path in
    it that pytest itself makes. `--basetemp` is passed on the command line and changes no
    setting `pyproject.toml` holds. The pytest process is one of `started`, which ends it when the
    check it runs for is cut short.
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
    completed = started.run(command, environment, space)
    return Run(completed=completed, cases=read_report(report))


def unfinished_text(unfinished: Run) -> str:
    """Return pytest's own error for a run over a test module that it did not finish, and nothing of the gate's own.

    pytest's own error is its whole console output, its stdout and then its stderr, printed
    as it wrote them and never parsed: pytest reports a collection error or a run that collected
    no test on its stdout, and a usage error or an unknown config key on its stderr, and a
    `conftest.py` may write to either. No line of the gate's own follows it, neither pytest's exit
    status nor that it collected no test, which pytest's output already says in its own words.
    """
    lines = [*unfinished.completed.stdout.splitlines(), *unfinished.completed.stderr.splitlines()]
    return "".join(f"{line}\n" for line in lines)


def report(module: str, given: Path, seed: int, space: Path, started: Started) -> Report:
    """Run pytest over the test module at `module`, given as `given`, with pytest-randomly's seed `seed` and the module's own temp directory `space`, as one of `started`, and return what the gate prints for it.

    A run pytest finished prints each failing test as one finding, its id, a colon, a space and
    the message of its failure with every line break replaced by a space. A run it did not finish
    prints pytest's own error in their place. A pytest the gate cannot run, an OS error met making
    its output files, starting it or reading its output, did not finish either, and prints one
    line naming the module and the OS error.
    """
    try:
        finished = run(module, seed, space, started)
    except OSError as error:
        return Report(text=f"{GATE}: cannot run pytest on {given}: {error}\n", findings=0, finished=False)
    found = verdict(finished, module, given)
    if found is None:
        return Report(text=unfinished_text(finished), findings=0, finished=False)
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


def check(selection: Selection, count: int, spaces: list[Path], deferral: Deferral) -> tuple[int, bool]:
    """Print the seed line, then run every test module of `selection` in parallel on a host of `count` CPUs and print each module's lines, in the order the modules were given.

    Each module's pytest process takes the directory of `spaces` at its own place in the order
    the modules were given, already made. Return how many findings the modules printed, and
    whether pytest did not finish over some module. On any exception, `KeyboardInterrupt`
    included, no module that has not started is run, and every pytest process already started
    is killed with every process in its process group, and has ended before the exception leaves
    this function. From the moment the modules stop running, `deferral` holds every signal, so
    none stops that cleanup partway.
    """
    seed = secrets.randbits(SEED_BITS)
    sys.stdout.write(f"{GATE}: seed {seed}\n")
    findings = 0
    unfinished = False
    seeds = [seed] * len(selection.modules)
    started = Started()
    pool = ThreadPoolExecutor(max_workers=processes(len(selection.modules), count))
    try:
        for module_report in pool.map(functools.partial(report, started=started), selection.modules.keys(), selection.modules.values(), seeds, spaces):
            sys.stdout.write(module_report.text)
            findings += module_report.findings
            unfinished = unfinished or not module_report.finished
    finally:
        deferral.holding = True
        started.end()
        pool.shutdown(wait=True, cancel_futures=True)
    return findings, unfinished


def claim(status: os.stat_result, unlocked: set[tuple[int, int]]) -> int | None:
    """Return the mode that gives the directory `status` describes its owner's read, write and search permission, recording it in `unlocked`, or `None` when it is no directory, has them all already, or is in `unlocked`, given them once before."""
    identity = (status.st_dev, status.st_ino)
    if not stat.S_ISDIR(status.st_mode) or status.st_mode & stat.S_IRWXU == stat.S_IRWXU or identity in unlocked:
        return None
    unlocked.add(identity)
    return stat.S_IMODE(status.st_mode) | stat.S_IRWXU


def open_holder(run_directory: Path, names: tuple[str, ...]) -> int:
    """Open the directory that holds the entry `names` reaches from the directory above `run_directory`, each name opened inside the directory before it and never through a symbolic link, and return its file descriptor."""
    descriptor = os.open(run_directory.parent, DIRECTORY_FLAGS)
    try:
        for name in names[:-1]:
            outer, descriptor = descriptor, os.open(name, DIRECTORY_FLAGS | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(outer)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def unlock(
    run_directory: Path,
    unlocked: set[tuple[int, int]],
    function: object,
    path: str,
    error: BaseException,
) -> None:
    """Answer the OS error `error` that `shutil.rmtree`, deleting `run_directory`, met calling `function` on the entry at `path`.

    A test may leave a directory under its own temp directory without the owner's read, write or
    search permission, which keeps its entries from being listed or removed. When the OS refused
    permission, the directory that holds the entry is given its owner's read, write and search
    permission, and so is the entry itself when it is a directory without them, whatever
    `function` is, since which function `shutil.rmtree` names depends on the platform; then
    `Unlocked` is raised, so that the deletion starts again. Only directories inside
    `run_directory`, itself included, are changed, never the scratch root above it, and never a
    symbolic link or what it points to: each is reached by name from the directory that holds
    it, none through a symbolic link, and changed through its file descriptor or by its name
    there. A directory given its permissions once is never given them again, so the deletion
    always ends. Any other error, a refusal that giving permissions cannot answer, and any OS
    error met giving them, is raised as `Left`, so that the deletion stops on it as it is.
    """
    if not isinstance(error, OSError):
        raise error
    if not isinstance(error, PermissionError):
        raise Left(error)
    names = (run_directory.name, *Path(path).relative_to(run_directory).parts)
    try:
        holder = open_holder(run_directory, names)
        try:
            changed = False
            mode = claim(os.fstat(holder), unlocked) if len(names) > 1 else None
            if mode is not None:
                os.fchmod(holder, mode)
                changed = True
            mode = claim(os.stat(names[-1], dir_fd=holder, follow_symlinks=False), unlocked)
            if mode is not None:
                os.chmod(names[-1], mode, dir_fd=holder, follow_symlinks=False)
                changed = True
        finally:
            os.close(holder)
    except OSError as failure:
        raise Left(failure) from error
    if not changed:
        raise Left(error)
    raise Unlocked


def delete(run_directory: Path) -> OSError | None:
    """Delete `run_directory` and all it holds, a directory a test left read-only included, and return the OS error that left any of it behind, or `None` when nothing is left.

    The deletion is `shutil.rmtree`'s own walk, which never follows a symbolic link, with `unlock`
    answering each error it meets; the walk starts again after each directory `unlock` gives back
    its owner's permissions.
    """
    unlocked: set[tuple[int, int]] = set()
    answer = functools.partial(unlock, run_directory, unlocked)
    while True:
        try:
            shutil.rmtree(run_directory, onexc=answer)
        except Unlocked:
            continue
        except Left as left:
            return left.error
        return None


def check_within(selection: Selection, count: int, run_directory: Path, deferral: Deferral) -> tuple[int, bool]:
    """Release the signals `deferral` holds, run the check of `selection` on a host of `count` CPUs in the run's temp directory `run_directory`, and delete it.

    The caller made `run_directory` while `deferral` held every signal, so that no signal's
    exception lands between its making and the `try` here whose `finally` deletes it; signals are
    let through only inside that `try`, and held again from the first statement of its `finally`
    on, so none stops the deletion partway. Each module's pytest process takes a directory of
    its own inside `run_directory`; one the OS will not make prints one line naming its path and
    the OS error, and no test runs. A deletion that fails prints one line naming the path and the
    OS error, after every module's lines. Return how many findings the modules printed, and
    whether the run exits 2: a directory not made, pytest not finishing over some module, or a
    deletion that failed.
    """
    findings = 0
    unfinished = False
    unmade: tuple[Path, OSError] | None = None
    try:
        deferral.release()
        spaces = [run_directory / str(index) for index in range(len(selection.modules))]
        unmade = make_spaces(spaces)
        if unmade is None:
            findings, unfinished = check(selection, count, spaces, deferral)
        else:
            space, refusal = unmade
            sys.stdout.write(f"{GATE}: cannot make a temp directory {space}: {refusal}\n")
    finally:
        deferral.holding = True
        left = delete(run_directory)
        if left is not None:
            sys.stdout.write(f"{GATE}: cannot delete the temp directory {run_directory}: {left}\n")
    return findings, unmade is not None or unfinished or left is not None


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
    included, are deleted on every exit path, every exception included, and so on a hangup, quit
    or terminate signal left to the OS default, which ends the gate once the run has cleaned up;
    a deletion that fails
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
    deferral = Deferral()
    try:
        deferral.install()
        try:
            run_directory = Path(tempfile.mkdtemp(prefix=RUN_PREFIX, dir=root))
        except OSError as error:
            sys.stdout.write(f"{GATE}: cannot make a temp directory in {root}: {error}\n")
            findings, blocked = 0, True
        else:
            findings, blocked = check_within(selection, count, run_directory, deferral)
    finally:
        deferral.restore()
    sys.stdout.write(f"{GATE}: {findings} finding(s) in {files} Python file(s)\n")
    if blocked:
        return BLOCKED
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
