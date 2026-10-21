"""One gate run, from start to exit: its sources, its scratch space, its checker's batches, its printed lines and exit."""

import os
import shutil
import stat
import sys
import tempfile
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, Protocol

from gates.core.checker import Command, Completed, Runner, run, run_all
from gates.core.project import Project, Source, python_files
from gates.core.report import GateError, Line, Outcome, Unfinished, exit_code, nothing_checked, render, write

# The mode every directory of the run's temp dir is given before it is deleted, so that a read-only one is deleted too.
DELETABLE = stat.S_IRWXU


class Scratch:
    """The run's temp space: one temp dir of its own in the root, made when first asked for, deleted by close."""

    root: Path

    def __init__(self, root: Path | None = None) -> None:
        """Take the root the run's temp dir goes in; None is the system temp directory as tempfile gives it now."""
        self.root = Path(tempfile.gettempdir()) if root is None else root
        self._directory: Path | None = None
        self._built: dict[str, Path] = {}

    def directory(self, name: str) -> Path:
        """Return a new, empty directory inside the run's temp dir, its last component starting with the name.

        Raises GateError when the run's temp dir or the directory cannot be made.
        """
        inside = self._run_directory()
        try:
            return Path(tempfile.mkdtemp(prefix=f"{name}-", dir=inside))
        except OSError as error:
            message = f"cannot make the temp space {name} in {inside}: {error}"
            raise GateError(message) from error

    def copy(self, tree: Path, name: str) -> Path:
        """Return a new directory inside the run's temp dir that holds a copy of the tree, a symlink as what it names.

        Raises GateError when the directory cannot be made or the tree cannot be copied.
        """
        target = self.directory(name)
        try:
            shutil.copytree(tree, target, dirs_exist_ok=True)
        except OSError as error:
            message = f"cannot copy {tree} to the temp space {target}: {error}"
            raise GateError(message) from error
        return target

    def once(self, name: str, make: Callable[[Path], None]) -> Path:
        """Return the directory make built for the name, building it in a new directory the first time only.

        A make that raises leaves nothing kept: its error goes to the caller, and the next call builds again.
        """
        if name not in self._built:
            path = self.directory(name)
            make(path)
            self._built[name] = path
        return self._built[name]

    def close(self) -> str | None:
        """Delete the run's temp dir and all it holds, read-only entries included; return the failure, never raise."""
        directory, self._directory = self._directory, None
        self._built.clear()
        if directory is None:
            return None
        try:
            _make_deletable(directory)
            shutil.rmtree(directory)
        except OSError as error:
            return f"cannot delete the temp space {directory}: {error}"
        return None

    def _run_directory(self) -> Path:
        """Return the run's own temp dir, made in the root the first time it is asked for.

        Raises GateError when it cannot be made.
        """
        if self._directory is None:
            try:
                self._directory = Path(tempfile.mkdtemp(dir=self.root))
            except OSError as error:
                message = f"cannot make the temp space in {self.root}: {error}"
                raise GateError(message) from error
        return self._directory


def _make_deletable(directory: Path) -> None:
    """Give the directory and every directory under it DELETABLE, each before it is listed; a symlink is left alone."""
    directory.chmod(DELETABLE)
    for parent, names, _ in os.walk(directory):
        for name in names:
            path = Path(parent) / name
            if not path.is_symlink():
                path.chmod(DELETABLE)


@dataclass(frozen=True)
class Run:
    """What a gate's check works with: the project, the selected sources, the run's scratch and its process runner.

    `given` is every Python file given, test files included, as `python_files` returns them; `sources` is selected
    from it. The default `()` keeps a hand-built Run valid and gives a check that reads it no file.
    """

    project: Project
    sources: tuple[Source, ...]
    scratch: Scratch
    process: Runner
    given: tuple[Source, ...] = ()


@dataclass(frozen=True)
class Gate:
    """A gate: its name, its check, the sources it selects, and what it calls them in an empty run's line."""

    name: str
    check: Callable[[Run], Outcome]
    select: Callable[[Sequence[Source]], list[Source]] = list
    selects: str = "Python file"


