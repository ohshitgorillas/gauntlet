# C5 review: check_pytest onto the gates core

Scope: commit 8bcfffb on main, diff 2c6093c..8bcfffb (gates/check_pytest.py, tests/test_check_pytest_core.py, tests/test_check_pytest_processes.py). Judged against docs/superpowers/specs/2026-10-20-gates-core-design.md §4 and the C5 row, decisions 26 and 27, and the pytest section of 2026-10-17-quality-gates-design.md.

Passes: a blind `diff-reviewer` over gates/ and a blind `test-reviewer` over tests/, each dispatched with the bare diff scope as CLAUDE.md requires, plus a third pass against the brief's focus points (deleted cpus/processes tests, per-module concurrency and seeds, killed pytest output). No source or test was edited. Only tests/test_check_pytest_processes.py and tests/test_check_pytest_core.py were run (11 passed), plus two scratchpad probes with a SIGKILLed module and an `os._exit(1)` module.

## Focus points

- One pytest per module, run concurrently: unchanged. `Pytest.batches` (gates/check_pytest.py:129) gives one batch per test module, and `run_all` runs them under `max(1, cpu_budget(...))`. That equals the old `max(1, min(modules, cpus // 2))` because `run_all` never starts more workers than there are commands.
- Seeds: unchanged. One `secrets.randbits(32)` per run (gates/check_pytest.py:196) is passed to every module as `--randomly-seed`, and the seed line comes first. Neither version sets PYTHONHASHSEED.
- Crashed or killed pytest: the whole output is printed. A signal death maps to 128+N and leaves no JUnit report, so `read` raises GateError and `_batch_lines` returns `Unfinished(completed.output())`. Probes confirmed that SIGKILL and `os._exit(1)` both print pytest's console output, a sibling module's finding still prints, and the run exits 2. No test drives the signal case (finding m14).
- Deleted cpus/processes tests: `test_half_cpus`, `test_odd_cpus` and `test_one_cpu` are covered by tests/test_core_checker_budget_cpus.py:54 and tests/test_core_runner_budget.py. `test_fewer_modules` is only partly covered. `test_host_count` is covered for the core only, and `test_no_command` is covered nowhere (finding B1).

## Findings

### Blocking

B1. tests/test_check_pytest_processes.py:59 (with gates/check_pytest.py:201,211)
- Problem: the deletion of `test_host_count` and `test_no_command` left untested two things: that check_pytest's default budget is `cpu_budget()` read in-process, and that the count never comes from a command. Every remaining test injects `read_cpus`, and the `GATE` tests use one module.
- Failing scenario: two mutants pass every test: `GATE = gate()` with its default budget replaced by `lambda: 1`, and `main`'s `read_cpus` default replaced by `lambda: 2`. A default that ran `nproc` from PATH would also pass. Meanwhile the docstring at lines 3-7 still claims "never from a command". `test_fewer_modules` (cap larger than the module count, all run at once) has no direct replacement either.
- Suggested fix: add a test that narrows affinity in-process (`os.sched_setaffinity` to 4 CPUs) and runs the rendezvous pair through `main` with no `read_cpus`, expecting exit 0. Restore a test that puts counting tools on PATH and asserts `cpu_budget()` equals the affinity count // 2. Add a rendezvous case with a cap above the module count.

### Minor

m1. gates/check_pytest.py:211,220
- Problem: `read_cpus: Callable[[], int | None]` keeps its type, but None now means "read the host" where it used to mean "count unreadable, exit 2".
- Failing scenario: a caller whose reader fails and returns None gets a full run on the host count. The spec's "a host whose CPU count the gate cannot read ... exit 2" can no longer be reached through `main`.
- Suggested fix: make `main` take `cpus: int | None` (None meaning host), or map a None from the reader to GateError.

m2. gates/check_pytest.py:195 (with gates/core/runner.py:228)
- Problem: the old gate's `Deferral` covered the run temp dir's whole life. Now module dirs are made before `run_all` installs `_Interrupts`, and `scratch.close()` runs after the handlers are restored.
- Failing scenario: a SIGTERM or SIGHUP while line 195 makes the dirs, or a Ctrl-C during `scratch.close()`'s rmtree, leaves the run temp dir in the scratch root. That breaks the spec's "deleted on every exit path ... scratch root holds exactly what it held before".
- Suggested fix: hold signals across the whole of `run_gate`'s scratch lifetime in the core (runner.py), not only inside `run_all`.

m3. gates/check_pytest.py:198
- Problem: the seed note is attached to every outcome, including one where no pytest ran.
- Failing scenario: when `cpu_budget` raises GateError (unreadable host count), or the first batch fails before pytest starts, the gate prints `check_pytest: seed N` for a seed no run used. The old gate printed no seed on the unreadable-CPU path.
- Suggested fix: attach the note only when at least one batch started, or compute the budget before the note.

