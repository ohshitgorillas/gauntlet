Status: approved by the owner.

## Why

The quality gates spec bars clock reads and sleeps from test files (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:118`), and the owner's task bars every wall clock and every slow test, with no exception. The tree has four kinds of clock in `tests/`, real time in `gates/` that no test can turn, and the same few helpers copied from file to file to carry them.

**Clock reads and sleeps in test code.** `time.monotonic` deadlines with `time.sleep` polls: `tests/test_core_checker_group.py:103`, `:108`, `:111`, `:116`; `tests/test_core_checker_signals.py:110`, `:118`, `:128`, `:130`, `:180`, `:187`, `:201`; `tests/test_core_checker_run_all_signals.py:129`, `:137`, `:142`, `:144`, `:147`; `tests/test_heavy_checker.py:67`, `:72`, `:106`, `:108`.

**Timed waits.** A positive timeout on a blocking wait, which the spec's rule does not reach: `tests/support/scripted.py:50` (`Event.wait(WAIT)`) and `:53` (`Event().wait(step.hold)`, a sleep under another name); `tests/test_heavy.py:204`, `:219`, `:225`, `:344`, `:345`; `tests/test_heavy_checker.py:54`, `:105`; `tests/test_heavy_lock.py:65`; `tests/test_heavy_dash_dash.py:63`; `tests/test_heavy_leading_dash.py:53`; `tests/test_core_checker_signals.py:136`; `tests/test_core_checker_run_all_signals.py:193`; `tests/test_support_capture.py:209`, `:293`, `:547`; and the capture helper's own bound, `tests/support/capture.py:29`, `:179`, `:357`.

**Sleeps in child code.** Strings run as child processes or as seeded test modules: `tests/test_core_checker_group.py:46`, `:55`, `:70`; `tests/test_core_checker_signals.py:65`, `:79`; `tests/test_core_checker_run_all_signals.py:50`, `:57`–`:59`, `:77`; `tests/test_heavy_checker.py:42`; `tests/test_check_pytest_parallel.py:35`–`:39`, `:47`–`:50`; `tests/test_check_pytest_cpus.py:42`; `tests/test_check_pytest_processes.py:35`.

**Bounds the pass path waits out.** These make the slow tests. Each passing run of a "held back" test in the pytest gate's CPU tests waits for a seeded rendezvous to give up, 200 polls of 0.05 s (`tests/test_check_pytest_cpus.py:39`–`:42`): `tests/test_check_pytest_cpus.py:67`, `:86`, `:100`, `:107`, and `tests/test_check_pytest_processes.py:67`. The heavy wrapper's waiting tests sit out `WAIT` (`tests/test_heavy.py:50`) in `_settle` (`tests/test_heavy.py:216`) at `:260` and `:287`. The time-cap tests sit out a 3 s cap (`tests/test_core_checker_group.py:28`) at `:139` and `:151`. The capture helper's held-fd tests sit out 0.5 s at `tests/test_support_capture.py:696`, `:720`, `:737`, `:826`. A signal test holds 0.5 s (`tests/test_core_checker_signals.py:38`, `:201`). The run-all and budget tests hold every call 0.3 s (`tests/test_core_checker_run_all.py:27`, `:77`, `:87`; `tests/test_core_runner_budget.py:30`, `:78`). How long the suite spends in these waits is unmeasured.

**Real time in production code.** The checker's time cap reaches real time as a bare timeout handed to the exit wait, `gates/core/checker.py:226` and `:242`, with no seam a test can turn. So the time-cap tests sit the cap out on the wall (`tests/test_core_checker_group.py:28`, `:139`, `:151`), and `main`'s command-line test arms a 60-second cap on the wall (`tests/test_core_runner.py:915`). `run_all`'s cleanup polls every `REKILL` seconds (`gates/core/checker.py:28`, `:473`) for checkers started after its first kill.

**Copies.** `_drain`, a FIFO read under a deadline, appears 3 times: `tests/test_core_checker_group.py:100`, `tests/test_core_checker_signals.py:107`, `tests/test_core_checker_run_all_signals.py:126`. `_kill_leftovers` appears 3 times: `tests/test_core_checker_group.py:91`, `tests/test_core_checker_signals.py:98`, `tests/test_core_checker_run_all_signals.py:117`. A wait on a child with a kill at the bound appears 3 times: `tests/test_core_checker_signals.py:133`, `tests/test_core_checker_run_all_signals.py:190`, `tests/test_heavy.py:222`. A poll for a file a child writes appears 4 times: `tests/test_core_checker_signals.py:126`, `:178`, `tests/test_core_checker_run_all_signals.py:56`, `tests/test_heavy_checker.py:65`. The sleeping grandchild appears 3 times: `tests/test_core_checker_group.py:50`, `tests/test_core_checker_signals.py:60`, `tests/test_core_checker_run_all_signals.py:45`. The seeded rendezvous module appears twice: `tests/test_check_pytest_cpus.py:30`, `tests/test_check_pytest_processes.py:25`.

**What is already clock-free.** `_hold` (`tests/test_heavy.py:231`) starts a child that writes a ready line on one pipe and then reads another pipe to its end. The test blocks on the first pipe and lets the child go by closing the second, with no clock anywhere (`tests/test_heavy.py:66`–`:76`). Every wait on a real process in this design has that shape.

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

Its job is unchanged (`docs/superpowers/specs/2026-10-20-capture-design.md:22`). Once the call has ended it blocks until both pipes reach end of file, and pytest-timeout is its one bound (decision 4). `HOLD_BOUND` (`tests/support/capture.py:29`), the `timeout` keyword (`:357`), the timed wait (`:179`) and `CaptureError` (`:65`), whose one raise is the held-fd raise (`:354`), all go. So do the held-fd tests (`tests/test_support_capture.py:687`, `:708`, `:725`) and the held-fd case of the exit-path test (`:837`, run by `_held` at `:823`). A leaked fd holder fails as pytest-timeout's 30-second timeout, with no `CaptureError` output. Step 1 rewrites the capture design to match: its holder constraint (`docs/superpowers/specs/2026-10-20-capture-design.md:9`), its stubs, where `captured` takes no `timeout` (`:48`) and neither `HOLD_BOUND` nor `CaptureError` stands, the holder behaviour (`:60`), its homes rows for the errors and the wait (`:71`, `:72`) and its decision 3 (`:86`–`:89`).

```python
def captured[T](call: Callable[[], T]) -> Captured[T]: ...  # blocks until fds 1 and 2 reach EOF once the call has ended; pytest-timeout is the one bound
```

### `gates/heavy.py`: a wait the test can see (decision 3)

Its job is unchanged. `run` asks for the lock without blocking first, where `gates/heavy.py:39` blocks at once (decision 3). When another process holds the lock, it writes one line on stderr and then blocks. A test that holds the lock reads that line as the event that the wrapper is waiting, then releases. That replaces the 5-second `_settle` in `test_second_run_waits` (`tests/test_heavy.py:260`, its call at `:266`) and `test_waits_on_flock` (`:287`, its call at `:294`). Every contended heavy run prints that one line more. Step 1 adds it to the wrapper's bullet in the agents design (`docs/superpowers/specs/2026-10-18-agents-design.md:50`).

```python
WAITING: str  # "heavy: waiting for the lock {path}", written once on stderr when another process holds the lock
def run(lock: Path, line: list[str]) -> int: ...  # LOCK_EX | LOCK_NB first; when refused, writes WAITING, then blocks on LOCK_EX
```

### `gates/core/clock.py`: the one home of real time (decision 6)

Its job is to carry every wait in `gates/` that can end on time as well as on an event, so that real time lives in `SystemClock` alone and a test turns the time through a `Clock` it hands in. The caller keeps its own wait on the event, as `Ready`; the clock decides what time that wait is given. It replaces the bare cap handed to the exit wait at `gates/core/checker.py:226` and `:242`, which becomes the `Ready` `run` hands its clock. Step 3 adds it to the gates core design beside `checker.py` (`docs/superpowers/specs/2026-10-20-gates-core-design.md:48`).

```python
type Ready = Callable[[float | None], bool]  # the caller's own wait on an event, for up to the seconds given (None: without end); True when the event came

class Clock(Protocol):
    def wait(self, ready: Ready, seconds: float | None) -> bool: ...  # True when the event came before `seconds` passed on this clock; None: no cap

class SystemClock:  # real time, the only real time in gates/: hands `seconds` to ready as they are
    def wait(self, ready: Ready, seconds: float | None) -> bool: ...

SYSTEM: Clock  # a SystemClock; the default of every clock parameter in gates/
```

### `tests/support/clock.py`: a virtual clock (decision 6)

Its job is to be the one clock a test hands to code that waits on time. Its time moves only as the test sets it, and it never hands a `Ready` a positive number, so no wait on it reads or waits on real time. It replaces the time-cap tests' wall-clock cap (`tests/test_core_checker_group.py:28`, `:139`, `:151`) and the 60-second cap at `tests/test_core_runner.py:915`.

```python
class VirtualClock:  # a Clock whose time moves only as the test sets it
    now: float  # virtual seconds passed, from 0
    def __init__(self, *, passes: float | None = None) -> None: ...  # the seconds that pass in a wait whose event has not come at its poll; None: time stands still
    def wait(self, ready: Ready, seconds: float | None) -> bool: ...  # ready(0) first; when False and passes reaches seconds, now += seconds and False; otherwise ready(None)
```

A still `VirtualClock()` never lets a cap pass, so a wait on it ends on its event alone. `VirtualClock(passes=p)` with `p` at or past the cap lets the cap pass at once, in virtual time, when the event has not come at the clock's one poll.

### `gates/core/checker.py`: an output reader and a clock the test can hand in, and a cleanup with no poll (decisions 5, 6, 7)

Its job is unchanged (`docs/superpowers/specs/2026-10-20-gates-core-design.md:56`). `run` (`gates/core/checker.py:66`) takes the function that reads each output file back, and its default is the reader it uses now (decision 5). Only a test passes that parameter; step 1 adds it to the gates core design's `run` line (`docs/superpowers/specs/2026-10-20-gates-core-design.md:56`). A test's driver hands in a reader that signals its own process from inside the read, which delivers the signal before `kill` returns. It then writes a line, which the driver writes only if the signal was held. That replaces the 0.5-second hold at `tests/test_core_checker_signals.py:201`.

`run` also takes a `Clock`, `SYSTEM` by default, and waits on the checker's exit through it, the time cap passing on that clock (decision 6). A gate's test hands it to a real run through the `process` argument of `run_gate` (`gates/core/runner.py:217`), as `functools.partial(run, clock=...)`, so `run_gate` takes no clock of its own. Step 3 adds the parameter to the gates core design's `run` line.

`run_all`'s cleanup (`gates/core/checker.py:469`) kills every live group once and then waits for its workers with no timeout. While it waits, a checker `run` starts is killed as it is added to the live set (`:259`), under the lock `add` already takes (`:261`), so `REKILL` (`:28`) and the timed wait at `:473` go (decision 7). `run_all`'s signature is unchanged. The gates core design names no poll interval; step 3 writes the kill at add into decision 26's cleanup (`docs/superpowers/specs/2026-10-20-gates-core-design.md:410`).

```python
def read_output(path: Path) -> str | None: ...  # run's default reader of an output file; GateError when it exists and cannot be read
def run(command: Command, *, read: Callable[[Path], str | None] = read_output, clock: Clock = SYSTEM) -> Completed: ...  # the time cap passes on clock

class _Live:  # the checkers run has started and not yet reaped
    def add(self, process: subprocess.Popen[bytes]) -> None: ...  # holds it; while closing, kills its group at once
    def closing(self) -> AbstractContextManager[None]: ...  # kills every group held; until it exits, every add kills at once (decision 7)
```

## Homes

A test waits only on an event: a pipe or FIFO opening, a line arriving, end of file arriving, a thread event being set. It blocks on that event with no timeout of its own. The one bound on a test that hangs is pytest-timeout's 30 seconds (`pyproject.toml:55`, `docs/superpowers/specs/2026-10-17-quality-gates-design.md:103`), so a hang costs time only when a test fails. Time a test needs to pass passes on a `VirtualClock`, never on the wall (decision 6). A test whose pass path needs something not to happen proves it through an event the code gives, or through a fake handed in as an argument, never by waiting for a while to see. A child process lives only as long as a pipe whose write end the test holds, so it dies when the test lets it go or when the test's process ends.

Real time enters `gates/` at one place, `SystemClock` in `gates/core/clock.py`. Every wait in `gates/` that can end on time as well as on an event goes through a `Clock` handed in, `SYSTEM` by default, and keeps its own wait on the event as the `Ready` it hands that clock (decision 6). The checker's exit wait (`gates/core/checker.py:226`, `:242`) is such a `Ready`. A test that hands `run` a positive cap hands it a `VirtualClock` too, and no test runs a positive cap on `SYSTEM`. A still `VirtualClock()` never lets the cap pass, so the wait ends on the child's exit, as `main`'s command-line test needs (`tests/test_core_runner.py:915`). A test that proves the cap itself hands `run` a positive cap and `VirtualClock(passes=...)` at or past it, against a child a `Lifeline` holds: the child is certainly alive at the clock's one poll, so the cap passes at once in virtual time and `run` reports `timed_out`, with no real time spent. `run_all`'s cleanup waits on its workers' end with no time in it at all (decision 7).

G6's clock rule reaches timed waits (decision 1). A test file fails on any positive number given as the timeout of a blocking wait: `wait`, `join`, `result`, `communicate`, `subprocess.run`, `call`, `check_call`, `check_output` and `select`. A cap handed to `Command` or `python_module` stays data. Step 1 writes that into the rule (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:118`), and G6 builds it when its turn comes. Child code in strings is out of any gate's reach, so `test-reviewer` holds it.

