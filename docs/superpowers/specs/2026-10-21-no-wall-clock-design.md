Status: proposed, for the owner's approval.

## Why

The quality gates spec bars clock reads and sleeps from test files (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:118`), and the owner's task bars every wall clock and every slow test, with no exception. The tree has four kinds of clock in `tests/`, and the same few helpers copied from file to file to carry them.

**Clock reads and sleeps in test code.** `time.monotonic` deadlines with `time.sleep` polls: `tests/test_core_checker_group.py:103`, `:108`, `:111`, `:116`; `tests/test_core_checker_signals.py:110`, `:118`, `:128`, `:130`, `:180`, `:187`, `:201`; `tests/test_core_checker_run_all_signals.py:129`, `:137`, `:142`, `:144`, `:147`; `tests/test_heavy_checker.py:67`, `:72`, `:106`, `:108`.

**Timed waits.** A positive timeout on a blocking wait, which the spec's rule does not reach: `tests/support/scripted.py:50` (`Event.wait(WAIT)`) and `:53` (`Event().wait(step.hold)`, a sleep under another name); `tests/test_heavy.py:204`, `:219`, `:225`, `:344`, `:345`; `tests/test_heavy_checker.py:54`, `:105`; `tests/test_heavy_lock.py:65`; `tests/test_heavy_dash_dash.py:63`; `tests/test_heavy_leading_dash.py:53`; `tests/test_core_checker_signals.py:136`; `tests/test_core_checker_run_all_signals.py:193`; `tests/test_support_capture.py:209`, `:293`, `:547`; and the capture helper's own bound, `tests/support/capture.py:29`, `:179`, `:357`.

**Sleeps in child code.** Strings run as child processes or as seeded test modules: `tests/test_core_checker_group.py:46`, `:55`, `:70`; `tests/test_core_checker_signals.py:65`, `:79`; `tests/test_core_checker_run_all_signals.py:50`, `:57`–`:59`, `:77`; `tests/test_heavy_checker.py:42`; `tests/test_check_pytest_parallel.py:35`–`:39`, `:47`–`:50`; `tests/test_check_pytest_cpus.py:42`; `tests/test_check_pytest_processes.py:35`.

**Bounds the pass path waits out.** These make the slow tests. Each passing run of a "held back" test in the pytest gate's CPU tests waits for a seeded rendezvous to give up, 200 polls of 0.05 s (`tests/test_check_pytest_cpus.py:39`–`:42`): `tests/test_check_pytest_cpus.py:67`, `:86`, `:100`, `:107`, and `tests/test_check_pytest_processes.py:67`. The heavy wrapper's waiting tests sit out `WAIT` (`tests/test_heavy.py:50`) in `_settle` (`tests/test_heavy.py:216`) at `:260` and `:287`. The time-cap tests sit out a 3 s cap (`tests/test_core_checker_group.py:28`) at `:139` and `:151`. The capture helper's held-fd tests sit out 0.5 s at `tests/test_support_capture.py:696`, `:720`, `:737`, `:826`. A signal test holds 0.5 s (`tests/test_core_checker_signals.py:38`, `:201`). The run-all and budget tests hold every call 0.3 s (`tests/test_core_checker_run_all.py:27`, `:77`, `:87`; `tests/test_core_runner_budget.py:30`, `:78`). How long the suite spends in these waits is unmeasured.

**Copies.** `_drain`, a FIFO read under a deadline, appears 3 times: `tests/test_core_checker_group.py:100`, `tests/test_core_checker_signals.py:107`, `tests/test_core_checker_run_all_signals.py:126`. `_kill_leftovers` appears 3 times: `tests/test_core_checker_group.py:91`, `tests/test_core_checker_signals.py:98`, `tests/test_core_checker_run_all_signals.py:117`. A wait on a child with a kill at the bound appears 3 times: `tests/test_core_checker_signals.py:133`, `tests/test_core_checker_run_all_signals.py:190`, `tests/test_heavy.py:222`. A poll for a file a child writes appears 4 times: `tests/test_core_checker_signals.py:126`, `:178`, `tests/test_core_checker_run_all_signals.py:56`, `tests/test_heavy_checker.py:65`. The sleeping grandchild appears 3 times: `tests/test_core_checker_group.py:50`, `tests/test_core_checker_signals.py:60`, `tests/test_core_checker_run_all_signals.py:45`. The seeded rendezvous module appears twice: `tests/test_check_pytest_cpus.py:30`, `tests/test_check_pytest_processes.py:25`.

**What is already clock-free.** `_hold` (`tests/test_heavy.py:231`) starts a child that writes a ready line on one pipe and then reads another pipe to its end. The test blocks on the first pipe and lets the child go by closing the second, with no clock anywhere (`tests/test_heavy.py:66`–`:76`). Every wait in this design has that shape.

## Modules

### `tests/support/scripted.py`: an in-process Runner whose waits are events

Its job is to order and overlap concurrent calls by events alone, with no timeout and no hold. It replaces `WAIT` and `hold` (`tests/support/scripted.py:17`, `:26`, `:50`, `:53`) and every `HOLD` its callers pass (`tests/test_core_checker_run_all.py:27`, `tests/test_core_runner_budget.py:30`). The pytest gate's cap tests reach it through `run_gate(..., process=...)` (`gates/core/runner.py:217`), so the seeded rendezvous modules (`tests/test_check_pytest_cpus.py:30`, `tests/test_check_pytest_processes.py:25`) and their 10-second give-up go too.

```python
class Released(Exception):  # a call still blocked when its Scripted closed
    name: str
    def __init__(self, name: str) -> None: ...

def last_argument(command: Command) -> str: ...  # the default key: the Command's last argv word

@dataclass(frozen=True)
class Step:
    reply: Completed | BaseException
    after: tuple[str, ...] = ()   # names whose calls have finished before this call returns
    beside: tuple[str, ...] = ()  # names whose calls have started before this call returns

class Scripted:  # a Runner safe across threads; every wait blocks on an event and has no timeout
    called: list[str]
    finished: list[str]
    peak: int                     # the most calls seen running at once
    def __init__(self, steps: Mapping[str, Step], *, key: Callable[[Command], str] = last_argument) -> None: ...
    def __call__(self, command: Command) -> Completed: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, *exc: object) -> None: ...  # every call still blocked raises Released, so no worker thread outlives the test
