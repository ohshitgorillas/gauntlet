# Gates core design

Approved 2026-10-20 under `~/dev/CLAUDE.md` §7a; the decisions taken are in section 7. It is based on a read-only survey of `~/dev/gauntlet` at a32db75, the uncommitted `g1l` and `mypy-cache` worktrees, and the G4 mutation branch (e46e613).

Not read: `gates/no_type_check.py`, which this design leaves unchanged; the G4 branch's `mutation_judge.py`, `mutation_settings.py` and `mutation_driver.py`; and `docs/design.md` beyond its outline, §8 and the uncommitted diff, because it says nothing about gates. Every section below is finished.

## Why

Each gate module on main carries its own copy of the run contract:

- 8 count-line f-strings
- 5 empty-run lines
- 6 `BLOCKED = 2` constants
- 5 `CONFIG`/`ROOT` lookups relative to `gates/`
- 4 copies of the output splitter
- 3 "unfinished" error types (json_report, check_suppressions, mutation_gate)
- 40 direct writes to stdout and stderr

The G4 branch adds another count line, error type, printer, temp dir, throttle and git environment. The copies have already drifted:

- **(a) mypy exit 1 with no record.** `check_mypy` reads it as finished. I verified it: with `MYPYPATH` set to site-packages, mypy prints `…/site-packages is in the MYPYPATH. Please remove it.` and the gate ends `check_mypy: 0 finding(s) in 1 Python file(s)` with exit 0. `mypy.api.run` returned `('', '', 1)`, so the refusal also got past its capture.
- **Parse warnings.** By the Gates intro, a warning during a parse means the file was not finished. 48a8771 fixed that in pyright's parse only. `check_suppressions.parse_pinned` still ignores `SyntaxWarning`, and no test covers it.
- **Empty runs.** Five gates print no count line on an empty run. The mutation gate prints one. The spec says the count line is printed "on every run".
- **Paths given twice.** mypy and pytest count such a file once in M. cast, pyright and suppressions count it twice.
- **Throttling.** The mutation gate hard-codes `nice … ionice -c3` and `sched_getaffinity`, and neither exists on macOS. `heavy.wrapped` already maps both hosts.
- **Exit 2 on an environment failure.** It was fixed one site at a time, three times (H-lock :55 and :72; mypy-cache :174 and :216). mypy-cache's `check_mypy` alone now has four `try/except OSError` blocks.

## 1. Core modules

There are five modules under `gates/core/`. They use the standard library only, import nothing from `gauntlet`, and hold no path of this repository. The imports form a chain with no cycles: report ← checker ← project ← source ← runner.

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

The "each Unfinished text once per run" rule settles G1l round 3's duplicate blocking error (D :94).

### checker.py: running a checker process

```python
Command(argv: tuple[str, ...], cwd: Path, env: Mapping[str, str] | None = None, timeout: float | None = None,
        throttled: bool = False, outputs: Mapping[str, Path] = {}, capture: bool = True, pass_fds: tuple[int, ...] = ())
Completed(status: int, stdout: str, stderr: str, timed_out: bool, outputs: Mapping[str, str | None])  # status as a shell reports it; .output() = stdout + stderr
type Runner = Callable[[Command], Completed]
def run(command: Command) -> Completed          # own session; the whole group is killed at the timeout or on any interrupt; GateError if the program cannot start
def python_module(module: str, *arguments: str | Path, cwd: Path, timeout: float | None = None) -> Command
def environment(*, drop_prefixes: tuple[str, ...] = (), drop: frozenset[str] = frozenset()) -> dict[str, str]
def throttle_line(platform: str, niceness: int) -> list[str]  # heavy's line; GateError on a host with none, or a tool not on PATH
def cpu_budget() -> int                          # floor(CPUs this process may run on / 2): the mutation and backstop cap
```

`outputs` names the files a checker writes, such as pytest's JUnit XML or mutmut's coverage record. `run` reads them back into `Completed.outputs`, so a gate reads its report from the Completed, and a fake can supply one without touching the filesystem.

**Replaces:**

- the subprocess calls in cast, pyright and pytest
- mypy's `api.run` (decision 3)
- `mutation_run`'s probe, mutate, stop, workers and NICE
- heavy's `wrapped`, `missing` and `status`, and its subprocess call
- `check_pytest.pytest_environment`

