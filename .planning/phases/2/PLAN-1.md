---
phase: 2
plan: 1
requirements:
  - CORE-05
  - CORE-06
files:
  - .planning/config.json
  - .github/cadence/coverage-policy.json
  - .github/cadence/coverage-report-check.mjs
  - .github/workflows/ci.yml
  - pyproject.toml
  - .shared/pin.py
  - .shared/tests/shared_helpers.py
  - .shared/tests/test_pin.py
  - .shared/red.py
  - .shared/tests/test_red.py
  - .shared/working-folder.ts
---

# Phase 2: Test gate and shared layer - Plan 1: Test gate and shared helpers

## Goal

The accepted testing policy is enforced in GitHub Actions, and the shared helpers that later phases import exist: `.shared/pin.py`'s `slug`, `.shared/red.py` and `.shared/working-folder.ts`, with the suites the testing policy requires.

## Must be true when done

- `node "${CLAUDE_PLUGIN_ROOT}/cadence-core/bin/planning.mjs" test-policy check --root .` returns `ok: true`. `.github/cadence/coverage-policy.json` and `.github/cadence/coverage-report-check.mjs` are tracked, and `.github/workflows/ci.yml` defines exactly the jobs `tests`, `fixtures` and `lint`.
- The accepted policy differs from its phase-start state (commit `22b9b59`) only by D-01's command swap and D-02's dropped include. The coverage configuration omits test files (D-03).
- `red()` returns True for a test that fails in the run and in neither baseline, and False for a failure the brief baseline already carries.
- `slug` turns `My Items.md` into `my-items` and `gauntlet/items/my-task.md` into `my-task`.
- `uv run --no-project --with pytest pytest -q .shared/tests` passes.
- `git log` shows each new suite (`test_pin.py`, `test_red.py`) committed red against a null stub before the commit that turns it green.
- `.shared/working-folder.ts` exports `requireIgnored` as the intake design states. It has no suite (D-06).

## Context

- Locked: D-01, D-02 and D-03 (owner-approved policy changes), D-05 (`slug` only in `pin.py`), D-06 (`working-folder.ts` ships with no suite), D-07 (fixtures checkout at `$ARCHON_HOME/workflows/gauntlet`, bare command), D-08 (CI layout), D-16 (`red.py` surface), D-17 (red-first suites, importlib loading), D-18 (lint job).
- Designs: `.shared/pin.py` in `worktree-cut-design.md` (module heading; only `slug` here), `.shared/red.py` in `gauntlet-design.md`, `.shared/working-folder.ts` in `gauntlet-intake-design.md`. Follow `docs/testing.md` for every test.
- Pattern to follow: `fence/files_helpers.py` `load` (importlib from a file path, environment as input).
- Out of scope: `branch_name` and `pin` (Phase 5), any `<workflow>/scripts/*.py`, any push (D-10), any Archon probe (CLAUDE.md 1.9).
- Every task ends with CLAUDE.md 1.8's `archon workflow list --json` and `archon validate workflows`, run from the root and showing no discovery error, and with the pre-commit gate passing. Each Verify below names only what it adds.

## Tasks

### Task 1: Enforce the accepted policy in GitHub Actions

