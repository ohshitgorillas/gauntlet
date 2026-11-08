---
phase: 2
plan: 3
requirements:
  - CORE-04
files:
  - .shared/rounds.py
  - .shared/tests/rounds_helpers.py
  - .shared/tests/test_rounds.py
  - fence/test_checks.py
---

# Phase 2: Test gate and shared layer - Plan 3: Round ledger and coverage close

## Goal

`.shared/rounds.py` reads a hearing's rounds, parses verdicts and the owner's cases, and writes rulings, guard records and `SCREENED` reviews, as the runtime model states. The phase's coverage gate then reads at or above 85 for lines and 85 for branches, with no threshold lowered.

## Must be true when done

- `main`, driven through a test `Profile` over real files, prints every mode's fields as `runtime-model-design.md`'s "Hearing state" and "Ledger" state them. The modes are `state`, `filing`, `docket`, `screen`, `record` and `close`.
- `next` reads `vacant` at the twelfth `OBJECTION: LEADING` review, although `owed` is the author.
- `first` lets several hearings share one folder.
- A changed item file sets the slug's files aside into `stale/<slug>.<n>/`, keeping the layout.
- `uv run --no-project --with pytest pytest -q .shared/tests` passes, `test_rounds.py` included.
- The D-01 command passes, and `node .github/cadence/coverage-report-check.mjs --format python --report coverage.json` prints lines and branches at or above 85 and exits 0.
- `git log` shows `test_rounds.py` committed red against the null stub before each commit that turns it green.

## Context

- Locked: D-05 (`rounds.py` imports `slug` from `.shared/pin.py`), D-09 (the shortfall closes with characterization tests for `fence/checks.py`, exempt from the red-run rule, and nothing is excluded), D-15 (every mode and field, `first`, the twelfth-LEADING `vacant`, bounds from "Loop shape and bounds", and a suite driving `main`), D-17.
- Designs:
  - behavior: `runtime-model-design.md`, headings "Hearing state", "Ledger" and "Loop shape and bounds";
  - constants, dataclasses and signatures: `spec-review-design.md` `.shared/rounds.py`.
  - Where the two disagree on behavior, the runtime model governs (its "Why" makes it the one home), and the hand-back names the disagreement. One example: `close` takes no `start` in the signature, but runtime-model says `close` passes `INPUTS_START`.
- Existing: `.shared/pin.py` `slug` and `.shared/tests/shared_helpers.py` (Plan 1); `fence/checks.py` (`_load`, `Clock`, `run_tests_with`, `MAX_LINES`, `MAX_CHARS`).
- Out of scope: any workflow's `scripts/ledger.py` or `Profile` (Phases 4 and 6), `cite.py`, and `checks.py` behavior changes (Phase 6).
- Every task ends with CLAUDE.md 1.8's `archon workflow list --json` and `archon validate workflows`, run from the root and showing no discovery error, and with the pre-commit gate passing.

## Tasks

### Task 1: Write the ledger-state suite red against a null stub

- **Files:** .shared/rounds.py, .shared/tests/rounds_helpers.py, .shared/tests/test_rounds.py
- **Action:**
  - Create `.shared/rounds.py` (standard library only) with the spec review design's constants, `OwnerCase` and `Profile` dataclasses, and every function it names: `cited`, `state`, `docket`, `screen`, `record`, `close` and `main`.
  - Each is a null stub returning its zero value: `False`, `{}`, `""` or `0`. The constants hold the runtime model's values: `SLOTS = 12`, `STRETCH = 12`, `REPAIRS = 5`, `CAP = 200`, `IDLE = 1`. They are data and not behavior.
  - The module imports `slug` with `from pin import slug` (D-05), resolved through `.shared` on `sys.path`, as the ledgers and `shared_helpers` arrange.
  - Create `.shared/tests/rounds_helpers.py`. Its functions write a hearing's files under `tmp_path`: round files, reviews by verdict line, rulings, guard entries, cite lines, iteration lines, idle files and the item file. Each returns paths or values and asserts nothing (rule 14). Its basename is unique across both test folders.
  - Write the state half of `.shared/tests/test_rounds.py`. It drives `main` through a test `Profile` with an absolute `folder` under `tmp_path`, and sets the `INPUTS_*` variables as input. `first` is passed through the public `state` function, because script modes hear from round 1. Pin:
    - mode `state`: `round`, `file`, `owed` (each value and its precedence), `next` (the twelfth-LEADING `vacant`, a slot name `<letter><n>`, and `retire=None` never vacant), `start`, `base`, `since`, `attempts`, `non_responsive`, `stretch`, `repairs`, `rulings` order, `review` and `verdict`;
    - verdict parsing: markup stripped, case ignored, longest known name;
    - `first`: earlier hearings' files are ignored;
    - mode `filing`: it appends one iteration line;
    - the item hash and the `stale/<slug>.<n>/` set-aside, keeping the `approved/` layout;
    - `cited`.
  - Write the bounds as numbers in the tests, never as the module's constants (rule 10).
  - Commit red (AC7).