m4. gates/check_pytest.py:149-150
- Problem: `-o junit_suite_name=<module>` overrides an ini key on the command line. The spec allows only `--basetemp` there, and cases are matched by the suite name pytest echoes back rather than by the batch actually run.
- Failing scenario: a `[tool.pytest.ini_options] junit_suite_name` in pyproject.toml is silently overridden.
- Suggested fix: match each report to its batch by order or path, or record the override in the quality-gates spec.

m5. gates/check_pytest.py:194
- Problem: `check` rebuilds the module list with its own `is_test_module` filter instead of using `Pytest.batches`, and `command` indexes `self.spaces[module]`.
- Failing scenario: if `batches` changes and line 194 does not, a KeyError inside the command generator escapes `run_all` and `run_gate` (both catch only GateError and OSError), so the gate dies with a traceback and no count line.
- Suggested fix: derive `spaces` from the same batches the checker runs.

m6. gates/check_pytest.py:182
- Problem: `if identity is not None` is dead code, because `read` (line 166) already raised on a case it cannot place. It also carries a second, silent-drop policy for foreign cases.
- Failing scenario: if the check in `read` is relaxed, a failing foreign case is dropped and the run exits 0.
- Suggested fix: drop the branch and make `identify` total after `read`.

m7. gates/check_pytest.py:105
- Problem: `message or ""` is a no-op at runtime that exists only to satisfy the type checkers, after the None test at line 103 was folded into `any(...)`.
- Failing scenario: if the guard at line 103 is loosened, a failure with no message becomes an empty-message finding instead of an unreadable report, and no type checker notices.
- Suggested fix: narrow `message` explicitly (`if message is None: raise ...`) and drop `or ""`.

m8. tests/test_check_pytest_core.py:67
- Problem: `test_one_pytest_per_module` seeds a single module and never checks that the module's path is in argv.
- Failing scenario: a gate that runs one pytest over all modules, or over tests/ with no module argument, still passes.
- Suggested fix: seed two modules and two replies, and assert that each Command names exactly one module and that the two modules differ.

m9. tests/test_check_pytest_core.py:73
- Problem: `"pytest" in command.argv` pins how pytest is invoked.
- Failing scenario: a correct gate that starts `/…/bin/pytest` by absolute path fails the test.
- Suggested fix: assert behaviour (the module in argv, the outputs) instead of the spelling.

m10. tests/test_check_pytest_core.py:76-84
- Problem: the test requires that no `PYTEST_`-prefixed variable reaches pytest. The spec names only PYTEST_ADDOPTS and PYTEST_PLUGINS, and the test leans on the ambient PYTEST_CURRENT_TEST.
- Failing scenario: a spec-correct gate that drops exactly those two variables fails.
- Suggested fix: seed both named variables and assert that those two are absent.

m11. tests/test_check_pytest_core.py:86
- Problem: `test_exit_five_is_unfinished` seeds a report holding one passing case, so it never exercises the empty report a real no-collection run writes.
- Failing scenario: a gate that expects status 5 for an empty report passes the test but lets a no-test-collected run exit 0.
- Suggested fix: seed `tests="0"` with no testcase.

m12. tests/test_check_pytest_core.py:109
- Problem: `test_foreign_case_is_unfinished` pins a classname rule that no document states.
- Failing scenario: a gate that reports every failed case in the module's report as `<path>::<name>` is spec-compliant but fails the test.
- Suggested fix: write the rule into the quality-gates spec first, or drop the test.

m13. tests/test_check_pytest_core.py:117-125
- Problem: for a scratch root that cannot be made, the test checks only exit 2, no Command and no seed line.
- Failing scenario: a gate that prints nothing, the wrong count line, or the error twice still passes.
- Suggested fix: assert the exact lines: one error line naming the path and the OS error, then `check_pytest: 0 finding(s) in 1 Python file(s)`.

m14. tests/test_check_pytest_core.py (no line: missing case), and the fake at :37
- Problem: no FakeRunner case covers a signal death (status 137 with `junit: None`). The fake also always answers with the suite name the gate itself chose, so dropping `-o junit_suite_name` would go unnoticed.
- Failing scenario: a `read` that returns an empty Report on a missing JUnit file is caught only by the status check, and a missing suite-name option passes every test.
- Suggested fix: add a 137-with-no-junit case asserting the seeded output is printed whole, and build the fake's suite name from the Command's argv.

### Note

n1. gates/core/report.py `render`, reached through gates/check_pytest.py:165
- Problem: an Unfinished text is printed once per run.
- Failing scenario: two modules whose pytest died with byte-identical output (for example, a shared conftest killing pytest during configure) print one block, and nothing names the modules that did not finish. The probe showed exactly this.
- Suggested fix: an owner ruling on whether the module's given path prefixes a pytest Unfinished.

n2. gates/check_pytest.py (through gates/core/checker.py)
- Problem: behaviour changes that conform to the core decisions: `start_new_session=True` in place of `process_group=0`, UTF-8 decoding with replacement, and a GateError or OSError in one module ending the check (decisions 23 and 27).
- Failing scenario: none; these are recorded so the change is visible.
- Suggested fix: none.

Counts: blocking 1, minor 14, note 2.

Verdict: NOT MINOR
