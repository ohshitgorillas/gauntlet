Status: approved by the owner.

## Why

C7c is the mutation gate's last port step, "copy, git and parse". It builds the `Plan` that C7b's `run_mutmut` takes from the changed functions of the given files and the copy mutmut works in. The gate holds the gap as a body that only raises (`gates/check_mutation.py:91`–`:100`).

The G4 branch the gate is ported from (`.claude/worktrees/agent-a3292c4f570aba00b/`, cited below as `G4/`) and the tree hold 20 copies of what the core owns, of what C7b gives one home, or of what this design gives one:

- **Running git, 5 copies.** G4's `git_environment` runs `git rev-parse --local-env-vars` itself (`G4/gates/mutation_changes.py:18`–`:29`), its `git` runs its own `subprocess.run` (`:32`–`:34`), and `tree_root` takes the git top level (`:37`–`:46`), which the gates core design refuses as the project root. G4's test scrubs `GIT_` itself and seeds its own repository (`G4/tests/test_check_mutation.py:108`, `:117`–`:142`). The homes are `Project.git` (`gates/core/project.py:168`–`:171`) and `scaffold(git=True)` (`tests/support/project.py:63`–`:67`).
- **A file's path in the project, 2 copies.** G4's `relative`, through `realpath` (`G4/gates/mutation_changes.py:49`–`:55`), and `module_classname`'s test, lexical (`gates/check_pytest.py:68`–`:70`). The core has no home for it.
- **Reading and parsing a Python file, 2 copies.** G4 parses with `parse_pinned` and its own list of failures (`G4/gates/mutation_changes.py:99`–`:103`) beside `source.parse` (`gates/core/source.py:62`–`:85`), and reads the pin with `pinned_grammar` (`G4/gates/check_mutation.py:55`) beside `pinned_version` (`gates/core/source.py:34`), which the gate already uses (`gates/check_mutation.py:127`).
- **Files placed in temp space, 4 copies.** `shutil.copy2` with its OSError left to escape (`G4/gates/mutation_copy.py:29`–`:32`), the shape of G4 finding B2; a `TemporaryDirectory` and `mkdir` (`G4/gates/check_mutation.py:68`–`:71`) beside `Scratch` (`gates/core/runner.py:21`); the settings file written by hand (`G4/gates/check_mutation.py:80`); and mutmut's layout spelled in the gate, `MUTANTS` and `mutated_name` (`G4/gates/mutation_copy.py:13`, `:24`), where C7b gives mutmut's file locations one home in the driver.
- **The test-file rule, 3 copies.** `check_pytest.select` in `copy_suite` and in `sources` (`G4/gates/mutation_copy.py:59`, `G4/gates/check_mutation.py:28`), and `CONFTEST` taken from check_pytest (`G4/gates/mutation_copy.py:8`, `:40`), beside `test_files` and `CONFTEST` (`gates/core/project.py:82`, `:31`).
- **mutmut's API outside the driver, 1 copy.** `mangle_function_name` imported in the gate (`G4/gates/mutation_changes.py:9`), where C7b allows mutmut's API only in the driver.
- **pytest's settings on a command line, 2 copies.** `-c` and the config spelled in mutmut's settings (`G4/gates/mutation_settings.py:51`) and in the pytest gate's command (`gates/check_pytest.py:156`–`:158`).
- **One-line output, 1 copy.** `check_pytest.one_line` imported for git's errors (`G4/gates/mutation_changes.py:11`) beside `report.one_line` (`gates/core/report.py:63`).

Git runs through `Project.git` on `run.process`, so the core's runner starts it and `mutate` starts no process of its own. The mutmut run design's forbid, "a process started in `mutate` or anywhere in C7c", is reworded in step 2 to name that one path.

## Modules

### `gates/core/runner.py`: `Scratch.place`

Its job is unchanged. `Scratch` gains the one way to put named files, copied or written, in a fresh directory of the run's temp space.

```python
class Scratch:  # gains
    def place(self, name: str, files: Mapping[str, Path | str]) -> Path
        # a new directory as directory(name) gives, holding each entry at its key, a relative POSIX path, its parents made:
        # a Path's bytes and permission bits, a symlink followed to what it names; a str written as UTF-8.
        # GateError naming the entry and the OS error, as copy's; GateError for a key that is absolute or holds a ".." part
```

