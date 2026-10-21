"""Red tests for the mypy gate's warm cache: one warm per run, a copy of it per file, all under the scratch root.

Source: the quality gates design spec under docs/superpowers/specs/, "Types", the sub-bullet under the first bullet,
and "Gates", the bullets on the count line and on a gate's own lines; the gates core design spec, section 2, the
paragraph on `warm_cache`, and its decisions 3, 18, 20 and 23.

Each run of the mypy gate warms one temp mypy cache on no repo file, and every per-file mypy run starts from its own
copy of it. `warm_cache(run, directory)` runs mypy through `run.process` and raises GateError unless mypy exits 0,
prints nothing and leaves a file. The warm cache and every copy live under the scratch root the run is handed, are
deleted on every exit path, and mypy's cache directory is passed on its command line. A warm, a copy or a deletion that
fails makes the run unfinished: the error, then the count line, exit 2, and never an uncached per-file run.

The runner below stands in for mypy. Its first call is the warm, and leaves a file of this test's own naming in the
cache directory the command names; each later call is a per-file run, which records what its cache directory holds
before it writes a file of its own there, as mypy would. Placement is judged only by the scratch root and the tree.
"""

import stat
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from gates.check_mypy import GATE, warm_cache
from gates.core.checker import Command, Completed
from gates.core.project import Project, Source
from gates.core.report import GateError
from gates.core.runner import Run, Scratch, run_gate
from tests.support.capture import captured
from tests.support.fake import completed
from tests.support.project import scaffold

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

SOURCE = "checked_module.py"

CACHE_FLAG = "--cache-dir"

# The file the stand-in's warm leaves in its cache directory, and what it holds: this test's naming, not mypy's.
WARM_FILE = "warmed.json"

WARM_TEXT = "warmed\n"

# The file each per-file run writes in its own cache directory after it has looked.
CHECKED_FILE = "checked.json"

KEEP = "keep"

# What mypy prints on success unless told not to, and a config complaint it prints on stderr with exit 0.
SUCCESS = "Success: no issues found in 1 source file\n"

UNRECOGNIZED = "pyproject.toml: [mypy]: Unrecognized option: bogus = True\n"

WARM_REFUSAL = "/opt/python/lib/python3.12/site-packages is in the MYPYPATH. Please remove it.\n"

DELETE_FAILURE = "cannot delete the temp space "

COUNT_ONE = "check_mypy: 0 finding(s) in 1 Python file(s)\n"

COUNT_TWO = "check_mypy: 0 finding(s) in 2 Python file(s)\n"

COUNT_THREE = "check_mypy: 0 finding(s) in 3 Python file(s)\n"

NAMES = ("first.py", "second.py", "third.py")

TWO_NAMES = ("first.py", "second.py")

ONE_NAME = ("first.py",)


def _leave_cache(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / WARM_FILE).write_text(WARM_TEXT, encoding="utf-8")


def _leave_nothing(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)


def _leave_empty_directory(directory: Path) -> None:
    (directory / "3.12").mkdir(parents=True, exist_ok=True)


def _leave_unreadable(directory: Path) -> None:
    _leave_cache(directory)
    (directory / WARM_FILE).chmod(0)


def _cache_dir(command: Command) -> Path | None:
    arguments = list(command.argv)
    if CACHE_FLAG not in arguments or arguments.index(CACHE_FLAG) + 1 >= len(arguments):
        return None
    return Path(arguments[arguments.index(CACHE_FLAG) + 1])


def _contents(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)): path.read_text(encoding="utf-8")
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def _under(path: Path | None, root: Path) -> bool:
    return path is not None and path.resolve().is_relative_to(root.resolve())


class MypyStandIn:
    """A Runner standing in for mypy: the first call is the warm, every later call a per-file run."""

    def __init__(
        self,
        *,
        warm: Callable[[Path], None] = _leave_cache,
        warm_reply: Completed | None = None,
        lock: Path | None = None,
    ) -> None:
        self.warm = warm
        self.warm_reply = completed(0) if warm_reply is None else warm_reply
        self.lock = lock
        self.commands: list[Command] = []
        self.seen: list[dict[str, str]] = []

    def __call__(self, command: Command) -> Completed:
        self.commands.append(command)
        directory = _cache_dir(command)
        if len(self.commands) == 1:
            if directory is not None:
                self.warm(directory)
            return self.warm_reply
        if directory is not None:
            directory.mkdir(parents=True, exist_ok=True)
            self.seen.append(_contents(directory))
            (directory / CHECKED_FILE).write_text("checked\n", encoding="utf-8")
        if self.lock is not None:
            self.lock.chmod(stat.S_IRUSR | stat.S_IXUSR)
        return completed(0)