- **Verify:**
  - `uv run --no-project --with pytest pytest -q .shared/tests/test_rounds.py` shows failures, with no ERROR. A test passing against the stub is named in the hand-back.
  - `wc -l .shared/tests/test_rounds.py` is below 800.
  - Testing scope: the outcomes are each state field and `owed` value, with one representative file set apiece. Precedence gets one test per ordered pair the model states: owner before author and reviewer, `approved` and `ended`. Nothing covers `rounds.py` yet.
  - Stop at one case per rule. No permutation sweeps over round counts beyond the bounds' edges.

### Task 2: Implement the ledger state

- **Files:** .shared/rounds.py
- **Action:**
  - Implement `state` and `filing`, the item hash and set-aside that run outside the loop, `cited`, verdict parsing, and the dispatch in `main` for modes `state` and `filing`. `main` reads `INPUTS_MODE`, `INPUTS_ITEMS` (slug from `pin.slug`), `INPUTS_START` and `INPUTS_BASE`, and prints JSON to stdout.
  - Implement them exactly as "Hearing state" and "Ledger" state, with the bounds from "Loop shape and bounds".
  - `docket`, `screen`, `record` and `close` stay stubs until Task 4.
  - Keep `.shared/rounds.py` under the 500-line cap. Plan no sibling module, because the design names one module.
- **Verify:**
  - `uv run --no-project --with pytest pytest -q .shared/tests` passes.
  - Testing scope: Task 1's suite is the whole check.

### Task 3: Write the docket, screen, record and close suite red

