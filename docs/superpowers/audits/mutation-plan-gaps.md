# C7c dry-run gaps

`P` = docs/superpowers/specs/mutation-plan-design.md, `R` = docs/superpowers/specs/mutmut-run-design.md, `G` = .claude/agents/gatesmith.md, `T` = .claude/agents/test-writer.md.

1. Step 1: "The mutmut run design's forbid (R:132) names git through `Project.git`" (P:167). R:132 is the "A capped checker's lines" row; the "a process started in `mutate` or anywhere in C7c" forbid is at R:126, so a docs builder told to reword :132 edits the wrong row or stops.

2. Step 1: "Steps 1 to 4 run beside C7b" (P:165), while step 1 writes `R` (P:167) and C7b's step 7 is an architect `rulings` pass writing the same file (R:154, "Paths: the mutmut run design"). Two concurrent writers of one design file collide, and the architect role edits only its own design file per dispatch.

3. Step 2: fits.

4. Step 3: "Red tests for `place`, `located` and `files`. Agent: `test-writer`. Paths: `tests/test_core_runner_place.py`, `tests/test_core_project_files.py`." (P:169) against "`red`: the word `red`; `behavior:`, one behavior …; `view:`, one `.pyi`" and "So is a brief that … holds two behaviors" (T:26, T:31). Three behaviors over two stub modules need two views, and the red shape has no file line, so test-writer returns `REJECTED: STEERING`.

5. Step 4: "`place`, `located` and `files`. Agent: `gatesmith` … Paths: `gates/core/runner.py`, `gates/core/project.py`." (P:170) against "Module: one path under `gates/` no gates-spec bullet builds … Scope: that path." (G:28) and "a brief carrying more than one gate, module or step is one [OVERLOADED]" (G:40). Two core modules fit no single gatesmith shape, and a split leaves step 2's one stub without the single build step it must land with.

6. Step 5: "Step 5 waits for C7b's step 16, the last C7b step that writes `gates/check_mutation.py` or `gates/mutmut_driver.py` (R:168)" (P:165). R:168 is C7b step 21; C7b's step 26 writes the driver and steps 27 and 34 write `gates/check_mutation.py` (R:173, R:174, R:181), so step 5 would stub into files C7b is still changing, and steps 7 and 11 need C7b's `meta_path` and `run_mutmut` (P:173, P:139), which only C7b steps 26 and 34 build.

7. Step 5: one `stub` over three paths (P:171), whose red tests are turned green by three build steps, 7, 9 and 11 (P:173, P:175, P:177), against "It lands, with its red tests, in the commit of the build step that turns those tests green" and "Each stub step is paired with the one build step that turns all its red tests green" (R:146). Step 7's commit would carry raise-only stubs in `check_pytest.py` and `check_mutation.py` that no test in it turns green, so `make check` fails before that commit.

8. Step 5: "in the driver `MUTANTS`, the three key names … each new body raising `NotImplementedError`" (P:171) against "write each stub path with the names and signatures the step names, each body `raise NotImplementedError`" (G:50); `P` gives `MUTANTS: str`, `SOURCE_PATHS: str`, `PYTEST_ARGUMENTS: str`, `TEST_SELECTION: str` no value (P:57–:60). A constant has no body to raise and no documented value, so gatesmith must invent the values (steering under G:38) or leave bare annotations that define no attribute, making step 6's import a `collection` error, not red.

9. Step 5: "`Mutmut.mangle`" is the only mangle stub named (P:171), while step 6 wants "`MUTMUT.mangle` on the pinned mutmut" (P:172) and C7b's `MUTMUT` is a concrete object whose entry points are stubbed separately ("`MUTMUT`, whose entry points raise", R:163). With no `mangle` on `MUTMUT`, step 6's test ends in `AttributeError`, which T:35 classes `test-error`, not `not-implemented`, so it cannot be certified red.

10. Step 6: "Red tests for the driver's additions, pure ones on a fake `Mutmut`, and `MUTMUT.mangle` on the pinned mutmut." (P:172) against "holds two behaviors" and "a test name, case, input, assertion, expected value, fixture, fake … is steering" (T:31). Seven names (`mutable`, `mutated_path`, `unmutated_path`, `settings_text`, `function_spans`, `MUTMUT.mangle`, the constants) are many behaviors, and naming the fake designs the test, so test-writer refuses it.

11. Step 7: "The driver's additions, and C7b's `meta_path` on `MUTANTS`." (P:173) against the module shape "one path … the spec file and section … and its red test paths" and "Every other line is steering: how to build the step" (G:28, G:38). `meta_path` on `MUTANTS` is a rewrite no step 6 test can turn red, and stating it in a gatesmith module brief is steering.

12. Step 8: "Paths: `tests/test_check_pytest_settings.py`" (P:174) against the red shape, which carries `red`, `behavior:`, `view:` and `replaces:` only and calls "another path" steering (T:26, T:31). The plan's file path cannot be put in the brief, so the file test-writer writes is its own choice, not the plan's.

13. Step 9: "`settings_arguments`, the pytest gate's command on it, and `module_classname` on `Project.located`." (P:175) against G:27–:28 and "how to build the step … is steering" (G:38). The command and `module_classname` changes keep behavior, so no step 8 red test covers them; carried in the brief they are steering, left out they are never built, and G:63 forbids the step from running anything beyond the red tests to check them.

14. Step 10: "Red tests for `hunk_changes`, `changed_functions`, `has_head`, `changes`, `select_changes`, `lay_out` and `mutate`, through `FakeRunner` and `scaffold(git=True)`." (P:176) against "holds two behaviors" and "fixture, fake … is steering" (T:31). Seven behaviors over two files with named fixtures get `REJECTED: STEERING`.

15. Step 10: the red test for `mutate` runs against a body "still raising its GateError" (P:171), against "each new test is `assertion` or `not-implemented`" (T:38) with any other exception classed `test-error` (T:35). A test that calls `mutate` directly fails on `GateError`, not for the right reason, so it cannot be certified red.

16. Step 11: "… and `mutate`, and `SCOPE_KEYS` on the driver's key names." (P:177) against "how to build the step … is steering" (G:38). `SCOPE_KEYS` on the key names is a rewrite with no red test from step 10, so it cannot be carried in a gate or module brief.
