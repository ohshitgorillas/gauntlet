# Gates core design

Status: approved.

## Why

The gates share one run contract for findings, unfinished checks, file counts, configuration, process execution and cleanup. Each concern has one home; every gate uses it.

- **(a) mypy exit 1 with no record** is unfinished: the checker's exit status must agree with its report before the gate can pass.
- Parse warnings, empty runs, files given twice, throttling on macOS and environment failures follow the same core rules in every gate.

## 1. Core modules

There are six modules under `gates/core/`. They use the standard library only, import nothing from `gauntlet`, and hold no path of this repository. The imports form a chain with no cycles: report ← checker ← project ← source ← runner.

Each checker's own record types stay in its gate: mypy's Record, pyright's Diagnostic, ruff's Violation and pytest's JUnit Case. A reader that two sibling gates share goes in `gates/<checker>_report.py`, for example ruff's for check_cast and G2.

### report.py: what a run prints and how it exits

```python
class GateError(Exception): __init__(self, report: str)  # something stops the checker; keeps `.report`, the report as given, which the runner reads by that name; printed as the checker's, exit 2
Finding(text: str)          # frozen dataclasses. One line, counted in N
Remark(text: str)           # a checker line that is no finding (a mypy note): printed, not counted
Unfinished(text: str)       # the checker's report on what it did not finish, or a GateError's report: exit 2
type Line = Finding | Remark | Unfinished
Outcome(lines: tuple[Line, ...] = (), notes: tuple[str, ...] = ())  # notes: the gate's own lines the spec names (pytest's seed)
def exit_code(outcome: Outcome) -> int                  # 2 on any Unfinished, else 1 on any Finding, else 0
def count_line(gate: str, findings: int, files: int) -> str
def one_line(text: str) -> str                          # every str.splitlines break becomes a space
def output_lines(text: str) -> list[str]                # a checker's console output, one printed line per str.splitlines line
def render(gate: str, outcome: Outcome, files: int) -> list[str]  # notes, lines in order, each Unfinished text once per run, count line last; passes every Finding and Remark text through one_line, the one home for that rule; passes each Unfinished text through output_lines, the one home for that rule
def nothing_checked(gate: str, selects: str, given: int) -> list[str]
def time_cap(checker: str, seconds: float) -> str       # the line naming the cap, its one home
def timed_out(output: str, checker: str, seconds: float) -> tuple[Unfinished, Unfinished]  # a checker its cap ended: its whole output, then time_cap
def write(lines: Sequence[str], *, error: bool = False) -> None  # the only writer: looks up sys.stdout/stderr at call time, flushes
```

**Replaces:**

- every direct write in the gates
- `json_report.print_unread` and `UnfinishedError`, `check_suppressions.UnpinnedError`, and `mutation_gate.UnfinishedError`
- g1l's `checker_output.print_output` (c): its line-splitting rule becomes `output_lines`
- `check_pytest.one_line` and `print_unfinished`
- `check_mypy.show` and `show_blocked`
- the mutation gate's `count_line` and `finish`
- all six exit constants

### clock.py: the one home of real time

```python
type Ready = Callable[[float | None], bool]  # the caller's own wait on an event, for up to the seconds given (None: without end); True when the event came
class Clock(Protocol):
    def wait(self, ready: Ready, seconds: float | None) -> bool  # True when the event came before `seconds` passed on this clock; None: no cap
class SystemClock:  # real time, the only real time in gates/: hands `seconds` to ready as they are
    def wait(self, ready: Ready, seconds: float | None) -> bool
SYSTEM: Clock  # a SystemClock; the default of every clock parameter in gates/
```

Every wait in `gates/` that can end on time as well as on an event goes through a `Clock` handed in, `SYSTEM` by default, and keeps its own wait on the event as the `Ready` it hands that clock; a test hands in a `VirtualClock` (`tests/support/clock.py`).

**Replaces:** the bare cap `run` handed to the checker's exit wait, which becomes the `Ready` `run` hands its clock.

### checker.py: running a checker process