It replaces G4's `copy` (`G4/gates/mutation_copy.py:29`–`:32`), its temp directories (`G4/gates/check_mutation.py:68`–`:71`) and its settings write (`:80`) (decision 3).

### `gates/core/project.py`: `Project.located` and `Project.files`

Its job is unchanged. `Project` gains a file's path in the project and the list of the tree's files.

```python
class Project:  # gains
    def located(self, absolute: Path) -> str | None
        # the path relative to root as a POSIX string, compared lexically as os.path.abspath spells both; None outside root
    def files(self, *, process: Runner = run) -> tuple[str, ...]
        # self.git("ls-files", "-z", "--cached", "--others", "--exclude-standard", process=process): each path, relative
        # to root, that names a regular file once symlinks are followed, in git's order; GateError carrying git's output
        # on a nonzero exit (decision 1)
```

`located` replaces G4's `relative` (`G4/gates/mutation_changes.py:49`–`:55`) and the path test in `module_classname` (`gates/check_pytest.py:68`–`:70`). `files` lists the tree as `make check` lists it (`Makefile:7`).

### `gates/mutmut_driver.py`: the copy's layout, mutmut's settings file and mutmut's functions

Its job, C7b's, gains the gate-side knowledge of where mutmut wants its files and which functions it mutates. Every function here is pure but `MUTMUT.mangle`, and each runs in the gate's own process.

```python
MUTANTS: str = "mutants"                                    # the directory of the copy where mutmut runs the tests, and every file it does not mutate goes
SOURCE_PATHS: str = "source_paths"                          # mutmut's [tool.mutmut] keys this module writes;
PYTEST_ARGUMENTS: str = "pytest_add_cli_args"               # check_mutation.SCOPE_KEYS names them through these (decision 9)
TEST_SELECTION: str = "pytest_add_cli_args_test_selection"

class Mutmut(Protocol):  # C7b's protocol (mutmut run design, decision 4), gaining:
    def mangle(self, name: str, class_name: str | None) -> str: ...
        # mutmut's mangled name of a function, a method's with its class (decision 2): the name changed_mutants matches it by,
        # so changed_mutants(self, {path: frozenset({self.mangle(name, class_name)})}) keeps that function's mutants and no other's (decision 8)

MUTMUT: Mutmut  # C7b's, gaining mangle: mutmut 3.8.0's mangle_function_name
```

```python
def mutable(located: str) -> bool        # False for a conftest.py and a .pyi, never mutated (quality gates spec :80, :83)
def mutated_path(located: str) -> str    # where a mutated file goes in the copy: located for a .py, located + ".py" for an extensionless file (:83)
def unmutated_path(located: str) -> str  # where every other file goes: MUTANTS / located
def settings_text(mutated: Sequence[str], tests: Sequence[str], pytest_arguments: Sequence[str]) -> str
    # the [tool.mutmut] table mutmut reads from Plan.settings: SOURCE_PATHS, PYTEST_ARGUMENTS and TEST_SELECTION, each a TOML array of strings
def function_spans(tree: ast.Module, mutmut: Mutmut = MUTMUT) -> dict[str, range]
    # each function mutmut mutates, by mutmut.mangle: every module-level function and every method of a module-level class,
    # first decorator to last line
```

`MUTMUT.mangle` is mutmut 3.8.0's `mangle_function_name`, as G4 imports it (`G4/gates/mutation_changes.py:9`) against the same lock (`G4/uv.lock:471`–`:472`). `function_spans` keeps G4's rule (`G4/gates/mutation_changes.py:78`–`:94`); whether it matches every function 3.8.0 mutates is unmeasured. Whether `changed_mutants` matches on the names `mangle_function_name` gives, the rule step 19's red test reads (decision 8), is unmeasured. It replaces G4's `MUTANTS`, `STUB_SUFFIX` and `mutated_name` (`G4/gates/mutation_copy.py:11`–`:26`), `function_spans` and `span` (`G4/gates/mutation_changes.py:78`–`:94`), and `mutmut_settings` (`G4/gates/mutation_settings.py:46`–`:57`).

