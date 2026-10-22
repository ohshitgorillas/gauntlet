Status: approved by the owner.

## Why

C7b is the mutation gate's process step: "processes and throttle" (`docs/superpowers/specs/2026-10-20-gates-core-design.md:338`). The gates core design gives it the worker cap of decision 30 (`:248`, `:432`) and the suite of decision 28 (`:243`, `:430`), and points here for the function that runs mutmut, its Command and the run's verdicts (`:247`, `:250`, `:431`). The gate has no wall-clock cap (decision 1) and no cap on the mutants a run checks (decision 9): it mutates only the changed functions and checks every mutant they yield, its scope alone drawing the line on its work (decision 11). The gate holds the gap as a body that only raises (`gates/check_mutation.py:91`–`:100`). This design names the function that runs mutmut and what it hands back, so C7b, and C7c, which builds that function's input, are built against it.

The tree, and the G4 branch the gate is ported from (`.claude/worktrees/agent-a3292c4f570aba00b/`), hold 22 copies of what the core already owns, of what this design gives one home, or of a cap the gate does not have:

- **A cap on the mutants a run checks, which the gate does not have, 8 copies.** The quality gates spec words it in the closed set of a gate's own lines, the mutation run bullet and the unfinished-run bullet (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:30`, `:89`, `:91`), and the gates core design in its mutmut bullet, its C7a-c row and decisions 29 and 30 (`docs/superpowers/specs/2026-10-20-gates-core-design.md:247`, `:250`, `:338`, `:431`, `:432`), each wording that cap or pointing here for it (decision 9).
- **A wall-clock cap the gate does not have, 3 copies.** `AT_THE_CAP` (`gates/check_mutation.py:18`), on `WALL_CLOCK_SECONDS` (`:15`), words a 600-second cap the gate does not have (decision 1), and a test pins the cap it names (`tests/test_check_mutation_core.py:246`, `:257`). G4 words it twice more (`.claude/worktrees/agent-a3292c4f570aba00b/gates/check_mutation.py:96`, `.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:40`).
- **A result shaped for the cap.** `Mutated.at_cap` flags a cap the gate does not have, and `Mutated.error` is one string (`gates/check_mutation.py:82`, `:83`), which holds the checker's error and the suite's lines only by joining them into one Unfinished.
- **Process running in G4, 5 copies.** A worker count from `os.sched_getaffinity` (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:24`) beside `cpu_budget` (`gates/core/checker.py:381`); a `nice`/`ionice` line (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:19`) beside `throttle_line` (`gates/core/checker.py:357`); a group kill (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:57`) and a `subprocess.run` and a `Popen` (`:38`, `:68`) beside `run` (`gates/core/checker.py:66`).
- **Real time in G4, 2 copies.** The gate reads `time.monotonic` (`.claude/worktrees/agent-a3292c4f570aba00b/gates/check_mutation.py:48`) and hands each of its two mutmut processes the time left (`:81`, `:91`). Real time in `gates/` has one home, and a timeout a module computes for itself is forbidden (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:215`).
- **mutmut's API in 3 modules of G4, 3 copies.** The driver (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_driver.py:19`, `:35`, `:42`, `:58`), the runner (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:10`) and the judge (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_judge.py:8`–`:10`) each import it.
- **An interpreter command line by hand in G4, 1 copy.** `driver` builds `sys.executable` with `-P` itself (`.claude/worktrees/agent-a3292c4f570aba00b/gates/mutation_run.py:29`–`:31`). The core's one builder, `python_module` (`gates/core/checker.py:342`), gives only the `-m` form, which puts the working directory, the copy mutmut works in, on `sys.path`.

mutmut is not in the dev group (`pyproject.toml:14`–`:22`), and `uv.lock` locks no mutmut; step 2 adds it at 3.8.0, the version decision 30 names.

