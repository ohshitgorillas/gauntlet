# Review: C3 hardening, f5ff6d2^..2795e3e

Both reports below are the reviewers' output, unedited. Each reviewer got the brief `f5ff6d2^..2795e3e` and nothing else. They ran on branch `c3-hardening-review` cut from `main` at 3cfd9ed, so the working tree was past 2795e3e; the diff-reviewer notes this.

## test-reviewer

Note: `~/dev/CLAUDE.md` does not exist on this host (neither `/root/dev/` nor `/home/user/dev/`), so I could not apply the 7.1f overload check. The brief is a bare commit range, so I reviewed it.

```
SCOPE f5ff6d2^..2795e3e -- tests/ | test files: 11
FINDINGS 14
  loosened /home/user/gauntlet/tests/test_core_checker_signals.py:146 | The diff dropped SIGQUIT at the OS default and gave the driver a Python handler that raises SystemExit(7), so the quit case now only tests `run`'s cleanup on any exception and no longer tests whether it answers SIGQUIT | passes on wrong code: a `run` that leaves SIGQUIT out of the signals it answers lets the caller's handler raise SystemExit inside its wait; the generic exception cleanup kills the group and the driver exits 7, while at the real OS default the process would dump core and orphan the group | docs: 2026-10-20-gates-core-design.md §1 checker.py (`run`: "the whole group is killed ... on any interrupt") | fix: make the handler exit 7 only if the checker's group is already dead when it runs (otherwise another code), or keep SIG_DFL with RLIMIT_CORE set to 0
  loosened /home/user/gauntlet/tests/test_core_checker_run_all_signals.py:203 | Same defect for `run_all`: with a SystemExit handler on SIGQUIT, the quit case cannot tell answering SIGQUIT apart from cleanup on any exception | passes on wrong code: a `run_all` whose main thread does not answer SIGQUIT still gets exit 7 and both groups killed through its any-exception cleanup | docs: 2026-10-20-gates-core-design.md §7 decision 26 | fix: same as above, so the handler's exit code shows whether the groups were dead before it ran
  loosened /home/user/gauntlet/tests/test_core_checker_run_all_signals.py:187 | Only the SIGTERM and SIGINT handlers are checked as put back, though the file itself treats SIGHUP and SIGQUIT as ending signals `run_all` answers | passes on wrong code: a `run_all` that restores SIGINT and SIGTERM but leaves its own SIGHUP and SIGQUIT handlers installed | docs: 2026-10-20-gates-core-design.md §7 decision 26 ("puts the handlers back") | fix: compare the SIGHUP, SIGQUIT, SIGTERM and SIGINT handlers before and after
  loosened /home/user/gauntlet/tests/test_check_pytest_processes.py:15 | The diff deleted `test_no_command` (counting commands seeded on PATH must not be what is read) and `test_host_count`, and no remaining or added test holds C to "read in the gate's own process and never from a command" | passes on wrong code: a `cpu_budget()` that shells out to `nproc` or `sysctl -n hw.ncpu` gives the same count, since the affinity that test_core_checker_budget_cpus narrows is inherited by the child command | docs: 2026-10-17-quality-gates-design.md §Tests, "pytest strictness", sub-bullet "Each test module" | fix: restore the seeded-counting-commands test against `cpu_budget`
  design-pinned /home/user/gauntlet/tests/test_check_pytest_core.py:117 | Asserts that no variable starting with `PYTEST_` reaches pytest, but the spec only requires that PYTEST_ADDOPTS and PYTEST_PLUGINS are gone | fails on right code: a gate that drops exactly PYTEST_ADDOPTS and PYTEST_PLUGINS still passes on PYTEST_CURRENT_TEST and PYTEST_VERSION, which pytest sets in the test's own environment | docs: 2026-10-17-quality-gates-design.md §Tests, "pytest strictness" ("an environment without `PYTEST_ADDOPTS` and `PYTEST_PLUGINS`") | fix: assert on the two named variables, seeded in the environment the gate starts from
  design-pinned /home/user/gauntlet/tests/test_check_pytest_core.py:159 | Treats a failed JUnit case whose classname is another module's as an unfinished run, which no document states | fails on right code: a gate that reports that case as a finding (`<path as given>::test_seeded: Seeded`, exit 1) | docs: none | fix: drop the test, or have the ruling written into the spec first
  design-pinned /home/user/gauntlet/tests/test_check_mypy_stopped.py:100 | Builds the gate-internal `Report(records, stderr)` to call `Mypy.lines`, while the design gives `lines` the `list[Record]` that `read` returns | fails on right code: a `Mypy` shaped as §2 shows, with no `Report` type, fails at import | docs: 2026-10-20-gates-core-design.md §2 | fix: drive the stopped path through `run_gate` with a FakeRunner reply of mypy's exit 2
  design-pinned /home/user/gauntlet/tests/test_check_mypy_stderr.py:211 | The whole file (lines 193, 204, 211, 222, 229) pins "a stop prints stderr as Unfinished, a finish prints it again as Remarks", which the file sources to a review ruling and no document states | fails on right code: a gate that prints a finished mypy's findings and count line only, which §Gates allows, fails the expected [PLUGIN_WARNING, REPORT_BUG, COUNT_ONE] | docs: none | fix: hold the tests until the ruling is written into the quality gates spec, then cite it
  loosened /home/user/gauntlet/tests/test_check_mypy_stderr.py:204 | A stop with a record asserts only the status, the line count and the last line, never that the first line carries the record | passes on wrong code: a gate that prints a line of its own (for example "mypy stopped") in place of the record it read | docs: 2026-10-17-quality-gates-design.md §Gates ("the gate prints the report it read") | fix: assert that the first line carries MESSAGE and the record's file
  loosened /home/user/gauntlet/tests/test_check_mypy_stderr.py:222 | Asserts that the stderr line is somewhere in the output and checks the count line, but never that the finding is printed or that no other line appears | passes on wrong code: a gate that counts the record as 1 finding but never prints its finding line | docs: 2026-10-17-quality-gates-design.md §Gates ("prints each finding on its own line") | fix: assert the exact list of lines
  loosened /home/user/gauntlet/tests/test_check_mypy_warm_cache.py:194 | The "warm on no repo file" check only looks for the source's file name among the warm's arguments | passes on wrong code: a warm of `python -m mypy --cache-dir D <project root>`, which checks every file in the tree | docs: 2026-10-17-quality-gates-design.md §Types (first bullet's sub-bullet: "warms one temp mypy cache on no repo file") | fix: assert that no argument names a path inside the project root
  loosened /home/user/gauntlet/tests/test_check_mypy_warm_cache.py:275 | A failed warm is checked for exit 2, the count line last and one command, but never for the error the spec says it prints | passes on wrong code: a gate whose warm GateError carries an empty report, so the run prints the count line alone | docs: 2026-10-17-quality-gates-design.md §Types ("the gate prints the error, then its count line, exits 2") | fix: assert that the lines before the count line carry WARM_REFUSAL
  loosened /home/user/gauntlet/tests/test_check_mypy_warm_cache.py:291 | A failed copy asserts that one line comes before the count, but not that it names the tree or the OS error | passes on wrong code: a gate that prints its own fixed wording, naming neither the path nor the error | docs: 2026-10-20-gates-core-design.md §7 decision 18 ("a GateError naming the tree and the OS error") | fix: assert that the error line holds the warm cache path and the OS error text
  design-pinned /home/user/gauntlet/tests/test_core_runner_budget.py:128 | Expects `Unfinished(str(error))` for the GateError case as well, which pins GateError's `str` to its report, while the documents say the runner reads `.report` | fails on right code: a GateError whose `str` differs from `.report` (for example prefixed), with `check_with` correctly giving `Unfinished(error.report)` | docs: 2026-10-20-gates-core-design.md §7 decisions 6 and 23 | fix: expect REFUSAL for the gate-error case and `str(error)` only for the OSError case
READ /home/user/gauntlet/docs/superpowers/specs/2026-10-20-gates-core-design.md, /home/user/gauntlet/docs/superpowers/specs/2026-10-17-quality-gates-design.md, /home/user/gauntlet/Makefile (check target), /home/user/gauntlet/tests/support/scripted.py, /home/user/gauntlet/tests/support/fake.py, /home/user/gauntlet/tests/support/project.py, /home/user/gauntlet/tests/test_core_checker_run_all.py, /home/user/gauntlet/tests/test_core_checker_run_all_signals.py, /home/user/gauntlet/tests/test_core_checker_signals.py, /home/user/gauntlet/tests/test_check_pytest_core.py, /home/user/gauntlet/tests/test_check_pytest_processes.py, /home/user/gauntlet/tests/test_core_runner_budget.py, /home/user/gauntlet/tests/test_check_mypy_core.py, /home/user/gauntlet/tests/test_check_mypy_stderr.py, /home/user/gauntlet/tests/test_check_mypy_stopped.py, /home/user/gauntlet/tests/test_check_mypy_warm_cache.py, /home/user/gauntlet/tests/test_check_pytest_cpus.py (lines 1-20, 100-140), /home/user/gauntlet/tests/test_core_checker_budget_cpus.py (lines 1-50), /home/user/gauntlet/tests/test_check_pytest_parallel.py (lines 1-22), /home/user/gauntlet/tests/support/capture.py (definitions only)
COMMANDS
  grep -n "7.1f" -A6 ~/dev/CLAUDE.md 2>&1 | head -30
  git -C /home/user/gauntlet diff f5ff6d2^..2795e3e --stat -- tests/
  ls /home/user/dev/CLAUDE.md /root/dev 2>&1; grep -n "7.1" /home/user/dev/CLAUDE.md 2>&1 | head
  git -C /home/user/gauntlet log --oneline f5ff6d2^..2795e3e; git -C /home/user/gauntlet diff f5ff6d2^..2795e3e -- tests/test_check_pytest_processes.py tests/test_core_checker_signals.py
  cd /home/user/gauntlet && ls docs docs/superpowers/specs tests tests/support && wc -c docs/*.md docs/superpowers/specs/*.md && sed -n '/^check:/,/^$/p' Makefile
  cd /home/user/gauntlet && cat -n tests/support/scripted.py && cat -n tests/support/fake.py && cat -n tests/support/project.py | head -80
  cd /home/user/gauntlet && cat -n tests/test_core_checker_run_all.py
  cd /home/user/gauntlet && cat -n tests/test_core_checker_run_all_signals.py
  Grep pattern="ENDING_SIGNALS|SIGQUIT|SIGHUP|SIGINT|signal" path=/home/user/gauntlet/docs
  cd /home/user/gauntlet && cat -n tests/test_core_checker_signals.py
  cd /home/user/gauntlet && cat -n tests/test_check_pytest_core.py; git diff f5ff6d2^..2795e3e --name-status -- tests/; grep -ln "cpu_budget\|sched_getaffinity\|cpus()" tests/
  Grep pattern="junit_suite_name|classname|foreign|suite name" path=/home/user/gauntlet/docs
  Grep pattern="sched_getaffinity|cpu_count|cpu_budget|COUNTING|sysctl" path=/home/user/gauntlet/tests
  cd /home/user/gauntlet && cat -n tests/test_check_pytest_processes.py; git show f5ff6d2^:tests/test_check_pytest_processes.py | sed -n 1,12p
  Grep pattern="PATH|nproc|getconf|read_cpus" path=/home/user/gauntlet/tests glob="test_{check_pytest_cpus,check_pytest_unread_cpus,core_checker_budget,core_checker_budget_cpus,check_pytest_parallel}.py"
  cd /home/user/gauntlet && sed -n 1,20p tests/test_check_pytest_cpus.py; sed -n 100,140p tests/test_check_pytest_cpus.py; sed -n 1,50p tests/test_core_checker_budget_cpus.py
  cd /home/user/gauntlet && cat -n tests/test_core_runner_budget.py
  cd /home/user/gauntlet && cat -n tests/test_check_mypy_core.py tests/test_check_mypy_stderr.py
  Grep pattern="stderr|INTERNAL|Remark" path=/home/user/gauntlet/docs
  cd /home/user/gauntlet && cat -n tests/test_check_mypy_stopped.py
  cd /home/user/gauntlet && cat -n tests/test_check_mypy_warm_cache.py
  cd /home/user/gauntlet && sed -n 1,22p tests/test_check_pytest_parallel.py; git log --oneline -1 -- tests/test_check_pytest_parallel.py
  cd /home/user/gauntlet && wc -l tests/support/capture.py && grep -n "def \|class \|merged" tests/support/capture.py | head -30
END REVIEW
```