- **Files:** .planning/config.json, .github/cadence/coverage-policy.json, .github/cadence/coverage-report-check.mjs, .github/workflows/ci.yml
- **Action:** Apply the owner-approved policy adjustments, then build the CI gate. No workflow exists under `.github/workflows/` yet, so this task creates the first one and overwrites nothing.
  - (a) Policy, D-01 and D-02. In `.planning/config.json`, replace `testing.coverage.commands[0]` with the old command plus two additions: `--cov=.shared` after `--cov=fence`, and `.shared/tests` after the final `fence`. The result is `uv run --no-project --with 'mcp>=1.2,<2' --with pytest --with pytest-cov pytest -q --cov=fence --cov=.shared --cov-branch --cov-report=json fence .shared/tests`. Remove `*/scripts/**/*.py` from `testing.coverage.include`.
  - (b) Change no other testing value. Edit the JSON directly, not with `config.mjs set`. That command takes an array value comma-separated, and the command contains `'mcp>=1.2,<2'`, so `set` would split it. Then run `node "${CLAUDE_PLUGIN_ROOT}/cadence-core/bin/config.mjs" validate`, and regenerate `.github/cadence/coverage-policy.json` with `planning.mjs test-policy render --root .`. Never hand-edit the regenerated file.
  - (c) Copy `${CLAUDE_PLUGIN_ROOT}/cadence-core/templates/coverage-report-check.mjs` to `.github/cadence/coverage-report-check.mjs` unchanged.
  - (d) Create `.github/workflows/ci.yml`, triggered on push and pull_request, with three jobs whose ids are exactly `tests`, `fixtures` and `lint`. Use block scalars for `run:` so that each of the four accepted `testing.coverage.commands` appears verbatim. `check` matches that text after normalizing whitespace.
  - (e) `tests`: check out the repository, set up uv (`astral-sh/setup-uv`, pinned to a major tag), run the new pytest command, then run `node .github/cadence/coverage-report-check.mjs --format python --report coverage.json`. The runner's preinstalled Node is enough, because the script imports `node:` builtins only.
  - (f) `fixtures` (D-07): set `ARCHON_HOME` to a folder inside the workspace, and check out the repository into `$ARCHON_HOME/workflows/gauntlet` (the `path:` of `actions/checkout`). Install the Archon CLI that this host runs (v0.13.2, from `~/.archon/install.json`). It is a GitHub release asset: download `archon-linux-x64` and `checksums.txt` from release `v0.13.2` of `coleam00/Archon` with `gh release download`, using `GH_TOKEN: ${{ github.token }}`. Check the binary with `sha256sum --check --ignore-missing checksums.txt`, then put it on `PATH` as `archon`. Run the bare `archon workflow test` with the checkout as the working directory. Never add a path argument, because D-07 rejects changing the accepted command.
  - (g) `lint` (D-18): check out the repository, set up uv, run `uv sync` (filepawl v0.11.0 installs from its public GitHub URL in `pyproject.toml`), then run `.venv/bin/pre-commit run -c .pre-commit/config.yaml --all-files`.
  - Pinning v0.13.2 is my discretion: it is the version this host runs, so discovery matches the host, which is D-07's aim.
- **Verify:**
  - `node "${CLAUDE_PLUGIN_ROOT}/cadence-core/bin/planning.mjs" test-policy check --root .` lists exactly one problem: `coverage.include ".shared/**/*.py" matches no tracked file`. Task 3's commit clears it.
  - The same check with `--base 22b9b59` reports `base.changes` as exactly three entries: `command_added` (the new command), `command_removed` (the old one) and `include_removed` (`*/scripts/**/*.py`).
  - `cmp` of the template and the copy prints nothing.
  - Reading `ci.yml` shows the job ids `tests`, `fixtures` and `lint` and no others. `check` cannot settle this: its job test is a substring match, and `tests` also occurs in `.shared/tests`.
  - human-verify (D-10, AC2): at /cad-verify the owner pushes the branch to `ohshitgorillas/gauntlet`, and the check runs of the commit show all three jobs passing.
  - Testing scope: this task adds configuration and no test. Evidence that it is correct is the `check` output above plus the first Actions run. Testing stops there.

### Task 2: Omit test files from the coverage measurement

- **Files:** pyproject.toml
- **Action:** Add a coverage.py run configuration to `pyproject.toml` that omits `**/test_*.py` and `**/tests/**` (D-03). coverage.py reads `pyproject.toml` from the working directory whatever uv's `--no-project` says, so the report's totals then measure only the included scope. Add nothing else: no `source`, no other omit, no threshold. The policy command keeps the scope on the command line, and the report check keeps the thresholds. Leave `[dependency-groups]` alone, so that `uv.lock` does not change.
- **Verify:**
  - Run the fence-only measurement `uv run --no-project --with 'mcp>=1.2,<2' --with pytest --with pytest-cov pytest -q --cov=fence --cov-branch --cov-report=json fence`. The D-01 command needs `.shared/tests`, which arrives in Task 3.
  - `grep -o '"fence/[a-z_]*\.py"' coverage.json | sort -u` lists `fence/checks.py`, `fence/files.py` and `fence/files_helpers.py`, and no `test_` file.
  - Delete `coverage.json` and `.coverage` afterwards. Neither is ever committed.
  - Testing scope: a configuration change. The report's file list is enough evidence.