```python
Command(argv: tuple[str, ...], cwd: Path, env: Mapping[str, str] | None = None, timeout: float | None = None,
        throttled: bool = False, outputs: Mapping[str, Path] = {}, capture: bool = True, pass_fds: tuple[int, ...] = ())
Completed(status: int, stdout: str, stderr: str, timed_out: bool, outputs: Mapping[str, str | None])  # status as a shell reports it; .output() = stdout + stderr
type Runner = Callable[[Command], Completed]
def read_output(path: Path) -> str | None  # run's default reader of an output file
def run(command: Command, *, read: Callable[[Path], str | None] = read_output, clock: Clock = SYSTEM) -> Completed  # own session; waits on the checker's exit through clock, the timeout passing on that clock; the whole group is killed whatever ends the wait, the timeout, an interrupt or the checker's own exit, so no process still in the group outlives the run (one that left it by its own `setsid` is not killed); GateError if the program cannot start
def python_module(module: str, *arguments: str | Path, cwd: Path, timeout: float | None = None) -> Command
def python_script(script: Path, *arguments: str | Path, cwd: Path, timeout: float | None = None) -> Command  # the interpreter run on a script by its path
def environment(*, drop_prefixes: tuple[str, ...] = (), drop: frozenset[str] = frozenset()) -> dict[str, str]
def throttle_line(platform: str, niceness: int, path: str | None = None) -> list[str]  # heavy's line; GateError on a host with none, or a tool not on `path` (None: os.environ's PATH)
def cpu_budget(cpus: int | None = None) -> int   # floor(cpus / 2), the mutation and backstop cap; None: the CPUs this process may run on (its affinity where the host keeps one, else the host's count), so a test sets the count in-process
```

```python
type NextDone = Callable[[Collection[Future[Completed]]], set[Future[Completed]]]  # blocks until at least one future in running is done; the done ones
def first_done(running: Collection[Future[Completed]]) -> set[Future[Completed]]  # concurrent.futures.wait(running, return_when=FIRST_COMPLETED), no timeout; the done ones
def run_all(process: Runner, commands: Iterable[Command], cap: int, *, next_done: NextDone = first_done) -> list[Completed | GateError | OSError]  # at most cap at once, results in command order; every wait on its workers, the cleanup's included, through next_done, which only a test hands in
```

`run` closes in the checker every descriptor of the running process except `pass_fds` and fds 0, 1 and 2. `capture=False` lets the checker inherit the run's own fds 1 and 2 and write straight to them; `Completed.stdout` and `.stderr` come back `""`. A throttled `run` looks its tools up on the PATH of `Command.env`, and on os.environ's PATH when `env` is None, so a test sets PATH in-process through `env`.

`outputs` names the files a checker writes, such as pytest's JUnit XML or mutmut's coverage record. `run` deletes a file already at an output path before it starts the checker, so a file it reads back is one this checker wrote, and one it cannot delete is a GateError, as `read_output` makes one that exists but cannot be read. `run` reads them back into `Completed.outputs` through `read`, which only a test passes, so a gate reads its report from the Completed and a fake supplies one without the filesystem.

**Replaces:**

- the subprocess calls in cast, pyright and pytest
- mypy's `api.run`
- `mutation_run`'s probe, mutate, stop, workers and NICE
- heavy's `wrapped`, `missing` and `status`, and its subprocess call
- `check_pytest.pytest_environment`

Concurrent batches are a core feature, so check_pytest keeps running its modules in parallel: `run_all(process, commands, cap, *, next_done=first_done)` runs each Command through `process` in worker threads, at most `cap` (1 or more) at once. It takes the next Command from `commands`, in the main thread, only when fewer than `cap` are running, so Commands are made and started in their order. Every wait on its workers, for one to end and in the cleanup for all of them, goes through `next_done`, with no timeout; it never looks at its Runner to find a wait. It returns one result per Command started, in the order of `commands` whatever the order they finish in: the Completed, or the GateError or OSError that taking the Command or calling `process` raised. Such an error stops it: no Command is taken once one is seen, the ones running are waited for, and the list ends at the first error in command order, so what stands never depends on finish order. Any other exception from `process` goes on after the cleanup below.

While it runs, the main thread answers ENDING_SIGNALS as `run` does; on any exception there, a signal's included, it holds signals, kills once the process group of every checker `run` has started, in any thread, and not yet reaped, waits through `next_done` until no worker is running, puts the handlers back, and only then do the exception and each signal recorded take their course. While it waits, each checker `run` starts is killed as it is added to the live set, under the lock that add takes, so the cleanup has no poll and no poll interval.

### project.py: the project, its config and its files

```python
Source(given: Path, absolute: Path)  # given: as the caller spelled it; absolute: os.path.abspath, the file's identity
def python_files(paths: Sequence[Path]) -> list[Source]  # the spec's Python-file rule; a file given twice is one Source, first spelling kept
def test_files(sources: Sequence[Source]) -> list[Source]  # the spec's one test-file definition
def non_test_files(sources: Sequence[Source]) -> list[Source]
Project(root: Path)
    Project.current() -> Project  # the working directory; GateError if it holds no pyproject.toml
    .config -> Path  # root / "pyproject.toml", the one file that holds every checker's settings
    .settings() -> Mapping[str, object]  # read once per run; GateError naming the file if unreadable or not TOML
    .setting(*keys: str) -> object | None
    .config_text() -> str  # raw text, for rules about comments (G2's ignore reasons)
    .git(*arguments: str, process: Runner = run) -> Completed  # in root, without the GIT_ variables a hook exports
KeyRule(keys: tuple[str, ...], breaks: Callable[[object], bool], says: str)
def key_findings(project: Project, rules: Sequence[KeyRule]) -> list[Finding]  # "pyproject.toml: tool.mutmut.paths_to_mutate: <says>"
```

