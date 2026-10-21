# No-wall-clock design: Order gaps, step 5 on

Spec is `docs/superpowers/specs/2026-10-21-no-wall-clock-design.md` (main, as checked out in the nwc-audit worktree). Steps 1-4 and step 5's port part count as built on nwc-build (bc412ad).

1. Step 5: the step's text "the group tests onto it, their time cap a positive cap on a `VirtualClock` ... `main`'s command-line test ... on a still `VirtualClock`" (spec:234) replaces at least `test_timed_out`, `test_timeout_kills_group` and `test_main_command_line` with new claims, but the red shape allows "optionally `replaces:`, one test id under `tests/`" (.claude/agents/test-writer.md:26), and the port shape requires "every assert statement byte for byte as before; no test removed, no expected value changed" (test-writer.md:40), so no single test-writer shape takes the step.

2. Steps 5-7: "Each step lands green under `make check` before the next starts." (spec:228) clashes with step 5's "These are the red tests for `run`'s wait through its clock" (spec:234), which step 8 (spec:237) turns green only after steps 6 and 7. Step 5's red tests stay failing through steps 6 and 7, so none of steps 5, 6 or 7 can land green.

3. Step 6: "the one real-time test, kept on its own, and every other behaviour of `SystemClock` through a `Ready` the test hands in" (spec:235) is two behaviours in two files, and a red brief takes "`behavior:`, one behavior" (test-writer.md:26), so test-writer refuses the step as steering.

4. Step 6: `SystemClock` "hands `seconds` to ready as they are" (spec:128), so the real time in the real-time test can only be spent in the test's own `Ready`, as a positive timeout on a blocking wait in a test file. Both the clock rule's "as does a timeout above 0 to a blocking `wait`, `join`, `result`..." (docs/superpowers/specs/2026-10-17-quality-gates-design.md:120) and the Homes row's "a positive timeout on `wait` ... in a test file" (spec:211) forbid that, and the data exception covers only "a cap handed to ... a `Clock`'s `wait`" (spec:203). The test cannot be written inside the rules.

5. Step 6: it relies on step 1's "decision 16, a cap handed to a `Clock`'s `wait` passing the clock rule at `:120` as data" (spec:230). Neither main's nor nwc-build's quality-gates-design.md contains the word `Clock`, and line 120 still exempts only "a cap handed to `Command` or `python_module`", so the test-writer, who reads expected behaviour from `docs/`, finds no document that allows the real-time test's cap.

6. Step 7: subject to item 2 only.

7. Step 8: fits.

8. Step 9: "`rewrite`: `run_all`'s cleanup on `_Live.closing`, with no `REKILL` (decision 7). Agent: `gatesmith`, no red test." (spec:238) is not a shape gatesmith takes: its only rewrite is "`rewrite`: one `mutant-hunter` `REWRITE` line naming a path under `gates/`, verbatim, as the whole brief" (.claude/agents/gatesmith.md:33), so the brief draws `REJECTED: STEERING`.

9. Step 9: the step adds behaviour, "a checker `run` starts is killed as it is added to the live set" (spec:159), with "no red test" (spec:238). That breaks "Every behavior gets its red test before its code" (CLAUDE.md:12), and no step writes a test that would fail on code that drops the kill at add.

10. Step 10: "prove ... that the bound raises in the main thread ... and that the exception reaches the code around the wait" and "No step from 11 on starts before the spike proves both" (spec:239) is two claims, and spiker answers "two claims it counts as "both" or joins with "and whether"" with `OVERLOADED:` before anything runs (.claude/agents/spiker.md:28).

11. Step 10: spiker's steps need "Run `nproc`" (spiker.md:35) and "is wrapped in `timeout`" (spiker.md:39), and its Bash rail allows "`podman`, `timeout`, `nproc`" (spiker.md:47). This macOS host has neither `nproc` nor `timeout`, so the spiker cannot run its own mandated commands.

