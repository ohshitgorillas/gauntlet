# Copyright 2026 oh shit, gorillas!
"""Red tests for the gates core runner: one gate run from start to exit, its scratch space and its checker driver.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "runner.py: one gate run, from start to
exit", section 3, "project.py", and its decisions 17 to 25; the quality gates design spec, "Gates", intro, for the
count line, the empty run and a checker that did not finish.

`run_gate` selects the sources from the Python files given, prints `nothing_checked` and exits 1 when none is
selected, opens the Scratch, resolves the project, calls `gate.check`, turns a GateError or OSError into an Unfinished
line, closes the Scratch on every path, then prints `render(...)` and returns `exit_code`; M is `len(sources)`.
`check_with` runs each batch and reads its report: a timeout, an output with no report the gate can read and an exit
status that is neither the one the report calls for nor a stop are Unfinished with the checker's whole output, and a
stopped batch always ends unfinished. A Scratch makes the run's own temp dir in its root at the first call that needs
one, gives a fresh path per `directory` or `copy`, builds `once` the first time only, and `close` deletes it all.

`scaffold` writes a project tree: the repository's own pyproject.toml unless given one, then the files, then a git
repository on request, then makes the `unreadable` paths lose every permission.

A test that makes a deletion fail does it by taking write permission from the scratch root, which stops no deletion
for root.
"""

import contextlib
import errno
import stat
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import override

import pytest

from gates.core import checker
from gates.core.checker import Command, Completed, Runner, environment
from gates.core.project import Project, Source, non_test_files, python_files
from gates.core.report import (
    Finding,
    GateError,
    Line,
    Outcome,
    Remark,
    Unfinished,
    count_line,
    nothing_checked,
)
from gates.core.runner import Gate, Run, Scratch, check_with, main, run_gate
from tests.support.capture import Captured, captured
from tests.support.clock import VirtualClock
from tests.support.fake import FakeRunner, completed
from tests.support.project import ScaffoldError, scaffold

DIRECTORY_COUNT = 2
CALL_COUNT = 2

NAME = "check_example"

ECHO = "echo"

STOP = 2

TIMEOUT = 5.0

CAP = f"the checker {ECHO} ran past its time cap of {TIMEOUT} seconds"

GARBAGE = "garbage\n"

REFUSAL = "cannot start the checker echo: refused"

FAILURE = "cannot delete the temp space"

KEEP = "keep"

CONFIG = "pyproject.toml"

# The repository root, put on the PYTHONPATH of a child that imports the gates core.
REPOSITORY = Path(__file__).resolve().parents[1]

# A gate script run by main: a Finding for a source named bad.py, an Unfinished for one named broken.py.
MAIN = f"""
from gates.core.report import Finding, Outcome, Unfinished
from gates.core.runner import Gate, main

SHOWN = {{"bad.py": Finding("bad.py"), "broken.py": Unfinished("broken.py")}}


def check(run):
    return Outcome(lines=tuple(SHOWN[source.given.name] for source in run.sources if source.given.name in SHOWN))


main(Gate(name="{NAME}", check=check))
"""


def _names(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir())


def _scratch_root(tmp_path: Path) -> Path:
    root = tmp_path / "scratch"
    root.mkdir()
    (root / KEEP).write_text("kept\n", encoding="utf-8")
    return root


def _project(tmp_path: Path, *names: str) -> Project:
    return scaffold(tmp_path / "project", dict.fromkeys(names, "value = 1\n"))


def _sources(project: Project, *names: str) -> tuple[Source, ...]:
    return tuple(
        Source(given=Path(name), absolute=project.root / name) for name in names
    )


def _printed(*lines: str) -> list[str]:
    return [f"{line}\n" for line in lines]


class Echo:
    """A checker run once per source, whose report is its stdout's lines: a Finding each, an Unfinished each when stopped."""

    stopped = frozenset({STOP})

    def __init__(self, *, refuse: str | None = None) -> None:
        """Initialize the seeded state."""
        self.refuse = refuse

    def batches(self, run: Run) -> list[list[Source]]:
        """Return batches."""
        return [[source] for source in run.sources]

    def command(self, run: Run, batch: Sequence[Source]) -> Command:
        """Return command."""
        given = [str(source.given) for source in batch]
        if self.refuse in given:
            raise GateError(REFUSAL)
        return Command(argv=(ECHO, *given), cwd=run.project.root, timeout=TIMEOUT)

    def read(self, completed: Completed) -> list[str]:
        """Return read."""
        if completed.stdout == GARBAGE:
            raise GateError(GARBAGE)
        return completed.stdout.splitlines()

    def expected_status(self, report: list[str]) -> int:
        """Return expected status."""
        return 1 if report else 0

    def lines(
        self, report: list[str], batch: Sequence[Source], *, stopped: bool
    ) -> list[Line]:
        """Return lines."""
        del batch
        return [Unfinished(text) if stopped else Finding(text) for text in report]


