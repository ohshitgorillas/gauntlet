Status: proposed, for the owner's approval.

## Why

C7b is the mutation gate's process step: "processes and throttle" (`docs/superpowers/specs/2026-10-20-gates-core-design.md:320`). The gates core design gives it parts but no interface: one `run.process(Command(...))` line (`:229`), the worker cap of decision 30 (`:230`, `:414`), the suite of decision 28 (`:225`, `:412`), and the 600-second cap lines of decision 29 (`:232`, `:413`), which the quality gates spec's wall-clock cap (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:89`) rests on. The gate has no wall-clock cap: it bounds its work, not its time (decision 1). The gate holds the gap as a body that only raises (`gates/check_mutation.py:91`–`:100`). Nothing names the function that runs mutmut or says what it hands back, so neither C7b nor C7c, which builds that function's input, can be built against it.

The tree, and the G4 branch the gate is ported from (`.claude/worktrees/agent-a3292c4f570aba00b/`), hold 14 copies of what the core already owns, of what this design gives one home, or of a cap the gate does not have:

- **A wall-clock cap the gate does not have, 3 copies.** `AT_THE_CAP` (`gates/check_mutation.py:18`), on `WALL_CLOCK_SECONDS` (`:15`), words a 600-second cap the gate does not have (decision 1), and a test pins the cap it names (`tests/test_check_mutation_core.py:215`, `:223`). G4 words it twice more (`.claude/worktrees/agent-a3292c4f570aba00b/gates/check_mutation.py:96`, `.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:40`).
- **A result shaped for the cap.** `Mutated.at_cap` flags a cap the gate does not have, and `Mutated.error` is one string (`gates/check_mutation.py:82`, `:83`), which holds the checker's error, the suite's lines and the bound's line only by joining them into one Unfinished.
- **Process running in G4, 5 copies.** A worker count from `os.sched_getaffinity` (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:24`) beside `cpu_budget` (`gates/core/checker.py:381`); a `nice`/`ionice` line (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:19`) beside `throttle_line` (`gates/core/checker.py:357`); a group kill (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:57`) and a `subprocess.run` and a `Popen` (`:38`, `:68`) beside `run` (`gates/core/checker.py:66`).
- **Real time in G4, 2 copies.** The gate reads `time.monotonic` (`.claude/worktrees/agent-a3292c4f570aba00b/gates/check_mutation.py:48`) and hands each of its two mutmut processes the time left (`:81`, `:91`). Real time in `gates/` has one home, and a timeout a module computes for itself is forbidden (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:163`).
- **mutmut's API in 3 modules of G4, 3 copies.** The driver (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_driver.py:19`, `:35`, `:42`, `:58`), the runner (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:10`) and the judge (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_judge.py:8`–`:10`) each import it.
- **An interpreter command line by hand in G4, 1 copy.** `driver` builds `sys.executable` with `-P` itself (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:29`–`:31`). The core's one builder, `python_module` (`gates/core/checker.py:342`), gives only the `-m` form, which puts the working directory, the copy mutmut works in, on `sys.path`.

mutmut is no dependency of the tree (`pyproject.toml:14`–`:22`), though decision 30 names its version.

## Modules

### `gates/check_mutation.py`: the mutmut run, its command and its verdict

Its job is to run mutmut once over a plan through the run's process runner and hand back `Mutated`, the value `outcome` takes. `run_mutmut` is the function that runs the mutation tool. C7c's `mutate` builds the `Plan` from the copy, git and parse steps and calls `run_mutmut`; it starts no process of its own.

```python
MOST_MUTANTS: int  # the work bound: the most mutants one run checks, its number as decision 5 sets it (decision 1)
DRIVER: Path       # gates/mutmut_driver.py, beside this module

@dataclass(frozen=True)
class Plan:  # what the copy, git and parse steps (C7c) hand the mutmut run
    settings: Path                         # the directory of the pyproject.toml mutmut reads, in the run's scratch
    work: Path                             # the copy mutmut works in, in the run's scratch
    changed: Mapping[str, frozenset[str]]  # each file mutmut mutates, by its path in the copy: its changed functions' mangled names
    given: Mapping[str, Source]            # the same files: the Source each was given as

@dataclass(frozen=True)
class Mutated:  # what one mutmut run left
    mutants: tuple[Mutant, ...] = ()         # every mutant not killed
    unfinished: tuple[Unfinished, ...] = ()  # what the checker did not finish, printed before every finding
```

```python
def mutmut_command(plan: Plan, workers: int) -> Command
    # python_script(DRIVER, plan.settings, plan.work, <plan.changed as JSON>, str(MOST_MUTANTS), "--", "run", "--max-children", str(workers),
    #               cwd=plan.work), with no timeout (decision 1), throttled=True,
    #               env=environment(drop_prefixes=(PYTEST_ENVIRONMENT,)), and outputs NAMES, REACH and one meta_key per changed file
def over_bound(generated: int) -> Unfinished
    # the gate's own line naming the mutants the changed functions yield, `generated`, and the bound, MOST_MUTANTS (decisions 1, 6)
def judge(plan: Plan, command: Command, completed: Completed, suite: Callable[[], tuple[Unfinished, ...]]) -> Mutated
    # reads only the Completed; calls suite only after a nonzero exit of a run the driver went ahead with
def suite_lines(run: Run, budget: Callable[[], int]) -> tuple[Unfinished, ...]
    # check_pytest.check(budget, the run with sources test_files(run.given)): () when its exit code is 0, else its notes, then its lines, each an Unfinished
def run_mutmut(run: Run, plan: Plan, *, budget: Callable[[], int] = cpu_budget) -> Mutated
def outcome(settings: Sequence[Finding], mutated: Mutated) -> Outcome
    # lines: mutated.unfinished, the key findings, then each mutant by path as given, then name; no notes
```

`run_mutmut` takes these steps in order:

1. A plan with no changed file gives `Mutated()`, and no process runs.
2. No file in `test_files(run.given)` is a GateError (decision 28).
3. `budget()` is called once; 0 is a GateError, and no process runs (decision 30).
4. `mutmut_command(plan, budget's number)` runs through `run.process`, once, with no timeout (decision 1). A GateError or OSError from it goes to the caller, where `check` makes it the run's one Unfinished.
5. The result is `judge(plan, command, completed, partial(suite_lines, run, budget))`.

The work is bounded, not the time (decision 1). Only the changed functions are mutated (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:80`). A run whose changed functions yield more than `MOST_MUTANTS` mutants checks none and says so before any mutant runs (decisions 5, 6). Each mutant's test run keeps its hang limit: pytest-timeout's 30 seconds per test (`pyproject.toml:55`) under mutmut's own default time limit, a key that changes it being a finding (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:85`, `gates/check_mutation.py:36`). Whether pytest-timeout ends a hung test inside mutmut's run in the copy is unmeasured; step 3 measures it.

`judge` reads the driver's outputs from the Completed: `NAMES`, the generated mutants with their diffs, mutmut's status table and whether the driver went ahead; `REACH`, tests collected and functions reached; and each file's `.meta` report under its `meta_key`, read through the status table. A mutant mutmut killed gives nothing. Each other mutant is a `Mutant`: the `given` of its file's Source, mutmut's name, its status, and the driver's diff, which `render` puts on one line.

- **`NAMES` absent or unreadable.** `unfinished=(Unfinished(completed.output()),)`.
- **Over the bound.** `NAMES` records that the driver did not go ahead: `unfinished=(over_bound(<the mutants NAMES lists>),)`, no mutant checked and none a finding, exit 2 (decisions 1, 6).
- **Exit 0.** Each mutant takes its status; any mutant left unchecked puts `Unfinished(completed.output())` first.
- **Nonzero exit.** `judge` calls `suite`. When the suite passed and `REACH` shows tests collected and no function reached, each unchecked mutant has mutmut's `NO_TESTS` status and the run is finished. Otherwise the run is unfinished: `Unfinished(completed.output())`, then the suite's lines, then the findings (quality gates spec, `docs/superpowers/specs/2026-10-17-quality-gates-design.md:91`).

It replaces the raising body of `mutate` as the process step (`gates/check_mutation.py:91`–`:100`), `WALL_CLOCK_SECONDS` and `AT_THE_CAP` (`:15`, `:18`), and `Mutated.at_cap` and `.error` (`:82`, `:83`); `check`'s catch gives `Mutated(unfinished=(Unfinished(error.report),))` (`:131`–`:132`). It also replaces G4's `mutation_run.py` and `mutation_judge.py`, and G4's remaining-time reads (`.claude/worktrees/agent-a3292c4f570aba00b/gates/check_mutation.py:48`, `:81`, `:91`).

### `gates/mutmut_driver.py`: the child mutmut runs in

Its job is to be the one module that imports mutmut. In an interpreter of its own it generates the mutants of the changed functions, writes their names and diffs with mutmut's status table and whether their count is within the bound, runs mutmut over them only when it is, and writes the reach record. Every own line also runs in a test's own process, as the core's child rule asks (`docs/superpowers/specs/2026-10-20-gates-core-design.md:182`, decision 4).

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
def within(mutants: Mapping[str, Sequence[tuple[str, str]]], most: int) -> bool
    # the one comparison of the work bound: True when the mutants, across every file, number at most `most` (decision 1)
def names_report(mutants: Mapping[str, Sequence[tuple[str, str]]], statuses: Mapping[int | None, str], ahead: bool) -> str
    # JSON; ahead: whether within() held and the run goes ahead
def reach_report(collected: int, reached: int) -> str  # JSON
def main(arguments: Sequence[str], mutmut: Mutmut = MUTMUT) -> None
    # <settings> <work> <changed as JSON> <most> -- <mutmut's arguments>: load; write names_path with within()'s answer;
    # run mutmut with the names appended only when there are some and within() holds, else no run and no reach record;
    # write reach_path from the process that started the run, however it ends short of a kill
```

Run as a script, it calls `main(sys.argv[1:])`. The gate builds mutmut's arguments and hands the bound, so `--max-children` and `MOST_MUTANTS` stand in the Command a FakeRunner records (decisions 1, 30), and the driver only appends the names. It replaces G4's `mutation_driver.py`, whose `probe` and `check` programs become one, the bound compared between generation and checking (decision 1), and the mutmut imports of G4's runner and judge (decision 2).

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
| The run's work bound | `check_mutation.MOST_MUTANTS`, handed to the driver in the Command's argv; compared once, by `mutmut_driver.within`; its line once, `check_mutation.over_bound` (decisions 1, 5, 6) | A timeout on the driver Command, or any time cap on the run; a second comparison of a mutant count with the bound; a `time` read, or time left computed, in the gate (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:163`) |
| Each mutant's hang limit | pytest-timeout's `timeout = 30` (`pyproject.toml:55`) under mutmut's default time limit, whose keys are findings (`gates/check_mutation.py:36`) (decision 1) | A per-mutant or per-test limit set in the gate or the driver |
| A capped checker's lines | `report.time_cap` and `report.timed_out`, for a Command with a timeout (decision 29); the mutation gate has none (decision 1) | `WALL_CLOCK_SECONDS`, `AT_THE_CAP` or any other wording of a cap in the mutation gate |
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

1. The gates core design names `python_script` in `checker.py`'s block (`docs/superpowers/specs/2026-10-20-gates-core-design.md:57`), and its mutmut bullet (`:224`–`:232`), decision 29's sentences on the mutation gate (`:413`) and its C7a-c row (`:320`) point here for C7b's interface and its work bound. The quality gates spec bounds the mutation run's work, not its time (decision 1): its wall-clock bullet (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:89`) gives way to the bound and its verdict as decisions 5 and 6 set them, the cap goes from the unfinished-run bullet (`:91`) and from the time-cap rule's exception (`:29`), and the closed set of a gate's own lines (`:30`) holds the bound's line. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/2026-10-20-gates-core-design.md`, `docs/superpowers/specs/2026-10-17-quality-gates-design.md`.
2. `dependency`: mutmut in the dev group, locked at the version decision 30 names. Agent: `gatesmith`, no red test. Paths: `pyproject.toml`, `uv.lock`.
3. Measure, on this tree, the mutants mutmut generates per changed function and the time one takes to check at the worker cap, for decision 5's number, and whether pytest-timeout's 30 seconds ends a hung test inside mutmut's run in a copy (decision 1). Its findings go to the owner before step 4; a hang limit that does not hold comes back to the owner. Agent: `spiker`, scratchpad only. Paths: none in the tree.
4. `stub`: `python_script`; `gates/mutmut_driver.py`, `within` among it; `MOST_MUTANTS` at decision 5's number, `Plan`, `mutmut_command`, `over_bound`, `judge`, `suite_lines`, `run_mutmut`, `Mutated` with `unfinished`, and `outcome`, each body raising `NotImplementedError`. Agent: `gatesmith`, no red test. Paths: `gates/core/checker.py`, `gates/mutmut_driver.py`, `gates/check_mutation.py`.
5. Red tests for `outcome` over `unfinished`, with no note (decision 1). Agent: `test-writer`. Paths: `tests/test_check_mutation_core.py`.
6. `outcome` and `check` on the new `Mutated`; `WALL_CLOCK_SECONDS` and `AT_THE_CAP` go. Agent: `gatesmith`, red test from step 5. Paths: `gates/check_mutation.py`.
7. `moved`: `test_at_the_cap` (`tests/test_check_mutation_core.py:215`) goes, its cap one the gate does not have (decision 1), and `test_unfinished` (`:234`) moves onto `Mutated.unfinished`; the docstring of `tests/test_core_report_cap.py` (`:8`) stops citing the mutation gate's call of `time_cap`, its cases (`:19`, `:33`, `:47`, `:51`) unchanged. Agent: `test-writer`. Paths: `tests/test_check_mutation_core.py`, `tests/test_core_report_cap.py`.
8. Red tests for `python_script`. Agent: `test-writer`. Paths: `tests/test_core_checker_python_script.py`.
9. `python_script`. Agent: `gatesmith`, red test from step 8. Paths: `gates/core/checker.py`.
10. Measure whether `MUTMUT`'s `load`, `run` and `reach` can run in a test's own process (decision 4). Agent: `spiker`, scratchpad only. Paths: none in the tree.
11. Red tests for the driver on a fake `Mutmut`, `within` among it, and for `MUTMUT` as step 10 finds. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
12. The driver. Agent: `gatesmith`, red test from step 11. Paths: `gates/mutmut_driver.py`.
13. Red tests for `mutmut_command`, `over_bound`, `judge`, `suite_lines` and `run_mutmut` through `FakeRunner`. Agent: `test-writer`. Paths: `tests/test_check_mutation_run.py`.
14. `mutmut_command`, `over_bound`, `judge`, `suite_lines` and `run_mutmut`. Agent: `gatesmith`, red test from step 13. Paths: `gates/check_mutation.py`.

`mutate` keeps raising after step 14; C7c builds the `Plan` and calls `run_mutmut` from it.

## Decisions for the owner

2. **Where is mutmut's Python API imported?** I recommend the driver alone, handing the gate mutmut's status table and each mutant's diff as JSON. Cost: the driver makes the diff of every generated mutant, killed ones included, before any is checked; the time that takes is unmeasured. The alternative lets the gate import mutmut's status table and diff function in its own process, as G4's judge does (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_judge.py:8`–`:10`). Cost: two homes of mutmut's API; whether importing those modules in the gate's process reads mutmut's settings from the gate's working directory is unmeasured.
3. **Where do the failing test ids come from after a nonzero exit?** I recommend running the suite on the unmutated tree through `check_pytest.check`, as G4 does through the pytest gate (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_judge.py:97`). Cost: a second suite run, bounded per test by pytest-timeout (`pyproject.toml:55`) and by no cap on the whole (decision 1); its time is unmeasured. The alternative prints mutmut's whole output alone. Cost: whether that output names the failing tests is unmeasured, and the spec asks for the ids (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:91`).
4. **How do the driver's own lines run in a test's own process?** I recommend handing mutmut's entry points in as `Mutmut`, testing the driver's logic in-process on a fake, and measuring first (step 10) whether `MUTMUT`'s `load`, `run` and `reach` can run in a test's process, its red tests following what that finds. Cost: one spike, and an adapter whose calls the spike may find cannot all run in-process, which comes back to the owner. The alternative drives mutmut's console command, with no own code in the child. Cost: no reach record, which G4 reads to tell a mutant no test reaches from a failed run (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_judge.py:52`), and the filter to changed functions has no home in the child; the console output's fitness is unmeasured.
5. **What measure, and what number, bounds the work?** I recommend a count of the mutants the changed functions yield across every file, `MOST_MUTANTS`, its number set by the owner from step 3's measure of this tree before step 4. Cost: one spike; a mutant's check time varies with the tests that reach it, so the count bounds time only as closely as that measure shows. The alternative counts changed functions, known from the diff before any process runs. Cost: functions yield different numbers of mutants, so it bounds the work more loosely, by an unmeasured margin. Under either, a commit above the bound cannot pass until it is split, every function of a new file counting as changed (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:81`).
6. **What does a run over the bound give?** I recommend exit 2, a run the checker did not finish: `over_bound`'s one line naming the mutant count and the bound, first, before the key findings, with no mutant checked, the line joining the closed set of a gate's own lines (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:30`). Cost: that spec change, in step 1. The alternative is exit 1 with one finding naming the count and the bound. Cost: a finding reads as a defect in the code where the cause is the commit's size, and `Mutated` gains a field for it, since `unfinished` prints only Unfinished lines. Under either, the same commit cannot pass until it is split.

## Decisions taken

Each entry gives the question in bold, the owner's ruling verbatim, `Adds:` each module, home and step the ruling adds, and `Written in:` each section it touches.

1. **One process or two under the 600-second cap?** Ruling: "No, that's not okay. That makes me question the 10-minute cap. I think that's appropriate in a lot of cases to prevent overruns, but in this case, I think we're basically patching on top of a patch. We're not addressing the problem correctly. We're doing a workaround to fit our own rules, which, you know, I made those rules. I'm happy to bend them if that's not the optimal way forward." Then, asked "Should I send that to the architect, to drop the ten-minute cap from the mutation gate and bound the work instead of the time: only the changed functions get mutated, each mutant's test run keeps its per-test hang limit, and if that's still too much work the gate says so up front instead of timing out halfway?", the owner said: "Yes, let's do that." Adds: `MOST_MUTANTS` and `over_bound` in `gates/check_mutation.py`, `within` and `names_report`'s `ahead` in `gates/mutmut_driver.py`; the homes "The run's work bound", "Each mutant's hang limit" and "A capped checker's lines"; the quality gates spec in step 1, step 3's spike, `tests/test_core_report_cap.py` in step 7, and the bound in steps 4, 11, 13 and 14; decisions 5 and 6. Written in: **Why**, **Modules**, **Homes**, **Order**, **Decisions for the owner**.
