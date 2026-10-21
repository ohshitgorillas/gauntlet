Status: proposed, for the owner's approval.

## Why

The roster gives `test-writer` two steps (`docs/superpowers/specs/2026-10-18-agents-design.md:28`). A red-test step writes the red test for one behavior against a `stubgen` view of a stub. A `finding` step fixes upheld findings, keeps every test green, and blocks any fix that removes a test or changes an expected value (`docs/superpowers/specs/2026-10-18-agents-design.md:60`). Neither shape fits the test work of the no-wall-clock design, read from the `no-wall-clock` branch, whose **Order** names `test-writer` for six steps (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:135`–`:142`).

- Steps 2, 3 and 8 (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:135`, `:136`, `:141`) write or rewrite a helper under `tests/support/` and move existing tests onto it, green before and after. No behavior is new, so there is no red test, and no finding names them, so there is no `finding` step.
- Steps 4 and 6 (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:137`, `:139`) mix that move with a red test for a production change that no step stubs first. `run` (`gates/core/checker.py:66`) takes no `read` parameter and `gates/heavy.py:20` has no `WAITING`, so a red test on either fails with a `TypeError` or an `AttributeError`, never the `AssertionError` or `NotImplementedError` the red-test proof reads (`docs/superpowers/specs/2026-10-18-agents-design.md:73`).
- Step 9 (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:142`) removes the held-fd tests (`:85`), which the `finding` step blocks and no other step allows.

A step no shape owns falls to `CLAUDE.md:33`: "A step no agent above owns goes to `general-purpose` with its red test from `test-writer`." The owner bars `general-purpose` from this work.

Three places define or route test work outside the `test-writer` row. `docs/superpowers/plans/structure-first-plan.md:29` defines a support-helper step in a plan: a helper "written in C2a beside its own tests, which pass at once". `docs/superpowers/specs/2026-10-20-gates-core-design.md:329` sends a test whose expected value a spec amendment moved to "the queued R-tw-moved shape", which no roster row holds. `CLAUDE.md:33` sends any step the roster does not own, test steps included, to `general-purpose`. `docs/roadmap.md:23` records the red-test step in its `stubgen` form as unproven.

The precedent for a helper beside its own tests is in the tree: `tests/test_support_capture.py:55` imports the helper it tests. The two helpers the no-wall-clock steps rewrite have callers that stay green through the move: `tests/support/scripted.py` at `tests/test_core_checker_run_all.py:22` and `tests/test_core_runner_budget.py:25`.

## Modules

### `test-writer`: four step shapes

Its job is every write under `tests/` except a mutant kill, each in one of four shapes: red, `finding`, `port` and `moved`. The shapes live in its agents-spec row and decisions; its role file `.claude/agents/test-writer.md` holds the same shapes, since a roster ruling's home is "agents spec and role" (`CLAUDE.md:45`). Every shape runs `make check-tests` with `FILES` set to the files it wrote or changed, never `make check` (`docs/superpowers/specs/2026-10-18-agents-design.md:49`, `Makefile:15`), and reads no path under `gauntlet/` or `gates/`. It replaces the plan's helper step (`docs/superpowers/plans/structure-first-plan.md:29`), the queued shape (`docs/superpowers/specs/2026-10-20-gates-core-design.md:329`) and, for test work, the fallback at `CLAUDE.md:33`.

The red step keeps its shape and gains one optional line:

```text
red
behavior: <one behavior, in the words of the owner or a document>
view: <the .pyi stubgen made from the stub module, in the scratchpad>
replaces: <a test id a port step reported UNMOVED for this behavior>   # optional; that test is removed in the same dispatch
# done: each new test red from a run with --tb=no -rA --assert=plain, as AssertionError or NotImplementedError
```

The `finding` step is unchanged (`docs/superpowers/specs/2026-10-18-agents-design.md:60`).

The `port` step moves tests onto what an approved design gives, and changes no claim:

```text
port
design: <an approved design under docs/superpowers/specs/>, step <n>
files: <each path under tests/ the step writes, at most five>
view: <one .pyi per own-code module the files import>
# done: the files' tests green before and after; every test held before is held after, its assert statements unchanged;
#   a helper the design gives is written to the design's stubs, beside its own test file where the design lists one;
#   a test's input changes only where the design step names the change; nothing is written outside tests/
# report adds: KEPT <test id>, one per test moved
#   UNMOVED <test id> | <the production change it needs>, one per test the step leaves as it was
```

The `moved` step changes exactly the tests a document change moved:

```text
moved
lines: <each document path:line whose text changed, quoted before and after>
files: <each path under tests/ the step writes, at most five>
view: <one .pyi per own-code module the files import>
# done: the files' tests green after; each test changed or removed cites the moved line it rests on;
#   no test changes that no moved line reaches; a test is removed only when no document line holds its claim;
#   a helper under tests/support/ whose documented behavior moved changes with its own tests
# report adds: MOVED <test id> | <path:line>, and REMOVED <test id> | <path:line>
```

