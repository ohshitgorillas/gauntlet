Status: approved by the owner.

## Why

C7b is the mutation gate's process step: "processes and throttle". The gates core design gives it the worker cap of decision 30 and the suite of decision 28, and points here for the function that runs mutmut, its Command and the run's verdicts. The gate has no wall-clock cap and no cap on the mutants a run checks: it mutates only the changed functions and checks every mutant they yield, its scope alone drawing the line on its work. The gate holds the gap as a body that only raises (`gates/check_mutation.py:91`–`:100`). This design names the function that runs mutmut and what it hands back, so C7b, and C7c, which builds that function's input, are built against it.

The tree, and the G4 branch the gate is ported from (`.claude/worktrees/agent-a3292c4f570aba00b/`), hold 22 copies of what the core already owns, of what this design gives one home, or of a cap the gate does not have:

- **A cap on the mutants a run checks, which the gate does not have, 8 copies.** The quality gates spec words it in the closed set of a gate's own lines, the mutation run bullet and the unfinished-run bullet, and the gates core design in its mutmut bullet, its C7a-c row and decisions 29 and 30, each wording that cap or pointing here for it.
- **No wall-clock cap.** The mutation gate has no 600-second cap, `AT_THE_CAP` or `WALL_CLOCK_SECONDS`.
- **A result shaped for the cap.** `Mutated.at_cap` flags a cap the gate does not have, and `Mutated.error` is one string (`gates/check_mutation.py:82`, `:83`), which holds the checker's error and the suite's lines only by joining them into one Unfinished.
- **Process running.** Worker counts come from `cpu_budget`, throttling from `throttle_line`, and process running and group kill from the core's `run`.
- **Real time.** Real time in `gates/` has one home, and a timeout a module computes for itself is forbidden.
- **mutmut's API.** Only `gates/mutmut_driver.py` imports mutmut.
- **The interpreter command line.** The core's `python_script` builds the script command with `-P`; `python_module` gives the `-m` form, which puts the working directory on `sys.path`.

mutmut belongs in the dev group and is locked at 3.8.0 in `uv.lock`.

mutmut runs the tests from inside the copy's `mutants/`. The driver's interpreter runs under `-P` (`python_script`, **Modules**), so pytest's `pythonpath` is the one setting that puts the copy's `mutants/` on the tests' `sys.path` and lets them import `gates`.

## Modules

### `gates/check_mutation.py`: the mutmut run, its command and its verdict

Its job is to run mutmut once over a plan through the run's process runner and hand back `Mutated`, the value `outcome` takes. `run_mutmut` is the function that runs the mutation tool. C7c's `mutate` builds the `Plan` from the copy, git and parse steps and calls `run_mutmut`; it starts no process of its own.