### project.py: the project, its config and its files

```python
Source(given: Path, absolute: Path)     # given: as the caller spelled it; absolute: os.path.abspath, the file's identity
def python_files(paths: Sequence[Path]) -> list[Source]  # the spec's Python-file rule; a file given twice is one Source, first spelling kept
def test_files(sources: Sequence[Source]) -> list[Source]     # the spec's one test-file definition
def non_test_files(sources: Sequence[Source]) -> list[Source]
Project(root: Path)
    Project.current() -> Project          # the working directory (decision 1); GateError if it holds no pyproject.toml
    .config -> Path                       # root / "pyproject.toml", the one file that holds every checker's settings
    .settings() -> Mapping[str, object]   # read once per run; GateError naming the file if unreadable or not TOML
    .setting(*keys: str) -> object | None
    .config_text() -> str                 # raw text, for rules about comments (G2's ignore reasons)
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

### runner.py: one gate run, from start to exit

```python
Gate(name: str, check: Callable[[Run], Outcome],
     select: Callable[[Sequence[Source]], list[Source]] = list, selects: str = "Python file")
Run(project: Project, sources: tuple[Source, ...], scratch: Scratch, process: Runner)
class Scratch:                                    # one per run
    __init__(self, root: Path | None = None)      # None: tempfile.gettempdir(), so TMPDIR moves it; never in the tree
    directory(self, name: str) -> Path            # a fresh dir inside the run's own temp dir; GateError on OSError
    copy(self, tree: Path, name: str) -> Path     # GateError on OSError
    once(self, name: str, make: Callable[[Path], None]) -> Path  # built the first time, the same path after (mypy's warm cache)
    close(self) -> str | None                     # deletes everything, read-only entries included; returns the failure, never raises
class Checker[R](Protocol):
    stopped: frozenset[int]                       # statuses where the checker stopped but its report stands (mypy: {2})
    def batches(self, run: Run) -> Sequence[Sequence[Source]]
    def command(self, run: Run, batch: Sequence[Source]) -> Command
    def read(self, completed: Completed) -> R     # GateError if the output holds no report the gate can read
    def expected_status(self, report: R) -> int   # the exit status this report calls for
    def lines(self, report: R, batch: Sequence[Source], *, stopped: bool) -> Sequence[Line]
def check_with(checker: Checker[R]) -> Callable[[Run], Outcome]
def run_gate(gate: Gate, paths: Sequence[Path], *, project: Project | None = None,
             process: Runner = run, scratch_root: Path | None = None) -> int
def main(gate: Gate) -> NoReturn
```

`run_gate` is the one place the contract is applied. It runs these steps in order:

1. Select the sources. If there are none, print `nothing_checked` and exit 1.
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

**Two rules come with the core:**

- A gate module writes output, starts a process or makes a temp dir only through these modules.
- Own code never runs only in a child process. The backstop counts such lines as unseen, and mutmut cannot reach them. So a child is always either a third-party checker or a module whose functions also have in-process tests, like the mutation driver.

## 2. A gate on the core

This is check_mypy in full, except `Record`, `record`, `describe` and `shown`, which stay in the gate:

```python
class Mypy:
    stopped = frozenset({2})                                  # a blocking error stops mypy; its records still stand

    def batches(self, run: Run) -> list[list[Source]]:
        return [[source] for source in run.sources]           # one mypy per file: no verdict depends on another file

    def command(self, run: Run, batch: list[Source]) -> Command:
        warm = run.scratch.once("warm", partial(warm_cache, run))   # one warm cache per run, one copy per file
        return python_module("mypy", "--config-file", run.project.config, "--cache-dir", run.scratch.copy(warm, "cache"),
                             "--show-absolute-path", "--no-error-summary", "--output", "json", batch[0].absolute,
                             cwd=run.project.root)

    def read(self, completed: Completed) -> list[Record]:
        return [record(line) for line in completed.stdout.splitlines()]   # record() raises GateError

    def expected_status(self, records: list[Record]) -> int:
        return 1 if records else 0                            # exit 1 with no record is a refusal, not a pass

    def lines(self, records: list[Record], batch: list[Source], *, stopped: bool) -> list[Line]:
        if stopped:
            return [Unfinished(describe(r)) for r in records] # every record, wherever it lies, once per run
        here = str(batch[0].absolute)
        return [line for r in records if r["file"] == here for line in shown(r)]  # a Finding per error, a Remark per note