**Replaces:**

- the five lookups relative to `gates/`, and the two tests that copy the whole `gates` package into a temp tree to move them
- `is_python_source`, which lives in check_suppressions and every gate imports
- `check_pytest.select` and `is_test_module`, and `check_mutation.sources`
- `mutation_changes`' `tree_root`, `git` and `git_environment`
- `mutation_settings`

Config suppressions are scanned here as KeyRule tables. The mutation and backstop narrowing keys, G2's ignore list and G10's ignore lists across every tool become table rows, not code.

Project root is the working directory, with a `project=` parameter for tests and other callers; never relative to `gates/`, never a nearer pyproject.toml. The test-file rule's `tests` directory is one constant in project.py.

`python_files` on a path it cannot read: a path that names nothing (it or a directory on it does not exist) or that is no regular file is no Python file; a `.py` or `.pyi` whose kind cannot be read, or an extensionless file whose kind or first line cannot be read, is taken as one, so the checker reports it unreadable and the run exits 2 rather than dropping it. This keeps `is_python_source`'s rule.

`setting(*keys)` is None when any key is absent or a value on the way to the last key is no table.

`settings()` and `config_text()` come from one read of the file per Project, as UTF-8: a file that cannot be read or decoded is a GateError naming the file from either, and a change after the first read is not seen.

`git` drops every variable whose name starts with `GIT_`, through `environment(drop_prefixes=("GIT_",))`, not a list of the variables a hook exports.

`key_findings`: a rule whose key is absent is no finding and its `breaks` is not called; each broken rule gives one Finding, in the order of the rules, reading `pyproject.toml: <keys joined by .>: <says>`.

### source.py: reading a Python file under the pinned version

```python
Parsed(source: Source, text: str, tokens: tuple[TokenInfo, ...], tree: ast.Module)
def pinned_version(project: Project) -> tuple[int, int]  # pyright's pythonVersion, the one pin rule; GateError naming the key
def parse(source: Source, version: tuple[int, int]) -> Parsed | Unfinished
    # read, decode, tokenize, parse; OSError, SyntaxError, any warning, MemoryError or RecursionError is Unfinished with its report
def comment_markers(parsed: Parsed, markers: Mapping[str, re.Pattern[str]]) -> list[tuple[int, tuple[str, ...]]]
```

**Replaces:**

- check_suppressions' `pinned_grammar`, `parse_pinned`, `scan`, and the read and tokenize steps of `find_suppressions`
- `check_pyright.parse`, which is the other, disagreeing copy of the warning rule

**Serves:**

- the suppression gate (comment markers, and the input to the no_type_check resolver)
- pyright
- the mutation gate's search for changed functions
- G6's test-shape gates
- G9's import scan
- M1.5's shell gate

`pinned_version` also refuses a version the parser has no grammar for, outside 3.7 to the running interpreter's own, as `pinned_grammar` did, since `ast.parse` takes such a version and parses with another grammar. Its GateError names `tool.pyright.pythonVersion` and the file.

`parse`'s report names the file as given: `<given>: <ErrorType>: <error>` for an error, and one `<given>:<line>: <Category>: <message>` line per warning, recorded whatever the caller's warning filters say, which are left as they were. It parses before it tokenizes: the tokenizer copies a token's whole line into every token, about 10 GB for a 100,000-deep one-line source, so a file too deep to parse stops at the parse.

`comment_markers` gives one entry per comment token that carries any marker: its start line, then the names of the markers it carries in the order of `markers`. Strings are never searched.

### runner.py: one gate run, from start to exit

```python
Gate(name: str, check: Callable[[Run], Outcome],
     select: Callable[[Sequence[Source]], list[Source]] = list, selects: str = "Python file")
Run(project: Project, sources: tuple[Source, ...], scratch: Scratch, process: Runner,
    given: tuple[Source, ...] = (), next_done: NextDone = first_done)  # given: every Python file given, test files included; sources is select(given); next_done: the wait run_all makes on its workers, which check_with hands to run_all beside process; only a test hands in another
class Scratch:  # one per run
    __init__(self, root: Path | None = None)  # None: tempfile.gettempdir(), so TMPDIR moves it; never in the tree
    directory(self, name: str) -> Path  # a fresh dir inside the run's own temp dir; GateError on OSError
    copy(self, tree: Path, name: str) -> Path  # GateError on OSError
    once(self, name: str, make: Callable[[Path], None]) -> Path  # built the first time, the same path after (mypy's warm cache)
    close(self) -> str | None  # deletes everything, read-only entries included; returns the failure, never raises
```