```python
DRIVER: Path = Path(__file__).with_name("mutmut_driver.py")


@dataclass(frozen=True)
class Plan:  # what the copy, git and parse steps (C7c) hand the mutmut run
    settings: (
        Path  # the directory of the pyproject.toml mutmut reads, in the run's scratch;
    )
    # its pytest_add_cli_args carry "-o", f"pythonpath={work / 'mutants'}" (decision 12)
    work: Path  # the copy mutmut works in, in the run's scratch
    changed: Mapping[
        str, frozenset[str]
    ]  # each file mutmut mutates, by its path in the copy: its changed functions' mangled names
    given: Mapping[str, Source]  # the same files: the Source each was given as


@dataclass(frozen=True)
class Mutated:  # what one mutmut run left
    mutants: tuple[Mutant, ...] = ()  # every mutant not killed
    unfinished: tuple[
        Unfinished, ...
    ] = ()  # what the checker did not finish, printed before every finding
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
2. No file in `test_files(run.given)` is a GateError.
3. `budget()` is called once; 0 is a GateError, and no process runs.
4. `mutmut_command(plan, budget's number)` runs through `run.process`, once, with no timeout. A GateError or OSError from it goes to the caller, where `check` makes it the run's one Unfinished.
5. The result is `judge(plan, command, completed, partial(suite_lines, run, budget))`.

The run has no time cap and no cap on the mutants it checks. Only the changed functions are mutated, every function of a new file counting as changed, and every mutant they yield is checked, however many. That scope alone draws the line on a run's work: no filter narrows it below the changed functions, and nothing in the gate weighs how much a commit changes, which is the reviewer's question. How long a run over many changed functions takes on this host is unmeasured. Each mutant's test run keeps its hang limit: pytest-timeout's 30 seconds per test (`pyproject.toml:55`) under mutmut's own default time limit, a key that changes it being a finding. Whether a mutant whose test never returns is a finding under these two limits, and not a mutant killed, is unmeasured; step 3 measures it.

mutmut runs the tests from inside `plan.work`'s `mutants/`, so the `[tool.mutmut]` `pytest_add_cli_args` of `plan.settings` carry `-o` and `pythonpath=<plan.work>/mutants`, the path absolute, after the arguments `settings_arguments` gives. pytest documents its `pythonpath` as putting its entries at the head of `sys.path` for each run it makes, so every pytest run mutmut makes, its stats run, its run on the unmutated copy and each mutant's, in the driver's process or in a test's, imports `gates` and `tests` from the copy, as the pytest gate's run imports them from the project root (`gates/check_pytest.py:154`, `:165`). The setting rides on mutmut's own settings file, which the mutation plan design's `settings_text` writes (`docs/superpowers/specs/mutation-plan-design.md:74`–`:75`), its `lay_out` handing it the pair after the arguments `settings_arguments` gives (`:142`), and it replaces any `pythonpath` the project's config sets. Whether pytest 9.1.1 (`uv.lock:425`–`:426`) puts the entry first under `-o`, whether mutmut 3.8.0 hands these arguments to each of its pytest runs, and whether under them its stats run collects the given tests in the copy and imports `gates` there, are unmeasured; steps 3 and 5 run under this setting.

`judge` reads the driver's outputs from the Completed: `NAMES`, the generated mutants with their diffs and mutmut's status table; `REACH`, tests collected and functions reached; and each file's `.meta` report under its `meta_key`, read through the status table. A mutant mutmut killed gives nothing. Each other mutant is a `Mutant`: the `given` of its file's Source, mutmut's name, its status, and the driver's diff, which `render` puts on one line.

- **`NAMES` absent or unreadable.** `unfinished=(Unfinished(completed.output()),)`.
- **Exit 0.** Each mutant takes its status; any mutant left unchecked puts `Unfinished(completed.output())` first.
- **Nonzero exit.** `judge` calls `suite`. When the suite passed and `REACH` shows tests collected and no function reached, each unchecked mutant has mutmut's `NO_TESTS` status and the run is finished. Otherwise the run is unfinished: `Unfinished(completed.output())`, then the suite's lines, then the findings.

It replaces the raising body of `mutate` as the process step (`gates/check_mutation.py:91`–`:100`), `WALL_CLOCK_SECONDS` and `AT_THE_CAP` (`:15`, `:18`), and `Mutated.at_cap` and `.error` (`:82`, `:83`); `check`'s catch gives `Mutated(unfinished=(Unfinished(error.report),))` (`:131`–`:132`). It also replaces G4's `mutation_run.py` and `mutation_judge.py`, and G4's remaining-time reads (`.claude/worktrees/agent-a3292c4f570aba00b/gates/check_mutation.py:48`, `:81`, `:91`).

### `gates/mutmut_driver.py`: the child mutmut runs in

Its job is to be the one module that imports mutmut. In an interpreter of its own it generates the mutants of the changed functions, writes their names and diffs with mutmut's status table, runs mutmut over every one of them, and writes the reach record. Every own line also runs in a test's own process, as the core's child rule asks. What each of `MUTMUT`'s entry points does in a test's process must follow the owner's ruling on steps 4 to 6's findings, which step 7 must write into this block before any stub; a red test of `MUTMUT` takes its expected values from that, never from a spiker's report.

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

Run as a script, it calls `main(sys.argv[1:])`. The gate builds mutmut's arguments, so `--max-children` stands in the Command a FakeRunner records, and the driver only appends the names.

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
| mutmut's Python API | `gates/mutmut_driver.py`, `MUTMUT` | An import of `mutmut` anywhere else in `gates/` |
| The child's command line | `checker.python_script` | `sys.executable` named in a gate module |
| The run's work | `mutmut_driver.changed_mutants`, the mutants of the changed functions and every one of them, run by the driver's one mutmut run, whose Command has no timeout, the scope alone drawing the line on the run's work | A cap on the number of mutants, functions or files a run checks, or any count that stops a run short of every mutant of its changed functions; a filter that drops a mutant of a changed function, as one on a line `git diff HEAD` leaves unchanged, and a gate line or verdict on how much a commit changes; a timeout on the driver Command, or any time cap on the run; a `time` read, or time left computed, in the gate |
| Each mutant's hang limit | pytest-timeout's `timeout = 30` (`pyproject.toml:55`) under mutmut's default time limit, whose keys are findings (`gates/check_mutation.py:36`); a hung mutant's verdict is step 3's finding as step 7 writes it here | A per-mutant or per-test limit set in the gate or the driver; a red test whose verdict a time limit decides, as a test of `MUTMUT.run` whose seeded tests do not return at once |
| A measured finding | This file, written by an architect `rulings` pass recording the owner's ruling on it: steps 3 to 6's findings by step 7 | An expected value, constant or number in a brief or a test taken from a spiker's report rather than from `docs/`; a builder or test step dispatched before the pass that writes the finding it rests on |
| A capped checker's lines | `report.time_cap` and `report.timed_out`, for a Command with a timeout; the mutation gate has none | `WALL_CLOCK_SECONDS`, `AT_THE_CAP` or any other wording of a cap in the mutation gate |
| Throttling | `Command.throttled=True`, through `checker.throttle_line` | `nice` or `ionice` in an argv |
| Workers | `run_mutmut`'s `budget`, `cpu_budget` by default, as `--max-children` in the Command's argv | An affinity or CPU read in the gate; a row for a key mutmut never reads |
| Timeout, group kill and output files | `checker.run`, through `run.process` | `subprocess`, `os.killpg` and reading the copy after the run in the gate |
| The copy's import path in mutmut's pytest runs | pytest's `pythonpath`, `-o pythonpath=<work>/mutants`, among the `pytest_add_cli_args` of the settings file `Plan.settings` holds, which `mutmut_driver.settings_text` writes | `PYTHONPATH` in the driver Command's env; a `sys.path` edit in the gate or the driver; a `pythonpath` key written into the copy's `pyproject.toml`; a `conftest.py` written into the copy; `-P` dropped from the driver's command line |
| pytest's environment | `check_pytest.PYTEST_ENVIRONMENT` (`gates/check_pytest.py:19`) through `checker.environment` | A second `"PYTEST_"` literal |
| The suite on the unmutated tree | `check_pytest.check` (`gates/check_pytest.py:205`), through `suite_lines` | A pytest command line built in the mutation gate |
| Where the driver and mutmut write | `mutmut_driver`'s `names_path`, `reach_path`, `meta_path` and their keys | A file name or output key spelled in the gate |
| mutmut's status names | `mutmut_driver`'s `KILLED`, `UNCHECKED`, `NO_TESTS`, their strings those the locked mutmut's status table gives, written once by step 16, and the table `statuses` gives | A status name of mutmut's spelled in the gate |
| A fake runner in tests | `tests/support/fake.py` `FakeRunner` and `completed` (`tests/support/fake.py:16`, `:32`) | A test's own Runner; a real mutmut run where a reply proves the branch |

A builder that needs what these homes lack stops and reports it, and writes no copy.

## Order

Each step lands green under `make check` before the next starts, save a `stub` step, which lands with its red tests in the commit of the build that turns them green. Each stub step is paired with the one build step that turns all its red tests green, and adds names to a module without changing a line already in it. A stub step writes each declaration **Modules** gives, a constant at the value given there, a dataclass's fields, a Protocol's signatures, and each function body raising `NotImplementedError` and nothing else. A red step holds one behavior. A spike step asks one claim with a yes-or-no reading (decision 7), and its finding reaches a builder or a test only once the owner rules on it and an architect `rulings` pass writes it here, by step 7 (decision 8).

1. The gates core design names `python_script` in `checker.py`'s block (`docs/superpowers/specs/gates-core-design.md:73`), and its mutmut bullet (`:242`–`:250`), the sentences of decisions 29 and 30 on the mutation gate (`:431`, `:432`) and its C7a-c row (`:338`) point here for C7b's interface, and each gives the mutation run no time cap and no cap on the mutants it checks (decisions 1, 9). The quality gates spec bounds the mutation run's work by its scope alone: its mutation run bullet (`docs/superpowers/specs/quality-gates-design.md:89`) gives the run no wall-clock cap and no cap on the mutants it checks, every mutant of the changed functions checked and each keeping its hang limit, the scope alone drawing the line on the run's work (decisions 1, 9, 11); the unfinished-run bullet (`:91`) names no run over a bound; the time-cap rule (`:29`) gives the mutation run no cap; and the closed set of a gate's own lines (`:30`) holds no line of the mutation gate's. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/gates-core-design.md`, `docs/superpowers/specs/quality-gates-design.md`.
2. `dependency`: mutmut in the dev group, locked at the version decision 30 names. Agent: `gatesmith`, no red test. Paths: `pyproject.toml`, `uv.lock`.
3. Claim: a mutant that makes a seeded test loop forever, that test's unmutated run returning at once, gets from mutmut 3.8.0, in a copy laid out as the mutation plan design's `lay_out` lays it out (`docs/superpowers/specs/mutation-plan-design.md:141`–`:142`), its settings file's `pytest_add_cli_args` carrying `-o pythonpath=<work>/mutants` (decision 12), under `timeout = 30` (`pyproject.toml:55`) and mutmut's default time limit, a status other than killed, so it is a finding (`docs/superpowers/specs/quality-gates-design.md:85`, decision 1). A no comes back to the owner through step 7, and so does a run that checks no mutant under that setting. Agent: `spiker`, scratchpad only, one claim (decision 7). Paths: none in the tree.
4. Claim: mutmut 3.8.0, called in the calling process, reads the settings of one directory's `pyproject.toml` and works in a second directory, starting no process, as `Mutmut.load` asks (decision 4). Agent: `spiker`, scratchpad only, one claim (decision 7). Paths: none in the tree.
5. Claim: mutmut 3.8.0's run command, called in the calling process over named mutants in a copy laid out and set as step 3's (decision 12), returns to its caller once they are checked, as `Mutmut.run` asks (decision 4). Agent: `spiker`, scratchpad only, one claim (decision 7). Paths: none in the tree.
6. Claim: after such a run, mutmut 3.8.0's record, read in the calling process, gives the tests collected and the functions a test reaches, as `Mutmut.reach` asks (decision 4). Agent: `spiker`, scratchpad only, one claim (decision 7). Paths: none in the tree.
7. The owner's rulings on steps 3 to 6's findings are written here: the hung mutant's verdict under "Each mutant's hang limit", and what each of `MUTMUT`'s entry points does in a test's process in the driver's block; an entry point that cannot run there comes back to the owner before step 16 (decisions 4, 8). Agent: `architect`, a `rulings` pass. Paths: `docs/superpowers/specs/mutmut-run-design.md`.
8. `moved`: `lines:` `docs/superpowers/specs/quality-gates-design.md:89` and `docs/superpowers/specs/gates-core-design.md:431`, each quoted as it stood before step 1, holding the 600-second cap and the mutation gate's `time_cap(argv[0], 600)`, and as it stands. `test_at_the_cap` (`tests/test_check_mutation_core.py:246`) and its `AT_THE_CAP` mutant (`:96`) go, the module docstring's sentence on the cap (`:11`–`:13`) with them, and the docstring of `tests/test_core_report_cap.py` (`:8`) stops citing the mutation gate's call of `time_cap`, its cases (`:19`, `:33`, `:47`, `:51`) unchanged. It lands before step 12 removes what the test reads. Agent: `test-writer`. Paths: `tests/test_check_mutation_core.py`, `tests/test_core_report_cap.py`.
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

The mutation plan design requires an architect `rulings` pass on the owner's `new:` ruling to make `lay_out` hand `settings_text` the pair `-o`, `pythonpath=<work>/mutants` after the arguments `settings_arguments` gives (`docs/superpowers/specs/mutation-plan-design.md:142`). That pass must land before that design's driver stub, its step 13 (`:190`), and no step here writes that file.

## Decisions

These constraints apply alongside **Modules**, **Homes** and **Order**.

1. Run limits: the driver Command has no timeout, and the gate reads no `time`. Each mutant keeps its per-test hang limit; decision 9 defines the run's scope.
2. mutmut's Python API: only `MUTMUT` and `Mutmut` in `gates/mutmut_driver.py` import mutmut. `names_report` carries the status table and each generated mutant's diff as JSON for `judge`.
3. Failing test ids: `suite_lines` runs the suite through `check_pytest.check` with no cap on the whole; `judge` takes it through its `suite` parameter.
4. The driver's lines run in a test's process through `Mutmut` and `main`'s `mutmut` parameter. An entry point that cannot run there must come back to the owner before step 16; step 20 tests `main` on a fake `Mutmut`.
5. Work scope: see decision 9.
6. Run verdicts: see `judge` in **Modules**.
7. Each spike step asks one measurement question and refuses two with `OVERLOADED`; steps 3 to 6 each ask one yes-or-no claim.
8. Step 7 records the owner's rulings on spike findings in this spec before dependent stubs or tests. **Modules**, **Homes** and **Order** define constants, entry points, test expectations, stub/build pairings and migration prerequisites.
9. `changed_mutants` hands the driver's one mutmut run every mutant of the changed functions. No bound in `mutmut_command`'s argv, `names_report` or `main` stops a run short of every mutant.
10. No spike measures how long a run takes.
11. Scope alone bounds the work: every mutant of every changed function is checked. No filter drops a mutant of a changed function. How much a commit changes is the reviewer's question; the gate gives no line or verdict on it.
12. `Plan.settings` carries `-o pythonpath=<work>/mutants` in `pytest_add_cli_args`, written by the mutation plan design's `settings_text`. Steps 3 and 5 use a copy laid out by that design's `lay_out` under this setting.
13. The mutation plan design's architect `rulings` pass on the owner's `new:` ruling makes `lay_out` hand `settings_text` the pair `-o`, `pythonpath=<work>/mutants` after `settings_arguments`' arguments. It must land before that design's driver stub, step 13. No step in this **Order** writes that file.
14. pytest's `pythonpath` in mutmut's `pytest_add_cli_args` is the one setting, carried by mutmut's settings file into every pytest run mutmut makes, in the driver's process and in a test's. The driver Command's env contains no `PYTHONPATH`.