class Refusing:
    """A Runner that gives its replies in order, then raises the error it holds in place of the next one."""

    def __init__(self, replies: Sequence[Completed], error: Exception) -> None:
        """Initialize the seeded state."""
        self.replies = FakeRunner(replies)
        self.left = len(replies)
        self.error = error
        self.calls = 0

    def __call__(self, command: Command) -> Completed:
        """Return the reply for the supplied call."""
        self.calls += 1
        if self.calls > self.left:
            raise self.error
        return self.replies(command)


def _checked(
    tmp_path: Path, process: Runner, *names: str, refuse: str | None = None
) -> Outcome:
    project = _project(tmp_path, *names)
    run = Run(
        project=project,
        sources=_sources(project, *names),
        scratch=Scratch(tmp_path),
        process=process,
    )
    return check_with(Echo(refuse=refuse))(run)


_DEFAULT_OUTCOME = Outcome()


class Seen:
    """A gate check that keeps every Run it is called with and gives the Outcome it holds."""

    def __init__(
        self, outcome: Outcome = _DEFAULT_OUTCOME, make: str | None = None
    ) -> None:
        """Initialize the seeded state."""
        self.outcome = outcome
        self.make = make
        self.runs: list[Run] = []
        self.made: list[Path] = []

    def __call__(self, run: Run) -> Outcome:
        """Return the reply for the supplied call."""
        self.runs.append(run)
        if self.make is not None:
            self.made.append(run.scratch.directory(self.make))
        return self.outcome


def _raising(error: BaseException) -> Callable[[Run], Outcome]:
    def check(run: Run) -> Outcome:
        run.scratch.directory("made")
        raise error

    return check


def _locking(root: Path, outcome: Outcome) -> Callable[[Run], Outcome]:
    def check(run: Run) -> Outcome:
        run.scratch.directory("made")
        root.chmod(stat.S_IRUSR | stat.S_IXUSR)
        return outcome

    return check


# Scratch.directory


def test_directory_in_root(tmp_path: Path) -> None:
    """A directory is a new, empty directory inside the run's own temp dir in the scratch root."""
    scratch = Scratch(tmp_path)
    path = scratch.directory("work")

    assert (path.parent.parent, _names(path)) == (tmp_path, [])


def test_directory_name(tmp_path: Path) -> None:
    """A directory's last component starts with the name asked for."""
    path = Scratch(tmp_path).directory("work")

    assert path.name.startswith("work")


def test_directory_fresh(tmp_path: Path) -> None:
    """One name asked for twice gives two directories."""
    scratch = Scratch(tmp_path)

    assert scratch.directory("work") != scratch.directory("work")


def test_one_run_directory(tmp_path: Path) -> None:
    """Every directory of one Scratch lies in the one temp dir of its run."""
    scratch = Scratch(tmp_path)
    first, second = scratch.directory("a"), scratch.directory("b")

    assert _names(tmp_path) == [first.parent.name] == [second.parent.name]


def test_no_temp_dir_until_asked(tmp_path: Path) -> None:
    """A Scratch makes nothing in its root until a temp path is asked for."""
    root = _scratch_root(tmp_path)
    Scratch(root)

    assert _names(root) == [KEEP]


def test_default_root() -> None:
    """With no root, the run's temp dir is in the system temp directory as tempfile gives it."""
    scratch = Scratch()
    path = scratch.directory("work")
    scratch.close()

    assert path.parent.parent == Path(tempfile.gettempdir())


def test_directory_missing_root(tmp_path: Path) -> None:
    """A root the run's temp dir cannot be made in is a GateError naming the root."""
    root = tmp_path / "missing"
    with pytest.raises(GateError) as raised:
        Scratch(root).directory("work")

    assert str(root) in raised.value.report


# Scratch.copy


def test_copy(tmp_path: Path) -> None:
    """A copy holds the tree's files, nested ones included, with their contents."""
    tree = tmp_path / "tree"
    (tree / "inner").mkdir(parents=True)
    (tree / "a.txt").write_text("a\n", encoding="utf-8")
    (tree / "inner" / "b.txt").write_text("b\n", encoding="utf-8")
    copy = Scratch(_scratch_root(tmp_path)).copy(tree, "cache")

    assert (
        (copy / "a.txt").read_text(encoding="utf-8"),
        (copy / "inner" / "b.txt").read_text(encoding="utf-8"),
    ) == (
        "a\n",
        "b\n",
    )