`MUTANTS` is mutmut's directory, the `mutants/` the quality gates spec names, and the three key names are the keys `SCOPE_KEYS` spells (`gates/check_mutation.py:29`–`:31`). C7b's `meta_path` builds on `MUTANTS`, its one spelling, a move that keeps behavior, held by C7b's tests of `mutmut_command`, whose Command names each changed file's report among its outputs (decision 9).

### `gates/check_pytest.py`: `settings_arguments`

Its job is unchanged. It gains the one builder of the arguments that root a pytest run in its settings.

```python
def settings_arguments(config: Path, root: Path) -> tuple[str, ...]
    # ("-c", str(config), f"--rootdir={root}"): pytest takes its settings from config alone, rooted at root
```

The pytest gate's command takes it with the project's config and root (`gates/check_pytest.py:156`–`:158`), and mutmut's settings take it with the copy's. `module_classname` tests its path through `Project.located` (`:68`–`:70`). Both moves keep behavior, held by the pytest gate's tests already in the tree (decision 9). It replaces G4's `pytest_arguments` (`G4/gates/mutation_settings.py:51`).

### `gates/check_mutation.py`: the changed functions and the copy

Its job, C7b's, gains the git, parse and copy steps that build the `Plan` and the `mutate` that hands it to `run_mutmut`.

```python
@dataclass(frozen=True)
class Changes:  # what `git diff HEAD` changed in one file, numbered as the file is now
    lines: frozenset[int]               # each line changed or added
    cuts: frozenset[int] = frozenset()  # each c where lines were removed between c and c + 1 and none added (decision 4)

@dataclass(frozen=True)
class Selection:  # what the git and parse steps found, before anything is copied
    changed: Mapping[str, frozenset[str]]    # each file to mutate, by Project.located: its changed functions' mangled names
    given: Mapping[str, Source]              # the same files: the Source each was given as
    unfinished: tuple[Unfinished, ...] = ()  # each given file outside the project (decision 5) or that parse leaves unfinished, in given order

def hunk_changes(diff: str) -> Changes
    # each hunk header of a --unified=0 diff: `+s,n` with n > 0 adds lines s to s + n - 1, `+s` adds line s, `+s,0` adds cut s
def changed_functions(spans: Mapping[str, range], changes: Changes | None) -> frozenset[str]
    # None, a new file: every name; else each name whose span holds a line of changes.lines, or both c and c + 1 for a cut c
```

```python
def has_head(run: Run) -> bool
    # run.project.git("rev-parse", "--verify", "--quiet", "HEAD", process=run.process) exiting 0 is True; else
    # run.project.git("rev-parse", "--git-dir", process=run.process) exiting 0 is False, a repository with no commit;
    # else a GateError carrying git's output
def changes(run: Run, located: str, head: bool) -> Changes | None
    # None, a new file, when head is False or `git ls-tree --name-only HEAD -- <located>` prints nothing; else
    # hunk_changes of `git diff --no-color --no-ext-diff --unified=0 HEAD -- <located>`; each git through
    # run.project.git(..., process=run.process), a nonzero exit a GateError naming the file and carrying git's output
def select_changes(run: Run, version: tuple[int, int], *, mutmut: Mutmut = MUTMUT) -> Selection
def lay_out(run: Run, selection: Selection) -> Plan
def mutate(run: Run, version: tuple[int, int]) -> Mutated
```

`select_changes` takes these steps:

1. Each file of `run.given`, test files included, that `run.project.located` places outside the project is an Unfinished naming it as given and the project root, and goes no further (decision 5).
2. Each of `run.sources`, in order, that `mutable` refuses is not mutated.
3. Each other is read through `source.parse(source, version)`. An Unfinished is kept, and the file is not mutated.
4. `has_head` is called once, at the first file parsed. A parsed file's changed functions are `changed_functions(function_spans(parsed.tree, mutmut), changes(run, located, head))`; a file with none is not mutated.

`lay_out` takes these steps:

