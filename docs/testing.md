# Testing policy

Binding for every test in the Gauntlet repository, written by a person or an agent. A test that breaks a rule here is rejected in review even when it passes. Adapted from `~/dev/hqptuner2/docs/spec/testing.md`; where that file and this one differ, this one governs here.

Two kinds of test live here:

- **Python suites** for the scripts a workflow runs, such as `fence/test_*.py`. Each one runs with `uv run --no-project --with <the script's dependencies> --with pytest pytest -q <folder>`.
- **Workflow fixtures**, the `fixtures/*.stubs.yaml` files that `archon workflow test` runs. Each one stubs node outputs and states the route the workflow must take.

## Core rules

1. **Test behavior, never implementation.** A test asserts the observable contract: given these inputs, files and environment, the public surface returns this result or leaves this file behind. Private helpers, internal state, call order and log text are off limits. A refactor that keeps the behavior but turns a test red shows the test is defective.

2. **One assertion per test.** Each test holds one `assert` statement or one `pytest.raises` block, so a failure names one broken behavior. Sweep cases with `@pytest.mark.parametrize`, one condition per case, never with an assert in a loop or a stack of asserts. `a and b` is two assertions, and `all()` or `any()` over a generator is a sweep that was not parametrized.

3. **Public surface only.** A test calls what a caller calls: an MCP tool function, a script's entry point or a workflow's inputs. It does not reach into `_private` names or monkeypatch internals. Setting the environment variables the script documents, such as `FENCE_READ`, is input, not monkeypatching.

4. **Fakes sit at the boundary, never over our own code.** Use a real temporary folder, a real subprocess and a real git repository where the code touches one. Never stub the script's own functions to test the script.

5. **Assert specific facts, not snapshots.** Compare the fields that carry meaning. Equality against a whole dumped structure re-asserts the implementation back at itself and breaks on harmless change.

6. **Names state behavior.** Write `test_copy_overwrites_existing_destination`, not `test_copy_2`.

7. **No test waits on the wall clock.** A timeout, retry or poll loop is tested by what it concludes and how many passes it makes, never by how long it takes. Code that paces itself takes an injectable clock or timeout, and the test hands in one that cannot stall. A test that needs a real wait to pass is defective whatever it covers. The `clock-seams` skill holds the mechanics.

8. **New tests must bite.** A test for new or changed behavior must fail against the code before the change. Prove it with a red run: tests in place, implementation not yet written, red expected. Only a failure while the test runs proves bite; an import or collection error proves nothing. For a new surface, write a null stub first, where every new function exists and returns its zero value or does nothing, and the new tests must go red against it. Characterization tests of existing behavior, and tests that accompany a pure refactor, are exempt, and the hand-back says so.

9. **Assert only what the test put in, wire identifiers, and values derived from them.** Error messages, return strings and status sentences written inside a script are copy and are never asserted. Match an error by its type, plus a wire identifier where the message carries one: `pytest.raises(PermissionError, match="FENCE_WRITE")` names an environment variable and is legal; `match="not unique"` is a sentence and is not. Environment variable names, JSON keys, exit codes, node ids and file paths the test supplied are contract.

10. **A test discriminates, or it is a tautology.** Name one plausible implementation the assertion fails and one it passes. If the only failing one is "the feature is absent", the test pins nothing. These shapes fail that check:
    - Asserting existence instead of value: truthiness, `is not None`, a length or a key's presence.
    - Asserting a value the absent feature also produces: `0`, `None`, `""`, `[]`, `False`, a file that was never written, or the fixture's own default.
    - Asserting the fix's own mechanism: a new helper was called or a new flag is set.
    - Round-tripping a writer through its own reader. Pin one half against a value the fixture supplied.
    - Restating the implementation's arithmetic. Write the number.

11. **A test guards against a bug, never against a change of mind.** Before keeping a test, write the bug report its failure would file. If the test can only turn red because the owner decided differently, it pins a decision: reshape it into the invariant the decision serves, or delete it. Formatting, key order and the wording of a return string are decisions.

12. **A test costs.** It costs run time, upkeep and every reader's time. A test that constrains nothing another test does not already constrain is deleted. Two tests where one cannot fail without the other are one test. A test written to reach a line is rule 1 broken by another route.

13. **Fakes answer from tables, never from logic.** A fake or stub that derives its answer with the code's own algorithm is a second implementation that is wrong together with the first. The test writes the table.

14. **Helpers return values.** No `assert` lives outside a `test_*` function. A helper builds the setup or returns the evidence, and the test asserts it. A fixture that must refuse to run raises.

15. **No environment coupling.** No test reads the hostname, locale, timezone, working directory, `HOME`, a fixed port or the real checkout. Every path comes from `tmp_path` or from what the test built.

16. **One unit, one result.** A decision lives in a function whose return value is the decision. New behavior that cannot name the one value its test will assert is split before it is written.

## Workflow fixtures

Rules 2, 6, 10, 11, 12 and 13 bind fixtures too, read this way:

- **One route per fixture.** Each fixture drives the workflow down one route and names it in its file name, such as `red-check.stubs.yaml`.
- **The stubs are the table.** A stub states node outputs as literal values; it never reproduces a node's own logic.
- **A fixture discriminates.** The `expect` and `reached` it states must fail if the route's deciding edge were wired to a different node. A fixture that any wiring of the workflow would pass is deleted.
- **One route, one fixture.** Two fixtures that cannot fail apart are one fixture.

## Skips

A `skip` or `xfail` on a test, or any skip whose reason is that the test is broken, flaky or unfinished, needs the owner's approval of that site before it is written. A skip on a precondition its reason names, such as `importorskip` or a missing binary, is allowed.