```python
class Checker[R](Protocol):
    stopped: frozenset[int]  # statuses where the checker stopped but its report stands (mypy: {2})
    def batches(self, run: Run) -> Sequence[Sequence[Source]]
    def command(self, run: Run, batch: Sequence[Source]) -> Command
    def read(self, completed: Completed) -> R  # GateError if the output holds no report the gate can read
    def expected_status(self, report: R) -> int  # the exit status this report calls for
    def lines(self, report: R, batch: Sequence[Source], *, stopped: bool) -> Sequence[Line]
def check_with(checker: Checker[R], *, budget: Callable[[], int] | None = None) -> Callable[[Run], Outcome]  # budget: batches at once
def run_gate(gate: Gate, paths: Sequence[Path], *, project: Project | None = None,
             process: Runner = run, next_done: NextDone = first_done, scratch_root: Path | None = None) -> int  # puts process and next_done in the Run it builds
def main(gate: Gate) -> NoReturn
```

`run_gate` is the one place the contract is applied. It runs these steps in order:

1. Take `python_files(paths)` as the given files and select the sources from them. If there are none, print `nothing_checked` and exit 1.
2. Open the Scratch, resolve the project and call `gate.check`. A GateError or OSError from any of these becomes an Unfinished line.
3. `Scratch.close()` runs on every path, interrupts included. A failure it returns becomes an Unfinished line too.
4. Print with `write(render(...))` and return `exit_code`.

M is `len(sources)` for every gate.

`check_with` runs each batch and reads its report. Three results are Unfinished, carrying the checker's whole output:

- a timeout
- an output with no report the gate can read (GateError from `read`)
- an exit status that is neither `expected_status(report)` nor in `stopped`

A stopped batch always ends unfinished. This is the exit rule (a) needs, and it is held in one place: mypy's exit 1 with no record is not the 0 an empty report calls for, so every gate treats a checker that exits nonzero with nothing to show as unfinished.

**Replaces:**

- every gate's main body
- mypy-cache's `run`, `check_copy`, `check_copied`, `remove` and `warm` wrappers
- the TemporaryDirectory handling in pytest and the mutation gate
- `json_report.load`'s FINISHED set
- `check_pytest.verdict`'s exit agreement

`Scratch` makes the run's own temp dir, with `tempfile.mkdtemp` in its root, at the first `directory`, `copy` or `once`, not in `__init__`: a run that asks for no temp space makes none, so a missing scratch root fails only a gate that uses one, and `close` then deletes nothing and returns None. A root it cannot make the run's temp dir in is a GateError naming the root and the OS error.

`directory(name)` and `copy(tree, name)` give a new path on every call, its last component starting with `name`, so one name twice gives two paths, as mypy's one cache copy per file needs. `copy` puts the tree's contents at that path, following symlinks, so no entry of the copy links back into the tree; a tree it cannot copy is a GateError naming the tree and the OS error.

`once(name, make)` keeps a path only after `make` returns: a `make` that raises is not kept, its error goes to the caller, and the next call with that name builds again. Each name is built apart from the others.

`close` deletes the run's temp dir and all it holds, making a read-only directory inside it writable on the way, and changes no mode outside it. A deletion that fails returns `cannot delete the temp space <path>: <error>`; after `close` the Scratch holds nothing, so a second `close` returns None.

`check_with` reads a status in `stopped` before it compares it with `expected_status`, so a stop is never a finish; a stopped batch whose `lines` hold no Unfinished gets one more, the checker's whole output, so a stopped batch always ends unfinished.

After a timeout `check_with` reads no report: its lines are an Unfinished of the checker's whole output, then an Unfinished of the gate's own line `the checker <argv[0]> ran past its time cap of <timeout> seconds`.

A GateError or OSError from `command` or from `run.process` ends `check_with` at that batch: the lines of the batches before it stand, then an Unfinished of the error's report, and no later batch runs. An OSError's report, here and in `run_gate`, is `str(error)`.

`run_gate`: the `given` of `nothing_checked` is `len(paths)`, every path as given; an error before or in `gate.check` gives an Outcome of its one Unfinished line; a failure `close` returns is an Unfinished after the Outcome's lines; on an interrupt `close` runs and the interrupt goes on, nothing printed. Every line goes to stdout. `main` runs `run_gate` over `sys.argv[1:]` and exits with its code.

`check_with(checker, *, budget=None)`: `budget` is the CPU budget the cap is sized by, `cpu_budget` for check_pytest; None runs one batch at a time, so every gate built before it keeps its order and its tests. `budget` is called once per check, after `batches` and before the first `command`; the cap is `max(1, budget())`, so a host of 0 or 1 CPUs still runs one batch at a time, and a GateError or OSError from it is the Outcome of its one Unfinished, with no batch run. The batches run through `run_all`, each batch's command made in batch order; each batch's lines follow the lines of the batch before it, whatever the order they finished in. A GateError or OSError ends the check at the first error, at the first failing batch in batch order: no batch starts once it is seen, and no later batch gives a line, even one that finished. On an interrupt every running batch's process group is killed before the interrupt goes on, through run_all's cleanup.