def test_copy_in_scratch(tmp_path: Path) -> None:
    """A copy lies in the run's own temp dir, its last component starting with the name asked for."""
    tree = tmp_path / "tree"
    tree.mkdir()
    root = _scratch_root(tmp_path)
    copy = Scratch(root).copy(tree, "cache")

    assert (copy.parent.parent, copy.name.startswith("cache")) == (root, True)


def test_copy_fresh(tmp_path: Path) -> None:
    """One tree copied twice under one name gives two copies."""
    tree = tmp_path / "tree"
    tree.mkdir()
    scratch = Scratch(_scratch_root(tmp_path))

    assert scratch.copy(tree, "cache") != scratch.copy(tree, "cache")


def test_copy_follows_links(tmp_path: Path) -> None:
    """A symlink in the tree is copied as the file it names, so the copy never links back into the tree."""
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "a.txt").write_text("a\n", encoding="utf-8")
    (tree / "link.txt").symlink_to(tree / "a.txt")
    copy = Scratch(_scratch_root(tmp_path)).copy(tree, "cache")

    assert (
        (copy / "link.txt").is_symlink(),
        (copy / "link.txt").read_text(encoding="utf-8"),
    ) == (False, "a\n")


def test_copy_missing_tree(tmp_path: Path) -> None:
    """A tree that cannot be copied is a GateError naming the tree."""
    tree = tmp_path / "missing"
    with pytest.raises(GateError) as raised:
        Scratch(_scratch_root(tmp_path)).copy(tree, "cache")

    assert str(tree) in raised.value.report


# Scratch.once


def test_once_built_once(tmp_path: Path) -> None:
    """The first call with a name builds, the next gives the same path without building again."""
    built: list[Path] = []
    scratch = Scratch(tmp_path)
    first = scratch.once("warm", built.append)
    second = scratch.once("warm", built.append)

    assert (first, second, built) == (first, first, [first])


def test_once_builds_in_its_path(tmp_path: Path) -> None:
    """The path once gives is the directory make built in."""

    def make(path: Path) -> None:
        (path / "built.txt").write_text("built\n", encoding="utf-8")

    path = Scratch(tmp_path).once("warm", make)

    assert _names(path) == ["built.txt"]


def test_once_names_apart(tmp_path: Path) -> None:
    """Each name is built apart from the others."""
    built: list[Path] = []
    scratch = Scratch(tmp_path)
    scratch.once("warm", built.append)
    scratch.once("cold", built.append)

    assert len(set(built)) == DIRECTORY_COUNT


def test_once_failed_make_not_kept(tmp_path: Path) -> None:
    """A make that raises is not kept, so the next call with its name builds again."""
    built: list[Path] = []

    def failing(path: Path) -> None:
        raise GateError(str(path))

    scratch = Scratch(tmp_path)
    with pytest.raises(GateError):
        scratch.once("warm", failing)
    path = scratch.once("warm", built.append)

    assert built == [path]


def test_once_error_to_caller(tmp_path: Path) -> None:
    """A make's error goes to the caller as it was raised."""
    error = GateError(REFUSAL)

    def failing(path: Path) -> None:
        del path
        raise error

    with pytest.raises(GateError) as raised:
        Scratch(tmp_path).once("warm", failing)

    assert raised.value is error


# Scratch.close


def test_close_deletes_everything(tmp_path: Path) -> None:
    """Close deletes the run's temp dir and all it holds, leaves every other entry in the root, and returns None."""
    root = _scratch_root(tmp_path)
    scratch = Scratch(root)
    (scratch.directory("work") / "a.txt").write_text("a\n", encoding="utf-8")
    scratch.once("warm", lambda _path: None)

    assert (scratch.close(), _names(root)) == (None, [KEEP])


def test_close_read_only(tmp_path: Path) -> None:
    """Close deletes read-only files and read-only directories."""
    root = _scratch_root(tmp_path)
    scratch = Scratch(root)
    path = scratch.directory("work")
    inner = path / "inner"
    inner.mkdir()
    (inner / "a.txt").write_text("a\n", encoding="utf-8")
    (inner / "a.txt").chmod(stat.S_IRUSR)
    inner.chmod(stat.S_IRUSR | stat.S_IXUSR)
    path.chmod(stat.S_IRUSR | stat.S_IXUSR)

    assert (scratch.close(), _names(root)) == (None, [KEEP])