```

### `tests/support/lifeline.py`: child processes held, met and ended by pipes

Its job is every wait a test makes on a real process: ready, held, met and ended, each one an event on a pipe or FIFO. It replaces the 3 `_drain` copies, the 3 `_kill_leftovers` copies, the 3 kill-at-the-bound waits, the 4 file polls and the 3 sleeping grandchildren listed under **Why**. It also replaces `_alive` (`tests/test_heavy_checker.py:57`), `_settle` (`tests/test_heavy.py:216`), `_hold` (`tests/test_heavy.py:231`), whose shape it generalises, and the sleeping child code at `tests/test_core_checker_group.py:46`, `:58`, `tests/test_core_checker_signals.py:68`, `tests/test_core_checker_run_all_signals.py:53` and `tests/test_heavy_checker.py:38`.

```python
class Lifeline:  # a pipe whose write end only the test holds; a child reading its read end to EOF lives until release
    read_fd: int
    def __init__(self) -> None: ...
    def release(self) -> None: ...                 # close the write end; a second call does nothing
    def __enter__(self) -> Self: ...
    def __exit__(self, *exc: object) -> None: ...  # release, then close the read end

class Witness:  # a FIFO the test reads; every process that opens it to write is a holder
    path: Path
    def __init__(self, path: Path) -> None: ...    # makes the FIFO and opens its read end without blocking
    def ended(self) -> bytes: ...                  # called after every holder's ready line: blocks, with no deadline, until every holder has closed it; returns what they wrote
    def __enter__(self) -> Self: ...
    def __exit__(self, *exc: object) -> None: ...

def ready(fd: int) -> bytes: ...  # block until a child writes one line on fd and return it; b"" when every writer closed first

class Pids:  # the pids children note in a file, killed by pid at teardown
    path: Path
    def __init__(self, path: Path) -> None: ...
    def noted(self) -> list[int]: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, *exc: object) -> None: ...  # SIGKILL each noted pid; ProcessLookupError passed over

