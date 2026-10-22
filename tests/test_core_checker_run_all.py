"""Red tests for `run_all`: Commands run through a Runner at most cap at once, results in command order.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process",
and its decision 26. `run_all(process, commands, cap)` runs each Command through `process` in worker threads, at most
`cap` at once, taking the next Command from `commands` in the main thread only when fewer than `cap` are running. It
returns one result per Command started, in the order of `commands`: the Completed, or the GateError or OSError that
taking the Command or calling `process` raised. Such an error stops it: no Command is taken once one is seen, the ones
running are waited for, and the list ends at the first error in command order. Any other exception from `process` goes
on. The signals that end a run are held in `test_core_checker_run_all_signals.py`.
"""

import errno
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from gates.core.checker import Command, Completed, run_all
from gates.core.report import GateError
from tests.support.fake import completed
from tests.support.scripted import Scripted, Step

REFUSAL = "cannot start the checker: refused"


def _command(tmp_path: Path, name: str) -> Command:
    return Command(argv=("checker", name), cwd=tmp_path)


def _commands(tmp_path: Path, *names: str) -> list[Command]:
    return [_command(tmp_path, name) for name in names]


class Taken:
    """The Commands for some names, given one at a time, recording at each take how many calls had finished and where."""

    def __init__(self, tmp_path: Path, process: Scripted, *names: str, error: Exception | None = None) -> None:
        self.tmp_path = tmp_path
        self.process = process
        self.names = names
        self.error = error
        self.finished_at_take: list[int] = []
        self.in_main: list[bool] = []

    def __iter__(self) -> Iterator[Command]:
        for name in self.names:
            self.finished_at_take.append(len(self.process.finished))
            self.in_main.append(threading.current_thread() is threading.main_thread())
            yield _command(self.tmp_path, name)
        if self.error is not None:
            self.finished_at_take.append(len(self.process.finished))
            raise self.error


def test_no_commands(tmp_path: Path) -> None:
    """No Command gives no result."""
    process = Scripted({})
    assert run_all(process, [], 2, next_done=process.next_done) == []


def test_results_in_command_order(tmp_path: Path) -> None:
    """The results come in the order of the Commands, though a later one finished first."""
    first, second = completed(1, "a\n"), completed(0, "b\n")
    process = Scripted({"a": Step(first, after=("b",)), "b": Step(second)})

    results = run_all(process, _commands(tmp_path, "a", "b"), 2, next_done=process.next_done)

    assert (results, process.finished) == ([first, second], ["b", "a"])


def test_at_most_cap(tmp_path: Path) -> None:
    """With more Commands than the cap, the cap's number run at once and no more."""
    names = ("a", "b", "c", "d", "e")
    process = Scripted({name: Step(completed()) for name in names})

    results = run_all(process, _commands(tmp_path, *names), 2, next_done=process.next_done)

    assert (len(results), process.peak) == (5, 2)


def test_cap_of_one(tmp_path: Path) -> None:
    """A cap of 1 runs one Command at a time."""
    names = ("a", "b", "c")
    process = Scripted({name: Step(completed()) for name in names})

    run_all(process, _commands(tmp_path, *names), 1, next_done=process.next_done)

    assert process.peak == 1


def test_taken_when_a_slot_frees(tmp_path: Path) -> None:
    """Each Command is taken, in the main thread, only once fewer than the cap are running."""
    names = ("a", "b", "c")
    process = Scripted({name: Step(completed()) for name in names})
    taken = Taken(tmp_path, process, *names)

    run_all(process, taken, 1, next_done=process.next_done)

    assert (taken.finished_at_take, taken.in_main, process.called) == ([0, 1, 2], [True, True, True], ["a", "b", "c"])


@pytest.mark.parametrize(
    "error",
    [GateError(REFUSAL), OSError(errno.ENOSPC, "No space left on device")],
    ids=["gate-error", "os-error"],
)
def test_process_error_ends_the_list(tmp_path: Path, error: Exception) -> None:
    """An error the process raises is the last result, and no Command is taken after it is seen."""
    first = completed(1, "a\n")
    process = Scripted({"a": Step(first), "b": Step(error), "c": Step(completed())})
    taken = Taken(tmp_path, process, "a", "b", "c")

    results = run_all(process, taken, 1, next_done=process.next_done)

    assert (results, process.called, len(taken.finished_at_take)) == ([first, error], ["a", "b"], 2)


def test_taking_error_ends_the_list(tmp_path: Path) -> None:
    """An error raised while taking the next Command is the last result, after the results of the ones started."""
    first = completed(1, "a\n")
    error = GateError(REFUSAL)
    process = Scripted({"a": Step(first)})

    results = run_all(process, Taken(tmp_path, process, "a", error=error), 2, next_done=process.next_done)

    assert results == [first, error]


def test_running_ones_waited_for(tmp_path: Path) -> None:
    """A Command running when an error is seen is waited for, and its result stands where it comes before the error."""
    first = completed(1, "a\n")
    error = GateError(REFUSAL)
    process = Scripted({"a": Step(first, after=("b",)), "b": Step(error), "c": Step(completed())})

    results = run_all(process, Taken(tmp_path, process, "a", "b", "c"), 2, next_done=process.next_done)

    assert (results, process.called) == ([first, error], ["a", "b"])


def test_first_error_in_command_order(tmp_path: Path) -> None:
    """Where two Commands fail, the list ends at the one first in command order, whichever failed first."""
    early = OSError(errno.ENOSPC, "No space left on device")
    process = Scripted({"a": Step(early, after=("b",)), "b": Step(GateError(REFUSAL))})

    results = run_all(process, _commands(tmp_path, "a", "b"), 2, next_done=process.next_done)

    assert results == [early]


def test_error_after_later_finished(tmp_path: Path) -> None:
    """A later Command that finished is dropped when an earlier one fails, so what stands never depends on finish order."""
    error = GateError(REFUSAL)
    process = Scripted({"a": Step(error, after=("b",)), "b": Step(completed(1, "b\n"))})

    results = run_all(process, _commands(tmp_path, "a", "b"), 2, next_done=process.next_done)

    assert results == [error]


def test_other_exception_goes_on(tmp_path: Path) -> None:
    """An exception from the process other than a GateError or OSError goes on out of run_all."""
    process = Scripted({"a": Step(completed()), "b": Step(ValueError("broken runner"))})

    with pytest.raises(ValueError, match="broken runner"):
        run_all(process, _commands(tmp_path, "a", "b"), 2, next_done=process.next_done)


def test_completed_identity(tmp_path: Path) -> None:
    """Each result is the very Completed the process gave back."""
    reply = Completed(status=0, stdout="", stderr="", timed_out=False, outputs={})
    process = Scripted({"a": Step(reply)})

    assert run_all(process, _commands(tmp_path, "a"), 3, next_done=process.next_done)[0] is reply
