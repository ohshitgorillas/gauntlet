"""Red tests for `check_with`'s budget: the batches it runs at once, and their lines in batch order.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "runner.py: one gate run, from start to
exit", and its decisions 23, 26 and 27. `budget` is called once per check, after `batches` and before the first
`command`; the cap is `max(1, budget())`, and None runs one batch at a time. A GateError or OSError from `budget` is the
Outcome of its one Unfinished, with no batch run. The batches run through `run_all`, each batch's command made in
batch order, and each batch's lines follow the lines of the batch before it, whatever the order they finished in. A
GateError or OSError ends the check at the first failing batch in batch order: its report follows the lines of the
batches before it, no batch starts once it is seen, and no later batch gives a line, even one that finished. The
interrupt is held in `test_core_checker_run_all_signals.py`.
"""

import errno
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from gates.core.checker import Command, Completed
from gates.core.project import Source
from gates.core.report import Finding, GateError, Line, Outcome, Unfinished
from gates.core.runner import Run, Scratch, check_with
from tests.support.fake import completed
from tests.support.project import scaffold
from tests.support.scripted import Scripted, Step

REFUSAL = "cannot start the checker: refused"


class Logged:
    """A checker with one batch per source, its report its stdout's lines, each a Finding; it logs each call it gets."""

    stopped: frozenset[int] = frozenset()

    def __init__(self, log: list[str], *, refuse: str | None = None) -> None:
        self.log = log
        self.refuse = refuse

    def batches(self, run: Run) -> list[list[Source]]:
        self.log.append("batches")
        return [[source] for source in run.sources]

    def command(self, run: Run, batch: Sequence[Source]) -> Command:
        name = batch[0].given.name
        self.log.append(f"command {name}")
        if name == self.refuse:
            raise GateError(REFUSAL)
        return Command(argv=("echo", name), cwd=run.project.root)

    def read(self, completed: Completed) -> list[str]:
        return completed.stdout.splitlines()

    def expected_status(self, report: list[str]) -> int:
        return 1 if report else 0

    def lines(
        self, report: list[str], batch: Sequence[Source], *, stopped: bool
    ) -> list[Line]:
        return [Finding(text) for text in report]


def _checked(
    tmp_path: Path,
    process: Scripted,
    budget: Callable[[], int] | None,
    *names: str,
    log: list[str] | None = None,
    refuse: str | None = None,
) -> Outcome:
    project = scaffold(tmp_path / "project", {name: "value = 1\n" for name in names})
    sources = tuple(
        Source(given=Path(name), absolute=project.root / name) for name in names
    )
    run = Run(
        project=project,
        sources=sources,
        scratch=Scratch(tmp_path),
        process=process,
        next_done=process.next_done,
    )
    return check_with(Logged([] if log is None else log, refuse=refuse), budget=budget)(
        run
    )


def _held(*names: str) -> Scripted:
    return Scripted({name: Step(completed()) for name in names})


def test_budget_sizes_the_cap(tmp_path: Path) -> None:
    """A budget of 2 runs two batches at once, and no more."""
    process = _held("a", "b", "c", "d")

    _checked(tmp_path, process, lambda: 2, "a", "b", "c", "d")

    assert process.peak == 2


@pytest.mark.parametrize(
    "budget", [None, lambda: 0, lambda: 1], ids=["none", "zero", "one"]
)
def test_one_at_a_time(tmp_path: Path, budget: Callable[[], int] | None) -> None:
    """No budget, or a budget of 0 or 1, runs one batch at a time."""
    process = _held("a", "b", "c")

    _checked(tmp_path, process, budget, "a", "b", "c")

    assert process.peak == 1


def test_budget_called_once_before_commands(tmp_path: Path) -> None:
    """The budget is called once, after batches and before the first command; commands are made in batch order."""
    log: list[str] = []

    def budget() -> int:
        log.append("budget")
        return 2

    process = Scripted({name: Step(completed()) for name in "abc"})
    _checked(tmp_path, process, budget, "a", "b", "c", log=log)

    assert log == ["batches", "budget", "command a", "command b", "command c"]


@pytest.mark.parametrize(
    "error",
    [GateError(REFUSAL), OSError(errno.ENOSPC, "No space left on device")],
    ids=["gate-error", "os-error"],
)
def test_budget_error(tmp_path: Path, error: Exception) -> None:
    """An error from the budget is the Outcome of its one Unfinished, and no batch runs."""
    process = Scripted({})
    log: list[str] = []

    def budget() -> int:
        raise error

    outcome = _checked(tmp_path, process, budget, "a", log=log)

    assert (outcome, process.called, log) == (
        Outcome(lines=(Unfinished(str(error)),)),
        [],
        ["batches"],
    )


def test_lines_in_batch_order(tmp_path: Path) -> None:
    """Each batch's lines follow the batch before it, though the later batch finished first."""
    process = Scripted(
        {"a": Step(completed(1, "a\n"), after=("b",)), "b": Step(completed(1, "b\n"))}
    )

    outcome = _checked(tmp_path, process, lambda: 2, "a", "b")

    assert (outcome, process.finished) == (
        Outcome(lines=(Finding("a"), Finding("b"))),
        ["b", "a"],
    )


def test_error_after_earlier_batch(tmp_path: Path) -> None:
    """A later batch's error ends the check after the lines of the batch before it, though that one finished last."""
    process = Scripted(
        {
            "a": Step(completed(1, "a\n"), after=("b",)),
            "b": Step(GateError(REFUSAL)),
            "c": Step(completed(1, "c\n")),
        }
    )

    outcome = _checked(tmp_path, process, lambda: 2, "a", "b", "c")

    assert (outcome, process.called) == (
        Outcome(lines=(Finding("a"), Unfinished(REFUSAL))),
        ["a", "b"],
    )


def test_no_line_after_first_error(tmp_path: Path) -> None:
    """An earlier batch's error ends the check there, and a later batch that finished gives no line."""
    process = Scripted(
        {"a": Step(GateError(REFUSAL), after=("b",)), "b": Step(completed(1, "b\n"))}
    )

    outcome = _checked(tmp_path, process, lambda: 2, "a", "b")

    assert outcome == Outcome(lines=(Unfinished(REFUSAL),))


def test_command_error_stops_starts(tmp_path: Path) -> None:
    """A command's error ends the check after the batches started before it, and no later command is made."""
    log: list[str] = []
    process = Scripted({name: Step(completed(1, f"{name}\n")) for name in "ac"})

    outcome = _checked(tmp_path, process, lambda: 2, "a", "b", "c", log=log, refuse="b")

    assert (outcome, process.called, log) == (
        Outcome(lines=(Finding("a"), Unfinished(REFUSAL))),
        ["a"],
        ["batches", "command a", "command b"],
    )