mutmut runs the tests from inside the copy's `mutants/` (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:92`, `docs/superpowers/specs/2026-10-21-mutation-plan-design.md:57`), and nothing the gate sets puts that directory on `sys.path`: the driver's interpreter runs under `-P` (`python_script`, **Modules**), and the tree's config sets no pytest `pythonpath` (`pyproject.toml:51`–`:55`). The pytest gate's run imports own code from the project root only as the working directory of `python -m pytest` (`gates/check_pytest.py:154`, `:165`), and a test's child that imports the gates core takes the root on `PYTHONPATH` (`tests/test_core_runner.py:71`, `:914`). mutmut 3.8.0, run in such a copy, collects `tests/` inside `mutants/` and cannot import `gates` (`docs/superpowers/audits/2026-10-21-mutmut-step3-finding.md:5`). This design gives the copy's import path one setting, pytest's `pythonpath` (decisions 12, 14).

## Modules

### `gates/check_mutation.py`: the mutmut run, its command and its verdict

Its job is to run mutmut once over a plan through the run's process runner and hand back `Mutated`, the value `outcome` takes. `run_mutmut` is the function that runs the mutation tool. C7c's `mutate` builds the `Plan` from the copy, git and parse steps and calls `run_mutmut`; it starts no process of its own.

```python
DRIVER: Path = Path(__file__).with_name("mutmut_driver.py")

@dataclass(frozen=True)
class Plan:  # what the copy, git and parse steps (C7c) hand the mutmut run
    settings: Path                         # the directory of the pyproject.toml mutmut reads, in the run's scratch;
                                           # its pytest_add_cli_args carry "-o", f"pythonpath={work / 'mutants'}" (decision 12)
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
    # python_script(DRIVER, plan.settings, plan.work, <plan.changed as JSON>, "--", "run", "--max-children", str(workers),
    #               cwd=plan.work), with no timeout (decision 1), throttled=True,
    #               env=environment(drop_prefixes=(PYTEST_ENVIRONMENT,)), and outputs NAMES, REACH and one meta_key per changed file
def judge(plan: Plan, command: Command, completed: Completed, suite: Callable[[], tuple[Unfinished, ...]]) -> Mutated
    # reads only the Completed; calls suite only after a nonzero exit
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

The run has no time cap (decision 1) and no cap on the mutants it checks (decision 9). Only the changed functions are mutated (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:80`), every function of a new file counting as changed (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:81`), and every mutant they yield is checked, however many. That scope alone draws the line on a run's work: no filter narrows it below the changed functions, and nothing in the gate weighs how much a commit changes, which is the reviewer's question (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:14`) (decision 11). How long a run over many changed functions takes on this host is unmeasured. Each mutant's test run keeps its hang limit: pytest-timeout's 30 seconds per test (`pyproject.toml:55`) under mutmut's own default time limit, a key that changes it being a finding (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:85`, `gates/check_mutation.py:36`). Whether a mutant whose test never returns is a finding under these two limits, and not a mutant killed, is unmeasured; step 3 measures it (decisions 7, 8).

mutmut runs the tests from inside `plan.work`'s `mutants/`, so the `[tool.mutmut]` `pytest_add_cli_args` of `plan.settings` carry `-o` and `pythonpath=<plan.work>/mutants`, the path absolute, after the arguments `settings_arguments` gives (decisions 12, 14). pytest documents its `pythonpath` as putting its entries at the head of `sys.path` for each run it makes, so every pytest run mutmut makes, its stats run, its run on the unmutated copy and each mutant's, in the driver's process or in a test's (decision 4), imports `gates` and `tests` from the copy, as the pytest gate's run imports them from the project root (`gates/check_pytest.py:154`, `:165`). The setting rides on mutmut's own settings file, which the mutation plan design's `settings_text` writes (`docs/superpowers/specs/2026-10-21-mutation-plan-design.md:74`–`:75`), its `lay_out` handing it the pair after the arguments `settings_arguments` gives (`:142`), as that design's architect `rulings` pass on the owner's `new:` ruling writes it, before its step 13 (`:190`) (decision 13), and it replaces any `pythonpath` the project's config sets, which this tree's sets none of (`pyproject.toml:51`–`:55`) (decision 14). Whether pytest 9.1.1 (`uv.lock:425`–`:426`) puts the entry first under `-o`, whether mutmut 3.8.0 hands these arguments to each of its pytest runs, and whether under them its stats run collects the given tests in the copy and imports `gates` there, are unmeasured; steps 3 and 5 run under this setting.

