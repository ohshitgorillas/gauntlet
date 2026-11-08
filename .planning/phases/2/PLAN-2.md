---
phase: 2
plan: 2
requirements:
  - CORE-01
  - CORE-02
  - CORE-03
files:
  - fence/test_files_patterns.py
  - fence/files.py
  - fence/files_helpers.py
  - fence/test_files_hide.py
  - docs/superpowers/specs/runtime-model-design.md
  - fence/test_files_commit.py
  - fence/files_commit.py
---

# Phase 2: Test gate and shared layer - Plan 2: Fence extensions

## Goal

The fence confines agents by name patterns, hides `FENCE_HIDE` paths from every tool, and lets a fenced writer commit through the `commit` tool under `FENCE_COMMIT`. Each extension has its own suite.

## Must be true when done

- With `FENCE_WRITE=gauntlet/mend/*.review.*.txt`, `write_file` succeeds on `gauntlet/mend/a.review.1.txt` and raises `PermissionError` on `gauntlet/mend/x/a.review.1.txt`. `fence/test_files_patterns.py` passes.
- A fenced `read_file` on a path under `FENCE_HIDE` raises a `PermissionError` whose message names `FENCE_HIDE`, and `list_directory` over its parent omits the path. `fence/test_files_hide.py` passes.
- With `FENCE_COMMIT=1`, `commit` creates a commit holding exactly the given `paths`. It raises when a recorded, changed path is missing from `paths`, and when a path is under `FENCE_HIDE`. Without `FENCE_COMMIT` the tool is absent. `fence/test_files_commit.py` passes.
- `runtime-model-design.md`, "Commit model", states the two D-04 rules. No other design restates them.
- `uv run --no-project --with 'mcp>=1.2,<2' --with pytest pytest -q fence` passes, and `fence/files.py` stays under the 500-line filepawl cap.
- `git log` shows each of the three suites committed red before the code that turns it green.

## Context

- Locked: D-04 (two commit rules into the design first), D-11 (only `commit` and path recording from writing-design step 1), D-12 (patterns), D-13 (`FENCE_HIDE`), D-14 (file length, sibling module), D-17 (red-first, importlib loading).
- Designs:
  - patterns: `plan-review-design.md` `fence/files.py (extended)`;
  - hiding: `gauntlet-design.md` `fence/files.py (hidden paths)`;
  - commit: `writing-design.md` `fence/files.py (commit)`, with its rules in `runtime-model-design.md` "Commit model", "The commit tool's rules (D-68)".
- Existing code: `fence/files.py` (`_folders`, `_inside`, `_visible`, `_resolve`, `_check_read`, `_check_write`, `_check_once`, `_check_copy`, `ALWAYS_DENY_WRITE`) and `fence/files_helpers.py` (`load`, `put`).
- Out of scope: `@base`, `gauntlet/settings.json`, `FENCE_CUT`, `fence/test_settings.py`, `checks.py` changes (Phase 6, D-11), and any fence config file.
- Every task ends with CLAUDE.md 1.8's `archon workflow list --json` and `archon validate workflows`, run from the root and showing no discovery error, and with the pre-commit gate passing. Each Verify names only what it adds. The fence suite command throughout is `uv run --no-project --with 'mcp>=1.2,<2' --with pytest pytest -q fence`.

## Tasks

### Task 1: Write the name-pattern suite red

- **Files:** fence/test_files_patterns.py
- **Action:**
  - Write `fence/test_files_patterns.py` through `files_helpers.load` and `put`, pinning D-12:
    - an entry holding `*`, `?` or `[` is a pattern;
    - a pattern matches a root-relative path segment by segment with `fnmatchcase`, at an equal segment count, so `*` never crosses `/`;
    - patterns work in READ, WRITE, DENY, ONCE and COPY;
    - for a pattern entry, `list_directory` and `find_files` show a folder only when it holds a readable file.
  - Include AC4's pair as written.
  - The null stub for this extension is the unchanged `fence/files.py`. Every tool exists, and no new public function is added, so the suite goes red against today's literal-folder reading of a pattern entry (D-17, AC7). Commit red.
- **Verify:**
  - The fence suite shows this file's new-behavior tests FAILED, with no ERROR, while `fence/test_files.py` and `fence/test_files_write.py` pass.
  - A test passing red is one pinning a refusal the old code already gives, such as AC4's nested path. The hand-back names each one.
  - Testing scope: `fence/` is a strong area. Its consequential defect is a pattern widening confinement, so pin:
    - `*` not crossing `/` for WRITE and for READ;
    - a DENY pattern refusing inside a writable folder.
  - Folder entries' prefix meaning is already covered by `test_fence_folder_does_not_cover_sibling_with_prefix_name` and `test_deny_does_not_cover_sibling_with_prefix_name`. Add no new test for it.
  - Stop at one check per list kind, plus the two listing rules.