def test_close_leaves_linked_directory(tmp_path: Path) -> None:
    """Close deletes a symlink to a directory outside the run's temp dir, and changes neither that directory's mode."""
    outside = tmp_path / "outside"
    outside.mkdir()
    outside.chmod(stat.S_IRUSR | stat.S_IXUSR)
    root = _scratch_root(tmp_path)
    scratch = Scratch(root)
    (scratch.directory("work") / "link").symlink_to(outside, target_is_directory=True)
    failure = scratch.close()
    mode = stat.S_IMODE(outside.stat().st_mode)
    outside.chmod(stat.S_IRWXU)

    assert (failure, _names(root), mode) == (None, [KEEP], stat.S_IRUSR | stat.S_IXUSR)


def test_close_nothing_made(tmp_path: Path) -> None:
    """A Scratch that made nothing deletes nothing and returns None."""
    root = _scratch_root(tmp_path)

    assert (Scratch(root).close(), _names(root)) == (None, [KEEP])


def test_close_twice(tmp_path: Path) -> None:
    """After close the Scratch holds nothing, so a second close returns None."""
    root = _scratch_root(tmp_path)
    scratch = Scratch(root)
    scratch.directory("work")
    scratch.close()

    assert (scratch.close(), _names(root)) == (None, [KEEP])


def test_close_failure_returned(tmp_path: Path) -> None:
    """A deletion that fails is returned, naming the run's temp dir, and never raised."""
    root = _scratch_root(tmp_path)
    scratch = Scratch(root)
    path = scratch.directory("work")
    root.chmod(stat.S_IRUSR | stat.S_IXUSR)
    failure = scratch.close()
    root.chmod(stat.S_IRWXU)

    assert failure is not None
    assert failure.startswith(f"{FAILURE} {path.parent}: ")


def test_close_failure_keeps_root_mode(tmp_path: Path) -> None:
    """Close changes no mode outside the run's temp dir, the root's own included."""
    root = _scratch_root(tmp_path)
    scratch = Scratch(root)
    scratch.directory("work")
    root.chmod(stat.S_IRUSR | stat.S_IXUSR)
    scratch.close()
    mode = stat.S_IMODE(root.stat().st_mode)
    root.chmod(stat.S_IRWXU)

    assert mode == stat.S_IRUSR | stat.S_IXUSR


# check_with


def test_clean(tmp_path: Path) -> None:
    """A batch that exits with the status its empty report calls for gives no line."""
    assert _checked(tmp_path, FakeRunner([completed(0)]), "a.py") == Outcome()


def test_findings(tmp_path: Path) -> None:
    """A batch that exits with the status its report calls for gives the checker's lines."""
    outcome = _checked(tmp_path, FakeRunner([completed(1, "one\ntwo\n")]), "a.py")

    assert outcome == Outcome(lines=(Finding("one"), Finding("two")))


def test_batches_in_order(tmp_path: Path) -> None:
    """Each batch runs once, in the order of batches, its lines after the lines of the batch before."""
    outcome = _checked(
        tmp_path,
        FakeRunner([completed(1, "a\n"), completed(0), completed(1, "c\n")]),
        "a.py",
        "b.py",
        "c.py",
    )

    assert outcome == Outcome(lines=(Finding("a"), Finding("c")))


def test_commands(tmp_path: Path) -> None:
    """Each batch's command goes to the run's process."""
    process = FakeRunner([completed(0), completed(0)])
    _checked(tmp_path, process, "a.py", "b.py")

    assert [command.argv for command in process.commands] == [
        (ECHO, "a.py"),
        (ECHO, "b.py"),
    ]


def test_timeout(tmp_path: Path) -> None:
    """A batch its time cap ended gives the checker's whole output, then the gate's line naming the cap."""
    outcome = _checked(
        tmp_path, FakeRunner([completed(1, "out\n", "err\n", timed_out=True)]), "a.py"
    )

    assert outcome == Outcome(lines=(Unfinished("out\nerr\n"), Unfinished(CAP)))


def test_timeout_report_not_read(tmp_path: Path) -> None:
    """A batch its time cap ended reads no report, so even an output with no report the gate can read is passed on."""
    outcome = _checked(
        tmp_path, FakeRunner([completed(1, GARBAGE, timed_out=True)]), "a.py"
    )

    assert outcome == Outcome(lines=(Unfinished(GARBAGE), Unfinished(CAP)))