`judge` reads the driver's outputs from the Completed: `NAMES`, the generated mutants with their diffs and mutmut's status table; `REACH`, tests collected and functions reached; and each file's `.meta` report under its `meta_key`, read through the status table. A mutant mutmut killed gives nothing. Each other mutant is a `Mutant`: the `given` of its file's Source, mutmut's name, its status, and the driver's diff, which `render` puts on one line.

- **`NAMES` absent or unreadable.** `unfinished=(Unfinished(completed.output()),)`.
- **Exit 0.** Each mutant takes its status; any mutant left unchecked puts `Unfinished(completed.output())` first.
- **Nonzero exit.** `judge` calls `suite`. When the suite passed and `REACH` shows tests collected and no function reached, each unchecked mutant has mutmut's `NO_TESTS` status and the run is finished. Otherwise the run is unfinished: `Unfinished(completed.output())`, then the suite's lines, then the findings (quality gates spec, `docs/superpowers/specs/2026-10-17-quality-gates-design.md:91`).

It replaces the raising body of `mutate` as the process step (`gates/check_mutation.py:91`–`:100`), `WALL_CLOCK_SECONDS` and `AT_THE_CAP` (`:15`, `:18`), and `Mutated.at_cap` and `.error` (`:82`, `:83`); `check`'s catch gives `Mutated(unfinished=(Unfinished(error.report),))` (`:131`–`:132`). It also replaces G4's `mutation_run.py` and `mutation_judge.py`, and G4's remaining-time reads (`.claude/worktrees/agent-a3292c4f570aba00b/gates/check_mutation.py:48`, `:81`, `:91`).

### `gates/mutmut_driver.py`: the child mutmut runs in

Its job is to be the one module that imports mutmut. In an interpreter of its own it generates the mutants of the changed functions, writes their names and diffs with mutmut's status table, runs mutmut over every one of them, and writes the reach record. Every own line also runs in a test's own process, as the core's child rule asks (`docs/superpowers/specs/2026-10-20-gates-core-design.md:200`, decision 4). What each of `MUTMUT`'s entry points does in a test's process is the owner's ruling on steps 4 to 6's findings, which step 7 writes into this block before any stub; a red test of `MUTMUT` takes its expected values from that, never from a spiker's report (decision 8).