| Concern | Its one home | What it forbids elsewhere |
|---|---|---|
| Ordering and overlapping in-process calls | `tests/support/scripted.py` `Scripted` | A timed wait, a hold or a poll in a test's own Runner; a real-process rendezvous to prove a cap the `process` argument of `run_gate` (`gates/core/runner.py:217`) can carry |
| Waiting on a real child: ready, met, ended | `tests/support/lifeline.py` `ready`, `MEET`, `Witness.ended` | `time` and `datetime` calls, a deadline loop, a poll for a file, and a positive timeout on `wait`, `join`, `result`, `communicate`, `subprocess.run`, `call`, `check_call`, `check_output` or `select`, in a test file or in child code |
| Keeping a child alive | `tests/support/lifeline.py` `Lifeline`, `HOLD`, `WITNESS` | A sleep in child code or in a seeded module |
| Killing leftovers | `tests/support/lifeline.py` `Pids`, by pid | A per-file `_kill_leftovers`; a kill by name |
| The bound on a hung test | pytest-timeout, `timeout = 30` (`pyproject.toml:55`) | Any other bound in `tests/`, `tests/support/capture.py` included (decision 4) |
| Real time in `gates/` | `gates/core/clock.py` `SystemClock`, reached only through a `Clock` parameter whose default is `SYSTEM` (decision 6) | A `time` or `datetime` import, a sleep, or a timeout a module computes or holds for itself on a blocking wait, anywhere else in `gates/`; a poll interval constant, as `REKILL` (`gates/core/checker.py:28`) is (decision 7) |
| Time in a test | `tests/support/clock.py` `VirtualClock`, handed to the code under test (decision 6) | A positive cap run on `SYSTEM`; a test's own fake clock |
| Proving the checker's time cap | A positive cap handed to `run` with `VirtualClock(passes=...)` at or past it, against a child a `Lifeline` holds (decision 6) | A cap the test sits out on the wall; `timeout=0` standing in for a positive cap |
| Ending `run_all`'s cleanup | `_Live.closing` in `gates/core/checker.py`, killing each checker added while it lasts (decision 7) | A rekill loop on a timer, a clock in `run_all` |
| Proving that something waits | An event the code gives: `heavy.WAITING` (decision 3); a reader handed to `checker.run` (decision 5); or a fake handed in | Waiting for a while to see that nothing happened |
| Enforcing all of the above | G6's clock rule (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:118`), reaching every positive timeout on a blocking wait (decision 1), and `test-reviewer` for child code in strings and for a positive cap run on `SYSTEM`; an import-linter contract stopping every `gates` module but `gates.core.clock` from importing `time` or `datetime` (decision 8), and `diff-reviewer` for a timeout handed to a blocking wait in `gates/` | An exemption of any kind |