- **Files:** .shared/tests/rounds_helpers.py, .shared/tests/test_rounds.py
- **Action:** Extend `test_rounds.py`, driving `main` as in Task 1, and extend `rounds_helpers.py` only for the file kinds these modes need. Pin:
  - mode `docket`:
    - case precedence in the model's order: `vacant`, `none` on `ended`, the profile's owner cases in order, `unknown`, `deadlock` at 5 attempts, `non-responsive` at 2, `guard` (stretch 12, repairs 5), `idle`, `cap` at 200 iteration lines above `base`, then `none`;
    - `ask`;
    - `options` (`reply` for non-owner cases);
    - `attention` per case;
    - `summary` only while the summary file is absent;
    - `round` (`state`'s round for `guard`, `idle` and `cap`);
    - `idle` K and `reason`;
  - mode `screen`: it writes line 1 `Verdict: SCREENED` and the quote, and exits 1 when the review exists;
  - mode `record`:
    - a ruling when the round's review exists, with exit 1 when the ruling exists, and the attempt, non-responsive and stretch counts reset;
    - a guard entry otherwise, with the cite-marker count, and the counts restarting from it;
  - mode `close`: outcome `approved`, `invalid` and `vacant`, the empty answer, and bare `file` and `summary` names.

  Commit red.
- **Verify:**
  - The new tests show failures with no ERROR, and Task 1's tests still pass.
  - `wc -l .shared/tests/test_rounds.py` is below 800.
  - Testing scope: one test per case or field rule. Each bound is tested at its edge (4 attempts against 5) as one parametrized sweep. Stop there.

### Task 4: Implement docket, screen, record and close

- **Files:** .shared/rounds.py
- **Action:**
  - Implement `docket`, `screen`, `record` and `close`, and their dispatch in `main`, exactly as "Ledger" and "Loop shape and bounds" state. `main` reads `INPUTS_ROUND`, `INPUTS_QUOTE`, `INPUTS_CASE`, `INPUTS_DECISION`, `INPUTS_TEXT` and `INPUTS_START`.
  - Each file is written once where the model says so, and exit 1 comes when it exists.
  - A guard record is never a ruling.
  - Keep the module under 500 lines.
- **Verify:**
  - `uv run --no-project --with pytest pytest -q .shared/tests` passes.
  - `wc -l .shared/rounds.py` is below 500.
  - Testing scope: Task 3's suite is the whole check.

### Task 5: Close the coverage shortfall with `checks.py` characterization

- **Files:** fence/test_checks.py
- **Action:**
  - Write `fence/test_checks.py`, characterizing `fence/checks.py` as it stands (D-09). Characterization tests are exempt from the red-run rule, and the hand-back says so.
  - Load the module through `importlib` with its documented environment as input (`CLAUDE_PROJECT_DIR`, `FENCE_TEST_COMMAND`, `FENCE_TEST_TIMEOUT`). A module-level helper in the test file returns the module, as `files_helpers.load` does.
  - Pin:
    - each startup refusal exits with status 2;
    - the default timeout of 900;
    - `run_tests_with`'s first line, with `exit=<n>` and `timed_out=` as wire fields;
    - the tail kept to the last 200 lines and 20000 characters;
    - a timeout kill.
  - Drive each run with a real `bash` subprocess under `tmp_path` and an injected `Clock` (rule 7):
    - for a normal run, a clock whose `sleep` never completes, so the process exit wins;
    - for a timeout, a clock whose `sleep` returns at once;
    - `monotonic` read from a table, so the `seconds=` value is a written number.
  - Measure before and after:
    - run the D-01 command, then the report check;
    - if lines or branches remain below 85, find the concrete gap in the report, add the smallest meaningful test in this plan's leased suites that closes it, and report the measured figures;
    - if the gap lies in a file this plan does not lease, or closing it would materially exceed this task, report that gap and tradeoff once and stop (test-policy completion rule);
    - never lower a threshold or exclude a file.
- **Verify:**
  - The D-01 command, `uv run --no-project --with 'mcp>=1.2,<2' --with pytest --with pytest-cov pytest -q --cov=fence --cov=.shared --cov-branch --cov-report=json fence .shared/tests`, passes.
  - `node .github/cadence/coverage-report-check.mjs --format python --report coverage.json` prints lines and branches at or above 85, names no in-scope file absent from the report, and exits 0.
  - `node "${CLAUDE_PLUGIN_ROOT}/cadence-core/bin/planning.mjs" test-policy check --root .` returns `ok: true`.
  - Delete `coverage.json` and `.coverage`.
  - human-verify (D-10, AC2): at /cad-verify the owner pushes this commit. `tests`, `fixtures` and `lint` pass on Actions, and the `tests` log shows both figures at or above 85.
  - Testing scope: the outcomes are `checks.py`'s startup refusals, its result head, its tail cut and its kill. Nothing covers them today, at 0% of 84 statements.
  - Evidence: the report check's figures. Stop when both reach 85 and those outcomes are pinned. Add no test written to reach a line.

## Notes

- Ordering: run after Plan 1, for `pin.slug`, `shared_helpers` and the D-01 command's `.shared/tests`, and after Plan 2, because Task 5 measures the whole phase's code. This plan's declared files overlap neither plan.
- Red commits (Tasks 1 and 3) leave `.shared/tests` red on purpose. AC7 requires them, and each commit message says so.
- The risk that `.shared/rounds.py` passes 500 lines is real, given how many modes it carries. If it cannot fit, the executor stops and reports, rather than adding an undeclared sibling. A second module would be a design change for the owner.
- `coverage.json` and `.coverage` are not gitignored. Executors delete them and never commit them.