`Run.given` carries every Python file given, test files included, as `python_files` returns them; `run_gate` selects `sources` from it, so M and the empty run are unchanged. The mutation and backstop suites are `test_files(run.given)`; a mutation run with a changed function and no test file there is unfinished. The default `()` keeps hand-built Runs valid and fails closed.

`check_with` calls `report.timed_out(output, argv[0], timeout)` for the timeout pair. The mutation gate calls neither `time_cap` nor `timed_out` and defines no separate cap line or `AT_THE_CAP` constant.

**Two rules come with the core:**

- A gate module writes output, starts a process or makes a temp dir only through these modules.
- Own code never runs only in a child process. The backstop counts such lines as unseen, and mutmut cannot reach them. So a child is always either a third-party checker or a module whose functions also have in-process tests, like the mutation driver.

## 2. A gate on the core

This is check_mypy in full, except `Record`, `record`, `describe` and `shown`, which stay in the gate:

```python
class Mypy:
    stopped = frozenset({2})  # a blocking error stops mypy; its records still stand

    def batches(self, run: Run) -> list[list[Source]]:
        return [
            [source] for source in run.sources
        ]  # one mypy per file: no verdict depends on another file

    def command(self, run: Run, batch: list[Source]) -> Command:
        warm = run.scratch.once(
            "warm", partial(warm_cache, run)
        )  # one warm cache per run, one copy per file
        return python_module(
            "mypy",
            "--config-file",
            run.project.config,
            "--cache-dir",
            run.scratch.copy(warm, "cache"),
            "--show-absolute-path",
            "--no-error-summary",
            "--output",
            "json",
            batch[0].absolute,
            cwd=run.project.root,
        )

    def read(self, completed: Completed) -> list[Record]:
        return [
            record(line) for line in completed.stdout.splitlines()
        ]  # record() raises GateError

    def expected_status(self, records: list[Record]) -> int:
        return 1 if records else 0  # exit 1 with no record is a refusal, not a pass

    def lines(
        self, records: list[Record], batch: list[Source], *, stopped: bool
    ) -> list[Line]:
        if stopped:
            return [
                Unfinished(describe(r)) for r in records
            ]  # every record, wherever it lies, once per run
        here = str(batch[0].absolute)
        return [
            line for r in records if r["file"] == here for line in shown(r)
        ]  # a Finding per error, a Remark per note


GATE = Gate(name="check_mypy", check=check_with(Mypy()))


def main(paths: list[Path]) -> int:
    return run_gate(GATE, paths)
```

`warm_cache(run, directory)` runs mypy on an empty program through `run.process`. It raises GateError unless mypy exits 0, prints nothing and leaves a file. No count line, exit constant, printer, temp handling or OSError handling is left in the gate. `main(paths)` keeps today's signature, so the existing tests stay green during the port.

C3 measures the cost of mypy as a child process (`python -m mypy` per file, from the warm cache); it keeps `mypy.api.run` only if that cost is large.

How the planned gates plug in:

- **ruff lint and format (G2).** One Checker each, with one batch. check_cast's ruff JSON reader moves to `gates/ruff_report.py`, shared with check_ruff. `expected_status` is `1 if entries else 0`, and E902 and invalid-syntax entries are Unfinished. The format check reads ruff's "Would reformat" lines. The ignore list, its reason comments and per-file-ignores become KeyRules, using `config_text`, in the suppression gate, where the spec lists them.
- **mutmut (G4) and the backstop.** These are plain `check(run)` functions, not Checkers. Each uses these core pieces:
  - `select=non_test_files`, and the suite is `test_files(run.given)`
  - `key_findings` over `[tool.mutmut]` or `[tool.coverage]`
  - `project.git("diff", "HEAD")` and `source.parse` to find changed functions
  - `scratch.copy` for the work copy
  - for mutmut, `check_mutation.run_mutmut(run, plan, *, budget)`, which runs it once through `run.process` with no timeout and no cap on the mutants it checks; its interface and its Command are the mutmut run design's (`docs/superpowers/specs/mutmut-run-design.md`)
  - a GateError when `cpu_budget() == 0`, and `--max-children` set to `cpu_budget()` on every mutmut run

  `run_mutmut` calls its `budget` once, using `cpu_budget` by default, and sets `run --max-children` to that number. Zero raises GateError without starting a process. Its Command has no timeout, and the gate imposes no time cap or mutant-count cap. Each mutant's hang limit is pytest-timeout's 30 seconds under mutmut's default time limit; settings that alter that limit are findings.

  The mutation gate supplies its own mutmut settings rather than the project's `[tool.mutmut]`; its dependency lock excludes pytest-xdist. A parallelism key gets a KeyRule only when the pinned checker reads it. That rule is built in `check(run)` from `cpu_budget()` and reports `pyproject.toml: <key>: raises the parallelism above the cap of <cap> workers; the run uses <cap>`. The backstop follows the same rule. C7b's FakeRunner tests assert the worker flag and budget in the recorded Command.

  The mutation run has no time cap and no cap on the mutants it checks: it checks every mutant of the changed functions, its scope alone drawing the line on its work, and its interface and the run's verdicts are the mutmut run design's. An unfinished run returns the checker's error as Unfinished first, then the findings. The branch's `mutation_gate.py`, count line, `finish`, NICE, `workers`, `stop`, git environment and its separate exit-2 paths all go.