A builder that needs a wait none of these homes gives stops and reports it. It does not write its own copy.

## Order

Each step lands green under `make check` before the next starts.

1. Spec lines for decisions 1, 3, 4 and 5. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/2026-10-17-quality-gates-design.md` (decision 1), `docs/superpowers/specs/2026-10-18-agents-design.md` (decision 3), `docs/superpowers/specs/2026-10-20-capture-design.md` (decision 4), `docs/superpowers/specs/2026-10-20-gates-core-design.md` (decision 5).
2. `Scripted` on events, and its two callers onto it. Agent: `test-writer`. Paths: `tests/support/scripted.py`, `tests/test_core_checker_run_all.py`, `tests/test_core_runner_budget.py`.
3. Spec lines for decisions 6, 7 and 8. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/2026-10-20-gates-core-design.md` (`clock.py` beside `checker.py` at `:48`, `run`'s `clock` parameter on its line at `:56`, decision 6; decision 26's cleanup at `:410` killing each checker `run` starts while it lasts, with no poll, decision 7), `docs/superpowers/specs/2026-10-17-quality-gates-design.md` (the contract beside the pure-core contract at `:131`, decision 8).
4. `stub`: `gates/core/clock.py`, each body `raise NotImplementedError`, and `run`'s `clock` parameter, which raises `NotImplementedError` for any clock but `SYSTEM` until step 7 (decision 6). Agent: `gatesmith`, no red test. Paths: `gates/core/clock.py`, `gates/core/checker.py`.
5. `VirtualClock` and its own tests (decision 6). Agent: `test-writer`. Paths: `tests/support/clock.py`, `tests/test_support_clock.py`.
6. `lifeline.py`, its own tests, and the group tests onto it, their time cap a positive cap on a `VirtualClock` (decision 6); `main`'s command-line test (`tests/test_core_runner.py:915`) on a still `VirtualClock`. These are the red tests for the clock seam. Agent: `test-writer`. Paths: `tests/support/lifeline.py`, `tests/test_support_lifeline.py`, `tests/test_core_checker_group.py`, `tests/test_core_runner.py`.
7. The clock seam: `SystemClock`, and `run` waiting on the checker's exit through its `clock` (decision 6). Agent: `gatesmith`, red test from step 6. Paths: `gates/core/clock.py`, `gates/core/checker.py`.
8. `rewrite`: `run_all`'s cleanup on `_Live.closing`, with no `REKILL` (decision 7). Agent: `gatesmith`, no red test. Paths: `gates/core/checker.py`.
9. The signal tests onto `lifeline.py`, with the red test for the output reader (decision 5). Agent: `test-writer`. Paths: `tests/test_core_checker_signals.py`, `tests/test_core_checker_run_all_signals.py`.
10. The output reader (decision 5). Agent: `gatesmith`, red test from step 9. Paths: `gates/core/checker.py`.
11. The heavy tests onto `lifeline.py`, with no timeout, and the red test for `WAITING` (decision 3). Agent: `test-writer`. Paths: `tests/test_heavy.py`, `tests/test_heavy_checker.py`, `tests/test_heavy_lock.py`, `tests/test_heavy_dash_dash.py`, `tests/test_heavy_leading_dash.py`.
12. `WAITING` (decision 3). Agent: `gatesmith`, red test from step 11. Paths: `gates/heavy.py`.
13. The pytest gate's cap tests onto `Scripted` through `run_gate`, and its given-order tests onto `MEET`. Agent: `test-writer`. Paths: `tests/test_check_pytest_cpus.py`, `tests/test_check_pytest_processes.py`, `tests/test_check_pytest_parallel.py`.
14. `captured` with no bound of its own (decision 4). Agent: `test-writer`. Paths: `tests/support/capture.py`, `tests/test_support_capture.py`.