12. Step 10: the spike depends on real time. It must wait until pytest-timeout's bound fires (`timeout = 30`, `pyproject.toml:55`) in each of three waits, and spiker may change "never a setting, dependency, timeout or cap the step does not name" (spiker.md:39). Each case sits out 30 real seconds, and its wrapping cap has to outlast that.

13. Step 11: "the red tests for `run_all`'s pacing and for `check_with` carrying `Run.next_done`" (spec:240) are two behaviours against two stubs (`gates/core/checker.py`, `gates/core/runner.py`), but a red brief takes "one behavior" and "`view:`, one `.pyi`" (test-writer.md:26), so the brief is refused.

14. Step 11: the step also moves "its two callers onto it" and rewrites `tests/support/scripted.py` (spec:240), which is port work, and port requires "every test of the `after` run is `passed`" (test-writer.md:43). The same brief's red tests must fail, so neither shape fits.

15. Step 12: step 11's red test for "`check_with` carrying `Run.next_done`" turns green only at step 13 (spec:242). After step 12 (spec:241) it still fails on `check_with`'s `NotImplementedError`, so step 12 cannot land green under "Each step lands green under `make check` before the next starts." (spec:228).

16. Step 13: fits.

17. Step 14: "with the red test for the output reader (decision 5)" (spec:243) needs `run`'s `read` parameter and `read_output`, but step 3 stubbed only "`run`'s `clock` parameter" and the `next_done` seams (spec:232), and nwc-build's `run` is `def run(command: Command, *, clock: Clock = SYSTEM)`. The red test fails with a `TypeError` (test-writer's `test-error`, "repair and rerun", test-writer.md:35, :38), not for the right reason.

18. Step 14: "The signal tests onto `lifeline.py`, with the red test for the output reader" (spec:243) mixes port, which needs a green `after` (test-writer.md:43), with a red test that must fail, so the step fits no single test-writer shape.

19. Step 15: gatesmith's module step requires "Each test must fail for the right reason, an assertion about the gate, the module or the stub's raise as the last frame. One that ... errors in its own lines or fixtures, goes on `TEST WRONG`" (gatesmith.md:52). Step 14's reader test can only error on the missing `read` keyword, so gatesmith writes nothing.

20. Step 16: "the red test for `WAITING` (decision 3)" (spec:245) imports `heavy.WAITING`, which no step stubs (step 3, spec:232, touches only clock.py, checker.py and runner.py; nwc-build's `gates/heavy.py` has no `WAITING`). The test fails as a `collection` error, not `assertion` or `not-implemented` (test-writer.md:35, :38).

21. Step 16: "The heavy tests onto `lifeline.py`, with no timeout, and the red test for `WAITING`" (spec:245) mixes a five-file port, which must end green (test-writer.md:43), with a red test that must fail, so no single shape fits.

22. Step 17: under gatesmith.md:52, step 16's `WAITING` test errors at import instead of failing on a stub's raise, so it goes on `TEST WRONG` and `gates/heavy.py` is not built.

23. Step 18: "The pytest gate's cap tests onto `Scripted` ... the red tests for `run_gate` carrying `next_done` ... and its given-order tests onto `MEET`" (spec:247) mixes two ports, which must end green (test-writer.md:43), with a red test that must fail, so test-writer has no shape for the brief.

24. Step 19: fits.

25. Step 20: "`captured` with no bound of its own (decision 4). Agent: `test-writer`." (spec:249) names no shape. The held-fd tests (`tests/test_support_capture.py:687`, `:708`, `:725`) can be removed only under `moved` ("remove a test only when no document line holds its claim", test-writer.md:41), and `moved` changes "exactly the tests whose claim a moved line reaches". That leaves the timed waits the design lists at `tests/test_support_capture.py:209`, `:293`, `:547` (`timeout=20`, spec:9), which no moved capture-design line reaches, so no shape removes both.
