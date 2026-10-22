"""Running a checker process: the command, what it gave back, and the host's throttle line and CPU budget."""

import contextlib
import functools
import os
import select as multiplexing
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType, TracebackType
from typing import IO, Protocol, Self, TypeGuard

from gates.core.clock import SYSTEM, Clock
from gates.core.report import GateError

# The niceness a throttled checker runs at: `nice -n` adds to the caller's own, so the step is this less it.
LOWEST_PRIORITY = 19

# The signals a closing terminal, the quit key, `kill` and the interrupt key send to end a process.
ENDING_SIGNALS = (signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM)

# How often `run_all`, cleaning up, kills again the groups of checkers started since, while it waits for its workers.
REKILL = 0.05

# The GateError's report when the count of CPUs cannot be read.
UNREAD_CPUS = "cannot read the host's CPU count"


@dataclass(frozen=True)
class Command:
    """A checker process to run: its argv, directory, environment, time cap, throttling, output files and fds."""

    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str] | None = None
    timeout: float | None = None
    throttled: bool = False
    outputs: Mapping[str, Path] = field(default_factory=dict[str, Path])
    capture: bool = True
    pass_fds: tuple[int, ...] = ()


@dataclass(frozen=True)
class Completed:
    """What a checker process gave back: its status as a shell reports it, its streams, and the files it wrote."""

    status: int
    stdout: str
    stderr: str
    timed_out: bool
    outputs: Mapping[str, str | None]

    def output(self) -> str:
        """Return the checker's whole console output: its stdout, then its stderr, joined as they are."""
        return self.stdout + self.stderr


type Runner = Callable[[Command], Completed]


def run(command: Command, *, clock: Clock = SYSTEM) -> Completed:
    """Run the checker in a session of its own; kill its whole group at the timeout or on any interrupt.

    An interrupt is any signal of ENDING_SIGNALS that would end this process, from the moment the checker starts
    to the moment it is reaped. The group is killed first; the signal then takes its course. Output files already
    at their paths are deleted before the checker starts, so each one read back was written by this checker.

    The wait on the checker's exit is the Ready handed to the clock, and the timeout passes on that clock.

    Raises GateError when the program cannot start, when the wait on it cannot be set up, or when an output file cannot be deleted or read.
    """
    argv = command.argv
    if command.throttled:
        path = os.pathsep.join(os.get_exec_path(command.env))
        argv = (*throttle_line(sys.platform, os.getpriority(os.PRIO_PROCESS, 0), path), *argv)
    paths = {name: command.cwd / path for name, path in command.outputs.items()}
    for output in paths.values():
        _clear(output)
    with _Interrupts() as interrupts, contextlib.ExitStack() as stack:
        out, err = _streams(command, stack)
        try:
            process = subprocess.Popen(
                argv,
                cwd=command.cwd,
                env=command.env,
                stdout=out,
                stderr=err,
                start_new_session=True,
                pass_fds=command.pass_fds,
            )
        except OSError as error:
            message = f"cannot start the checker {argv[0]}: {error}"
            raise GateError(message) from error
        with process:
            _LIVE.add(process)
            timed_out = _settle(process, command.timeout, interrupts, clock)
        return Completed(
            status=_shell_status(process.wait()),
            stdout=_text(out),
            stderr=_text(err),
            timed_out=timed_out,
            outputs={name: _written(output) for name, output in paths.items()},
        )


class _Ended(BaseException):
    """Raised in place of a signal whose action was the OS default, so that the run cleans up before the signal ends the process."""