def _scratch_root(tmp_path: Path) -> Path:
    root = tmp_path / "scratch"
    root.mkdir()
    (root / KEEP).write_text("kept\n", encoding="utf-8")
    return root


def _gate(tmp_path: Path, names: Sequence[str], runner: MypyStandIn, scratch: Path) -> tuple[int, list[str]]:
    """Run the gate over clean files of a scaffolded project, with the stand-in as its process and the given root."""
    project = scaffold(tmp_path / "project", dict.fromkeys(names, CLEAN))
    try:
        output = captured(
            lambda: run_gate(
                GATE,
                [project.root / name for name in names],
                project=project,
                process=runner,
                scratch_root=scratch,
            )
        )
    finally:
        scratch.chmod(stat.S_IRWXU)
    return output.result, output.merged


def _warm_run(tmp_path: Path, runner: MypyStandIn) -> tuple[Run, Path]:
    """A run over one clean file with the stand-in as its process, and an empty directory to warm in."""
    project: Project = scaffold(tmp_path / "project", {SOURCE: CLEAN})
    run = Run(
        project=project,
        sources=(Source(given=project.root / SOURCE, absolute=project.root / SOURCE),),
        scratch=Scratch(tmp_path / "scratch"),
        process=runner,
    )
    directory = tmp_path / "warm"
    directory.mkdir()
    return run, directory


def test_warm_runs_mypy_as_a_module_on_the_directory_as_its_cache(tmp_path: Path) -> None:
    """The warm runs `python -m mypy` through the run's process, with the directory it is given as mypy's cache."""
    runner = MypyStandIn()
    run, directory = _warm_run(tmp_path, runner)
    warm_cache(run, directory)

    assert [(command.argv[1:3], _cache_dir(command)) for command in runner.commands] == [(("-m", "mypy"), directory)]


def test_warm_names_no_file_of_the_run(tmp_path: Path) -> None:
    """The warm is on no repo file: no argument of its one command names the run's source."""
    runner = MypyStandIn()
    run, directory = _warm_run(tmp_path, runner)
    warm_cache(run, directory)

    assert [[argument for argument in command.argv if SOURCE in argument] for command in runner.commands] == [[]]


def test_warm_that_exits_nonzero_is_a_gate_error(tmp_path: Path) -> None:
    """A warm whose mypy exits 1, even printing nothing and leaving a file, raises GateError."""
    run, directory = _warm_run(tmp_path, MypyStandIn(warm_reply=completed(1)))

    with pytest.raises(GateError):
        warm_cache(run, directory)


def test_warm_that_prints_on_stdout_is_a_gate_error(tmp_path: Path) -> None:
    """A warm whose mypy exits 0 and leaves a file but prints on stdout raises GateError."""
    run, directory = _warm_run(tmp_path, MypyStandIn(warm_reply=completed(0, SUCCESS)))

    with pytest.raises(GateError):
        warm_cache(run, directory)


def test_warm_that_prints_on_stderr_is_a_gate_error(tmp_path: Path) -> None:
    """A warm whose mypy exits 0 and leaves a file but prints on stderr raises GateError."""
    run, directory = _warm_run(tmp_path, MypyStandIn(warm_reply=completed(0, "", UNRECOGNIZED)))

    with pytest.raises(GateError):
        warm_cache(run, directory)


def test_warm_that_leaves_no_file_is_a_gate_error(tmp_path: Path) -> None:
    """A warm whose mypy exits 0 and prints nothing but leaves its directory empty raises GateError."""
    run, directory = _warm_run(tmp_path, MypyStandIn(warm=_leave_nothing))

    with pytest.raises(GateError):
        warm_cache(run, directory)


def test_warm_that_leaves_only_a_directory_is_a_gate_error(tmp_path: Path) -> None:
    """A directory is no file: a warm that leaves only an empty directory in its own raises GateError."""
    run, directory = _warm_run(tmp_path, MypyStandIn(warm=_leave_empty_directory))

    with pytest.raises(GateError):
        warm_cache(run, directory)


