"""Host-safety wrapper: run one heavy command under an exclusive lock, at niceness 19 and, on Linux, the lowest I/O priority."""

import argparse
import os
import shutil
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import override

LOCK = Path("/tmp/gauntlet-heavy.lock")

LOCK_OPTION = "--lock"

BLOCKED = 2

NICENESS = 19

NICE = "nice"

END_OPTIONS = "--"

# The words before `nice` that lower the I/O priority on each host the wrapper runs on: none on `darwin`, whose
# background policy would confine a run to the efficiency cores.
IO_LOWEST: dict[str, list[str]] = {"darwin": [], "linux": ["ionice", "-c3"]}


def wrapped(command: list[str], platform: str, niceness: int) -> list[str] | None:
    """Return the command line that runs `command` at niceness 19, and on `linux` the lowest I/O priority, or None.

    `platform` is a host as `sys.platform` names it. On `linux` the line is
    `ionice -c3 nice -n <k> -- <command>`; on `darwin` it is `nice -n <k> -- <command>`, with no
    `taskpolicy -b`, since macOS's background policy confines a run to the efficiency cores. Each
    tool is named bare, for `PATH` to find. Any other host gets no line, since a heavy run is
    never made unthrottled.

    `nice` takes an increment, not a niceness, so the line raises the niceness by the difference
    between 19 and `niceness`, the caller's own, which the line's process inherits. A caller at 19
    or above, macOS's ceiling being 20, gets `nice -n 0`, never a negative increment, which asks
    to lower the niceness. `nice`'s options end with `--`, so the command is run as given whatever
    its first word.
    """
    io_lowest = IO_LOWEST.get(platform)
    if io_lowest is None:
        return None
    return [*io_lowest, NICE, "-n", str(max(NICENESS - niceness, 0)), END_OPTIONS, *command]


def missing(platform: str) -> list[str]:
    """Return each tool of `platform`'s line that is not found on `PATH`: its I/O tool where it has one, and `nice`.

    `platform` is one `wrapped` gives a line for.
    """
    return [tool for tool in (*IO_LOWEST[platform][:1], NICE) if shutil.which(tool) is None]


def status(returncode: int) -> int:
    """Return the exit status a shell gives a command that ended with `returncode`: 128 plus the signal that killed it, or the status itself."""
    return 128 - returncode if returncode < 0 else returncode


def run(lock: Path, line: list[str]) -> int:
    """Hold an exclusive `fcntl.flock` on `lock` for the whole of `line`'s run and return its exit status.

    The lock is waited on, never polled, so a second run on the same path starts once the first
    ends. The locked descriptor is passed to `line`'s process, as `flock(1)` passes it, so the
    lock lasts as long as the command and every process that inherits the descriptor from it,
    not only as long as this wrapper: a wrapper killed alone leaves its command holding the lock.
    Where `lock` cannot be opened or locked, `line` is never run: the wrapper prints why and
    returns 2. `fcntl` is imported here, not with the module, because a host without it gets no
    line and must still be told so with exit 2 rather than fail on import.
    """
    import fcntl

    with ExitStack() as stack:
        try:
            handle = stack.enter_context(lock.open("a", encoding="utf-8"))
            fcntl.flock(handle, fcntl.LOCK_EX)
        except OSError as error:
            sys.stderr.write(f"heavy: cannot lock {lock}: {error}; nothing was run\n")
            return BLOCKED
        return status(subprocess.run(line, check=False, pass_fds=(handle.fileno(),)).returncode)


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
    wrapper prints its usage and exits 2. The line comes from `wrapped`, given this process's own
    niceness as `os.getpriority` reads it, which, unlike `os.nice(0)`, asks for no change and so
    cannot be refused at macOS's ceiling of 20. On a host with no line, or one with no
    `os.getpriority` to read a niceness by, or where a tool of the line is not on `PATH`, it runs
    nothing, takes no lock, prints why and exits 2. Where the lock cannot be opened or locked, it
    runs nothing, prints why and exits 2. A command killed by a signal exits 128 plus that
    signal's number, as a shell reports it.
    """
    parsed = parser().parse_args(arguments, namespace=Arguments())
    line = wrapped(parsed.command, sys.platform, os.getpriority(os.PRIO_PROCESS, 0)) if hasattr(os, "getpriority") else None
    if line is None:
        sys.stderr.write(f"heavy: no throttled command line for host {sys.platform!r}; nothing was run\n")
        return BLOCKED
    absent = missing(sys.platform)
    if absent:
        sys.stderr.write(f"heavy: not found on PATH: {', '.join(absent)}; nothing was run\n")
        return BLOCKED
    return run(parsed.lock, line)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