## diff-reviewer

```
SCOPE f5ff6d2^..2795e3e
REVIEWED 5
  /home/user/gauntlet/gates/check_mypy.py
  /home/user/gauntlet/gates/check_pytest.py
  /home/user/gauntlet/gates/core/checker.py
  /home/user/gauntlet/gates/core/runner.py
  /home/user/gauntlet/tests/support/scripted.py
SKIPPED 11
  /home/user/gauntlet/docs/superpowers/specs/2026-10-20-gates-core-design.md
  /home/user/gauntlet/tests/test_check_mypy_core.py
  /home/user/gauntlet/tests/test_check_mypy_stderr.py
  /home/user/gauntlet/tests/test_check_mypy_stopped.py
  /home/user/gauntlet/tests/test_check_mypy_warm_cache.py
  /home/user/gauntlet/tests/test_check_pytest_core.py
  /home/user/gauntlet/tests/test_check_pytest_processes.py
  /home/user/gauntlet/tests/test_core_checker_run_all.py
  /home/user/gauntlet/tests/test_core_checker_run_all_signals.py
  /home/user/gauntlet/tests/test_core_checker_signals.py
  /home/user/gauntlet/tests/test_core_runner_budget.py
READ /home/user/gauntlet/gates/core/report.py, /home/user/gauntlet/gates/core/project.py, /home/user/gauntlet/tests/support/fake.py, /home/user/gauntlet/Makefile, /home/user/gauntlet/docs/design.md (the Not instead lines, §1, §8), /home/user/gauntlet/docs/superpowers/specs/2026-10-17-quality-gates-design.md. In the working tree, check_pytest.py, checker.py, runner.py and report.py no longer match 2795e3e. Every line cited below is at 2795e3e, rebuilt with `git diff 2795e3e`. That also means I saw the later working-tree version of those files.
FINDINGS 7
  shortcut | /home/user/gauntlet/gates/check_pytest.py:220 | `main` hands its reader's None (the CPU count that cannot be read) to `cpu_budget`, where None means "read this host's own CPUs"; the `lambda: None` default at line 211 exists only to land in that fallback | fails when: `main(paths, read_cpus=lambda: None)` runs on a host whose affinity can be read: every test module runs and the gate exits 0 or 1, but the spec says a CPU count the gate cannot read is a run the checker did not finish, exit 2.
  gate-gaming | /home/user/gauntlet/gates/check_pytest.py:105 | `message or ""` guards against a None that the check on line 103 already rejects (it tests every failed child, `failed[0]` included); it is there only so mypy and pyright accept `str | None` as `str` | fails when: mutmut turns `""` into another string and the mutant survives because no input reaches it, an equivalent mutant the spec answers with a rewrite; and if line 103's check is ever narrowed, a failure with no message becomes an empty-message finding instead of a report the gate cannot read, with no type error left to catch it.
  leftover | /home/user/gauntlet/gates/check_pytest.py:182 | `lines` runs `identify` again on every case that `read` already identified at line 166, and its `if identity is not None` can never be false because `read` raises on any None | fails when: the two copies of the rule drift apart, for example `read`'s check is loosened: a failing case that is not the module's is then silently dropped from the findings instead of marking the module unfinished, and N in the count line comes out too low.
  shortcut | /home/user/gauntlet/gates/check_pytest.py:198 | the seed note is attached to whatever Outcome `check_with` returns, including the one it builds at runner.py:155-156 when the budget raises and no pytest starts | fails when: the host's CPU count cannot be read (`cpu_budget` raises at checker.py:398): the gate prints `check_pytest: seed N` for a seed pytest-randomly never used, then the error and the count line. A temp space that cannot be made prints no seed line, as the docstring at lines 190-192 says.
  shortcut | /home/user/gauntlet/gates/check_pytest.py:149 | the module's path goes into pytest's JUnit report through an `-o junit_suite_name=` ini override (lines 149-150) and comes back as `report.module`, a way around `Checker.read` not being given its batch | fails when: pyproject.toml's pytest settings set `junit_suite_name`: the gate overrides it on the command line, so pytest runs with a setting pyproject.toml does not hold, against the spec's "pytest takes its settings from the repository's `pyproject.toml` only".
  shortcut | /home/user/gauntlet/gates/core/checker.py:471 | `run_all`'s cleanup re-kills `_LIVE` on a 50 ms poll (`REKILL`, line 28), because `run` registers a checker only after `Popen` returns (line 95) and nothing stops a worker from starting a checker once the end has begun; the removed `Started.end` closed this under a lock | fails when: an interrupt lands while a worker is between `_streams` and `Popen`: the first `kill_all` misses it, the worker starts a new checker after the gate was told to end, and that checker runs until a later tick kills it.
  gate-gaming | /home/user/gauntlet/tests/support/scripted.py:53 | `threading.Event().wait(step.hold)` waits on a new Event that nothing ever sets, so it is a sleep written in a form the spec's no-sleep rule (which matches `time.sleep` and similar by name) cannot see, and it makes calls overlap by timing instead of by synchronisation such as `threading.Barrier` | fails when: on a loaded host a held call ends before the next one is submitted, so `peak` comes out below the cap and any test that counts concurrency through it fails intermittently.
COMMANDS
  git -C /home/user/gauntlet diff f5ff6d2^..2795e3e --name-only
  git -C /home/user/gauntlet diff f5ff6d2^..2795e3e -- gauntlet gates pyproject.toml uv.lock Makefile .pre-commit-config.yaml .gitignore conftest.py tests/support
  git -C /home/user/gauntlet diff 2795e3e --name-only -- gauntlet gates pyproject.toml uv.lock Makefile .pre-commit-config.yaml .gitignore conftest.py tests/support
  git -C /home/user/gauntlet diff 2795e3e -- gates/check_pytest.py gates/core/checker.py gates/core/runner.py
  git -C /home/user/gauntlet status --short
  wc -c /home/user/gauntlet/docs/design.md /home/user/gauntlet/docs/superpowers/specs/2026-10-17-quality-gates-design.md
  git -C /home/user/gauntlet diff 2795e3e -- gates/core/report.py
END REVIEW
```