1. `work` is `run.scratch.place("work", ...)`: each file of `selection.changed` at `mutated_path(located)`, from its Source's absolute path; every other file `run.project.files(process=run.process)` lists (decision 1), each given file inside the project, and the project's config, at `unmutated_path(located)`.
2. `settings` is `run.scratch.place("settings", {CONFIG: settings_text(mutated, tests, settings_arguments(work / MUTANTS / CONFIG, work / MUTANTS))})`, `mutated` being the mutated paths and `tests` the located path of each of `test_files(run.given)` inside the project. pytest reads the copy's config, rooted in the copy, so no pytest run writes in the tree (quality gates spec `:92`).
3. The Plan holds `settings`, `work`, and `changed` and `given` keyed by `mutated_path`.

`mutate` calls `select_changes(run, version)`. With no file to mutate it returns `Mutated(unfinished=selection.unfinished)`: nothing is placed and mutmut does not run. Otherwise it returns `run_mutmut(run, lay_out(run, selection))` with the selection's Unfinished lines before its own. A GateError from any step goes to `check`, which makes it the run's one Unfinished (`gates/check_mutation.py:129`–`:132`).

It replaces the raising body of `mutate` (`gates/check_mutation.py:91`–`:100`), G4's `mutation_changes.py` and `mutation_copy.py` whole, and G4's plan, copy and settings steps in `main` (`G4/gates/check_mutation.py:52`–`:80`).

`SCOPE_KEYS` names `source_paths`, `pytest_add_cli_args` and `pytest_add_cli_args_test_selection` (`gates/check_mutation.py:29`–`:31`) through the driver's key names, a move that keeps behavior, held by the gate's key tests already in the tree (`tests/test_check_mutation_core.py:194`) (decision 9).

## Homes

| Concern | Its one home | What it forbids elsewhere |
|---|---|---|
| Running git | `Project.git(..., process=run.process)` (`gates/core/project.py:168`) | `subprocess` or a `"git"` argv in a gate; a list of `GIT_` variables; the git top level as a root (gates core design, decision 1) |
| A file's path in the project | `Project.located` | `relpath`, `relative_to` or `is_relative_to` on a file's path in a gate |
| The tree's files | `Project.files` (decision 1) | An `ls-files` argv in a gate |
| Reading and parsing a Python file | `source.parse` under `source.pinned_version` (`gates/core/source.py:62`, `:34`) | `ast.parse`, a file read, or a list of parse failures in a gate |
| What `git diff HEAD` changed | `check_mutation.changes` and `hunk_changes` (decision 4) | A hunk-header pattern anywhere else |
| Which functions mutmut mutates, and their names | `mutmut_driver.function_spans` through `Mutmut.mangle` (decision 2) | An AST walk for mutmut's functions, or a mangling rule, in `check_mutation`; a `mutmut` import outside the driver; a mangled name spelled in a test or a gate (decision 8) |
| Which given files are never mutated | `mutmut_driver.mutable` | A `.pyi` or `conftest.py` test in `check_mutation` |
| The copy's layout and mutmut's settings file | `mutmut_driver`'s `MUTANTS`, `mutated_path`, `unmutated_path`, `settings_text` and its key names | A path in the copy, a `[tool.mutmut]` key or TOML text spelled in `check_mutation` |
| Files placed in temp space | `Scratch.place` and `Scratch.copy` (`gates/core/runner.py:44`) (decision 3) | `shutil`, a file write or a `mkdir` in a gate |
| pytest's settings on a command line | `check_pytest.settings_arguments` | `-c` or `--rootdir` spelled anywhere else |
| The test-file rule | `test_files` and `non_test_files` (`gates/core/project.py:82`, `:92`) | `check_pytest.select` or a `conftest.py` rule of its own in the mutation gate |
| A file the checker did not finish | An `Unfinished` in `Selection.unfinished` (decision 5) | An exception that ends the run for one file |
| A move onto a home that keeps behavior | The moved module's block of **Modules**, built by that module's build step and held by the tests already in the tree under the build commit's `make check` (decision 9) | The move named in a brief or a step's text, a step of its own for it, or the old spelling left beside its home |
| A stub's signatures | Its module's block of **Modules**, the one spelling, each declaration line written word for word, up to its comment, in its stub step's block in **Order**, which every architect `rulings` pass that touches the module's block rewrites beside it and the architect's reread checks against it (decisions 10, 11) | A signature in a stub step's block that its module's block does not give word for word; a declaration a stub writes that its step's block does not list; an edit to a module's block that leaves its stub step's block behind |
| A repository in tests | `scaffold(..., git=True)` (`tests/support/project.py:63`), then the test's own writes for a change; `FakeRunner` and `completed` for git's replies (`tests/support/fake.py:16`, `:32`) | A test's own `git init` or commit, or its own `GIT_` scrub |