### Task 3: Write the `slug` suite red against a null stub

- **Files:** .shared/pin.py, .shared/tests/shared_helpers.py, .shared/tests/test_pin.py
- **Action:**
  - Create `.shared/pin.py` as a standard-library-only module whose one function is `slug(path: str) -> str`, the signature in the worktree cut design's `.shared/pin.py` comment block. Its body is the null stub: it returns `""`. `branch_name` and `pin` are not written (D-05, Phase 5).
  - Create `.shared/tests/shared_helpers.py`. It loads a `.shared` module by file name through `importlib`, as `fence/files_helpers.py` does, with `.shared` on `sys.path`, the way the designs' ledgers insert it. Then `.shared/rounds.py`'s later `from pin import slug` resolves under test as it does in production.
  - The helper returns the module and asserts nothing (rule 14). Its basename stays unique against `fence/`'s, because the D-01 command collects both folders in one pytest run.
  - Write `.shared/tests/test_pin.py` with the cases the design names for `slug`: `My Items.md` gives `my-items`, and `gauntlet/items/my-task.md` gives `my-task`. Add one case where nothing is left, which gives `""`. Sweep them with one parametrized test (rule 2).
  - Commit with a message saying the suite is red against the null stub (AC7). This is the one sanctioned commit of a red suite for this module.
- **Verify:**
  - `uv run --no-project --with pytest pytest -q .shared/tests` shows the `my-items` and `my-task` cases FAILED and nothing ERRORED. The `""` case passes against the stub. The hand-back names it as a guard that the stub cannot fail, and the next task's green run makes it discriminate.
  - Testing scope: the outcomes are the design's two derivations plus the empty result. The kebab-unchanged rule is already covered by `my-task`. Evidence: the red run, then Task 4's green run. Testing stops at these three cases.

### Task 4: Implement `slug`

- **Files:** .shared/pin.py
- **Action:** Implement `slug` exactly as the worktree cut design's comment states, using the standard library only:
  - take the file name of the path without its extension;
  - lowercase it;
  - make each run of characters outside `[a-z0-9]` one `-`;
  - trim `-` from both ends;
  - return `""` when nothing is left.

  Add nothing else to the module.
- **Verify:**
  - `uv run --no-project --with pytest pytest -q .shared/tests` passes.
  - `node "${CLAUDE_PLUGIN_ROOT}/cadence-core/bin/planning.mjs" test-policy check --root .` returns `ok: true` (AC1). Task 3's commit tracked `.shared/pin.py`.
  - Testing scope: Task 3's suite is the whole check. No test is added.

### Task 5: Write the `red.py` suite red against a null stub

- **Files:** .shared/red.py, .shared/tests/test_red.py
- **Action:**
  - Create `.shared/red.py` (standard library only) with the three functions of `gauntlet-design.md`'s `.shared/red.py` block (D-16): `cut`, `listing` and `red(run, brief, head="")`. As null stubs they return `""`, `{}` and `False`.
  - Write `.shared/tests/test_red.py`. Load the module through `shared_helpers`, and build each run, brief and head text as the designs give it: first line `exit=<n> timed_out=<true|false>`, then the output.
  - Pin these behaviors:
    - `cut` drops everything from the first ` - ` on each line.
    - `listing` reads only lines beginning `PASSED <id>`, `FAILED <id>` or `ERROR <id>`, after the cut, and ignores every other line.
    - `red` is True for a test failing in the run and in neither baseline (AC6).
    - `red` is False for a failure the brief baseline carries (AC6), and False for a failure carried by a given `head`.
    - `red` is True for a run timeout that neither baseline has, and False when the timeout is already in brief or head.
    - `red` is True for a non-zero exit with no failing line while brief exited 0, and head too when given. It is False when brief exited non-zero.
    - `head` `""` makes no head check.
  - Each True and False pair sweeps through one parametrized test, so that every test bites against the stub's `False`.
  - Commit red (AC7).