The contract of decision 8 is built with the layering gate (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:130`), which no step here builds.

## Decisions taken

Each entry gives the question, or for a ruling no open decision covered a name for the structure, in bold; the owner's ruling verbatim; `Adds:` each module, home and step the ruling adds; and `Written in:` each section it touches.

1. **Does G6's clock rule reach timed waits?** Ruling: "Do whatever you recommend." Adds: the home enforcing every wait home, G6's clock rule reaching every positive timeout on a blocking wait, with `test-reviewer` for child code in strings; step 1's line in `docs/superpowers/specs/2026-10-17-quality-gates-design.md`. Written in: Homes, Order.
2. **How is the checker's time cap proven?** Ruling: "Do whatever you recommend." Adds: none. Written in: none. Replaced by 6.
3. **How do the heavy tests see that a second run waits?** Ruling: "Yeah, fine. Do whatever you recommend." Adds: the module `gates/heavy.py` with `WAITING`; `heavy.WAITING` in the home for proving that something waits; step 1's line in `docs/superpowers/specs/2026-10-18-agents-design.md`, step 11's red test for `WAITING`, and step 12. Written in: Modules, Homes, Order.
4. **Does `captured` keep a bound of its own?** Ruling: "Do whatever you recommend." Adds: the module `tests/support/capture.py` with no bound and no `CaptureError`; pytest-timeout as the one bound on a hung test, `tests/support/capture.py` included; step 1's lines in `docs/superpowers/specs/2026-10-20-capture-design.md`, and step 14. Written in: Modules, Homes, Order.
5. **How does the signal test prove a SIGTERM is held while `run` reads its outputs?** Ruling: "Do whatever you recommend." Adds: the module `gates/core/checker.py` with `read_output` and `run`'s `read` parameter; a reader handed to `checker.run` in the home for proving that something waits; step 1's line in `docs/superpowers/specs/2026-10-20-gates-core-design.md`, step 9's red test for the reader, and step 10. Written in: Modules, Homes, Order.
6. **Virtual clocks, and the seams that carry them.** Ruling: "No wall clocks, we use virtual clocks and we cut seams in reasonable places that makes the code testable, fast and quick." Adds: the module `gates/core/clock.py` with `Ready`, `Clock`, `SystemClock` and `SYSTEM`; the module `tests/support/clock.py` with `VirtualClock`; `run`'s `clock` parameter in `gates/core/checker.py`; the homes for real time in `gates/`, for time in a test, and for proving the checker's time cap on a `VirtualClock`; step 3's lines in `docs/superpowers/specs/2026-10-20-gates-core-design.md`, steps 4 and 5, step 6's time-cap and command-line tests on a `VirtualClock`, and step 7; decisions 7 and 8, opened. Written in: Why, Modules, Homes, Order, Decisions for the owner.
7. **How does `run_all`'s cleanup end without polling on `REKILL`?** Ruling: "Take the recommendation." Adds: `_Live.closing`, and `_Live.add` killing each checker's group at once while closing, in the module `gates/core/checker.py`, with `REKILL` and the timed wait in `_drain` gone; the home for ending `run_all`'s cleanup, and a poll interval constant among what the home for real time in `gates/` forbids; step 3's line on decision 26's cleanup in `docs/superpowers/specs/2026-10-20-gates-core-design.md`, and step 8. Written in: Modules, Homes, Order.
8. **What stops real time coming back into `gates/`?** Ruling: "Take the recommendation." Adds: an import-linter forbidden contract stopping every `gates` module but `gates.core.clock` from importing `time` or `datetime`, built with the layering gate, and `diff-reviewer` for a timeout handed to a blocking wait in `gates/`, both in the home enforcing all of the above; step 3's line in `docs/superpowers/specs/2026-10-17-quality-gates-design.md` beside the pure-core contract. Written in: Homes, Order.