```python
NAMES: str = "names"       # the Completed.outputs key of the generated mutants
REACH: str = "reach"       # the Completed.outputs key of the reach record
KILLED: str                # mutmut's status names in the pinned version, which judge reads: the strings the status table
UNCHECKED: frozenset[str]  # of the mutmut step 2 locks gives for a killed mutant, for each unchecked one, and for one no
NO_TESTS: str              # test reaches, written by step 16 (decision 8)
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
    # each file's mutants whose function is changed, in mutmut's order, every one of them (decision 9)
def names_report(mutants: Mapping[str, Sequence[tuple[str, str]]], statuses: Mapping[int | None, str]) -> str  # JSON
def reach_report(collected: int, reached: int) -> str  # JSON
def main(arguments: Sequence[str], mutmut: Mutmut = MUTMUT) -> None
    # <settings> <work> <changed as JSON> -- <mutmut's arguments>: load; write names_path;
    # run mutmut with the names appended only when there are some, else no run and no reach record;
    # write reach_path from the process that started the run, however it ends short of a kill
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
| The run's work | `mutmut_driver.changed_mutants`, the mutants of the changed functions and every one of them, run by the driver's one mutmut run, whose Command has no timeout, the scope alone drawing the line on the run's work (decisions 1, 9, 11) | A cap on the number of mutants, functions or files a run checks, or any count that stops a run short of every mutant of its changed functions (decision 9); a filter that drops a mutant of a changed function, as one on a line `git diff HEAD` leaves unchanged, and a gate line or verdict on how much a commit changes (decision 11); a timeout on the driver Command, or any time cap on the run; a `time` read, or time left computed, in the gate (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:215`) |
| Each mutant's hang limit | pytest-timeout's `timeout = 30` (`pyproject.toml:55`) under mutmut's default time limit, whose keys are findings (`gates/check_mutation.py:36`) (decision 1); a hung mutant's verdict is step 3's finding as step 7 writes it here (decision 8) | A per-mutant or per-test limit set in the gate or the driver; a red test whose verdict a time limit decides, as a test of `MUTMUT.run` whose seeded tests do not return at once (decision 8) |
| A measured finding | This file, written by an architect `rulings` pass recording the owner's ruling on it: steps 3 to 6's findings by step 7 (decision 8) | An expected value, constant or number in a brief or a test taken from a spiker's report rather than from `docs/`; a builder or test step dispatched before the pass that writes the finding it rests on |
| A capped checker's lines | `report.time_cap` and `report.timed_out`, for a Command with a timeout (decision 29); the mutation gate has none (decision 1) | `WALL_CLOCK_SECONDS`, `AT_THE_CAP` or any other wording of a cap in the mutation gate |
| Throttling | `Command.throttled=True`, through `checker.throttle_line` | `nice` or `ionice` in an argv |
| Workers | `run_mutmut`'s `budget`, `cpu_budget` by default, as `--max-children` in the Command's argv (decision 30) | An affinity or CPU read in the gate; a row for a key mutmut never reads |
| Timeout, group kill and output files | `checker.run`, through `run.process` | `subprocess`, `os.killpg` and reading the copy after the run in the gate |
| The copy's import path in mutmut's pytest runs | pytest's `pythonpath`, `-o pythonpath=<work>/mutants`, among the `pytest_add_cli_args` of the settings file `Plan.settings` holds, which `mutmut_driver.settings_text` writes (`docs/superpowers/specs/2026-10-21-mutation-plan-design.md:74`, `:162`) (decisions 12, 13, 14) | `PYTHONPATH` in the driver Command's env; a `sys.path` edit in the gate or the driver; a `pythonpath` key written into the copy's `pyproject.toml`; a `conftest.py` written into the copy; `-P` dropped from the driver's command line |
| pytest's environment | `check_pytest.PYTEST_ENVIRONMENT` (`gates/check_pytest.py:19`) through `checker.environment` | A second `"PYTEST_"` literal |
| The suite on the unmutated tree | `check_pytest.check` (`gates/check_pytest.py:205`), through `suite_lines` (decision 3) | A pytest command line built in the mutation gate |
| Where the driver and mutmut write | `mutmut_driver`'s `names_path`, `reach_path`, `meta_path` and their keys | A file name or output key spelled in the gate |
| mutmut's status names | `mutmut_driver`'s `KILLED`, `UNCHECKED`, `NO_TESTS`, their strings those the locked mutmut's status table gives, written once by step 16 (decision 8), and the table `statuses` gives | A status name of mutmut's spelled in the gate |
| A fake runner in tests | `tests/support/fake.py` `FakeRunner` and `completed` (`tests/support/fake.py:16`, `:32`) | A test's own Runner; a real mutmut run where a reply proves the branch |

A builder that needs what these homes lack stops and reports it, and writes no copy.

## Order

Each step lands green under `make check` before the next starts, save a `stub` step, which lands with its red tests in the commit of the build that turns them green (`docs/superpowers/specs/2026-10-18-agents-design.md:64`). Each stub step is paired with the one build step that turns all its red tests green, and adds names to a module without changing a line already in it. A stub step writes each declaration **Modules** gives, a constant at the value given there, a dataclass's fields, a Protocol's signatures, and each function body raising `NotImplementedError` and nothing else. A red step holds one behavior (`docs/superpowers/specs/2026-10-18-agents-design.md:61`). A spike step asks one claim with a yes-or-no reading (decision 7), and its finding reaches a builder or a test only once the owner rules on it and an architect `rulings` pass writes it here, by step 7 (decision 8).