### Task 2: Implement name patterns

- **Files:** fence/files.py
- **Action:**
  - Make every check that now uses `_inside` against a `FENCE_*` entry treat a pattern entry as D-12 states, and keep a folder entry's prefix test. `_visible`, and the pruning in `grep`, which uses it, follow the D-12 listing rule. All of READ, WRITE, DENY, ONCE and COPY take patterns, and `ALWAYS_DENY_WRITE` stays a folder list.
  - The match runs on the parts `_resolve` returns, the real path, so a symlink cannot reach a pattern-matched name from outside it.
  - Keep `fence/files.py` well under 500 lines, because Tasks 4 and 7 add to it.
- **Verify:**
  - The fence suite passes.
  - `wc -l fence/files.py` is below 500.
  - Testing scope: Task 1's suite plus the existing suites are the whole check.

### Task 3: Write the `FENCE_HIDE` suite red

- **Files:** fence/files_helpers.py, fence/test_files_hide.py
- **Action:**
  - Give `files_helpers.load` a `hide` parameter that sets `FENCE_HIDE`, defaulting to `""` like the others, so that existing callers are unchanged.
  - Write `fence/test_files_hide.py`, pinning D-13:
    - every existing tool refuses a hidden path inside a readable or writable folder with `PermissionError` matching `FENCE_HIDE` (`read_file`, `write_file`, `edit_file`, `copy_file` source and destination, `delete_file`, and `list_directory` or `grep` on the hidden path itself);
    - `list_directory`, `find_files` and `grep` never show a hidden path, nor a folder holding only hidden paths;
    - a pattern entry hides by D-12's rule;
    - unset hides nothing.
  - Include AC3's pair as written. The `commit` refusal is pinned in Task 6's suite, because that tool does not exist yet.
  - The null stub is today's `fence/files.py`, which ignores `FENCE_HIDE`. Commit red.
- **Verify:**
  - The fence suite shows this file's refusal and omission tests FAILED, with no ERROR, and the other suites passing. The "unset hides nothing" case passes red; the hand-back names it.
  - Testing scope: a strong area. The plausible bypass is a hide check run on the given path rather than the resolved one, so add one test: a symlink in a readable folder pointing at a hidden file is refused.
  - Each tool gets one parametrized refusal sweep. The listing rules get one test each. Stop there.

### Task 4: Implement `FENCE_HIDE`

- **Files:** fence/files.py
- **Action:**
  - Parse `FENCE_HIDE` with `_folders`, so patterns are included through Task 2's matching (D-13).
  - Every tool refuses a hidden path before any other effect with `PermissionError(f"{path}: hidden (FENCE_HIDE)")`, using the resolved parts as `_resolve` gives them.
  - `list_directory`, `find_files` and `grep` skip hidden paths, and skip a folder that holds only hidden paths.
  - Unset hides nothing.
  - Leave the `commit` refusal to Task 7.
- **Verify:**
  - The fence suite passes.
  - `wc -l fence/files.py` is below 500.
  - Testing scope: Task 3's suite is the whole check.

### Task 5: Write the two commit rules into the design

- **Files:** docs/superpowers/specs/runtime-model-design.md
- **Action:** In "Commit model", "The commit tool's rules (D-68)", add the two D-04 rules as part of that bullet list, cited `(Phase 2 D-04)`.
  - Rule 1: the tool refuses, staging nothing, when any path that this server process recorded is changed and missing from `paths`. "Recorded" means wrote, edited, copied to or deleted, the writing design's recording rule.
  - Rule 2: when git exits non-zero, the hook names the tool returns are the file names of the commit hooks git ran, found in the hooks folder (`git rev-parse --git-path hooks`, which resolves `.git/hooks` in a worktree too). They are never parsed from a hook's or a hook manager's output.
  - The refusal raises `ValueError`. It is a wrong argument and not a fence boundary, which keeps it apart from the existing `PermissionError` for paths outside `FENCE_WRITE`. Choosing `ValueError` is my discretion, recorded here so the suite can match on the type (`docs/testing.md` rule 9).
  - State each rule once and only here (D-98 (2)). `writing-design.md` and `contracts.md` row H54 already point to this heading and need no change.
- **Verify:**
  - `grep -n "D-04" docs/superpowers/specs/runtime-model-design.md` shows both rules inside the "Commit model" section.
  - `grep -rln "git-path hooks" docs/superpowers/specs/` lists only `runtime-model-design.md`.
  - Testing scope: a design text change, so no test.