HOLD: str     # child code: write a ready line to fd 1, then read fd int(sys.argv[1]) to EOF and exit 0
WITNESS: str  # child code: open the FIFO at sys.argv[1] to write, write a mark, write a ready line, then HOLD on fd int(sys.argv[2])
MEET: str     # child code: open the FIFO at sys.argv[1] for reading or writing as sys.argv[2] says; returns once the other side has opened it
```

`MEET` is a two-process rendezvous: a FIFO's open blocks until both ends are open. A seeded test module that must end after another one opens such a FIFO and reads it to its end, which comes when the other module's process has exited. That replaces the timed waits at `tests/test_check_pytest_parallel.py:30` and `:43`.

### `tests/support/capture.py`: no bound of its own (decision 4)

Its job is unchanged (`docs/superpowers/specs/2026-10-20-capture-design.md:9`). Under decision 4's recommendation it blocks until both pipes reach end of file, and pytest-timeout is its one bound. `HOLD_BOUND` (`tests/support/capture.py:29`), the `timeout` keyword (`:357`), the timed wait (`:179`) and the held-fd path of `CaptureError` all go.

```python
def captured[T](call: Callable[[], T]) -> Captured[T]: ...  # blocks until fds 1 and 2 reach EOF once the call has ended; pytest-timeout is the one bound
```

### `gates/heavy.py`: a wait the test can see (decision 3)

Its job is unchanged. Under decision 3's recommendation, `run` first asks for the lock without blocking (`gates/heavy.py:39` today blocks at once). When another process holds the lock, it writes one line on stderr and then blocks. A test that holds the lock reads that line as the event that the wrapper is waiting, then releases. That replaces the 5-second `_settle` at `tests/test_heavy.py:260` and `:287`.

```python
WAITING: str  # "heavy: waiting for the lock {path}", written once on stderr when another process holds the lock
def run(lock: Path, line: list[str]) -> int: ...  # LOCK_EX | LOCK_NB first; when refused, writes WAITING, then blocks on LOCK_EX
```

### `gates/core/checker.py`: an output reader the test can hand in (decision 5)

Its job is unchanged (`docs/superpowers/specs/2026-10-20-gates-core-design.md:55`). Under decision 5's recommendation, `run` (`gates/core/checker.py:66`) takes the function that reads each output file back, and its default is today's reader. A test's driver hands in a reader that signals its own process from inside the read, which delivers the signal before `kill` returns. It then writes a line, which the driver writes only if the signal was held. That replaces the 0.5-second hold at `tests/test_core_checker_signals.py:201`.

```python
def read_output(path: Path) -> str | None: ...  # today's reader of an output file; GateError when it exists and cannot be read
def run(command: Command, *, read: Callable[[Path], str | None] = read_output) -> Completed: ...
```

## Homes

A test waits only on an event: a pipe or FIFO opening, a line arriving, end of file arriving, a thread event being set. It blocks on that event with no timeout of its own. The one bound on a test that hangs is pytest-timeout's 30 seconds (`pyproject.toml:55`, `docs/superpowers/specs/2026-10-17-quality-gates-design.md:103`), so a hang costs time only when a test fails. A test whose pass path needs something not to happen proves it through an event the code gives, or through a fake handed in as an argument, never by waiting for a while to see. A child process lives only as long as a pipe whose write end the test holds, so it dies when the test lets it go or when the test's process ends.

A positive time cap handed to the code under test is data, not a wait, where the pass path ends on the child's exit before the cap. The core's wait ends on the exit event (`gates/core/checker.py:226`, `:242`), so `tests/test_core_runner.py:915` reads no clock. A test that proves the cap itself passes `timeout=0` against a child held by a lifeline, which the spec's rule admits (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:118`), and the core polls once and reports `timed_out` (decision 2).

| Concern | Its one home | What it forbids elsewhere |
|---|---|---|
| Ordering and overlapping in-process calls | `tests/support/scripted.py` `Scripted` | A timed wait, a hold or a poll in a test's own Runner; a real-process rendezvous to prove a cap the `process` argument of `run_gate` (`gates/core/runner.py:217`) can carry |
| Waiting on a real child: ready, met, ended | `tests/support/lifeline.py` `ready`, `MEET`, `Witness.ended` | `time` and `datetime` calls, a deadline loop, a poll for a file, and a positive timeout on `wait`, `join`, `result`, `communicate`, `subprocess.run` or `select`, in a test file or in child code |
| Keeping a child alive | `tests/support/lifeline.py` `Lifeline`, `HOLD`, `WITNESS` | A sleep in child code or in a seeded module |
| Killing leftovers | `tests/support/lifeline.py` `Pids`, by pid | A per-file `_kill_leftovers`; a kill by name |
| The bound on a hung test | pytest-timeout, `timeout = 30` (`pyproject.toml:55`) | Any other bound in `tests/`, `tests/support/capture.py` included (decision 4) |
| Proving the checker's time cap | `Command(timeout=0)` against a child held by a `Lifeline` (decision 2) | A positive cap the test sits out |
| Proving that something waits | An event the code gives (decisions 3 and 5) or a fake handed in | Waiting for a while to see that nothing happened |
| Enforcing all of the above | G6's clock rule (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:118`), as decision 1 rules it, and `test-reviewer` | An exemption of any kind |

A builder that needs a wait none of these homes gives stops and reports it. It does not write its own copy.

## Order

Each step lands green under `make check` before the next starts. A step marked with a decision runs only when the owner rules that decision as recommended. Otherwise it is dropped, and the steps that rest on it take the alternative the ruling gives.