1. The gates core design names `python_script` in `checker.py`'s block (`docs/superpowers/specs/2026-10-20-gates-core-design.md:73`), and its mutmut bullet (`:242`–`:250`), the sentences of decisions 29 and 30 on the mutation gate (`:431`, `:432`) and its C7a-c row (`:338`) point here for C7b's interface, and each gives the mutation run no time cap and no cap on the mutants it checks (decisions 1, 9). The quality gates spec bounds the mutation run's work by its scope alone: its mutation run bullet (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:89`) gives the run no wall-clock cap and no cap on the mutants it checks, every mutant of the changed functions checked and each keeping its hang limit, the scope alone drawing the line on the run's work (decisions 1, 9, 11); the unfinished-run bullet (`:91`) names no run over a bound; the time-cap rule (`:29`) gives the mutation run no cap; and the closed set of a gate's own lines (`:30`) holds no line of the mutation gate's. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/2026-10-20-gates-core-design.md`, `docs/superpowers/specs/2026-10-17-quality-gates-design.md`.
2. `dependency`: mutmut in the dev group, locked at the version decision 30 names. Agent: `gatesmith`, no red test. Paths: `pyproject.toml`, `uv.lock`.
3. Claim: a mutant that makes a seeded test loop forever, that test's unmutated run returning at once, gets from mutmut 3.8.0, in a copy laid out as the mutation plan design's `lay_out` lays it out (`docs/superpowers/specs/2026-10-21-mutation-plan-design.md:141`–`:142`), its settings file's `pytest_add_cli_args` carrying `-o pythonpath=<work>/mutants` (decision 12), under `timeout = 30` (`pyproject.toml:55`) and mutmut's default time limit, a status other than killed, so it is a finding (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:85`, decision 1). A no comes back to the owner through step 7, and so does a run that checks no mutant under that setting. Agent: `spiker`, scratchpad only, one claim (decision 7). Paths: none in the tree.
4. Claim: mutmut 3.8.0, called in the calling process, reads the settings of one directory's `pyproject.toml` and works in a second directory, starting no process, as `Mutmut.load` asks (decision 4). Agent: `spiker`, scratchpad only, one claim (decision 7). Paths: none in the tree.
5. Claim: mutmut 3.8.0's run command, called in the calling process over named mutants in a copy laid out and set as step 3's (decision 12), returns to its caller once they are checked, as `Mutmut.run` asks (decision 4). Agent: `spiker`, scratchpad only, one claim (decision 7). Paths: none in the tree.
6. Claim: after such a run, mutmut 3.8.0's record, read in the calling process, gives the tests collected and the functions a test reaches, as `Mutmut.reach` asks (decision 4). Agent: `spiker`, scratchpad only, one claim (decision 7). Paths: none in the tree.
7. The owner's rulings on steps 3 to 6's findings are written here: the hung mutant's verdict under "Each mutant's hang limit", and what each of `MUTMUT`'s entry points does in a test's process in the driver's block; an entry point that cannot run there comes back to the owner before step 16 (decisions 4, 8). Agent: `architect`, a `rulings` pass. Paths: `docs/superpowers/specs/2026-10-21-mutmut-run-design.md`.
8. `moved`: `lines:` `docs/superpowers/specs/2026-10-17-quality-gates-design.md:89` and `docs/superpowers/specs/2026-10-20-gates-core-design.md:431`, each quoted as it stood before step 1, holding the 600-second cap and the mutation gate's `time_cap(argv[0], 600)`, and as it stands. `test_at_the_cap` (`tests/test_check_mutation_core.py:246`) and its `AT_THE_CAP` mutant (`:96`) go, the module docstring's sentence on the cap (`:11`–`:13`) with them, and the docstring of `tests/test_core_report_cap.py` (`:8`) stops citing the mutation gate's call of `time_cap`, its cases (`:19`, `:33`, `:47`, `:51`) unchanged. It lands before step 12 removes what the test reads. Agent: `test-writer`. Paths: `tests/test_check_mutation_core.py`, `tests/test_core_report_cap.py`.
9. `port`: `design:` this file, step 9. `test_unfinished` (`tests/test_check_mutation_core.py:269`) is reported `UNMOVED`, the production change it needs `outcome` reading `Mutated.unfinished`; no test is written. Agent: `test-writer`. Paths: `tests/test_check_mutation_core.py`.
10. `stub`: `Mutated.unfinished`, beside the fields step 12 removes. Agent: `gatesmith`, no red test. Paths: `gates/check_mutation.py`.
11. Red test: `outcome` over `unfinished`, its lines first, then every finding, exit 2, with no note (decision 1); `replaces:` `test_unfinished`, as step 9 reports it. Agent: `test-writer`. Paths: `tests/test_check_mutation_core.py`.
12. `outcome` and `check` on `Mutated.unfinished`; `WALL_CLOCK_SECONDS`, `AT_THE_CAP`, `Mutated.at_cap` and `Mutated.error` go. Lands with steps 10 and 11. Agent: `gatesmith`, red test from step 11. Paths: `gates/check_mutation.py`.
13. `stub`: `python_script`. Agent: `gatesmith`, no red test. Paths: `gates/core/checker.py`.
14. Red test: `python_script`. Agent: `test-writer`. Paths: `tests/test_core_checker_python_script.py`.
15. `python_script`. Lands with steps 13 and 14. Agent: `gatesmith`, red test from step 14. Paths: `gates/core/checker.py`.
16. `stub`: `gates/mutmut_driver.py`, its constants at the values **Modules** gives, `KILLED`, `UNCHECKED` and `NO_TESTS` the strings the status table of the mutmut step 2 locks gives; the `Mutmut` Protocol; `MUTMUT`, whose entry points raise; every function. Agent: `gatesmith`, no red test. Paths: `gates/mutmut_driver.py`.
17. Red test: `changed_mutants`. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
18. Red test: `names_report`. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
19. Red test: `reach_report`. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
20. Red test: `main`, on a fake `Mutmut`. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
21. Red test: `MUTMUT.load`, as step 7 writes it. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
22. Red test: `MUTMUT.mutants`. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
23. Red test: `MUTMUT.statuses`. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
24. Red test: `MUTMUT.run`, as step 7 writes it, its seeded tests returning at once so an assertion, not a time limit, decides each mutant. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
25. Red test: `MUTMUT.reach`, as step 7 writes it. Agent: `test-writer`. Paths: `tests/test_mutmut_driver.py`.
26. The driver. Lands with steps 16 to 25. Agent: `gatesmith`, red tests from steps 17 to 25. Paths: `gates/mutmut_driver.py`.
27. `stub`: `DRIVER`, `Plan`, `mutmut_command`, `judge`, `suite_lines` and `run_mutmut`. Agent: `gatesmith`, no red test. Paths: `gates/check_mutation.py`.
28. Red test: `mutmut_command`, through `FakeRunner`. Agent: `test-writer`. Paths: `tests/test_check_mutation_run.py`.
29. Red test: `judge` with `NAMES` absent or unreadable. Agent: `test-writer`. Paths: `tests/test_check_mutation_run.py`.
30. Red test: `judge` on exit 0. Agent: `test-writer`. Paths: `tests/test_check_mutation_run.py`.
31. Red test: `judge` on a nonzero exit. Agent: `test-writer`. Paths: `tests/test_check_mutation_run.py`.
32. Red test: `suite_lines`. Agent: `test-writer`. Paths: `tests/test_check_mutation_run.py`.
33. Red test: `run_mutmut`, through `FakeRunner`. Agent: `test-writer`. Paths: `tests/test_check_mutation_run.py`.
34. `mutmut_command`, `judge`, `suite_lines` and `run_mutmut`. Lands with steps 27 to 33. Agent: `gatesmith`, red tests from steps 28 to 33. Paths: `gates/check_mutation.py`.