- **pytest (G3, already built).** A Checker with one batch per test module and `outputs={"junit": ...}`; the seed line is an Outcome note.
- **filepawl (G5), import-linter and vulture (G7), deptry and the lock check (G8).** Checkers. Each `read` guards its JSON and `expected_status` states the tool's documented exit rule. The runner makes M the Python files given, whatever else the checker reads.
- **test-shape (G6) and wiring (G9).** In-process `check(run)` over `source.parse` of `test_files`, the Makefile and `git ls-files`. No process runs.
- **suppression completion (G10).** KeyRule rows only.

## 3. Tests

There are three helpers in `tests/support/`. The spec already names that directory as the home of seeded strings.

- **`capture.py`.** `captured(call: Callable[[], T]) -> Captured[T]`, which has `.result`, `.out`, `.err` and `.merged`: `.out` and `.err` are the lines written to fd 1 and fd 2 (and to `sys.stdout` and `sys.stderr`), kept apart, and `.merged` is every line of both in the order written.
  - It sees writes to either Python stream in the order made, direct fd writes, and a checker child's output.
  - The gate's code runs in the test's own interpreter, so coverage and mutmut's trampolines reach it. g1l's child-interpreter helper cannot give that.
  - It replaces 12 files using capsys, 11 using redirect_stdout, 4 using capfd and 10 that start a child.
- **`project.py`.** `scaffold(root, files: Mapping[str, str | bytes], *, pyproject: str | None = None, unreadable: tuple[str, ...] = (), git: bool = False) -> Project`.
  - The default pyproject.toml is the repository's own, found from this module's path, so a gate test runs under `make check`'s settings.
  - `git=True` initialises a repository and commits, for the mutation gate, G8 and G9.
  - It replaces 58 `_seed` copies, the `_seed_tree` and `_layout` helpers, and the two `_tree` helpers that copy `gates/`.
- **`fake.py`.** `FakeRunner(replies: Sequence[Completed])` returns canned replies in order and appends each Command to the public `commands: list[Command]`; a call with no reply left raises AssertionError naming the Command's argv. `completed(status=0, stdout="", stderr="", outputs={}, *, timed_out=False) -> Completed` builds a reply.
  - Because the test seeds the checker's whole output, "prints what the checker reported and nothing else" becomes an exact list check, `lines == [*seeded, count]`, instead of a predicate over the printed lines.
  - That removes the cause of G1l's T1 cluster (`_carries_report`, `_first_number`), which was filed three times.

`scaffold` writes the config first, then `files`, so a `files` entry named `pyproject.toml` replaces it, bytes included; with `git=True` it initialises the repository and commits everything through `Project.git`, a failing git step raising `ScaffoldError` with that Completed; the `unreadable` paths lose every permission last, after the commit. Its tests sit in `tests/test_core_runner.py`, B5's one test file.

**Contract suite, `tests/test_gate_contract.py`.** It holds a registry with one entry per gate script: the module, a clean source, a one-finding source with a fragment of its message, the checker's empty report, and whether the gate parses. Every case runs over every entry:

- **C1** A clean run exits 0 with the count line last.
- **C2** One finding exits 1 with one line carrying it, and N=1.
- **C3** Exactly one line counts files, on every run.
- **C4** .py, .pyi and python-shebang files count; .pyw and other files do not; a file given twice counts once.
- **C5** The empty run.
- **C6** An unreadable file exits 2, and the other files' findings still print.
- **C7** An unparseable file exits 2.
- **C8** No readable report, through FakeRunner (garbage, a refusal, nonzero with an empty report, death by signal, a timeout): exit 2, and the output is exactly the checker's output followed by the count line; after a timeout, one gate line naming the cap comes between them.
- **C9** A file's verdict is unchanged beside a broken file or one sharing its module name.
- **C10** Settings come only from the project's pyproject.toml.
- **C11** For parsing gates: a missing or malformed pin, a parse warning, or a parse too deep exits 2.
- **C12** After every run, unfinished ones included, the tree is byte-identical and the scratch root is empty; a failed cleanup exits 2.
- **C13** Every script under `gates/` has a registry entry.