def test_unreadable_report(tmp_path: Path) -> None:
    """An output with no report the gate can read gives the checker's whole output, and not the reader's error."""
    outcome = _checked(tmp_path, FakeRunner([completed(1, GARBAGE, "err\n")]), "a.py")

    assert outcome == Outcome(lines=(Unfinished(GARBAGE + "err\n"),))


@pytest.mark.parametrize(
    ("status", "stdout"),
    [(1, ""), (0, "one\n"), (3, ""), (137, "one\n")],
    ids=["nonzero-empty-report", "zero-with-report", "undocumented", "signal"],
)
def test_unexpected_status(tmp_path: Path, status: int, stdout: str) -> None:
    """A status that is neither the one the report calls for nor a stop gives the checker's whole output."""
    outcome = _checked(
        tmp_path, FakeRunner([completed(status, stdout, "err\n")]), "a.py"
    )

    assert outcome == Outcome(lines=(Unfinished(stdout + "err\n"),))


def test_stopped(tmp_path: Path) -> None:
    """A stop gives the lines of the report it read, as stopped."""
    outcome = _checked(
        tmp_path, FakeRunner([completed(STOP, "one\n", "err\n")]), "a.py"
    )

    assert outcome == Outcome(lines=(Unfinished("one"),))


def test_stopped_empty_report(tmp_path: Path) -> None:
    """A stopped batch whose lines hold no Unfinished gets the checker's whole output, so it ends unfinished."""
    outcome = _checked(tmp_path, FakeRunner([completed(STOP, "", "err\n")]), "a.py")

    assert outcome == Outcome(lines=(Unfinished("err\n"),))


def test_later_batches_after_unfinished(tmp_path: Path) -> None:
    """A batch that did not finish leaves the batches after it to run."""
    outcome = _checked(
        tmp_path,
        FakeRunner([completed(3, "", "err\n"), completed(1, "b\n")]),
        "a.py",
        "b.py",
    )

    assert outcome == Outcome(lines=(Unfinished("err\n"), Finding("b")))


def test_process_error(tmp_path: Path) -> None:
    """A GateError from the process ends the check: the lines before it stand, then its report."""
    process = Refusing([completed(1, "a\n")], GateError(REFUSAL))
    outcome = _checked(tmp_path, process, "a.py", "b.py", "c.py")

    assert outcome == Outcome(lines=(Finding("a"), Unfinished(REFUSAL)))


def test_process_error_stops_batches(tmp_path: Path) -> None:
    """After a GateError from the process no later batch runs."""
    process = Refusing([completed(1, "a\n")], GateError(REFUSAL))
    _checked(tmp_path, process, "a.py", "b.py", "c.py")

    assert process.calls == CALL_COUNT


def test_process_os_error(tmp_path: Path) -> None:
    """An OSError from the process ends the check with its text as the report."""
    error = OSError(errno.ENOSPC, "No space left on device")
    outcome = _checked(tmp_path, Refusing([], error), "a.py")

    assert outcome == Outcome(lines=(Unfinished(str(error)),))


def test_command_error(tmp_path: Path) -> None:
    """A GateError from the command ends the check: the lines before it stand, then its report, and no later batch runs."""
    process = FakeRunner([completed(1, "a\n"), completed(1, "c\n")])
    outcome = _checked(tmp_path, process, "a.py", "b.py", "c.py", refuse="b.py")

    assert (outcome, len(process.commands)) == (
        Outcome(lines=(Finding("a"), Unfinished(REFUSAL))),
        1,
    )


# run_gate


def _run(
    tmp_path: Path,
    gate: Gate,
    *names: str,
    project: Project | None = None,
    process: Runner | None = None,
) -> Captured[int]:
    project = project or _project(tmp_path, *names)
    paths = [project.root / name for name in names]
    root = tmp_path / "scratch"
    root.mkdir(exist_ok=True)
    return captured(
        lambda: run_gate(
            gate,
            paths,
            project=project,
            process=process or FakeRunner([]),
            scratch_root=root,
        )
    )


def test_nothing_checked(tmp_path: Path) -> None:
    """A run given no Python file prints the nothing-checked lines and exits 1."""
    project = _project(tmp_path, "a.txt", "b.md")
    gate = Gate(name=NAME, check=Seen())

    output = _run(tmp_path, gate, "a.txt", "b.md", project=project)

    assert (output.result, output.out) == (
        1,
        _printed(*nothing_checked(NAME, "Python file", 2)),
    )