`mutate` keeps raising after step 34; C7c builds the `Plan` and calls `run_mutmut` from it.

The setting of decision 12 reaches the mutation plan design through the owner's `new:` ruling on `docs/superpowers/specs/2026-10-21-mutation-plan-design.md` and that file's architect `rulings` pass, which makes `lay_out` hand `settings_text` the pair `-o`, `pythonpath=<work>/mutants` after the arguments `settings_arguments` gives (`:142`). That pass lands before that design's driver stub, its step 13 (`:190`), and no step here writes that file (decision 13).

## Decisions taken

Each entry gives the question, or for a `new:` ruling a name for the structure, in bold, the owner's ruling verbatim, `Adds:` each module, home and step the ruling adds, and `Written in:` each section it touches.

1. **One process or two under the 600-second cap?** Ruling: "No, that's not okay. That makes me question the 10-minute cap. I think that's appropriate in a lot of cases to prevent overruns, but in this case, I think we're basically patching on top of a patch. We're not addressing the problem correctly. We're doing a workaround to fit our own rules, which, you know, I made those rules. I'm happy to bend them if that's not the optimal way forward." Then, asked "Should I send that to the architect, to drop the ten-minute cap from the mutation gate and bound the work instead of the time: only the changed functions get mutated, each mutant's test run keeps its per-test hang limit, and if that's still too much work the gate says so up front instead of timing out halfway?", the owner said: "Yes, let's do that." Adds: the driver Command in `gates/check_mutation.py` with no timeout, and no `time` read in the gate; the homes "The run's work", "Each mutant's hang limit" and "A capped checker's lines"; the quality gates spec in step 1, step 3's spike, and `tests/test_core_report_cap.py` in step 8. Written in: **Why**, **Modules**, **Homes**, **Order**. Replaced by 9.
2. **Where is mutmut's Python API imported?** Ruling: The owner's standing ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." Void agrees with this recommendation, so it is taken. Adds: `MUTMUT` and `Mutmut` in `gates/mutmut_driver.py` as the only mutmut imports in `gates/`, and `names_report` carrying mutmut's status table and each generated mutant's diff as JSON, which `judge` reads; the homes "mutmut's Python API", "mutmut's status names" and "Where the driver and mutmut write"; the driver in steps 16 to 26. Written in: **Modules**, **Homes**, **Order**.
3. **Where do the failing test ids come from after a nonzero exit?** Ruling: The owner's standing ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." Void agrees with this recommendation, so it is taken. Adds: `suite_lines` in `gates/check_mutation.py` and `judge`'s `suite` parameter, the suite run through `check_pytest.check` with no cap on the whole; the home "The suite on the unmutated tree"; `suite_lines` in steps 27, 32 and 34. Written in: **Modules**, **Homes**, **Order**.
4. **How do the driver's own lines run in a test's own process?** Ruling: The owner's standing ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." Void agrees with this recommendation, so it is taken. Adds: `Mutmut` and `main`'s `mutmut` parameter in `gates/mutmut_driver.py`; an entry point that cannot run in a test's process coming back to the owner before step 16, and step 20's red test of `main` on a fake `Mutmut`. Written in: **Modules**, **Order**. Replaced by 8.
5. **What measure, and what number, bounds the work?** Ruling: The owner's standing ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." Void agrees with this recommendation, so it is taken. Adds: none. Written in: none. Replaced by 8. Replaced by 9.
6. **What does a run over the bound give?** Ruling: The owner's standing ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." Void agrees with this recommendation, so it is taken. Adds: none. Written in: none. Replaced by 9.
7. **One measurement question per spike step.** Ruling: The owner's standing ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." Asked under it, Void and the architect's own agent rules agree: spiker (.claude/agents/spiker.md at 16a2af3) answers one measurement question per step and refuses a step holding two with OVERLOADED, so step 3, which asks for the mutants per changed function, the time one takes to check, and whether pytest-timeout ends a hung test inside mutmut, is cut into one step per question. Adds: one `spiker` claim per spike step, steps 3 to 6; no module and no home. Written in: **Modules**, **Order**, **Decisions taken**. Replaced by 8.
8. **The audit's gaps 3 to 16 closed in Order.** Ruling: "Yes, fix the mutation testing gaps, please (the gaps: /Users/atom/dev/gauntlet/.gauntlet/jobs/C7b-audit/gaps.md, gaps 3-16)" Adds: `DRIVER`'s value in `gates/check_mutation.py`, and in `gates/mutmut_driver.py` the values of `NAMES` and `REACH`, the source of `KILLED`, `UNCHECKED` and `NO_TESTS`, and `MUTMUT`'s entry points as step 7 writes them; the home "A measured finding", and a red test no time limit decides and the status names' strings in the homes "Each mutant's hang limit" and "mutmut's status names"; step 7, an architect `rulings` pass writing here the owner's rulings on spike findings; steps 3 to 6, each one claim with a yes-or-no reading, step 3 asking whether a hung mutant is a finding, steps 4 to 6 asking of mutmut's own `load`, `run` and `reach` in a calling process; step 8's `moved` with its document lines, before the build that removes what its test reads, and step 9's `port`; stubs at steps 10, 13, 16 and 27, each adding to a module without changing its lines and landing with its one build at step 12, 15, 26 or 34; red steps 11, 14, 17 to 25 and 28 to 33, one behavior each. Written in: **Modules**, **Homes**, **Order**, **Decisions taken**. Replaced by 9. Replaced by 10.
9. **What number does step 4 hold the tree's files to?** Ruling: "Um, well, no, I don't like the idea of arbitrarily capping the mutant testing. I think we should find another way to draw that line" Adds: no cap on the mutants a run checks, `changed_mutants` handing the driver's one mutmut run every mutant of the changed functions, with no bound in `mutmut_command`'s argv, `names_report` or `main`; the home "The run's work", which forbids any count that stops a run short of every mutant; step 1's spec lines giving the run no cap on its mutants (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:30`, `:89`, `:91`; `docs/superpowers/specs/2026-10-20-gates-core-design.md:247`, `:250`, `:338`, `:431`, `:432`); decision 11. Written in: **Why**, **Modules**, **Homes**, **Order**, **Decisions for the owner**, **Decisions taken**.
10. **Does step 5's time measure stay?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." Under it the recommendation is taken, the brief bringing no conflict: no spike measures how long a run takes. Adds: none. Written in: **Order**, **Decisions for the owner**, **Decisions taken**.
11. **What draws the line on a run's work, with no number capping it?** Ruling: "I see the first way" The first way the decision gave is its recommendation, the scope alone, so it is taken. Adds: the scope alone, the changed functions, drawing the line on a run's work, every mutant they yield checked, and how much a commit changes left to the reviewer (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:14`); in the home "The run's work", a filter that drops a mutant of a changed function, and a gate line or verdict on how much a commit changes, forbidden; step 1's quality gates spec bullet bounding the run's work by its scope alone under this decision; no module and no new step. Written in: **Why**, **Modules**, **Homes**, **Order**, **Decisions for the owner**, **Decisions taken**.
12. **The settings that let mutmut collect the tests from inside `mutants/`.** Ruling: "in the mutmut run design, choose the settings that let mutmut collect the tests from inside `mutants/`" Adds: in `gates/check_mutation.py`, `Plan.settings` whose `pytest_add_cli_args` carry pytest's `pythonpath` set to the copy's `mutants/`, `-o pythonpath=<work>/mutants`, written by the mutation plan design's `settings_text` under decision 13, the choice over the driver Command's `PYTHONPATH` open as decision 14; the home "The copy's import path in mutmut's pytest runs"; steps 3 and 5 run in a copy laid out as that design's `lay_out` lays it out, under that setting; decisions 13 and 14. Written in: **Why**, **Modules**, **Homes**, **Order**, **Decisions for the owner**, **Decisions taken**.
13. **Where does the mutation plan design take the setting of decision 12?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." Under it the recommendation is taken, the brief bringing no conflict: a `new:` ruling on `docs/superpowers/specs/2026-10-21-mutation-plan-design.md`, whose architect `rulings` pass makes `lay_out` hand `settings_text` the pair `-o`, `pythonpath=<work>/mutants` after the arguments `settings_arguments` gives (`:142`), landing before that design's driver stub, its step 13 (`:190`), and no step in this **Order** writing that file. Adds: no module, no home and no step here; in **Modules**, the route by which `settings_text` writes the setting, and in **Order**, that pass's place before the mutation plan design's step 13. Written in: **Modules**, **Order**, **Decisions for the owner**, **Decisions taken**.
14. **Which setting puts the copy's `mutants/` on the tests' `sys.path`?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." Under it the recommendation is taken, the brief bringing no conflict: pytest's `pythonpath` in mutmut's `pytest_add_cli_args`, riding on mutmut's settings file into every pytest run mutmut makes, in the driver's process and in a test's (decision 4). Adds: no module and no step; decision 12's `-o pythonpath=<work>/mutants` in `Plan.settings` as the one setting, and the home "The copy's import path in mutmut's pytest runs", whose forbids keep `PYTHONPATH` out of the driver Command's env, rest on it. Written in: **Why**, **Modules**, **Decisions for the owner**, **Decisions taken**.