**Per-gate tests** hold only what the gate's own checker finds:

- mypy: its options, notes, an imported blocking error, and the warm cache
- pyright: strict mode, severities and versions
- cast: the TID251 aliases
- suppressions: the markers and the no_type_check resolution
- pytest: its strict settings, seed and test ids
- heavy: its lock and arguments

**Core tests.** One test file per core module, plus `tests/test_gates_structure.py`. That file scans `gates/` with the AST and fails when any module other than the designated home:

- writes to stdout or stderr
- formats a count line
- starts a process
- makes a temp dir
- defines an exit-status constant

That turns 7a.4, "copies are findings", into a red test.

| Today | Becomes |
|---|---|
| 31 contract-type files, about 3,000 lines: cast_{contract,count_line,end,python_files,settings,unfinished}, mypy_{count,files,neighbours,tree,unfinished,unfinished_count}, pyright_{count_line,end,one_count,pinned_version,parse_limits,parse_warning,python_files,tree,unfinished}, pytest_end, suppressions_{count_line,exit_status,last,parse_exhausted,pin,pyi,reach,unfinished}, json_report_unread; also g1l's mypy/pytest unfinished_quiet, unread_only and pytest_unfinished_output | test_gate_contract.py, with the pin and parse cases in test_core_source.py |
| cast, cast_extensions, cast_reach | test_check_cast.py |
| mypy, mypy_tests_scope, g1l's mypy_imported_blocker, mypy-cache's mypy_cache | test_check_mypy.py |
| pyright, _findings, _message, _scope, _version | test_check_pyright.py |
| pytest | test_check_pytest.py |
| suppressions and its 22 grammar files | test_check_suppressions_{comments,bindings,patterns}.py |
| heavy, 6 files | test_heavy.py, with the throttle cases in test_core_checker.py |
| g1l's captured_output.py; mypy-cache's write_recorder.py and its test | tests/support/{capture,project,fake}.py |

The result is about 20 test files and about 5,000 lines, down from about 81 files and 8,800 lines.

## 4. Migration order

Each step follows the usual chain: stub, red tests from test-writer (reading this design and the stubgen view), build, blind reviews, `make check`, one commit. Sizes count the files written; deleted test files are listed but not counted.

A1 applies these five spec amendments:

- A checker run counts as finished only when its exit status is the one its report calls for.
- A gate's own lines are a closed set: the empty-run line, the pin error, pytest's seed, and a GateError's report (temp space, cleanup, or a checker that could not start or ran past its cap).
- An empty run prints its count line.
- A file given twice is one file in M.
- G9 admits the core modules and `tests/support/` as importers alongside gate scripts and their own tests.

| Step | Agent | Writes | Files |
|---|---|---|---|
| A1 | architect (design); general-purpose (gates spec) | This design into `docs/superpowers/specs/`, and the five spec amendments into the gates spec (docs only) | 2 |
| B1 | test-writer | tests/support/capture.py, tests/test_support_capture.py | 2 |
| B2 | gatesmith (source); test-writer (tests) | gates/core/__init__.py, report.py, tests/test_core_report.py | 3 |
| B3 | gatesmith (source); test-writer (tests) | gates/core/checker.py, tests/support/fake.py, tests/test_core_checker.py | 3 |
| B4 | gatesmith (source); test-writer (tests) | gates/core/project.py, source.py, tests/test_core_project.py, tests/test_core_source.py | 4 |
| B5 | gatesmith (source); test-writer (tests) | gates/core/runner.py, tests/support/project.py, tests/test_core_runner.py | 3 |
| C1 | gatesmith (source); test-writer (tests) | check_cast onto the core | 1-3 |
| C2 | gatesmith (source); test-writer (tests) | check_pyright; json_report.py deleted | 2-3 |
| C3 | gatesmith (source); test-writer (tests) | check_mypy, with the warm cache, the child process (measured first) and a red test for (a) | 2-3 |
| C4 | gatesmith (source); test-writer (tests) | check_suppressions on source.py; parse warnings become unfinished, as the spec says | 2-3 |
| C5 | gatesmith (source); test-writer (tests) | check_pytest, with g1l's whole console output for a module pytest did not finish | 2-3 |
| C6 | gatesmith (source); test-writer (tests) | heavy.py on `checker.run` and `throttle_line` | 2-3 |
| C7a-c | gatesmith (source); test-writer (tests) | The G4 branch rebased onto the core: first gate and outcome, then processes and throttle, then copy, git and parse; C7b's interface, the mutation run having no time cap and no cap on the mutants it checks: `docs/superpowers/specs/mutmut-run-design.md` | 2-4 each |
| D1 | test-writer | test_gate_contract.py with check_cast's entry; deletes cast's 6 contract files | 1 |
| D2-D5 | test-writer | One registry entry each for pyright, mypy, suppressions and pytest; deletes their 9, 6, 8 and 1 contract files, plus json_report_unread | 1 each |
| D6 | test-writer | Behavior-file merges for cast, mypy, pyright and pytest | 4 |
| D7-D9 | test-writer | Suppressions' 23 files into 3, one topic per step | 1 each |
| D10 | test-writer | Heavy's 6 files into 1 | 1 |
| D11 | test-writer | tests/test_gates_structure.py, last, once it is green | 1 |