class _Interrupts:
    """The handlers of ENDING_SIGNALS during one run, so that the run cleans up before any of them takes its course.

    A signal whose handler is Python's, or whose action is the OS default, is answered here; one ignored stays
    ignored. While `holding`, a signal is only recorded, so no handler's exception lands where the run has no
    process yet to kill or is killing it. `release` lets signals through and raises each one recorded; leaving the
    run puts the handlers back and raises each signal recorded since, so the signal takes the course it would have
    taken without the run. Handlers are set only in the main thread, the one thread Python allows to set them.
    """

    def __init__(self) -> None:
        """Hold every signal that arrives, and replace no handler yet."""
        self.holding = True
        self.replaced: dict[int, Callable[[int, FrameType | None], object] | signal.Handlers] = {}
        self.pending: list[int] = []

    def __enter__(self) -> Self:
        """Answer each signal of ENDING_SIGNALS that has a Python handler or the OS default, in the main thread."""
        if threading.current_thread() is threading.main_thread():
            for signum in ENDING_SIGNALS:
                handler = signal.getsignal(signum)
                if callable(handler):
                    self.replaced[signum] = handler
                elif handler == signal.SIG_DFL:
                    self.replaced[signum] = signal.Handlers.SIG_DFL
                else:
                    continue
                signal.signal(signum, self.answer)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Put back every handler replaced, then raise each signal recorded, which its own handler now answers."""
        self.holding = True
        try:
            for signum, handler in self.replaced.items():
                signal.signal(signum, handler)
        finally:
            self.holding = False
        self._raise_pending()

    def answer(self, signum: int, frame: FrameType | None) -> None:
        """Record the signal while holding; otherwise pass it to the Python handler it replaced, or end the run."""
        if self.holding:
            self._record(signum)
            return
        handler = self.replaced[signum]
        if callable(handler):
            handler(signum, frame)
            return
        self._record(signum)
        raise _Ended(signal.Signals(signum).name)

    def release(self) -> None:
        """Stop holding, then raise each signal recorded so far."""
        self.holding = False
        self._raise_pending()

    def _record(self, signum: int) -> None:
        """Record the signal once, however often it arrives, to raise it again later."""
        if signum not in self.pending:
            self.pending.append(signum)

    def _raise_pending(self) -> None:
        """Raise, in the order they arrived, each signal recorded, until one's handler raises."""
        while self.pending:
            signal.raise_signal(self.pending.pop(0))


def _streams(command: Command, stack: contextlib.ExitStack[bool | None]) -> tuple[IO[bytes] | None, IO[bytes] | None]:
    """Open the files the checker's stdout and stderr go to, or none when it writes straight to the run's own fds."""
    if not command.capture:
        return None, None
    return stack.enter_context(tempfile.TemporaryFile()), stack.enter_context(tempfile.TemporaryFile())


def _settle(process: subprocess.Popen[bytes], timeout: float | None, interrupts: _Interrupts, clock: Clock) -> bool:
    """Wait through the clock for the checker to end; return whether the timeout passed first on that clock.

    Whatever ends the wait, the checker's whole process group is then killed, so no process still in that group
    outlives the run; one that left it, as by its own setsid, is not killed. The checker is reaped only after that
    kill, so its pid still names its group.
    """
    ended = False
    try:
        interrupts.release()
        ended = clock.wait(functools.partial(_await_exit, process), timeout)
    finally:
        interrupts.holding = True
        _kill_group(process)
    return not ended


def _await_exit(process: subprocess.Popen[bytes], timeout: float | None) -> bool:
    """Wait up to the timeout until the checker has exited, without reaping it; return whether it has.

    The wait is on the checker alone, never on what a process of its own holds open. On Linux it waits on a pidfd
    of the checker; elsewhere, as on macOS, on a kqueue event for its exit, whose registration the OS refuses with
    ProcessLookupError for a process that has exited already and waits to be reaped.

    Raises GateError when the pidfd cannot be opened, as on a kernel before Linux 5.3 or under a seccomp filter.
    """
    if sys.platform == "linux":
        try:
            descriptor = os.pidfd_open(process.pid)
        except OSError as error:
            message = f"cannot wait on the checker {process.pid}: {error}"
            raise GateError(message) from error
        try:
            return bool(multiplexing.select([descriptor], [], [], timeout)[0])
        finally:
            os.close(descriptor)
    else:
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
                return True
            return bool(queue.control(None, 1, timeout))
        finally:
            queue.close()