### `gatesmith` `stub` on a live module (decision 2)

Its job is to give a red test a name to call on a module that already holds code, so the red run reads `AssertionError` or `NotImplementedError`. It lands in the commit of the build that turns its red tests green (`docs/superpowers/specs/2026-10-18-agents-design.md:61`). It replaces the missing stubs ahead of the red tests at `docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:137` and `:139`.

```text
stub
step: <the design step's text>
paths: <each stub path>
# a new function: its body is raise NotImplementedError
# a new keyword parameter on a live function: accepted and unused, its default as the design gives it
# a new constant: the value the design gives it
```

### `CLAUDE.md` roster routing (decision 3)

Its job is to route every step that writes under `tests/` to an agent that owns a shape for it. It replaces the fallback at `CLAUDE.md:33` for those steps; a step outside `tests/` that no agent owns keeps that route.

```text
A step that writes under `tests/` goes to `test-writer`, or to `mutant-hunter` for a surviving mutant, and never to `general-purpose`; one that fits no shape stops and is reported.
```

## Homes

| Concern | Its one home | What it forbids elsewhere |
|---|---|---|
| `test-writer`'s step shapes | Its row and decisions in `docs/superpowers/specs/2026-10-18-agents-design.md` (`:28`, `:60`), with `.claude/agents/test-writer.md` holding the same shapes | A step shape defined in a plan or a design; `docs/superpowers/plans/structure-first-plan.md:29` and `docs/superpowers/specs/2026-10-20-gates-core-design.md:329` become pointers. A test brief outside the four shapes |
| Who writes under `tests/` | The roster: `test-writer`, and `mutant-hunter` for a surviving mutant (`docs/superpowers/specs/2026-10-18-agents-design.md:29`), routed by `CLAUDE.md` (decision 3) | `general-purpose`, a builder or the coordinator writing any path under `tests/` |
| What `test-writer` reads of own code | The `stubgen` view the orchestrator generates into the scratchpad (`docs/superpowers/specs/2026-10-18-agents-design.md:28`, `:58`) | A read under `gauntlet/` or `gates/`; source quoted in a brief |
| A helper's interface under `tests/support/` | The approved design's stubs for that helper, as `docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:21`–`:81` gives them | A `.pyi` brief for a helper; an interface the step chooses where a design gives one |
| Changing an expected value or removing a test | The `moved` step, each change resting on a quoted document line | A `port`, `finding` or red step that changes an expected value or removes a test, save a red step's `replaces:` of a test a port reported UNMOVED |
| A production change a test needs | The builder's `stub` step, then a red step, then the build, in one commit (decision 2) | A port that writes outside `tests/`; a test that keeps a clock wait because the seam is missing; a red test against a name the tree lacks |
| A test step's gate run | `make check-tests` with `FILES` set (`docs/superpowers/specs/2026-10-18-agents-design.md:49`, `Makefile:15`) | `make check` from `test-writer` |

A test step that fits none of the four shapes stops and reports it. It goes to no `general-purpose` agent and no builder, and the shapes are extended only by a design change.

## Order

Steps 1 to 3 land on `main`'s line; steps 4 to 16 run where the no-wall-clock design and its step-1 spec lines are. Each step lands green under `make check` before the next starts, save that steps 8 to 10 land as one commit and steps 12 to 14 as one commit (`docs/superpowers/specs/2026-10-18-agents-design.md:61`).