GATE = Gate(name="check_mypy", check=check_with(Mypy()))

def main(paths: list[Path]) -> int:
    return run_gate(GATE, paths)
```

`warm_cache(run, directory)` runs mypy on an empty program through `run.process`. It raises GateError unless mypy exits 0, prints nothing and leaves a file. No count line, exit constant, printer, temp handling or OSError handling is left in the gate. `main(paths)` keeps today's signature, so the existing tests stay green during the port.

How the planned gates plug in:

- **ruff lint and format (G2).** One Checker each, with one batch. check_cast's ruff JSON reader moves to `gates/ruff_report.py`, shared with check_ruff. `expected_status` is `1 if entries else 0`, and E902 and invalid-syntax entries are Unfinished. The format check reads ruff's "Would reformat" lines. The ignore list, its reason comments and per-file-ignores become KeyRules, using `config_text`, in the suppression gate, where the spec lists them.
- **mutmut (G4) and the backstop.** These are plain `check(run)` functions, not Checkers. Each uses these core pieces:
  - `select=non_test_files`
  - `key_findings` over `[tool.mutmut]` or `[tool.coverage]`
  - `project.git("diff", "HEAD")` and `source.parse` to find changed functions
  - `scratch.copy` for the work copy
  - `run.process(Command(..., timeout=remaining, throttled=True, env=environment(drop_prefixes=("PYTEST_",)), outputs={"record": ...}))`
  - a GateError when `cpu_budget() == 0`

  At the cap, unchecked mutants are Findings (exit 1). Any other unfinished run returns the checker's error as Unfinished first, then the findings. The branch's `mutation_gate.py`, count line, `finish`, NICE, `workers`, `stop`, git environment and its separate exit-2 paths all go.
- **pytest (G3, already built).** A Checker with one batch per test module and `outputs={"junit": ...}`; the seed line is an Outcome note.
- **filepawl (G5), import-linter and vulture (G7), deptry and the lock check (G8).** Checkers. Each `read` guards its JSON and `expected_status` states the tool's documented exit rule. The runner makes M the Python files given, whatever else the checker reads.
- **test-shape (G6) and wiring (G9).** In-process `check(run)` over `source.parse` of `test_files`, the Makefile and `git ls-files`. No process runs.
- **suppression completion (G10).** KeyRule rows only.

## 3. Tests

There are three helpers in `tests/support/`. The spec already names that directory as the home of seeded strings.

- **`capture.py`.** `captured(call: Callable[[], T]) -> Captured[T]`, which has `.result`, `.out`, `.err` and `.merged`: `.out` and `.err` are the lines written to fd 1 and fd 2 (and to `sys.stdout` and `sys.stderr`), kept apart, and `.merged` is every line of both in the order written. How capture works is in `2026-10-20-capture-design.md`.
  - It sees writes to either Python stream in the order made, direct fd writes, and a checker child's output.
  - The gate's code runs in the test's own interpreter, so coverage and mutmut's trampolines reach it. g1l's child-interpreter helper cannot give that.
  - It replaces 12 files using capsys, 11 using redirect_stdout, 4 using capfd and 10 that start a child.
- **`project.py`.** `scaffold(root, files: Mapping[str, str | bytes], *, pyproject: str | None = None, unreadable: tuple[str, ...] = (), git: bool = False) -> Project`.
  - The default pyproject.toml is the repository's own, found from this module's path, so a gate test runs under `make check`'s settings.
  - `git=True` initialises a repository and commits, for the mutation gate, G8 and G9.
  - It replaces 58 `_seed` copies, the `_seed_tree` and `_layout` helpers, and the two `_tree` helpers that copy `gates/`.
- **`fake.py`.** `FakeRunner(replies: Sequence[Completed])` returns canned replies in order and records each Command. `completed(status=0, stdout="", stderr="", outputs={}) -> Completed` builds a reply.
  - Because the test seeds the checker's whole output, "prints what the checker reported and nothing else" becomes an exact list check, `lines == [*seeded, count]`, instead of a predicate over the printed lines.
  - That removes the cause of G1l's T1 cluster (`_carries_report`, `_first_number`), which was filed three times.

**Contract suite, `tests/test_gate_contract.py`.** It holds a registry with one entry per gate script: the module, a clean source, a one-finding source with a fragment of its message, the checker's empty report, and whether the gate parses. Every case runs over every entry:

- **C1** A clean run exits 0 with the count line last.
- **C2** One finding exits 1 with one line carrying it, and N=1.
- **C3** Exactly one line counts files, on every run.
- **C4** .py, .pyi and python-shebang files count; .pyw and other files do not; a file given twice counts once.
- **C5** The empty run.
- **C6** An unreadable file exits 2, and the other files' findings still print.
- **C7** An unparseable file exits 2.
- **C8** No readable report, through FakeRunner (garbage, a refusal, nonzero with an empty report, death by signal, a timeout): exit 2, and the output is exactly the checker's output followed by the count line; after a timeout, one gate line naming the cap comes between them (decision 2(ii)).
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

| Today (72 files on main, 7,714 lines, plus 9 uncommitted, about 1,100 lines) | Becomes |
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

A prerequisite is the queued R-helper job, which gives gatesmith a brief shape for a non-gate module under `gates/`; every B step is one. Each step follows the usual chain: stub, red tests from test-writer (reading this design once it is in `docs/`, plus the stubgen view), build, blind reviews, `make check`, one commit. Sizes count the files written; deleted test files are listed but not counted.

| Step | Writes | Files |
|---|---|---|
| A1 | This design into `docs/superpowers/specs/`, and the decision-2 amendments into the gates spec (docs only) | 2 |
| B1 | tests/support/capture.py, tests/test_support_capture.py | 2 |
| B2 | gates/core/__init__.py, report.py, tests/test_core_report.py | 3 |
| B3 | gates/core/checker.py, tests/support/fake.py, tests/test_core_checker.py | 3 |
| B4 | gates/core/project.py, source.py, tests/test_core_project.py, tests/test_core_source.py | 4 |
| B5 | gates/core/runner.py, tests/support/project.py, tests/test_core_runner.py | 3 |
| C1 | check_cast onto the core | 1-3 |
| C2 | check_pyright; json_report.py deleted | 2-3 |
| C3 | check_mypy, with the warm cache, the child process (measured first) and a red test for (a) | 2-3 |
| C4 | check_suppressions on source.py; parse warnings become unfinished, as the spec says | 2-3 |
| C5 | check_pytest, with g1l's whole console output for a module pytest did not finish | 2-3 |
| C6 | heavy.py on `checker.run` and `throttle_line` | 2-3 |
| C7a-c | The G4 branch rebased onto the core: first gate and outcome, then processes and throttle, then copy, git and parse | 2-4 each |
| D1 | test_gate_contract.py with check_cast's entry; deletes cast's 6 contract files | 1 |
| D2-D5 | One registry entry each for pyright, mypy, suppressions and pytest; deletes their 9, 6, 8 and 1 contract files, plus json_report_unread | 1 each |
| D6 | Behavior-file merges for cast, mypy, pyright and pytest | 4 |
| D7-D9 | Suppressions' 23 files into 3, one topic per step | 1 each |
| D10 | Heavy's 6 files into 1 | 1 |
| D11 | tests/test_gates_structure.py, last, once it is green | 1 |

That is 26 steps.

During the C steps, the old tests stay green because `main(paths)` keeps its signature. If an A1 amendment moves a test's expected value (the empty-run count line, the suppression warning rule, files given twice), the test changes in the same step under the queued R-tw-moved shape. It is not routed around. A gate that has not yet been ported keeps its copies until its step, but no fix adds a new copy: a finding in an unported gate waits for that gate's port.

In-flight work:

- **g1l: do not commit it.**
  - Its spec sentence goes into A1, widened into the closed set of the gate's own lines (decision 2).
  - `print_output` becomes `report.output_lines` (B2).
  - Its json_report edits disappear with json_report (C2).
  - `show_blocked` becomes mypy's `stopped` path plus the once-per-run rule (C3).
  - pytest's whole console output for an unfinished module goes into C5.
  - Its tests:
    - captured_output.py is dropped, because it runs gate code in a child.
    - The two unfinished_quiet files, unread_only and pytest_unfinished_output become C8 cases with exact expected lines (D1-D5).
    - imported_blocker moves to test_check_mypy.py (D6).
- **mypy-cache: do not commit it.**
  - Its Types-bullet sentence goes into A1 with one change: cache placement is judged by the scratch root the test hands the run, not by TMPDIR.
  - `warm`, `copy`, `remove`, `check_copy` and `check_copied` become `Scratch.once`, `copy` and `close` (C3). Its four `try/except OSError` blocks go away.
  - write_recorder.py and its test (329 lines) are dropped. A scratch root the test owns, plus C12, proves both placement and cleanup without an audit hook.
  - The cache test's cases, the open :109 finding, and G-mypy-cache-gap's failed-warm and failed-copy paths become test_check_mypy.py cases using FakeRunner.
- **G4 branch (e46e613): pause G4-3b B1-B4 until C7.** Then re-judge each finding against the ported code. B2 (copy2's OSError escaping) and the macOS throttle failure both fall under core rules and should disappear.
- **Queue items the core absorbs:** G1f (in B4), T-capture (in B1 and D), G1m (M is `len(sources)`, in B5) and Q-C's count question (in C4). G1e and G1h remain spec questions; each one later changes one adapter, or `python_files` only.
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
  - one record-type module and one JSON codec for `state.json` and `trace.jsonl`
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

## 6. Decisions for the owner

1. **Project root.** I recommend the working directory, which is where `make check` and pre-commit run, with a `project=` parameter for tests and other callers. It should never be relative to `gates/`, and never a nearer pyproject.toml, which the spec forbids reading. The alternative is the git top level of the given files, as the mutation gate's `tree_root` does it, but that puts a git repository in every test tree. The test-file rule's `tests` directory stays one constant in project.py until a second project needs a different one.
2. **Spec amendments in A1.** I recommend all five:
   - (i) a checker run counts as finished only when its exit status is the one its report calls for
   - (ii) a gate's own lines are a closed set: the empty-run line, the pin error, pytest's seed, and a GateError's report (temp space, cleanup, or a checker that could not start or ran past its cap). This reconciles g1l's "nothing of its own" with mypy-cache's "prints the error".
   - (iii) an empty run prints its count line, as "on every run" reads
   - (iv) a file given twice is one file in M
   - (v) G9's "nothing imports it except gate scripts and its own tests" also admits the core modules and `tests/support/`; as written, the core importing itself would be a finding
3. **mypy as a child process.** I recommend running `python -m mypy` per file from the warm cache, replacing `mypy.api.run`. `api.run` let the MYPYPATH refusal escape its capture, shares the gate's interpreter state, and keeps mypy out of the single Checker driver. The cost is one interpreter start per file, which has not been measured. Measure it in C3, and keep `api.run` only if the cost turns out large.
4. **Where the core lives.** I recommend `gates/core/` now: standard library only, nothing from `gauntlet`, no repository path. Extracting it for HQPTuner is then a move of `gates/`, `tests/support/` and the gate tests. The alternative, a separate package now, adds a pinned dependency and a second repository before the design has run even once.
5. **In-flight work.** I recommend:
   - committing neither g1l nor mypy-cache, and harvesting them as section 4 describes
   - folding G1l, G-mypy-cache, G-mypy-cache-gap, T-capture, G1f and G1m into the steps above and closing them
   - pausing G4-3b B1-B4 until C7

## 7. Decisions taken (2026-10-20)

- 1, project root: the working directory, with a `project=` parameter for tests and other callers; never relative to `gates/`, never a nearer pyproject.toml. (Void, technical.)
- 2, spec amendments: all five, (i) to (v), as written above, land in step A1. (Void, technical.)
- 3, mypy as a child process (`python -m mypy` per file, from the warm cache), with its cost measured in C3; keep `mypy.api.run` only if that cost is large. (Void, technical.)
- 4, the core lives in `gates/core/` inside Gauntlet for now: standard library only, nothing Gauntlet-specific, extractable later for HQPTuner. (Owner.)
- 5, in-flight work: g1l and mypy-cache are not committed; their good parts are harvested as section 4 describes. G1l, G-mypy-cache, G-mypy-cache-gap, T-capture, G1f and G1m fold into the core steps and close. G4-3b B1-B4 pause until C7. (Owner.)
- 6, GateError keeps `.report`, the report as given, and the runner reads that named field. (Void, technical.)
- 7, `render` passes every Finding and Remark text through `one_line`, the one home for that rule. (Void, technical.)
- 8, `render` passes each Unfinished text through `output_lines`, the one home for that rule. (Void, technical.)