class _Live:
    """The checkers `run` has started, in any thread, and not yet reaped, so that `run_all` can kill their groups.

    A checker is reaped only under the lock and leaves the set there, so every checker the set holds is unreaped and
    its pid still names its group.
    """

    def __init__(self) -> None:
        """Hold no checker yet."""
        self._lock = threading.Lock()
        self._processes: set[subprocess.Popen[bytes]] = set()

    def add(self, process: subprocess.Popen[bytes]) -> None:
        """Hold a checker just started."""
        with self._lock:
            self._processes.add(process)

    def reap(self, process: subprocess.Popen[bytes]) -> None:
        """Kill the checker's group unless the checker has been reaped, then reap it and let it go."""
        with self._lock:
            _kill_unreaped(process)
            process.wait()
            self._processes.discard(process)

    def kill_all(self) -> None:
        """Kill the group of every checker held."""
        with self._lock:
            for process in self._processes:
                _kill_unreaped(process)


_LIVE = _Live()


def _kill_group(process: subprocess.Popen[bytes]) -> None:
    """Kill every process of the checker's group unless the checker has been reaped, then reap the checker."""
    _LIVE.reap(process)


def _kill_unreaped(process: subprocess.Popen[bytes]) -> None:
    """Kill every process of the checker's group unless the checker has been reaped.

    A reaped checker's pid may name another process, so it is never signalled. A group already gone is
    ProcessLookupError; macOS refuses a group of zombies alone with PermissionError.
    """
    if process.returncode is None:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signal.SIGKILL)


def _shell_status(returncode: int) -> int:
    """Return the status as a shell reports it: an exit code as it is, a death by signal as 128 plus the signal."""
    return returncode if returncode >= 0 else 128 - returncode


def _text(stream: IO[bytes] | None) -> str:
    """Return what the checker wrote to the stream, or nothing for a stream it wrote straight to the run's own fd."""
    if stream is None:
        return ""
    stream.seek(0)
    return _decode(stream.read())


def _clear(path: Path) -> None:
    """Delete an output file left at the path before the checker starts, so that one found after was written by it.

    Raises GateError when the path cannot be deleted, a directory among them.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError as error:
        message = f"cannot delete the output file {path}: {error}"
        raise GateError(message) from error


def _written(path: Path) -> str | None:
    """Return the text of an output file the checker wrote, or None for one it did not write.

    Raises GateError when the file exists and cannot be read.
    """
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        message = f"cannot read the output file {path}: {error}"
        raise GateError(message) from error
    return _decode(data)


def _decode(data: bytes) -> str:
    """Decode a checker's bytes as UTF-8, a byte that is no UTF-8 as the replacement character."""
    return data.decode("utf-8", errors="replace")


def python_module(module: str, *arguments: str | Path, cwd: Path, timeout: float | None = None) -> Command:
    """Return the Command that runs the module with this interpreter, each argument as its text."""
    argv = (sys.executable, "-m", module, *(str(argument) for argument in arguments))
    return Command(argv=argv, cwd=cwd, timeout=timeout)


def environment(*, drop_prefixes: tuple[str, ...] = (), drop: frozenset[str] = frozenset()) -> dict[str, str]:
    """Return this process's variables now, less each whose name starts with a prefix or is in the drop set."""
    return {
        name: value
        for name, value in os.environ.items()
        if name not in drop and not name.startswith(drop_prefixes)
    }


def throttle_line(platform: str, niceness: int, path: str | None = None) -> list[str]:
    """Return heavy's line up to its `--` for the host and the caller's niceness; each tool is looked up on path.

    Raises GateError on a host with no line, or when a tool of the line is not on path (None: os.environ's PATH).
    """
    nice = ["nice", "-n", str(max(0, LOWEST_PRIORITY - niceness)), "--"]
    tools: tuple[str, ...]
    match platform:
        case "linux":
            line = ["ionice", "-c3", *nice]
            tools = ("ionice", "nice")
        case "darwin":
            line = nice
            tools = ("nice",)
        case _:
            message = f"cannot throttle the checker: no throttle line for host {platform}"
            raise GateError(message)
    missing = [tool for tool in tools if shutil.which(tool, path=path) is None]
    if missing:
        message = f"cannot throttle the checker: not on PATH: {' '.join(missing)}"
        raise GateError(message)
    return line