1. The shapes into the spec: `port` and `moved` in `test-writer`'s row and decisions, red's `replaces:` line, the `stub` step on a live module in `gatesmith`'s row and the stub decision (decision 2), the build-order proof lines (decision 5), and pointers from the plan and the gates core design. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/2026-10-18-agents-design.md`, `docs/superpowers/specs/2026-10-20-gates-core-design.md`, `docs/superpowers/plans/structure-first-plan.md`, `docs/roadmap.md`.
2. The routing line (decision 3). Agent: `role-author`. Paths: `CLAUDE.md`.
3. The role files to match step 1. Agent: `role-author`. Paths: `.claude/agents/test-writer.md`, `.claude/agents/gatesmith.md`.
4. The no-wall-clock design's **Order** re-cut onto steps 5 to 16 (decision 1). Agent: `architect`, on a `rulings` brief carrying the owner's ruling. Paths: `docs/superpowers/specs/2026-10-21-no-wall-clock-design.md`.
5. `port`, no-wall-clock step 2: `Scripted` on events and its two callers. Agent: `test-writer`. Paths: `tests/support/scripted.py`, `tests/test_core_checker_run_all.py`, `tests/test_core_runner_budget.py`.
6. `port`, no-wall-clock step 3: `lifeline.py`, its own tests, and the group tests onto it. Agent: `test-writer`. Paths: `tests/support/lifeline.py`, `tests/test_support_lifeline.py`, `tests/test_core_checker_group.py`.
7. `port`, no-wall-clock step 4: the signal tests onto `lifeline.py`; the held-output test, whose hold is at `tests/test_core_checker_signals.py:201`, comes back UNMOVED. Agent: `test-writer`. Paths: `tests/test_core_checker_signals.py`, `tests/test_core_checker_run_all_signals.py`.
8. `stub`: `read_output` raising, and `run`'s `read` parameter accepted and unused. Agent: `gatesmith`. Paths: `gates/core/checker.py`.
9. Red: the signal held while `run` reads its outputs, through a reader handed in, with `replaces:` naming step 7's UNMOVED test. Agent: `test-writer`. Paths: `tests/test_core_checker_signals.py`.
10. Build: the output reader, on step 9's red test. Agent: `gatesmith`. Paths: `gates/core/checker.py`.
11. `port`, no-wall-clock step 6: the heavy tests onto `lifeline.py`; the two waiting tests (`tests/test_heavy.py:260`, `:287`) come back UNMOVED. Agent: `test-writer`. Paths: `tests/test_heavy.py`, `tests/test_heavy_checker.py`, `tests/test_heavy_lock.py`, `tests/test_heavy_dash_dash.py`, `tests/test_heavy_leading_dash.py`.
12. `stub`: `WAITING` at the value the no-wall-clock design gives (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:96`). Agent: `gatesmith`. Paths: `gates/heavy.py`.
13. Red: one dispatch per waiting behavior, each with `replaces:` naming its UNMOVED test from step 11. Agent: `test-writer`. Paths: `tests/test_heavy.py`.
14. Build: `WAITING`, on step 13's red tests. Agent: `gatesmith`. Paths: `gates/heavy.py`.
15. `port`, no-wall-clock step 8: the pytest gate's cap tests onto `Scripted` through `run_gate`, its given-order tests onto `MEET`. Agent: `test-writer`. Paths: `tests/test_check_pytest_cpus.py`, `tests/test_check_pytest_processes.py`, `tests/test_check_pytest_parallel.py`.
16. `moved`, no-wall-clock step 9: `captured` with no bound of its own, its `lines:` the capture design's lines the no-wall-clock step 1 moved (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:85`). Agent: `test-writer`. Paths: `tests/support/capture.py`, `tests/test_support_capture.py`.

## Decisions for the owner

1. **Where does the re-cut no-wall-clock order live?** Recommend: an `architect` `rulings` pass writes steps 5 to 16 into the no-wall-clock design's **Order**, its one home, and this design's steps 5 to 16 then point there. Cost: one owner ruling line and one `architect` dispatch before step 5. Alternative: this design's **Order** is the home for those steps, and the no-wall-clock design's **Order** gains a pointer. Cost: the same `rulings` pass for the pointer, and until it lands two orders name the same steps differently.
2. **How does a red test reach a change to a live module?** Recommend: `gatesmith`'s `stub` step widens to a live module: a new function raises, a new keyword parameter is accepted and unused, a new constant takes the design's value, so the red run reads `AssertionError` or `NotImplementedError`. Cost: the stub rule at `docs/superpowers/specs/2026-10-18-agents-design.md:32` and `:47`, now raise-only, gains these cases; the unused parameter lives only inside one commit. Alternative: no stub; the red test is written against the design's stubs and the red run accepts `TypeError` and `AttributeError`. Cost: a red run that cannot tell a missing name from a test that calls it wrongly.
3. **Who writes `CLAUDE.md`'s roster lines?** Recommend: `role-author`, whose Writes gains `CLAUDE.md`'s Roster section, since the roster is its craft (`CLAUDE.md:18`). Cost: its row (`docs/superpowers/specs/2026-10-18-agents-design.md:26`) and role file widen, and `CLAUDE.md`'s 4,000-byte cap binds each edit. Alternative: the owner edits `CLAUDE.md` by hand, as its first version was (`docs/superpowers/specs/2026-10-18-agents-design.md:71`). Cost: the owner's time on each roster change.
4. **Two shapes or one for test rework?** Recommend: `port` and `moved` as two shapes, since their done-checks oppose: one keeps every claim and expected value, the other changes exactly those a quoted line moved. Cost: two shapes in a role file whose headroom under its 16,000-byte cap is unmeasured. Alternative: one `rework` shape whose `lines:` is optional, claims kept where it is absent. Cost: one done-check that branches per test, which a reviewer checks test by test.
5. **What proves the fixed `test-writer`?** Recommend: the first live dispatch of each shape is its proof, written as build-order lines: step 5 for `port` and step 16 for `moved`, each with `COMMANDS` showing no read under `gauntlet/` or `gates/` and, for `port`, each KEPT test's assert statements unchanged in the diff; step 9 for the red step in its `stubgen` form, which `docs/roadmap.md:23` records as unproven. Cost: a failed proof blocks the no-wall-clock work until the role is fixed. Alternative: a proof dispatch per shape on a scratch test before step 5. Cost: three more dispatches, unmeasured in time, whose output lands nowhere.