def test_nothing_selected(tmp_path: Path) -> None:
    """A run whose gate selects none of the Python files given names what it selects, and exits 1."""
    gate = Gate(name=NAME, check=Seen(), select=non_test_files, selects="non-test file")

    output = _run(tmp_path, gate, "tests/test_a.py")

    assert (output.result, output.out) == (
        1,
        _printed(*nothing_checked(NAME, "non-test file", 1)),
    )


def test_nothing_checked_no_check(tmp_path: Path) -> None:
    """A run that checks nothing never calls the gate's check."""
    seen = Seen()
    status = _run(tmp_path, Gate(name=NAME, check=seen), "a.txt").result

    assert (status, seen.runs) == (1, [])


def test_clean_run(tmp_path: Path) -> None:
    """A clean run prints its count line alone and exits 0."""
    output = _run(tmp_path, Gate(name=NAME, check=Seen()), "a.py")

    assert (output.result, output.out) == (
        0,
        _printed(count_line(NAME, 0, 1)),
    )


def test_finding_run(tmp_path: Path) -> None:
    """A run with findings prints the notes, then the lines in order, then the count line, and exits 1."""
    outcome = Outcome(
        lines=(Finding("a.py:1: one"), Remark("a.py:1: note"), Finding("a.py:2: two")),
        notes=("seed",),
    )
    gate = Gate(name=NAME, check=Seen(outcome))

    output = _run(tmp_path, gate, "a.py")

    assert (output.result, output.out) == (
        1,
        _printed(
            "seed", "a.py:1: one", "a.py:1: note", "a.py:2: two", count_line(NAME, 2, 1)
        ),
    )


def test_unfinished_run(tmp_path: Path) -> None:
    """A run with an Unfinished line prints it and exits 2."""
    gate = Gate(
        name=NAME,
        check=Seen(Outcome(lines=(Finding("a.py:1: one"), Unfinished("err\n")))),
    )

    output = _run(tmp_path, gate, "a.py")

    assert (output.result, output.out) == (
        2,
        _printed("a.py:1: one", "err", count_line(NAME, 1, 1)),
    )


def test_stdout_only(tmp_path: Path) -> None:
    """Every line goes to stdout."""
    gate = Gate(
        name=NAME, check=Seen(Outcome(lines=(Finding("one"), Unfinished("err\n"))))
    )

    output = _run(tmp_path, gate, "a.py")

    assert (output.out, output.err) == (
        _printed("one", "err", count_line(NAME, 1, 1)),
        [],
    )


def test_sources(tmp_path: Path) -> None:
    """The run's sources are the Python files given, in order, a file given twice once, as first given."""
    seen = Seen()
    project = _project(tmp_path, "a.py", "b.py")
    paths = [
        project.root / "b.py",
        project.root / "a.txt",
        project.root / "a.py",
        project.root / "." / "b.py",
    ]
    captured(
        lambda: run_gate(
            Gate(name=NAME, check=seen), paths, project=project, scratch_root=tmp_path
        )
    )

    assert seen.runs[0].sources == tuple(python_files(paths[:3]))


def test_selected_sources(tmp_path: Path) -> None:
    """The run's sources are those the gate selects."""
    seen = Seen()
    _run(
        tmp_path,
        Gate(name=NAME, check=seen, select=non_test_files),
        "a.py",
        "tests/test_a.py",
    )

    assert [source.given.name for source in seen.runs[0].sources] == ["a.py"]


def test_files_counted(tmp_path: Path) -> None:
    """M is the number of sources: a file given twice counts once, and a file the gate does not select not at all."""
    project = _project(tmp_path, "a.py", "tests/test_a.py")
    paths = [
        project.root / "a.py",
        project.root / "a.py",
        project.root / "tests/test_a.py",
    ]
    gate = Gate(name=NAME, check=Seen(), select=non_test_files)
    output = captured(
        lambda: run_gate(gate, paths, project=project, scratch_root=tmp_path)
    )

    assert output.out == _printed(count_line(NAME, 0, 1))


def test_project_given(tmp_path: Path) -> None:
    """The run's project is the one given."""
    seen = Seen()
    project = _project(tmp_path, "a.py")
    _run(tmp_path, Gate(name=NAME, check=seen), "a.py", project=project)

    assert seen.runs[0].project is project


def test_project_current(tmp_path: Path) -> None:
    """With no project given, the run's project is the working directory's."""
    seen = Seen()
    project = _project(tmp_path, "a.py")
    with contextlib.chdir(project.root):
        captured(
            lambda: run_gate(
                Gate(name=NAME, check=seen), [Path("a.py")], scratch_root=tmp_path
            )
        )

    assert seen.runs[0].project.root.resolve() == project.root.resolve()


