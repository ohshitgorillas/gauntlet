# C3 review: check_mypy onto the gates core

Scope: `edaa211..afcf5a8`, blind, by the `diff-reviewer` method. Judged against `docs/superpowers/specs/2026-10-20-gates-core-design.md` section 4 and its C3 row, with sections 1 and 2 for the contract the port must meet, as the job brief directs.

Reviewed: `gates/check_mypy.py`. Skipped, unread as the role requires (test-reviewer's half): `tests/test_check_mypy_core.py`, `tests/test_check_mypy_stopped.py`, `tests/test_check_mypy_warm_cache.py`; only their test names were listed, to confirm the C3 row's red test for (a) exists.

Read beyond the diff: `gates/core/runner.py`, `gates/core/report.py`, `gates/core/checker.py`, `gates/core/source.py`, `gates/check_suppressions.py:80-105`, `gates/check_pyright.py:185-215`, `pyproject.toml` `[tool.mypy]`, `docs/superpowers/specs/2026-10-17-quality-gates-design.md:29,42`, `docs/measured.md` (searched), the uv-tool mypy 2.3.1 `mypy/errors.py` found on this host (the project venv was absent) `report_internal_error` and `new_messages`. `check_mypy.py` and `_batch_lines` are unchanged between `afcf5a8` and the reviewed checkout.

## Conformance with section 4 and the C3 row

The port matches section 2's `Mypy` almost line for line: `Record`, `record`, `describe` and `shown` stay in the gate; `stopped = {2}`, one batch per file, `expected_status = 1 if records else 0`, the stopped path giving every record as Unfinished, the finished path filtering to the batch's file. The count line, exit constants, printer, `api.run`, temp handling and every OSError block are gone, as section 4 requires (g1l's `show_blocked` becomes the stopped path plus render's once-per-run rule; mypy-cache's warm/copy/remove become `Scratch.once`, `copy` and `close`). `warm_cache` runs through `run.process`, raises GateError unless mypy exits 0, prints nothing and leaves a file, as section 2 states. `main(paths)` keeps its signature. A red test for (a) exists by name (`tests/test_check_mypy_core.py:73`, `:80`). The one deviation from section 2's sketch is `_options`, which factors the options the warm and per-file runs share; it changes no argv.

## Findings

### 1. minor — `gates/check_mypy.py:163`

The stopped path returns only the records as Unfinished, so `_batch_lines` (`gates/core/runner.py:189-193`) never adds the whole output, and mypy's stderr is dropped on every exit 2 whose stdout held a record.

Failing scenario: mypy hits an internal error while checking a file that already has an ordinary type error. Its `report_internal_error` (`mypy/errors.py`, 2.3.1) dumps the errors so far through `new_messages`, which uses the run's `error_formatter`, so stdout holds a valid JSON record; it then prints `<file>:<line>: error: INTERNAL ERROR -- Please try using mypy master on GitHub…` and the bug-report lines to stderr and exits 2. The gate reads the record, takes status 2 as a blocking-error stop, prints the ordinary type error as unfinished and the count line, and exits 2. Nothing says mypy crashed; the reader looks for a blocking error that does not exist. The quality spec (line 29) allows a stop to print only "the report it read" for a stop "whose report still stands"; a crash shares the status but its report does not stand.

Suggested fix: keep stderr with the report, e.g. `read` returns a small `Report(records, stderr)` and the stopped path adds `Unfinished(stderr)` when stderr is not empty (this review did not run mypy, so whether a true blocking error writes anything to stderr is unconfirmed; if it does, the line still names the stop's cause). This changes printed output.

### 2. note — `gates/check_mypy.py:151`

On a finished check, mypy's stderr is now discarded; the old gate echoed it (`sys.stderr.write(errors)`, removed in this diff). Section 1 and section 2 list no keep or drop for it. The window is small: config and plugin-load warnings also print on the warm run, where `warm_cache` turns any output into a GateError, so only stderr mypy writes while checking a repository module (a plugin hook's message, a library warning raised during analysis) is lost silently. Fix, if the owner wants it kept: give finished-run stderr as Remark lines, which the same `Report` shape as finding 1 would carry. An owner ruling, not a builder fix.

### 3. note — `gates/check_mypy.py:163`

A stop no longer names the file whose check stopped (the old `mypy stopped on a blocking error checking <source>` line is gone), and a non-blocking error in the checked file during a stop is Unfinished, not counted. Both follow section 2 and quality spec line 29, so no change is asked; recorded so the owner sees the drop. Scenario: `a.py` imports `b.py` with a syntax error; the run prints `b.py`'s error once and `0 finding(s)`, with no line saying which file's check it stopped.

### 4. note — builder flag: the class moved from `json_report.py` (`gates/check_mypy.py:13`)

The move itself happened in C2 (`dade7cc`, which deleted `json_report.py` and gave `check_mypy` its own `UnfinishedError`); this range deletes that copy and uses `report.GateError` and `Unfinished`, as section 1's *Replaces* list requires for `json_report`'s `UnfinishedError`. A search finds no `UnfinishedError` or `json_report` left under `gates/` or `tests/`. Nothing to fix.

### 5. note — builder flag: `source.parse` returns an opaque Unfinished (`gates/core/source.py:80`)

Not in this range and not used by `check_mypy`. Treating any parse warning and any parse error alike as Unfinished is what section 1 specifies ("OSError, SyntaxError, any warning … is Unfinished") and what the quality spec's parse-warning rule asks, so the opacity conforms. Its one visible effect is in `gates/check_pyright.py:204`: a ruleless pyright diagnostic in a file whose parse only warned (e.g. a `SyntaxWarning` for an invalid escape) is printed as Unfinished rather than counted as a Finding. The run exits 2 either way; only N differs. If the owner wants the two told apart, `parse` would need to return the warning separately; that is a ruling for the source.py/pyright owner, not a C3 fix.

### 6. note — C3 row "the child process (measured first)" (`docs/measured.md:1`)

`docs/measured.md` holds no mypy entry, so the tree carries no record that the child-process cost was measured before the port replaced in-process `api.run`. The measurement may live in the dated log, which this review does not read. Suggested fix: if it was measured, record the result in `docs/measured.md` so it is not measured again.

## Count

blocking 0, minor 1, note 5.

VERDICT: NOT MINOR — finding 1's fix changes what the gate prints on an exit 2.