That is 26 steps.

During the C steps, the old tests stay green because `main(paths)` keeps its signature. If an A1 amendment moves a test's expected value (the empty-run count line, the suppression warning rule, files given twice), the test changes in the same step under the queued R-tw-moved shape. It is not routed around. A gate that has not yet been ported keeps its copies until its step, but no fix adds a new copy: a finding in an unported gate waits for that gate's port.

In-flight work:

- **g1l and mypy-cache: neither is committed.** Their code is harvested (A1, B2, C2, C3, C5). Left of g1l's tests: the two unfinished_quiet files, unread_only and pytest_unfinished_output become C8 cases with exact expected lines (D1-D5), and imported_blocker moves to test_check_mypy.py (D6). g1l's captured_output.py, which runs gate code in a child, and mypy-cache's write_recorder.py are dropped: a scratch root the test owns, plus C12, proves placement and cleanup.
- **G4 branch: pause G4-3b B1-B4 until C7.** Then re-judge each finding against the ported code. B2 (copy2's OSError escaping) and the macOS throttle failure both fall under core rules and should disappear.
- **Queue items:** G1e and G1h remain spec questions; each later changes one adapter, or `python_files` only.
- **Worktrees:** each stays as a reference until its harvest step lands, then it is removed.

## 5. Structure first for M1-M3

Before each milestone's first chunk, one design step produces a document like this one. The owner approves it, and it goes in `docs/` so that test-writer and the blind reviewers read it. Rulings made at the cause then reach the reviewers, which the churn analysis found missing. The document contains:

1. A module map: each module's job in one line, and its interface as stubs ready for stubgen.
2. A table naming the one home for each shared concern (records and their serialization, errors, process running, config, output, cleanup, test helpers), and what that home replaces or forbids elsewhere.
3. The contract tests every piece must pass, and the tests/support helpers, written before any piece's own tests.
4. The chunk order, each chunk under five files, marking which chunks can run in parallel.
5. At most five decisions, each with a recommendation.

What each milestone's design step must settle:

- **M1:**
  - one definition per record in its domain module: answer primitives in `gauntlet/core/verdicts.py`, design records in `gauntlet/core/design.py`, cause records in `gauntlet/core/causes.py`, and workflow/recovery records in `gauntlet/core/records.py`; design and cause records retain their existing homes (`gauntlet/core/design.py:15`, `gauntlet/core/causes.py:12`); one JSON codec and catalog covers every domain for `state.json` and `trace.jsonl` (`docs/superpowers/specs/m1-core-records-design.md:673`)
  - one family of typed errors that carry data (the "No copy" bullet)
  - the stage table and round caps as data that `decide` reads
  - a role registry, so "every role has a schema" is a contract test over it, as C13 is here
  - State and Answer builders in tests/support

  M1.5's shell gate is built on this gates core, and is its first gate that runs no checker.
- **M2:**
  - the process-running seam that `docs/design.md` leaves unnamed: its Command/Completed/Runner shape, the same as `gates.core.checker`'s but written separately in `gauntlet/seams/`, because `gauntlet` may not import `gates`
  - a FakeRunner in tests/support
  - one git command builder that always passes `--git-dir` and `--work-tree`
  - the kind tables as data
  - the §4 hardening flags in one builder
- **M3:**
  - screens as a pure render function plus one writer, as `report.py` is here
  - the runner's result type (outcome and exception type only)
  - the land decision's inputs as one record
  - the layout of the fixture repository and the end-to-end harness

M1 record homes follow the module map and interfaces in `docs/superpowers/specs/m1-core-records-design.md:25`, `docs/superpowers/specs/m1-core-records-design.md:79`, `docs/superpowers/specs/m1-core-records-design.md:537` and `docs/superpowers/specs/m1-core-records-design.md:673`:

| Shared concern | One home | Forbids elsewhere |
|---|---|---|
| Answer primitives | gauntlet/core/verdicts.py | Duplicate answer primitives in any domain or consumer. |
| Design record definitions | gauntlet/core/design.py | Moving or copying design records into verdicts, records or a consumer. |
| Cause record definitions | gauntlet/core/causes.py | Moving or copying cause records into verdicts, records or a consumer. |
| Workflow and recovery records | gauntlet/core/records.py | A second definition of a workflow or recovery record. |
| Record serialization | gauntlet/core/codec.py | Domain-specific codecs or duplicate record catalogs. |