def cpu_budget(cpus: int | None = None) -> int:
    """Return floor(cpus / 2), the cap on mutation and backstop workers; 0 and 1 CPUs give 0, never lifted to 1.

    With no count, the CPUs are those this process may run on: its affinity where the host keeps one (it has
    `os.sched_getaffinity`), else the host's count, as on macOS.

    Raises GateError when no count is given and the host's count cannot be read.
    """

    class Affinity(Protocol):
        def sched_getaffinity(self, pid: int, /) -> set[int]: ...

    def keeps_affinity(host: object) -> TypeGuard[Affinity]:
        return hasattr(host, "sched_getaffinity")

    host: object = os
    if cpus is None:
        cpus = len(host.sched_getaffinity(0)) if keeps_affinity(host) else os.cpu_count()
    if cpus is None:
        raise GateError(UNREAD_CPUS)
    return cpus // 2


type NextDone = Callable[[Collection[Future[Completed]]], set[Future[Completed]]]


def first_done(running: Collection[Future[Completed]]) -> set[Future[Completed]]:
    raise NotImplementedError


def run_all(
    process: Runner,
    commands: Iterable[Command],
    cap: int,
    *,
    next_done: NextDone = first_done,
) -> list[Completed | GateError | OSError]:
    """Run each Command through the process in worker threads, at most cap at once; return the results in their order.

    The next Command is taken, in the calling thread, only when fewer than cap are running. A GateError or OSError from
    taking a Command or from the process is that Command's result and stops the run: no Command is taken after it is
    seen, the ones running are waited for, and the list ends at the first error in command order. While it runs, the
    main thread answers ENDING_SIGNALS as `run` does; on any exception there, a signal's included, it holds signals,
    kills the group of every checker `run` has started and not yet reaped, waits for every worker, puts the handlers
    back, and only then lets the exception and each signal recorded take their course.
    """
    if next_done is not first_done:
        raise NotImplementedError
    results: dict[int, Completed | GateError | OSError] = {}
    running: dict[Future[Completed], int] = {}
    with _Interrupts() as interrupts, ThreadPoolExecutor(max_workers=cap) as pool:
        try:
            interrupts.release()
            _feed(process, iter(commands), cap, pool, running, results, interrupts)
        except BaseException:
            interrupts.holding = True
            _drain(running)
            raise
    return _in_order(results)


def _feed(
    process: Runner,
    commands: Iterator[Command],
    cap: int,
    pool: ThreadPoolExecutor,
    running: dict[Future[Completed], int],
    results: dict[int, Completed | GateError | OSError],
    interrupts: _Interrupts,
) -> None:
    """Start Commands while fewer than cap run and none has failed, and gather each result until none is running.

    A worker is submitted while signals are held, so no signal lands between its start and its record in `running`.
    """
    taken = 0
    taking = True
    while True:
        while taking and len(running) < cap:
            try:
                command = next(commands)
            except StopIteration:
                taking = False
                break
            except (GateError, OSError) as error:
                results[taken] = error
                taking = False
                break
            interrupts.holding = True
            running[pool.submit(process, command)] = taken
            interrupts.release()
            taken += 1
        if not running:
            return
        done, _ = wait(running, return_when=FIRST_COMPLETED)
        for future in done:
            index = running.pop(future)
            try:
                results[index] = future.result()
            except (GateError, OSError) as error:
                results[index] = error
                taking = False


def _drain(running: dict[Future[Completed], int]) -> None:
    """Kill the group of every unreaped checker, again and again, until every worker has ended."""
    while True:
        _LIVE.kill_all()
        _, left = wait(running, timeout=REKILL)
        if not left:
            return


def _in_order(results: Mapping[int, Completed | GateError | OSError]) -> list[Completed | GateError | OSError]:
    """Return the results in command order, ending at the first error."""
    ordered: list[Completed | GateError | OSError] = []
    for index in sorted(results):
        ordered.append(results[index])
        if isinstance(results[index], GateError | OSError):
            break
    return ordered