def test_one_warm_per_run_and_a_cache_of_its_own_per_file(tmp_path: Path) -> None:
    """Three files make four mypy runs, one warm and one per file, each on a cache directory no other run names."""
    runner = MypyStandIn()
    _gate(tmp_path, NAMES, runner, _scratch_root(tmp_path))

    assert (len(runner.commands), len({_cache_dir(command) for command in runner.commands})) == (4, 4)


def test_each_file_run_starts_from_a_copy_of_the_warm_cache(tmp_path: Path) -> None:
    """Each per-file run finds exactly what the warm left, and nothing an earlier per-file run wrote."""
    runner = MypyStandIn()
    _gate(tmp_path, NAMES, runner, _scratch_root(tmp_path))

    assert runner.seen == [{WARM_FILE: WARM_TEXT}, {WARM_FILE: WARM_TEXT}, {WARM_FILE: WARM_TEXT}]


def test_the_warm_cache_and_every_copy_lie_under_the_scratch_root(tmp_path: Path) -> None:
    """The cache directory of the warm and of each per-file run lies under the scratch root the run is handed."""
    runner = MypyStandIn()
    scratch = _scratch_root(tmp_path)
    _gate(tmp_path, NAMES, runner, scratch)

    assert [_under(_cache_dir(command), scratch) for command in runner.commands] == [True, True, True, True]


def test_a_finished_run_leaves_the_scratch_root_as_it_was(tmp_path: Path) -> None:
    """After a clean run the warm cache and every copy are gone, and the scratch root holds only what it held."""
    scratch = _scratch_root(tmp_path)
    status, lines = _gate(tmp_path, NAMES, MypyStandIn(), scratch)

    assert (status, lines, sorted(entry.name for entry in scratch.iterdir())) == (0, [COUNT_THREE], [KEEP])


def test_a_failed_warm_is_unfinished_and_runs_no_file(tmp_path: Path) -> None:
    """A warm that fails ends the run unfinished: the count line last, exit 2, and no per-file mypy run at all."""
    runner = MypyStandIn(warm_reply=completed(1, "", WARM_REFUSAL))
    status, lines = _gate(tmp_path, TWO_NAMES, runner, _scratch_root(tmp_path))

    assert (status, lines[-1], len(runner.commands)) == (2, COUNT_TWO, 1)


def test_a_failed_warm_leaves_the_scratch_root_as_it_was(tmp_path: Path) -> None:
    """The warm cache a failed warm left is deleted too: the scratch root holds only what it held."""
    scratch = _scratch_root(tmp_path)
    _gate(tmp_path, TWO_NAMES, MypyStandIn(warm_reply=completed(1, "", WARM_REFUSAL)), scratch)

    assert sorted(entry.name for entry in scratch.iterdir()) == [KEEP]


def test_a_failed_copy_is_one_error_then_the_count_line(tmp_path: Path) -> None:
    """A warm cache that cannot be copied prints one error and the count line, exits 2 and runs no per-file mypy."""
    runner = MypyStandIn(warm=_leave_unreadable)
    status, lines = _gate(tmp_path, ONE_NAME, runner, _scratch_root(tmp_path))

    assert (status, len(lines), lines[-1], len(runner.commands)) == (2, 2, COUNT_ONE, 1)


def test_a_failed_copy_leaves_the_scratch_root_as_it_was(tmp_path: Path) -> None:
    """After a copy that failed, the warm cache and any part of the copy are deleted."""
    scratch = _scratch_root(tmp_path)
    _gate(tmp_path, ONE_NAME, MypyStandIn(warm=_leave_unreadable), scratch)

    assert sorted(entry.name for entry in scratch.iterdir()) == [KEEP]


def test_a_failed_deletion_is_one_error_then_the_count_line(tmp_path: Path) -> None:
    """A clean run whose temp space cannot be deleted prints the deletion error, then the count line, and exits 2."""
    scratch = _scratch_root(tmp_path)
    status, lines = _gate(tmp_path, ONE_NAME, MypyStandIn(lock=scratch), scratch)

    assert (status, [line.startswith(DELETE_FAILURE) for line in lines], lines[-1]) == (2, [True, False], COUNT_ONE)