def test_project_missing(tmp_path: Path) -> None:
    """A working directory with no pyproject.toml is an Unfinished line with its report, and the run exits 2."""
    (tmp_path / "a.py").write_text("value = 1\n", encoding="utf-8")
    with contextlib.chdir(tmp_path):
        output = captured(
            lambda: run_gate(
                Gate(name=NAME, check=Seen()), [Path("a.py")], scratch_root=tmp_path
            )
        )

    assert (output.result, CONFIG in output.out[0], output.out[1:]) == (
        2,
        True,
        _printed(count_line(NAME, 0, 1)),
    )


def test_process_given(tmp_path: Path) -> None:
    """The run's process is the one given."""
    seen = Seen()
    process = FakeRunner([])
    _run(tmp_path, Gate(name=NAME, check=seen), "a.py", process=process)

    assert seen.runs[0].process is process


def test_process_default(tmp_path: Path) -> None:
    """With no process given, the run's process is the checker's run."""
    seen = Seen()
    project = _project(tmp_path, "a.py")
    captured(
        lambda: run_gate(
            Gate(name=NAME, check=seen),
            [project.root / "a.py"],
            project=project,
            scratch_root=tmp_path,
        )
    )

    assert seen.runs[0].process is checker.run


def test_gate_error(tmp_path: Path) -> None:
    """A GateError from the check prints its report, then the count line, and the run exits 2."""
    gate = Gate(name=NAME, check=_raising(GateError(REFUSAL)))

    output = _run(tmp_path, gate, "a.py")

    assert (output.result, output.out) == (
        2,
        _printed(REFUSAL, count_line(NAME, 0, 1)),
    )


def test_os_error(tmp_path: Path) -> None:
    """An OSError from the check prints its text, then the count line, and the run exits 2."""
    error = OSError(errno.ENOSPC, "No space left on device")
    gate = Gate(name=NAME, check=_raising(error))

    output = _run(tmp_path, gate, "a.py")

    assert (output.result, output.out) == (
        2,
        _printed(str(error), count_line(NAME, 0, 1)),
    )


class Uncapped(Echo):
    """An Echo whose command sets no time cap."""

    @override
    def command(self, run: Run, batch: Sequence[Source]) -> Command:
        return Command(
            argv=(ECHO, *(str(source.given) for source in batch)), cwd=run.project.root
        )


def test_timeout_without_cap(tmp_path: Path) -> None:
    """A batch that timed out though its command sets no time cap prints the gate's report, then the count line, and the run exits 2."""
    process = FakeRunner([completed(1, "out\n", timed_out=True)])
    gate = Gate(name=NAME, check=check_with(Uncapped()))

    output = _run(tmp_path, gate, "a.py", process=process)

    assert (output.result, output.out) == (
        2,
        _printed(
            f"the checker {ECHO} timed out with no time cap", count_line(NAME, 0, 1)
        ),
    )


def test_scratch_in_root(tmp_path: Path) -> None:
    """The run's scratch makes its temp space in the scratch root given."""
    seen = Seen(make="work")
    _run(tmp_path, Gate(name=NAME, check=seen), "a.py")

    assert seen.made[0].parent.parent == tmp_path / "scratch"


def test_scratch_closed(tmp_path: Path) -> None:
    """The run's scratch is deleted after the run, every other entry in the root left as it was."""
    root = _scratch_root(tmp_path)
    _run(tmp_path, Gate(name=NAME, check=Seen(make="work")), "a.py")

    assert _names(root) == [KEEP]


def test_scratch_closed_on_error(tmp_path: Path) -> None:
    """The run's scratch is deleted after a check that raised."""
    root = _scratch_root(tmp_path)
    _run(tmp_path, Gate(name=NAME, check=_raising(GateError(REFUSAL))), "a.py")

    assert _names(root) == [KEEP]