### Task 6: Write the `commit` suite red against a null stub

- **Files:** fence/files.py, fence/files_helpers.py, fence/test_files_commit.py
- **Action:**
  - In `fence/files.py`, add the tool `commit(message: str, paths: list[str]) -> str`, registered with the server only when `FENCE_COMMIT=1` (`writing-design.md` signature). Its null-stub body returns `""`.
  - Give `files_helpers.load` a `commit` parameter that sets `FENCE_COMMIT`, defaulting to `""`.
  - Write `fence/test_files_commit.py` against a real git repository under `tmp_path` (rule 4). Pin the writing design's suite list:
    - a commit holding exactly `paths` while another path is staged;
    - the refusal of a recorded, changed path left out of `paths` (`ValueError`, Task 5);
    - a listed path that does not exist left out;
    - a listed new file in a missing directory committed;
    - `exit=0 nothing` when no path changed;
    - the one retry after a hook changed files;
    - a failing `pre-commit` hook giving a non-zero `exit`, the hook name `pre-commit`, and no commit;
    - the tool's absence without `FENCE_COMMIT`.
  - Pin AC5's `FENCE_HIDE` refusal, and a path outside `FENCE_WRITE` raising `PermissionError` and staging nothing.
  - Isolate every git call from the host with git's documented `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_NOSYSTEM` variables, set as input (rule 15), so a host hooks path or signing setting cannot change the result. Give the repository a local identity.
  - Observe the tool's absence through the server's own tool listing (FastMCP `list_tools`), the public surface.
  - Hooks are test-written files under the repository's hooks folder. The retry hook keeps its pass count in a file the test reads, so the count comes from a table and not from logic (rule 13).
  - Commit red.
- **Verify:**
  - The fence suite shows this file's behavior tests FAILED, with no ERROR, and the other suites passing. The absence test passes red; the hand-back names it.
  - Testing scope: strong area plus the `destructive` and `concurrency` risk surfaces. The fence refusals are the deeper checks.
  - The lock is not tested: writers run one at a time (`max_parallel: 1`), so a race has no observable behavior in one process.
  - Stop at the design's list, AC5 and the two fence refusals.

### Task 7: Implement `commit` and path recording

- **Files:** fence/files.py, fence/files_commit.py
- **Action:** Implement the "Commit model" rules exactly, including Task 5's two rules.
  - In `fence/files.py`:
    - record every path that `write_file`, `edit_file`, `copy_file` (its destination) and `delete_file` touch in this process;
    - keep `commit`'s registration under `FENCE_COMMIT=1`;
    - run the fence checks first: a path outside `FENCE_WRITE`, or inside `FENCE_DENY` or `FENCE_HIDE`, raises `PermissionError` and stages nothing;
    - apply the recorded-path refusal.
  - Put the git half in the sibling `fence/files_commit.py` (D-14):
    - the exclusive lock on `<git rev-parse --git-dir>/gauntlet-commit.lock`, held across every command;
    - `git status --porcelain -z -uall` over the listed paths;
    - `git add -A` then `git commit --only -m`, with hooks running and never `--no-verify`;
    - the one retry after a hook changed files among the changed paths;
    - hook names read from the hooks folder;
    - the `exit=<n>`, `nothing` and `commit=<full hash>` answers.
  - The sibling takes what it needs as arguments, so it imports nothing from `files.py`. `files.py` imports it as a sibling of the script, which works when the script runs and under `files_helpers.load` alike.
  - No path other than the listed changed paths is staged.
- **Verify:**
  - The fence suite passes.
  - `wc -l fence/files.py` is below 500.
  - `uv run --no-project --with 'mcp>=1.2,<2' --with pytest --with pytest-cov pytest -q --cov=fence --cov-branch --cov-report=term fence` lists `fence/files_commit.py` as measured. Delete `.coverage` afterwards.
  - Testing scope: Task 6's suite is the whole check.

## Notes

- Ordering: this plan shares no file with Plan 1 and may run in parallel with it. Plan 3's closing coverage task runs after this plan.
- D-17 and AC7 ask for a null stub. For patterns and `FENCE_HIDE`, no new public function exists, so the unchanged `fence/files.py` is the stub. Only `commit` gets a stub body. If the owner reads AC7 as needing a separate stub commit for those two, that is a gap for the owner to rule on.
- Red commits (Tasks 1, 3 and 6) leave the fence suite gate red on purpose. AC7 requires them, and each commit message says so. Phase 1 Plan 6 made no task commits (`phases/1/SUMMARY.md`, phase 1), but this phase needs per-task commits, because AC7 reads them from `git log`.
- Task 5 edits an approved design under D-04, the owner's answer of 2026-11-08.
