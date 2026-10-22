"""Host-safety wrapper: run one heavy command under an exclusive lock, at niceness 19 and, on Linux, the lowest I/O priority."""

import argparse
import os
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import IO, override

from gates.core.checker import Command, run as run_command, throttle_line
from gates.core.report import GateError, Outcome, Unfinished, exit_code, output_lines, write

LOCK = Path("/tmp/gauntlet-heavy.lock")

LOCK_OPTION = "--lock"

END_OPTIONS = "--"

WAITING: str = "heavy: waiting for the lock {path}"


def acquire(handle: IO[str], lock: Path, err: IO[str]) -> None:
    """Take an exclusive `fcntl.flock` on `handle`, the open of `lock`, and return once it is held.

    The lock is asked for without blocking first. When another holder has it, `WAITING` for `lock`
    and a line end are written on `err` once, as one write, and flushed, so a reader of `err` sees
    the wait as that line; then the lock is waited on, never polled. Any `OSError` from the lock
    reaches the caller. `fcntl` is imported here, not with the module, because a host without it
    gets no throttle line, which `main` reports with exit 2 before this runs.
    """
    import fcntl

    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        err.write(f"{WAITING.format(path=lock)}\n")
        err.flush()
        fcntl.flock(handle, fcntl.LOCK_EX)


def run(lock: Path, line: list[str]) -> int:
    """Hold an exclusive `fcntl.flock` on `lock` for the whole of `line`'s run and return its exit status.

    The lock is taken through `acquire`, with `sys.stderr` as its stream, so a run that finds the
    lock held writes `WAITING` for `lock` there once and then waits, never polls, and a second run
    on the same path starts once the first ends. The locked descriptor is passed to `line`'s process, as `flock(1)` passes it, so the
    lock lasts as long as the command and every process that inherits the descriptor from it,
    not only as long as this wrapper. The line runs through `checker.run`, writing straight to this
    process's own output, in a session of its own whose whole group is killed if a signal ends the
    wrapper, so a wrapper that is stopped leaves no command holding the lock.

    Raises GateError where `lock` cannot be opened or locked, or the line's program cannot start;
    `line` is then never run.
    """
    with ExitStack() as stack:
        try:
            handle = stack.enter_context(lock.open("a", encoding="utf-8"))
            acquire(handle, lock, sys.stderr)
        except OSError as error:
            message = f"cannot lock {lock}: {error}"
            raise GateError(message) from error
        command = Command(argv=tuple(line), cwd=Path.cwd(), capture=False, pass_fds=(handle.fileno(),))
        return run_command(command).status


class Arguments(argparse.Namespace):
    """The wrapper's arguments as `parser` reads them: the path to lock and the command to run under it."""

    lock: Path
    command: list[str]


class Parser(argparse.ArgumentParser):
    """An argument parser that takes a word for an option only where its own option table holds it.

    `argparse` takes a word that begins with `-` for an option even where it has no option of that
    name, and refuses it. Here such a word is an argument, so a command whose first word begins
    with `-` is read as the command, and the option table is all that decides which words are
    options.
    """

    @override
    def _parse_optional(self, arg_string: str) -> list[tuple[argparse.Action | None, str, str | None, str | None]] | None:
        """Return what `argparse` makes of `arg_string` where the text before any `=` names an option, else None, an argument."""
        if arg_string.partition("=")[0] in self._option_string_actions:
            return super()._parse_optional(arg_string)
        return None


def lock_path(text: str) -> Path:
    """Return `text` as the path to lock, refusing an empty one, which `Path` would read as the current directory."""
    if not text:
        raise argparse.ArgumentTypeError("empty path")
    return Path(text)


def parser() -> argparse.ArgumentParser:
    """Return the parser of `heavy [--lock <path>] [--] <command> ...`, whose usage errors exit 2.

    `--lock` takes its path as a separate word or after `=`, defaults to `LOCK`, and refuses an
    empty path. The command is every word from the first one that is not an option of the
    wrapper's own, one that begins with `-` included, and is required; it keeps every argument it
    was given, a `--lock` among them. One `--` right after the options ends them and is not part
    of the command, as `argparse.PARSER` drops it; a later `--` is the command's own. The parser
    has no `--help`, since a wrapper that exits 0 having run nothing would read as a passed gate,
    and takes no abbreviation of `--lock`.
    """
    result = Parser(
        prog="heavy",
        usage=f"%(prog)s [{LOCK_OPTION} <path>] [{END_OPTIONS}] <command> ...",
        add_help=False,
        allow_abbrev=False,
    )
    result.add_argument(LOCK_OPTION, type=lock_path, default=LOCK)
    result.add_argument("command", nargs=argparse.PARSER)
    return result


def main(arguments: list[str]) -> int:
    """Run the command in `arguments` under the host lock, throttled, and exit with its exit status.

    `arguments` is read by `parser`: the command, optionally preceded by `--lock <path>` or
    `--lock=<path>`, which locks that path in place of `/tmp/gauntlet-heavy.lock`, and by one
    `--`, which is not passed on. The command is run as given whatever its first word, one that
    begins with `-` included. With no command, or `--lock` with no path or an empty one, the
    wrapper prints its usage and exits 2. The line comes from `throttle_line`, given this process's own
    niceness as `os.getpriority` reads it, which, unlike `os.nice(0)`, asks for no change and so
    cannot be refused at macOS's ceiling of 20. On a host with no line, or one with no
    `os.getpriority` to read a niceness by, or where a tool of the line is not on `PATH`, it runs
    nothing, takes no lock, prints why on stderr and exits 2. Where the lock cannot be opened or locked,
    or the line's program cannot start, it runs nothing, prints why and exits 2. A command killed by a signal exits 128 plus that
    signal's number, as a shell reports it.
    """
    parsed = parser().parse_args(arguments, namespace=Arguments())
    # A host with no `os.getpriority` has no throttle line either, so `throttle_line` refuses it whatever the niceness.
    niceness = os.getpriority(os.PRIO_PROCESS, 0) if hasattr(os, "getpriority") else 0
    try:
        line = [*throttle_line(sys.platform, niceness), *parsed.command]
        return run(parsed.lock, line)
    except GateError as error:
        write(output_lines(f"heavy: {error.report}; nothing was run"), error=True)
        return exit_code(Outcome(lines=(Unfinished(error.report),)))

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