1. Spec lines for the decisions ruled. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/2026-10-17-quality-gates-design.md` (decision 1), `docs/superpowers/specs/2026-10-18-agents-design.md` (decision 3), `docs/superpowers/specs/2026-10-20-capture-design.md` (decision 4), `docs/superpowers/specs/2026-10-20-gates-core-design.md` (decision 5).
2. `Scripted` on events, and its two callers onto it. Agent: `test-writer`. Paths: `tests/support/scripted.py`, `tests/test_core_checker_run_all.py`, `tests/test_core_runner_budget.py`.
3. `lifeline.py`, its own tests, and the group tests onto it, the time cap at `timeout=0` (decision 2). Agent: `test-writer`. Paths: `tests/support/lifeline.py`, `tests/test_support_lifeline.py`, `tests/test_core_checker_group.py`.
4. The signal tests onto `lifeline.py`, with the red test for the output reader (decision 5). Agent: `test-writer`. Paths: `tests/test_core_checker_signals.py`, `tests/test_core_checker_run_all_signals.py`.
5. The output reader (decision 5). Agent: `gatesmith`, red test from step 4. Paths: `gates/core/checker.py`.
6. The heavy tests onto `lifeline.py`, with no timeout, and the red test for `WAITING` (decision 3). Agent: `test-writer`. Paths: `tests/test_heavy.py`, `tests/test_heavy_checker.py`, `tests/test_heavy_lock.py`, `tests/test_heavy_dash_dash.py`, `tests/test_heavy_leading_dash.py`.
7. `WAITING` (decision 3). Agent: `gatesmith`, red test from step 6. Paths: `gates/heavy.py`.
8. The pytest gate's cap tests onto `Scripted` through `run_gate`, and its given-order tests onto `MEET`. Agent: `test-writer`. Paths: `tests/test_check_pytest_cpus.py`, `tests/test_check_pytest_processes.py`, `tests/test_check_pytest_parallel.py`.
9. `captured` with no bound of its own (decision 4). Agent: `test-writer`. Paths: `tests/support/capture.py`, `tests/test_support_capture.py`.

## Decisions for the owner

1. **Does G6's clock rule reach timed waits?** The spec's rule fails clock calls and timeouts under 0.5 s only (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:118`), so `Event.wait(5.0)` and `subprocess.run(..., timeout=20)` pass it. No gate script under `gates/` runs G6 yet. Recommend: widen the rule so a test file fails on any positive number given as the timeout of a blocking wait, that is `wait`, `join`, `result`, `communicate`, `subprocess.run`, `call`, `check_call`, `check_output` and `select`. A cap handed to `Command` or `python_module` stays data. Cost: one spec line, and more for G6 to build when its turn comes. Alternative: keep the rule as written and leave timed waits to `test-reviewer`. Cost: no gate stops a timed wait from coming back, and child code in strings is out of any gate's reach either way.
2. **How is the checker's time cap proven?** Recommend: `Command(timeout=0)` against a child a `Lifeline` holds. The core polls once (`gates/core/checker.py:226`, `:242`) and the child is certainly alive, so no production change is needed. Cost: a positive cap firing is never exercised; it is the same call with another number. Alternative: a wait function handed to `run`, faked in tests. Cost: a new core parameter, a gates-core design change, a `gatesmith` step, and the real wait still needs the `timeout=0` test.
3. **How do the heavy tests see that a second run waits?** Recommend: the wrapper writes `WAITING` on stderr when the lock is held, and the test reads that line before it releases. Cost: a new line on every contended heavy run, a spec line in the agents design, and step 7 of the order, which changes `gates/heavy.py`. Alternative: hand `heavy.run` a lock function and fake it. Cost: the real cross-process `flock` wait goes unproven.
4. **Does `captured` keep a bound of its own?** Recommend: no; it blocks to end of file, and pytest-timeout is the bound. Cost: a leaked fd holder fails as a 30-second pytest timeout with no `CaptureError` output; capture-design decision 3 (`docs/superpowers/specs/2026-10-20-capture-design.md:93`–`:96`) is rewritten; the held-fd tests at `tests/test_support_capture.py:687`, `:708`, `:725` and `:826` go. Alternative: keep `HOLD_BOUND` as a bound that only a failure reaches, and test it at `timeout=0` against a held child. Cost: one timed wait stays in `tests/support/`. A killed grandchild that has not yet closed fd 1 when the call returns could make that test fail now and then; how often is unmeasured.
5. **How does the signal test prove a SIGTERM is held while `run` reads its outputs?** No event shows that the signal has arrived before the test writes the report (`tests/test_core_checker_signals.py:190`–`:209`). Recommend: `run` takes its output reader as a parameter, and the driver's reader signals its own process from inside the read. Cost: a core parameter that only a test passes, a gates-core design change, and steps 4 and 5. Alternative: delete the test. Cost: holding a signal during the output read goes unproven, since `_Interrupts` is private and G6 bars a test from reaching it (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:115`).