- **Verify:**
  - `uv run --no-project --with pytest pytest -q .shared/tests/test_red.py` shows failures in every test and no ERROR. Within a sweep, a False case may pass against the stub; the hand-back names those cases.
  - Testing scope: `.shared/red.py` is a strong area, so add the deeper checks a plausible defect justifies:
    - a failure message that contains ` - ` must not change the test id;
    - an indented `  FAILED x` line, or `xFAILED x`, is not a result;
    - `ERROR` in the run against `FAILED` in brief for the same id is not red.
  - Nothing exists yet that covers these outcomes. Evidence: this red run and Task 6's green run. Stop at the design's rules plus those three cases. No extra permutation.

### Task 6: Implement `red.py`

- **Files:** .shared/red.py
- **Action:**
  - Implement `cut`, `listing` and `red` exactly as the design block states, using the standard library only.
  - `listing` uses `cut`, so the coder's cut output and red read the same text.
  - `red` reads `exit` and `timed_out` from each text's first line, and computes the comparison here and nowhere else (design "Homes").
  - Add no parsing of a runner's full output.
- **Verify:**
  - `uv run --no-project --with pytest pytest -q .shared/tests` passes.
  - Testing scope: Task 5's suite is the whole check.

### Task 7: Write the working-folder guard module

- **Files:** .shared/working-folder.ts
- **Action:**
  - Write `.shared/working-folder.ts` for Bun, exporting `requireIgnored(options?: { committed?: boolean }): void` exactly as `gauntlet-intake-design.md`'s `.shared/working-folder.ts` block states. It runs from the checkout and asks git, so `.gitignore`, `.git/info/exclude` and the global excludes file all count.
  - Fail on a tracked file under `gauntlet/`, naming the first such path.
  - With `committed`, read the rule from what the tree will hold. `git check-ignore -v` names the file that a rule came from, and a `.gitignore` rule counts only as `HEAD` commits that file.
  - Each failure writes its one line to stderr verbatim from the design, with `<root>` from `git rev-parse --show-toplevel`, then exits 1. The design is the one home of these messages.
  - No suite (D-06): CORE-06's proof is a Phase 4 guard-node fixture.
- **Verify:**
  - In throwaway git repositories under `/tmp`, removed afterwards, `bun -e` importing the module by absolute path and calling `requireIgnored` shows:
    - exit 0 when a committed `.gitignore` holds `gauntlet/`, with and without `committed: true`;
    - exit 1 with one stderr line naming `<root>/gauntlet/` when nothing ignores it;
    - exit 1 naming the `.gitignore` under `committed: true` when the rule is uncommitted, and exit 0 for the same repository without the option;
    - exit 1 naming the file when a file under `gauntlet/` is tracked.
  - Testing scope: these are uncommitted observations that prove the task. The committed proof is Phase 4's fixture (D-06), and nothing further is tested here.

## Notes

- Ordering: run this plan before Plan 3, because Plan 3's `rounds.py` imports `slug` and its tests load through `shared_helpers`. This plan shares no file with Plan 2, so the two may run in parallel.
- Red commits (Tasks 3 and 5) leave a suite red on purpose. AC7, the owner's criterion, requires them, and they are the only commits where a suite gate is red. Each commit message says so, which keeps CLAUDE.md 4.2's intent visible. Phase 1 Plan 6 made no task commits (`phases/1/SUMMARY.md`, phase 1), but this phase needs per-task commits, because AC7 reads them from `git log`.
- `coverage.json` and `.coverage` land in the root on every local measurement and are not gitignored. Executors delete them and never `git add` them.
- Recalled and applied: D-01, D-03, D-05 and D-06 (`phases/2/CONTEXT.md`, phase 2).