def test_scratch_closed_on_interrupt(tmp_path: Path) -> None:
    """An interrupt goes on after the run's scratch is deleted."""
    root = _scratch_root(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        _run(tmp_path, Gate(name=NAME, check=_raising(KeyboardInterrupt())), "a.py")

    assert _names(root) == [KEEP]


def test_close_failure(tmp_path: Path) -> None:
    """A failed deletion of the run's scratch prints after the run's lines, before the count line, and exits 2."""
    root = _scratch_root(tmp_path)
    gate = Gate(
        name=NAME, check=_locking(root, Outcome(lines=(Finding("a.py:1: one"),)))
    )
    output = _run(tmp_path, gate, "a.py")
    status, out = output.result, output.out
    root.chmod(stat.S_IRWXU)

    assert (status, out[0], out[1].startswith(FAILURE), out[2:]) == (
        2,
        "a.py:1: one\n",
        True,
        _printed(count_line(NAME, 1, 1)),
    )


# main


def test_main_exits(tmp_path: Path) -> None:
    """Main exits with the run's exit code."""
    del tmp_path
    gate = Gate(name=NAME, check=Seen(), select=lambda _sources: [])
    with pytest.raises(SystemExit) as raised:
        captured(lambda: main(gate))

    assert raised.value.code == 1


@pytest.mark.parametrize(
    ("name", "status", "lines"),
    [
        ("a.py", 0, [count_line(NAME, 0, 1)]),
        ("bad.py", 1, ["bad.py", count_line(NAME, 1, 1)]),
        ("broken.py", 2, ["broken.py", count_line(NAME, 0, 1)]),
    ],
)
def test_main_command_line(
    tmp_path: Path, name: str, status: int, lines: list[str]
) -> None:
    """Main runs over the paths of its command line and exits with the run's exit code."""
    project = scaffold(tmp_path, {name: "value = 1\n"})
    env = {**environment(), "PYTHONPATH": str(REPOSITORY)}
    command = Command(
        argv=(sys.executable, "-c", MAIN, name), cwd=project.root, env=env, timeout=60.0
    )
    reply = checker.run(command, clock=VirtualClock())

    assert (reply.status, reply.stdout.splitlines()) == (status, lines)


# scaffold


def test_scaffold_files(tmp_path: Path) -> None:
    """The files are written under the root, text and bytes, in directories made for them."""
    project = scaffold(tmp_path, {"pkg/a.py": "value = 1\n", "b.bin": b"\xff\x00"})

    assert (
        (project.root / "pkg/a.py").read_text(encoding="utf-8"),
        (project.root / "b.bin").read_bytes(),
    ) == (
        "value = 1\n",
        b"\xff\x00",
    )


def test_scaffold_root(tmp_path: Path) -> None:
    """The project is the one in the root."""
    assert scaffold(tmp_path / "root", {}).root == tmp_path / "root"


def test_scaffold_default_config(tmp_path: Path) -> None:
    """With no pyproject given, the config is the repository's own."""
    assert scaffold(tmp_path, {}).setting("project", "name") == "gauntlet"


def test_scaffold_config(tmp_path: Path) -> None:
    """A pyproject given is the config's text."""
    text = '[tool.pyright]\npythonVersion = "3.12"\n'

    assert scaffold(tmp_path, {}, pyproject=text).config_text() == text


def test_scaffold_config_replaced(tmp_path: Path) -> None:
    """A file named pyproject.toml replaces the config, bytes included."""
    project = scaffold(tmp_path, {"pyproject.toml": b"\xff"}, pyproject="x = 1\n")

    assert project.config.read_bytes() == b"\xff"


def test_scaffold_unreadable(tmp_path: Path) -> None:
    """An unreadable path loses every permission."""
    project = scaffold(tmp_path, {"a.py": "value = 1\n"}, unreadable=("a.py",))
    mode = stat.filemode((project.root / "a.py").stat().st_mode)
    (project.root / "a.py").chmod(stat.S_IRWXU)

    assert mode == "----------"


def test_scaffold_git(tmp_path: Path) -> None:
    """With git, the root is a repository whose commit holds every file."""
    project = scaffold(
        tmp_path, {"a.py": "value = 1\n", "pkg/b.py": "value = 2\n"}, git=True
    )

    assert project.git("ls-tree", "-r", "--name-only", "HEAD").stdout.splitlines() == [
        "a.py",
        "pkg/b.py",
        "pyproject.toml",
    ]


def test_scaffold_git_unreadable(tmp_path: Path) -> None:
    """With git, an unreadable path is committed before it loses its permissions."""
    project = scaffold(
        tmp_path, {"a.py": "value = 1\n"}, unreadable=("a.py",), git=True
    )
    names = project.git("ls-tree", "--name-only", "HEAD").stdout.splitlines()
    (project.root / "a.py").chmod(stat.S_IRWXU)

    assert names == ["a.py", "pyproject.toml"]


def test_scaffold_git_failure(tmp_path: Path) -> None:
    """A git step that fails raises ScaffoldError."""
    with pytest.raises(ScaffoldError) as raised:
        scaffold(tmp_path, {".git": "not a repository\n"}, git=True)

    assert (
        raised.value.completed.status,
        raised.value.completed.stderr.startswith("fatal: "),
    ) == (128, True)