A builder that needs what these homes lack stops and reports it, and writes no copy.

## Order

Each step lands green under `make check` before the next starts, save a `stub` step and a red step, which land in the commit of the build that turns those red tests green. Each stub step writes one module and is paired with the one build step that turns all its red tests green. A red step holds one behavior, the one name it gives, as **Modules** gives it; its brief carries no path, fixture or fake, so its Paths are `tests/`, the one file `test-writer` names in its report. A build step is a `gatesmith` module step: one module by its path and its block of **Modules**, on the red tests of its own stub's group; what that block moves onto a home is held by the tests already in the tree (decision 9). Whether a `gatesmith` module step builds what its block gives beyond its red tests is unmeasured, so a move it gets wrong shows first at the build commit's `make check`.

A stub step's text holds a fenced block of each declaration line its module's block of **Modules** gives, word for word up to its comment, so its brief, the plan step's text, carries every signature the stub writes (decision 10). The module's block is the one spelling; the step's block is its copy, rewritten beside it by every architect `rulings` pass that touches the module's block and checked against it at the architect's reread, and how often an edit reaches one and misses the other is unmeasured (decision 11). A stub step writes each declaration its block lists and no other, a constant at the value given there, a dataclass's fields, a Protocol's signatures and each new function's or method's body raising `NotImplementedError`, and changes no line already in the module save `mutate`'s body at step 21.

Step 1 and steps 3 to 12 run beside C7b, steps 10 to 12 once step 9 lands. Step 2 waits for C7b's step 7, the architect pass that writes the mutmut run design (`docs/superpowers/specs/mutmut-run-design.md:160`). Steps 13 to 20 wait for C7b's step 34, the last C7b step that writes `gates/check_mutation.py` or `gates/mutmut_driver.py` (`docs/superpowers/specs/mutmut-run-design.md:187`), and run beside steps 10 to 12. Step 21 waits for steps 2, 5, 9, 12 and 20.

