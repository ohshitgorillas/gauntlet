Status: proposed, for the owner's approval.

## Why

C7b is the mutation gate's process step: "processes and throttle" (`docs/superpowers/specs/2026-10-20-gates-core-design.md:320`). The gates core design gives it parts but no interface: one `run.process(Command(...))` line (`:229`), the worker cap of decision 30 (`:230`, `:414`), the cap lines of decision 29 (`:232`, `:413`) and the suite of decision 28 (`:225`, `:412`). The gate holds the gap as a body that only raises (`gates/check_mutation.py:91`–`:100`). Nothing names the function that runs mutmut or says what it hands back, so neither C7b nor C7c, which builds that function's input, can be built against it.

The tree, and the G4 branch the gate is ported from (`.claude/worktrees/agent-a3292c4f570aba00b/`), hold 14 copies of what the core already owns or of what this design gives one home:

- **The cap line, 3 copies.** `AT_THE_CAP` (`gates/check_mutation.py:18`) words the cap its own way beside `report.time_cap` (`gates/core/report.py:95`), and a test pins that wording (`tests/test_check_mutation_core.py:212`). G4 words it twice more (`.claude/worktrees/agent-a3292c4f570aba00b/gates/check_mutation.py:96`, `.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:40`).
- **A result that cannot carry decision 29.** `Mutated.at_cap` is a flag and `Mutated.error` one string (`gates/check_mutation.py:82`, `:83`). The note `time_cap(argv[0], 600)` needs the Command's `argv[0]`, and the pair `report.timed_out` gives (`gates/core/report.py:100`) fits one string only by composing a second copy of it.
- **Process running in G4, 5 copies.** A worker count from `os.sched_getaffinity` (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:24`) beside `cpu_budget` (`gates/core/checker.py:381`); a `nice`/`ionice` line (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:19`) beside `throttle_line` (`gates/core/checker.py:357`); a group kill (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:57`) and a `subprocess.run` and a `Popen` (`:38`, `:68`) beside `run` (`gates/core/checker.py:66`).
- **Real time in G4, 2 copies.** The gate reads `time.monotonic` (`.claude/worktrees/agent-a3292c4f570aba00b/gates/check_mutation.py:48`) and hands each of its two mutmut processes the time left (`:81`, `:91`). Real time in `gates/` has one home, and a timeout a module computes for itself is forbidden (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:163`).
- **mutmut's API in 3 modules of G4, 3 copies.** The driver (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_driver.py:19`, `:35`, `:42`, `:58`), the runner (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:10`) and the judge (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_judge.py:8`–`:10`) each import it.
- **An interpreter command line by hand in G4, 1 copy.** `driver` builds `sys.executable` with `-P` itself (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:29`–`:31`). The core's one builder, `python_module` (`gates/core/checker.py:342`), gives only the `-m` form, which puts the working directory, the copy mutmut works in, on `sys.path`.

mutmut is no dependency of the tree (`pyproject.toml:14`–`:22`), though decision 30 names its version.

## Modules

### `gates/check_mutation.py`: the mutmut run, its command and its verdict

Its job is to run mutmut once over a plan through the run's process runner and hand back `Mutated`, the value `outcome` takes. `run_mutmut` is the function that runs the mutation tool. C7c's `mutate` builds the `Plan` from the copy, git and parse steps and calls `run_mutmut`; it starts no process of its own.

```python
WALL_CLOCK_SECONDS = 600  # the one cap: the driver Command's timeout (decision 1)
DRIVER: Path              # gates/mutmut_driver.py, beside this module
UNCHECKED_AT_CAP = "unchecked at the cap"  # the spec's status for a mutant the cap left unchecked

@dataclass(frozen=True)
class Plan:  # what the copy, git and parse steps (C7c) hand the mutmut run
    settings: Path                         # the directory of the pyproject.toml mutmut reads, in the run's scratch
    work: Path                             # the copy mutmut works in, in the run's scratch
    changed: Mapping[str, frozenset[str]]  # each file mutmut mutates, by its path in the copy: its changed functions' mangled names
    given: Mapping[str, Source]            # the same files: the Source each was given as

@dataclass(frozen=True)
class Mutated:  # what one mutmut run left
    mutants: tuple[Mutant, ...] = ()         # every mutant not killed
    capped: str | None = None                # at the cap: time_cap(the driver Command's argv[0], 600), the note before the findings
    unfinished: tuple[Unfinished, ...] = ()  # what the checker did not finish, printed before every finding
```

```python
def mutmut_command(plan: Plan, workers: int) -> Command
    # python_script(DRIVER, plan.settings, plan.work, <plan.changed as JSON>, "--", "run", "--max-children", str(workers),
    #               cwd=plan.work, timeout=WALL_CLOCK_SECONDS), with throttled=True,
    #               env=environment(drop_prefixes=(PYTEST_ENVIRONMENT,)), and outputs NAMES, REACH and one meta_key per changed file
def judge(plan: Plan, command: Command, completed: Completed, suite: Callable[[], tuple[Unfinished, ...]]) -> Mutated
    # reads only the Completed; calls suite only after a nonzero exit before the cap
def suite_lines(run: Run, budget: Callable[[], int]) -> tuple[Unfinished, ...]
    # check_pytest.check(budget, the run with sources test_files(run.given)): () when its exit code is 0, else its notes, then its lines, each an Unfinished
def run_mutmut(run: Run, plan: Plan, *, budget: Callable[[], int] = cpu_budget) -> Mutated
def outcome(settings: Sequence[Finding], mutated: Mutated) -> Outcome
    # lines: mutated.unfinished, the key findings, then each mutant by path as given, then name; notes: (mutated.capped,) when set
```

`run_mutmut` takes these steps in order:

1. A plan with no changed file gives `Mutated()`, and no process runs.
2. No file in `test_files(run.given)` is a GateError (decision 28).
3. `budget()` is called once; 0 is a GateError, and no process runs (decision 30).
4. `mutmut_command(plan, budget's number)` runs through `run.process`, once. A GateError or OSError from it goes to the caller, where `check` makes it the run's one Unfinished.
5. The result is `judge(plan, command, completed, partial(suite_lines, run, budget))`.

`judge` reads the driver's outputs from the Completed: `NAMES`, the generated mutants with their diffs and mutmut's status table; `REACH`, tests collected and functions reached; and each file's `.meta` report under its `meta_key`, read through the status table. A mutant mutmut killed gives nothing. Each other mutant is a `Mutant`: the `given` of its file's Source, mutmut's name, its status, and the driver's diff, which `render` puts on one line.

- **Timed out, no `NAMES`.** Mutant generation ran past the cap: `unfinished=timed_out(completed.output(), command.argv[0], command.timeout)`, exit 2 (decision 29).
- **Timed out, with `NAMES`.** The run hit the cap: each mutant mutmut never checked has status `UNCHECKED_AT_CAP`, every other one its own, and `capped=time_cap(command.argv[0], command.timeout)`, exit 1 (decision 29).
- **Not timed out, `NAMES` absent or unreadable.** `unfinished=(Unfinished(completed.output()),)`.
- **Exit 0.** Each mutant takes its status; any mutant left unchecked puts `Unfinished(completed.output())` first.
- **Nonzero exit.** `judge` calls `suite`. When the suite passed and `REACH` shows tests collected and no function reached, each unchecked mutant has mutmut's `NO_TESTS` status and the run is finished. Otherwise the run is unfinished: `Unfinished(completed.output())`, then the suite's lines, then the findings (quality gates spec, `docs/superpowers/specs/2026-10-17-quality-gates-design.md:90`).

It replaces the raising body of `mutate` as the process step (`gates/check_mutation.py:91`–`:100`), `AT_THE_CAP` (`:18`), and `Mutated.at_cap` and `.error` (`:82`, `:83`); `check`'s catch gives `Mutated(unfinished=(Unfinished(error.report),))` (`:131`–`:132`). It also replaces G4's `mutation_run.py` and `mutation_judge.py`, and G4's remaining-time reads (`.claude/worktrees/agent-a3292c4f570aba00b/gates/check_mutation.py:48`, `:81`, `:91`).

### `gates/mutmut_driver.py`: the child mutmut runs in

Its job is to be the one module that imports mutmut. In an interpreter of its own it generates the mutants of the changed functions, writes their names and diffs with mutmut's status table, runs mutmut over them, and writes the reach record. Every own line also runs in a test's own process, as the core's child rule asks (`docs/superpowers/specs/2026-10-20-gates-core-design.md:182`, decision 4).

```python
NAMES: str                 # the Completed.outputs key of the generated mutants
REACH: str                 # the Completed.outputs key of the reach record
KILLED: str                # mutmut's status names in the pinned version, which judge reads
UNCHECKED: frozenset[str]
NO_TESTS: str
def names_path(settings: Path) -> Path            # in the settings directory, outside the copy
def reach_path(settings: Path) -> Path
def meta_key(located: str) -> str                 # the Completed.outputs key of a mutated file's .meta report
def meta_path(work: Path, located: str) -> Path   # where mutmut writes that report in the copy

class Mutmut(Protocol):  # mutmut's entry points, handed in so every own line runs in a test's process (decision 4)
    def load(self, settings: Path, work: Path) -> None: ...        # read settings/pyproject.toml, then work in the copy
    def mutants(self, located: str) -> list[tuple[str, str]]: ...  # each mutant mutmut generates for the file: its name, then its diff
    def statuses(self) -> Mapping[int | None, str]: ...            # mutmut's status per exit code a .meta report records; None: never checked
    def run(self, arguments: Sequence[str]) -> None: ...           # mutmut's own command line, in this process
    def reach(self) -> tuple[int, int]: ...                        # tests collected, then functions a test reaches

MUTMUT: Mutmut  # the real entry points: the only mutmut imports in gates/ (decision 2)
```

```python
def changed_mutants(mutmut: Mutmut, changed: Mapping[str, frozenset[str]]) -> dict[str, list[tuple[str, str]]]
    # each file's mutants whose function is changed, in mutmut's order
def names_report(mutants: Mapping[str, Sequence[tuple[str, str]]], statuses: Mapping[int | None, str]) -> str  # JSON
def reach_report(collected: int, reached: int) -> str  # JSON
def main(arguments: Sequence[str], mutmut: Mutmut = MUTMUT) -> None
    # <settings> <work> <changed as JSON> -- <mutmut's arguments>: load; write names_path; run mutmut with the names appended,
    # no run when there are none; write reach_path from the process that started the run, however it ends short of a kill
```

Run as a script, it calls `main(sys.argv[1:])`. The gate builds mutmut's arguments, so `--max-children` stands in the Command a FakeRunner records (decision 30), and the driver only appends the names. It replaces G4's `mutation_driver.py`, whose `probe` and `check` programs become one (decision 1), and the mutmut imports of G4's runner and judge (decision 2).

### `gates/core/checker.py`: `python_script` beside `python_module`

Its job is unchanged. It gains the one builder of an interpreter that runs a script by its path.

```python
def python_script(script: Path, *arguments: str | Path, cwd: Path, timeout: float | None = None) -> Command
    # (sys.executable, "-P", str(script), *arguments): -P keeps the script's directory and the working directory off sys.path
```

It replaces G4's `driver` (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:29`–`:31`).

## Homes

| Concern | Its one home | What it forbids elsewhere |
|---|---|---|
| Running mutmut: its name, input and result | `check_mutation.run_mutmut(run, plan, *, budget) -> Mutated` | A second function that starts mutmut; a process started in `mutate` or anywhere in C7c |
| mutmut's Python API | `gates/mutmut_driver.py`, `MUTMUT` (decision 2) | An import of `mutmut` anywhere else in `gates/` |
| The child's command line | `checker.python_script` | `sys.executable` named in a gate module |
| The run's wall-clock cap | One driver Command, `timeout=WALL_CLOCK_SECONDS` (decision 1) | A second timed Command per run; a `time` read, or time left computed, in the gate (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:163`) |
| The cap note and the capped pair | `report.time_cap` and `report.timed_out` (decision 29) | `AT_THE_CAP` or any other wording of the cap |
| Throttling | `Command.throttled=True`, through `checker.throttle_line` | `nice` or `ionice` in an argv |
| Workers | `run_mutmut`'s `budget`, `cpu_budget` by default, as `--max-children` in the Command's argv (decision 30) | An affinity or CPU read in the gate; a row for a key mutmut never reads |
| Timeout, group kill and output files | `checker.run`, through `run.process` | `subprocess`, `os.killpg` and reading the copy after the run in the gate |
| pytest's environment | `check_pytest.PYTEST_ENVIRONMENT` (`gates/check_pytest.py:19`) through `checker.environment` | A second `"PYTEST_"` literal |
| The suite on the unmutated tree | `check_pytest.check` (`gates/check_pytest.py:205`), through `suite_lines` (decision 3) | A pytest command line built in the mutation gate |
| Where the driver and mutmut write | `mutmut_driver`'s `names_path`, `reach_path`, `meta_path` and their keys | A file name or output key spelled in the gate |
| mutmut's status names | `mutmut_driver`'s `KILLED`, `UNCHECKED`, `NO_TESTS`, and the table `statuses` gives | A status name of mutmut's spelled in the gate |
| A fake runner in tests | `tests/support/fake.py` `FakeRunner` and `completed` (`tests/support/fake.py:16`, `:32`) | A test's own Runner; a real mutmut run where a reply proves the branch |

A builder that needs what these homes lack stops and reports it, and writes no copy.

## Order

Each step lands green under `make check` before the next starts, save a `stub` step, which lands with its red tests in the commit of the build that turns them green (`docs/superpowers/specs/2026-10-18-agents-design.md:64`).

1. The gates core design names `python_script` in `checker.py`'s block (`docs/superpowers/specs/2026-10-20-gates-core-design.md:57`), and its mutmut bullet (`:224`–`:232`) and C7a-c row (`:320`) point here for C7b's interface. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/2026-10-20-gates-core-design.md`.
2. `dependency`: mutmut in the dev group, locked at the version decision 30 names. Agent: `gatesmith`, no red test. Paths: `pyproject.toml`, `uv.lock`.
3. `stub`: `python_script`; `gates/mutmut_driver.py`; `Plan`, `mutmut_command`, `judge`, `suite_lines`, `run_mutmut`, `Mutated` with `capped` and `unfinished`, and `outcome`, each body raising `NotImplementedError`. Agent: `gatesmith`, no red test. Paths: `gates/core/checker.py`, `gates/mutmut_driver.py`, `gates/check_mutation.py`.
4. Red tests for `outcome` over `capped` and `unfinished`: the cap note and the capped pair (decision 29). Agent: `test-writer`. Paths: `tests/test_check_mutation_core.py`.
5. `outcome` and `check` on the new `Mutated`; `AT_THE_CAP` goes. Agent: `gatesmith`, red test from step 4. Paths: `gates/check_mutation.py`.
6. `moved`: `test_at_the_cap` and `test_unfinished`, which decision 29's line moved (`docs/superpowers/specs/2026-10-20-gates-core-design.md:413`). Agent: `test-writer`. Paths: `tests/test_check_mutation_core.py`.
7. Red tests for `python_script`. Agent: `test-writer`. Paths: `tests/test_core_checker_python_script.py`.
8. `python_script`. Agent: `gatesmith`, red test from step 7. Paths: `gates/core/checker.py`.
9. Measure whether `MUTMUT`'s `load`, `run` and `reach` can run in a test's own process (decision 4). Agent: `spiker`, scratchpad only. Paths: none in the tree.
10. Red tests for the driver on a fake `Mutmut`, and for `MUTMUT` as step 9 finds. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
11. The driver. Agent: `gatesmith`, red test from step 10. Paths: `gates/mutmut_driver.py`.
12. Red tests for `mutmut_command`, `judge`, `suite_lines` and `run_mutmut` through `FakeRunner`. Agent: `test-writer`. Paths: `tests/test_check_mutation_run.py`.
13. `mutmut_command`, `judge`, `suite_lines` and `run_mutmut`. Agent: `gatesmith`, red test from step 12. Paths: `gates/check_mutation.py`.

`mutate` keeps raising after step 13; C7c builds the `Plan` and calls `run_mutmut` from it.

## Decisions for the owner

1. **One process or two under the 600-second cap?** I recommend one driver Command for generation and checking, with `timeout=WALL_CLOCK_SECONDS`; whether `NAMES` was written tells generation past the cap (exit 2) from a run at the cap (exit 1), as decision 29 splits them. Cost: none in the core; the driver holds both phases, and a FakeRunner reply proves each branch with no clock. The alternative keeps G4's two processes, the second given the 600 seconds less the first's time. Cost: the gate needs elapsed time, and `Clock` gives only `wait` (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:109`–`:110`), so the approved no-wall-clock design and `gates/core/clock.py`, not yet built, gain a method, and every test of the split hands in a `VirtualClock`.
2. **Where is mutmut's Python API imported?** I recommend the driver alone, handing the gate mutmut's status table and each mutant's diff as JSON. Cost: the driver makes the diff of every generated mutant, killed ones included, before any is checked; the time that takes is unmeasured. The alternative lets the gate import mutmut's status table and diff function in its own process, as G4's judge does (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_judge.py:8`–`:10`). Cost: two homes of mutmut's API; whether importing those modules in the gate's process reads mutmut's settings from the gate's working directory is unmeasured.
3. **Where do the failing test ids come from after a nonzero exit?** I recommend running the suite on the unmutated tree through `check_pytest.check`, as G4 does through the pytest gate (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_judge.py:97`). Cost: a second suite run, outside the 600-second cap and bounded per test by pytest-timeout (`pyproject.toml:55`); its time is unmeasured. The alternative prints mutmut's whole output alone. Cost: whether that output names the failing tests is unmeasured, and the spec asks for the ids (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:90`).
4. **How do the driver's own lines run in a test's own process?** I recommend handing mutmut's entry points in as `Mutmut`, testing the driver's logic in-process on a fake, and measuring first (step 9) whether `MUTMUT`'s `load`, `run` and `reach` can run in a test's process, its red tests following what that finds. Cost: one spike, and an adapter whose calls the spike may find cannot all run in-process, which comes back to the owner. The alternative drives mutmut's console command, with no own code in the child. Cost: no reach record, which G4 reads to tell a mutant no test reaches from a failed run (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_judge.py:52`), and the filter to changed functions has no home in the child; the console output's fitness is unmeasured.