class Checker[R](Protocol):
    """A checker process the gate runs in batches, and how its report becomes the gate's lines."""

    stopped: frozenset[int]

    def batches(self, run: Run) -> Sequence[Sequence[Source]]: ...

    def command(self, run: Run, batch: Sequence[Source]) -> Command: ...

    def read(self, completed: Completed) -> R: ...

    def expected_status(self, report: R) -> int: ...

    def lines(self, report: R, batch: Sequence[Source], *, stopped: bool) -> Sequence[Line]: ...


def check_with[R](checker: Checker[R], *, budget: Callable[[], int] | None = None) -> Callable[[Run], Outcome]:
    """Return the check that runs the checker's batches, the budget's number at once, and gives their lines in order.

    The budget is called once per check, after `batches` and before the first `command`; the cap is `max(1, budget())`,
    and None runs one batch at a time. A GateError or OSError from the budget is the one Unfinished, with no batch run.
    The batches run through `run_all`, each command made in batch order. A GateError or OSError from a batch's command
    or process ends the check at the first such batch in batch order: its report follows the lines of the batches
    before it, no batch starts once it is seen, and no later batch gives a line.
    """

    def check(run: Run) -> Outcome:
        batches = checker.batches(run)
        try:
            cap = 1 if budget is None else max(1, budget())
        except (GateError, OSError) as error:
            return Outcome(lines=(Unfinished(_report(error)),))
        commands: list[Command] = []

        def made() -> Iterator[Command]:
            for batch in batches:
                commands.append(checker.command(run, batch))
                yield commands[-1]

        lines: list[Line] = []
        for index, result in enumerate(run_all(run.process, made(), cap)):
            if isinstance(result, GateError | OSError):
                lines.append(Unfinished(_report(result)))
                break
            lines.extend(_batch_lines(checker, batches[index], commands[index], result))
        return Outcome(lines=tuple(lines))

    return check


def _batch_lines[R](checker: Checker[R], batch: Sequence[Source], command: Command, completed: Completed) -> list[Line]:
    """Return one batch's lines: its report's, or the checker's whole output when the batch did not finish.

    A timeout reads no report and adds the gate's line naming the cap. A stop is read before the expected status, so a
    stop is never a finish, and a stopped batch whose lines hold no Unfinished gets the whole output as one.
    """
    output = completed.output()
    if completed.timed_out:
        cap = f"the checker {command.argv[0]} ran past its time cap of {command.timeout} seconds"
        return [Unfinished(output), Unfinished(cap)]
    try:
        report = checker.read(completed)
    except GateError:
        return [Unfinished(output)]
    if completed.status in checker.stopped:
        lines = list(checker.lines(report, batch, stopped=True))
        if not any(isinstance(line, Unfinished) for line in lines):
            lines.append(Unfinished(output))
        return lines
    if completed.status == checker.expected_status(report):
        return list(checker.lines(report, batch, stopped=False))
    return [Unfinished(output)]


def _report(error: GateError | OSError) -> str:
    """Return what an error that stopped the run reports: a GateError's report, an OSError's text."""
    return error.report if isinstance(error, GateError) else str(error)


def run_gate(
    gate: Gate,
    paths: Sequence[Path],
    *,
    project: Project | None = None,
    process: Runner = run,
    scratch_root: Path | None = None,
) -> int:
    """Run the gate over the paths, print its lines and return its exit code; M is the number of sources selected.

    The scratch is closed on every path, an interrupt included, which then goes on with nothing printed.
    """
    given = tuple(python_files(paths))
    sources = gate.select(given)
    if not sources:
        write(nothing_checked(gate.name, gate.selects, len(paths)))
        return 1
    scratch = Scratch(scratch_root)
    try:
        try:
            run_project = Project.current() if project is None else project
            gate_run = Run(project=run_project, sources=tuple(sources), scratch=scratch, process=process, given=given)
            outcome = gate.check(gate_run)
        except (GateError, OSError) as error:
            outcome = Outcome(lines=(Unfinished(_report(error)),))
    finally:
        failure = scratch.close()
    if failure is not None:
        outcome = Outcome(lines=(*outcome.lines, Unfinished(failure)), notes=outcome.notes)
    write(render(gate.name, outcome, len(sources)))
    return exit_code(outcome)


def main(gate: Gate) -> NoReturn:
    """Run the gate over the paths of the command line and exit with its exit code."""
    sys.exit(run_gate(gate, [Path(argument) for argument in sys.argv[1:]]))