1. The gates core design's `runner.py` block names `place` (`docs/superpowers/specs/gates-core-design.md:153`–`:158`), its `project.py` block names `located` and `files` (`:101`–`:107`), and its C7a-c row points here for C7c (`:338`). The quality gates spec's changed-function rule (`docs/superpowers/specs/quality-gates-design.md:81`) holds decision 4's ruling, and its closed set of a gate's own lines (`:30`) holds decision 5's. The gap list decision 7 closes is removed. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/gates-core-design.md`, `docs/superpowers/specs/quality-gates-design.md`, `docs/superpowers/audits/mutation-plan-gaps.md`.
2. The mutmut run design's forbid (`docs/superpowers/specs/mutmut-run-design.md:131`) names git through `Project.git` on `run.process` as the one process C7c reaches, and its driver block points here for C7c's additions (`:78`–`:101`). Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/mutmut-run-design.md`.
3. `stub`: `Scratch.place`. Agent: `gatesmith`, no red test. Paths: `gates/core/runner.py`.

   ```python
   class Scratch:
       def place(self, name: str, files: Mapping[str, Path | str]) -> Path
   ```

4. Red test: `Scratch.place`. Agent: `test-writer`. Paths: `tests/`.
5. `gates/core/runner.py`, as its block of **Modules** gives it. Lands with steps 3 and 4. Agent: `gatesmith`, red test from step 4. Paths: `gates/core/runner.py`.
6. `stub`: `Project.located` and `Project.files`. Agent: `gatesmith`, no red test. Paths: `gates/core/project.py`.

   ```python
   class Project:
       def located(self, absolute: Path) -> str | None
       def files(self, *, process: Runner = run) -> tuple[str, ...]
   ```

7. Red test: `Project.located`. Agent: `test-writer`. Paths: `tests/`.
8. Red test: `Project.files`. Agent: `test-writer`. Paths: `tests/`.
9. `gates/core/project.py`, as its block of **Modules** gives it. Lands with steps 6 to 8. Agent: `gatesmith`, red tests from steps 7 and 8. Paths: `gates/core/project.py`.
10. `stub`: `settings_arguments`. Agent: `gatesmith`, no red test. Paths: `gates/check_pytest.py`.

    ```python
    def settings_arguments(config: Path, root: Path) -> tuple[str, ...]
    ```

11. Red test: `settings_arguments`. Agent: `test-writer`. Paths: `tests/`.
12. `gates/check_pytest.py`, as its block of **Modules** gives it (decision 9). Lands with steps 10 and 11. Agent: `gatesmith`, red test from step 11. Paths: `gates/check_pytest.py`.
13. `stub`: in the driver, `MUTANTS`, `SOURCE_PATHS`, `PYTEST_ARGUMENTS` and `TEST_SELECTION` at their values, `mangle` in the `Mutmut` Protocol and on `MUTMUT`, `mutable`, `mutated_path`, `unmutated_path`, `settings_text` and `function_spans`. Agent: `gatesmith`, no red test. Paths: `gates/mutmut_driver.py`.

    ```python
    MUTANTS: str = "mutants"
    SOURCE_PATHS: str = "source_paths"
    PYTEST_ARGUMENTS: str = "pytest_add_cli_args"
    TEST_SELECTION: str = "pytest_add_cli_args_test_selection"

    class Mutmut(Protocol):
        def mangle(self, name: str, class_name: str | None) -> str: ...

    MUTMUT: Mutmut

    def mutable(located: str) -> bool
    def mutated_path(located: str) -> str
    def unmutated_path(located: str) -> str
    def settings_text(mutated: Sequence[str], tests: Sequence[str], pytest_arguments: Sequence[str]) -> str
    def function_spans(tree: ast.Module, mutmut: Mutmut = MUTMUT) -> dict[str, range]
    ```

14. Red test: `mutable`. Agent: `test-writer`. Paths: `tests/`.
15. Red test: `mutated_path`. Agent: `test-writer`. Paths: `tests/`.
16. Red test: `unmutated_path`. Agent: `test-writer`. Paths: `tests/`.
17. Red test: `settings_text`. Agent: `test-writer`. Paths: `tests/`.
18. Red test: `function_spans`. Agent: `test-writer`. Paths: `tests/`.
19. Red test: `MUTMUT.mangle`, as the driver block gives its rule, no mangled name spelled (decision 8). Agent: `test-writer`. Paths: `tests/`.
20. `gates/mutmut_driver.py`, as its block of **Modules** gives it (decision 9). Lands with steps 13 to 19. Agent: `gatesmith`, red tests from steps 14 to 19. Paths: `gates/mutmut_driver.py`.
21. `stub`: `Changes`, `Selection`, `hunk_changes`, `changed_functions`, `has_head`, `changes`, `select_changes` and `lay_out`, and `mutate`'s body raising `NotImplementedError` in place of its GateError (`gates/check_mutation.py:96`–`:100`), so its red test reads `NotImplementedError`. Agent: `gatesmith`, no red test. Paths: `gates/check_mutation.py`.

    ```python
    @dataclass(frozen=True)
    class Changes:
        lines: frozenset[int]
        cuts: frozenset[int] = frozenset()

    @dataclass(frozen=True)
    class Selection:
        changed: Mapping[str, frozenset[str]]
        given: Mapping[str, Source]
        unfinished: tuple[Unfinished, ...] = ()

    def hunk_changes(diff: str) -> Changes
    def changed_functions(spans: Mapping[str, range], changes: Changes | None) -> frozenset[str]
    def has_head(run: Run) -> bool
    def changes(run: Run, located: str, head: bool) -> Changes | None
    def select_changes(run: Run, version: tuple[int, int], *, mutmut: Mutmut = MUTMUT) -> Selection
    def lay_out(run: Run, selection: Selection) -> Plan
    def mutate(run: Run, version: tuple[int, int]) -> Mutated
    ```

22. Red test: `hunk_changes`. Agent: `test-writer`. Paths: `tests/`.
23. Red test: `changed_functions`. Agent: `test-writer`. Paths: `tests/`.
24. Red test: `has_head`. Agent: `test-writer`. Paths: `tests/`.
25. Red test: `changes`. Agent: `test-writer`. Paths: `tests/`.
26. Red test: `select_changes`. Agent: `test-writer`. Paths: `tests/`.
27. Red test: `lay_out`. Agent: `test-writer`. Paths: `tests/`.
28. Red test: `mutate`. Agent: `test-writer`. Paths: `tests/`.
29. `gates/check_mutation.py`, as its block of **Modules** gives it (decision 9). Lands with steps 21 to 28. Agent: `gatesmith`, red tests from steps 22 to 28. Paths: `gates/check_mutation.py`.

## Decisions taken

Each entry gives the question, or for a `new:` ruling a name for the structure, in bold, the owner's ruling verbatim, `Adds:` each module, home and step the ruling adds, and `Written in:` each section it touches.

1. **What does the copy hold?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." No conflict was brought on this decision, so the recommendation is taken: every file `Project.files` lists, the tree as `make check` lists it (`Makefile:7`), with the given files and the config. Adds: `Project.files` in `gates/core/project.py`; the home "The tree's files"; `lay_out`'s step 1 placing every listed file, and `files` in steps 1, 6, 8 and 9. Written in: **Modules**, **Homes**, **Order**, **Decisions taken**.
2. **Where is a function's mangled name made?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." No conflict was brought on this decision, so the recommendation is taken: `Mutmut.mangle` in the driver's protocol, called by `function_spans` in the gate's process, C7b's `Plan` as approved. Adds: `Mutmut.mangle` and `function_spans` in `gates/mutmut_driver.py`; the home "Which functions mutmut mutates, and their names"; `mangle` in steps 13, 19 and 20, and `function_spans` in steps 13, 18 and 20. Written in: **Modules**, **Homes**, **Order**, **Decisions taken**.
3. **Where are files placed in temp space?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." No conflict was brought on this decision, so the recommendation is taken: `Scratch.place` in the core. Adds: `Scratch.place` in `gates/core/runner.py`; the home "Files placed in temp space"; `place` in steps 1, 3, 4 and 5, and in `lay_out`'s steps 1 and 2. Written in: **Modules**, **Homes**, **Order**, **Decisions taken**.
4. **Is a function whose lines were only removed a changed function?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." No conflict was brought on this decision, so the recommendation is taken: yes, when the removal lies inside its span. Adds: `Changes.cuts` in `gates/check_mutation.py`, with `hunk_changes`' cut and `changed_functions`' rule for it; the home "What `git diff HEAD` changed"; step 1's amendment of the quality gates spec's changed-function rule, and `Changes` in steps 21 and 29 and in the red tests of steps 22, 23 and 25. Written in: **Modules**, **Homes**, **Order**, **Decisions taken**.
5. **What does a given file outside the project give?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." No conflict was brought on this decision, so the recommendation is taken: an Unfinished for that file, naming it as given and the project root, the run going on over the others. Adds: `Selection.unfinished` in `gates/check_mutation.py` and `select_changes`' step 1; the home "A file the checker did not finish"; step 1's addition to the closed set of a gate's own lines, and `Selection` in steps 21 and 29 and in the red tests of steps 26 to 28. Written in: **Modules**, **Homes**, **Order**, **Decisions taken**.
6. **The 16 gaps closed in this design.** Ruling: "Yes, have the architect fix it (the gaps: /tmp/c7c-gaps-gaps.md, all 16)" The list it names lies outside the repository, where the architect does not read, so no gap is designed by this entry; decision 7 asks where the list reaches the architect. Adds: none; decision 7. Written in: **Decisions for the owner**, **Decisions taken**.
7. **Where does the architect read the 16 gaps ruling 6 closes?** Ruling: "Sounds good, keep things rolling, as I said" Adds: the values of `MUTANTS` and the three key names, `mangle` on `MUTMUT` and its rule through `changed_mutants` in `gates/mutmut_driver.py`, and `SCOPE_KEYS` on those names in `gates/check_mutation.py`; the home "A move onto a home that keeps behavior", and a mangled name forbidden in a test or a gate; step 1's removal of the list, and step 2 after C7b's step 7 (gap 2); one module per stub at steps 3, 6, 10, 13 and 21, each paired with its one build at step 5, 9, 12, 20 or 29 (gaps 5, 7), step 13 writing the constants' values and `MUTMUT`'s `mangle` (gaps 8, 9), step 21 `mutate`'s body raising `NotImplementedError` (gap 15); red steps 4, 7, 8, 11, 14 to 19 and 22 to 28, one behavior each with no path, fixture or fake in the brief (gaps 4, 10, 12, 14); build steps naming a module and its block, its moves held by the tree's tests (gaps 11, 13, 16); decisions 8 and 9. Written in: **Why**, **Modules**, **Homes**, **Order**, **Decisions for the owner**, **Decisions taken**.
8. **Where does the red test of `MUTMUT.mangle` take its expected names?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." No conflict was brought on this decision, so the recommendation is taken: from the rule the driver block gives `mangle`, that `changed_mutants` keeps a function's mutants and no other's when handed `mangle`'s name for it, so no mangled name is spelled in a test, and no spike step measures mutmut's names. Adds: `Mutmut.mangle`'s rule through `changed_mutants` in `gates/mutmut_driver.py` as the source of step 19's expected values, whether `changed_mutants` matches on 3.8.0's names written as unmeasured; in the home "Which functions mutmut mutates, and their names", a mangled name spelled in a test or a gate forbidden; step 19's red test, spelling no mangled name, after C7b's driver build as steps 13 to 20 wait for C7b's step 34. Written in: **Modules**, **Homes**, **Order**, **Decisions for the owner**, **Decisions taken**.
9. **How does a move onto a home that keeps behavior reach its builder?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." No conflict was brought on this decision, so the recommendation is taken: each move is written in its module's block of **Modules**, built by the build step that names the module by its path and that block, and held by the tests already in the tree under the build commit's `make check`. Adds: the moves in the blocks of `gates/check_pytest.py` (the pytest gate's command onto `settings_arguments`, `module_classname` onto `Project.located`), `gates/mutmut_driver.py` (`meta_path` onto `MUTANTS`) and `gates/check_mutation.py` (`SCOPE_KEYS` onto the driver's key names); the home "A move onto a home that keeps behavior"; build steps 12, 20 and 29 carrying them, with no step and no `finding` step of their own, whether a `gatesmith` module step builds what its block gives beyond its red tests written as unmeasured. Written in: **Modules**, **Homes**, **Order**, **Decisions for the owner**, **Decisions taken**.
10. **Each stub signature in its stub step.** Ruling: "Write each stub signature into the mutation plan design step list, please thank you" Each stub step's text holds a fenced block of every declaration line its module's block of **Modules** gives, word for word up to its comment, so the `stub` brief, the plan step's text, carries each signature its stub writes. Adds: no module; the home "A stub's signatures"; the blocks of stub steps 3, 6, 10, 13 and 21, and **Order**'s rule that a stub writes each declaration its step's block lists and no other; decision 11. Written in: **Homes**, **Order**, **Decisions for the owner**, **Decisions taken**.
11. **Where does a stub's signature have its one spelling, now that its module's block and its stub step's block both give it (decision 10)?** Ruling: "Where you and the Architect both agree is fine with me. I want you to bring me conflicts." No conflict was brought on this decision, so the recommendation is taken: its module's block of **Modules**, its stub step's block a word-for-word copy of its declaration lines up to their comments, rewritten beside it by every `rulings` pass that touches the module's block and checked against it at the architect's reread, how often the two drift apart unmeasured. Adds: no module and no step; in the home "A stub's signatures", the module's block as the one spelling, its stub step's block rewritten beside it and checked at the reread, and an edit that leaves the step's block behind forbidden; in **Order**, the same rule beside decision 10's. Written in: **Homes**, **Order**, **Decisions for the owner**, **Decisions taken**.
