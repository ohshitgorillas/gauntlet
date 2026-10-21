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

Its job is every write under `tests/` except a mutant kill, each in one of four shapes: red, `finding`, `port` and `moved`. `port` and `moved` are two shapes, not one, since their done-checks oppose: one keeps every claim and expected value, the other changes exactly those a quoted line moved (decision 4). The shapes live in its agents-spec row and decisions; its role file `.claude/agents/test-writer.md` holds the same shapes, since a roster ruling's home is "agents spec and role" (`CLAUDE.md:45`). Every shape runs `make check-tests` with `FILES` set to the files it wrote or changed, never `make check` (`docs/superpowers/specs/2026-10-18-agents-design.md:49`, `Makefile:15`), and reads no path under `gauntlet/` or `gates/`. It replaces the plan's helper step (`docs/superpowers/plans/structure-first-plan.md:29`), the queued shape (`docs/superpowers/specs/2026-10-20-gates-core-design.md:329`) and, for test work, the fallback at `CLAUDE.md:33`.

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

### `CLAUDE.md` roster lines (decision 3)

Its job is to route every step that writes under `tests/` to an agent that owns a shape for it, and to keep the roster lines with one writer: `role-author`, whose Writes gains `CLAUDE.md`'s Roster section, since the roster is its craft (`CLAUDE.md:18`). The routing line replaces the fallback at `CLAUDE.md:33` for those steps; a step outside `tests/` that no agent owns keeps that route. `role-author`'s row gains the section in the agents spec (`docs/superpowers/specs/2026-10-18-agents-design.md:26`) and in `CLAUDE.md` (`CLAUDE.md:22`). Its role file gains it by the owner's hand, since `role-author` writes every other agent (`CLAUDE.md:18`) and was itself hand-written (`docs/superpowers/specs/2026-10-18-agents-design.md:45`). Each edit fits `CLAUDE.md`'s 4,000-byte cap (`CLAUDE.md:43`); the headroom under it is unmeasured.

```text
A step that writes under `tests/` goes to `test-writer`, or to `mutant-hunter` for a surviving mutant, and never to `general-purpose`; one that fits no shape stops and is reported.
| `role-author` | `.claude/agents/`, `roles/`, `.gauntlet/skills/`, `CLAUDE.md`'s Roster section | **none** |
```

### `test-writer`'s proof (decision 5)

Its job is to prove each shape on its first live dispatch, with no proof dispatch of its own. It is one line in the agents spec's **Build order** (`docs/superpowers/specs/2026-10-18-agents-design.md:67`–`:76`), after that order's step 6, and `docs/roadmap.md:23` names these proofs as outstanding where it records the `stubgen` form as unproven. In this design's **Order** the first `port` is step 7, the first red step on a `stubgen` view is step 11, and the first `moved` is step 18.

```text
7. `role-author` rewrites `test-writer` with the `port` and `moved` shapes and red's `replaces:` line. Proof: the first live dispatch of each shape, its `COMMANDS` showing no read under `gauntlet/` or `gates/`; for `port`, each KEPT test's assert statements unchanged in the diff; for the red step on a `stubgen` view, each test's summary line showing `AssertionError` or `NotImplementedError`, as step 3 reads it. A failed proof stops the work its dispatch serves until the role is fixed.
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
| Who writes `CLAUDE.md`'s Roster section | `role-author`, its row widened at `docs/superpowers/specs/2026-10-18-agents-design.md:26` and `CLAUDE.md:22` (decision 3) | A roster line written by any other agent; `role-author` writing any other section of `CLAUDE.md`, or its own role file |
| What proves `test-writer`'s shapes | The agents spec's **Build order** line 7, read on each shape's first live dispatch (decision 5) | A proof dispatch on a scratch test; a second dispatch of a shape whose first failed its proof |
| The no-wall-clock work's step order | The no-wall-clock design's **Order**, as step 5 writes it (decision 1) | A second order naming the same steps: this design's steps 7 to 18 are the re-cut step 5 carries, and step 6 makes each a pointer there |

A test step that fits none of the four shapes stops and reports it. It goes to no `general-purpose` agent and no builder, and the shapes are extended only by a design change.

## Order

Steps 1 to 4 land on `main`'s line; steps 5 to 18 run where the no-wall-clock design and its step-1 spec lines are. Steps 7 to 18 are the re-cut no-wall-clock order, which step 5 writes into the no-wall-clock design's **Order**, their one home, and step 6 makes each step here a pointer to its step there (decision 1). Each step lands green under `make check` before the next starts, save that steps 10 to 12 land as one commit and steps 14 to 16 as one commit (`docs/superpowers/specs/2026-10-18-agents-design.md:61`).

1. The shapes into the spec: `port` and `moved` in `test-writer`'s row and decisions (decision 4), red's `replaces:` line, the `stub` step on a live module in `gatesmith`'s row and the stub decision (`docs/superpowers/specs/2026-10-18-agents-design.md:32`, `:47`, decision 2), `CLAUDE.md`'s Roster section in `role-author`'s row (`:26`, decision 3), the build-order proof line 7 and the outstanding proofs at `docs/roadmap.md:23` (decision 5), and pointers from the plan and the gates core design. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/2026-10-18-agents-design.md`, `docs/superpowers/specs/2026-10-20-gates-core-design.md`, `docs/superpowers/plans/structure-first-plan.md`, `docs/roadmap.md`.
2. `role-author`'s role file gains `CLAUDE.md`'s Roster section (decision 3). Agent: none; the owner, by hand, since `role-author` writes every other agent (`CLAUDE.md:18`) and was itself hand-written (`docs/superpowers/specs/2026-10-18-agents-design.md:45`). Paths: `.claude/agents/role-author.md`.
3. The routing line and `role-author`'s widened row at `CLAUDE.md:22` (decision 3). Agent: `role-author`. Paths: `CLAUDE.md`.
4. The role files to match step 1. Agent: `role-author`. Paths: `.claude/agents/test-writer.md`, `.claude/agents/gatesmith.md`.
5. Steps 7 to 18 into the no-wall-clock design's **Order** (decision 1). Agent: `architect`, on a `rulings` brief carrying the owner's ruling. Paths: `docs/superpowers/specs/2026-10-21-no-wall-clock-design.md`.
6. Steps 7 to 18 here as pointers to their steps in the no-wall-clock design's **Order** (decision 1). Agent: `architect`, on a `rulings` brief carrying the owner's ruling. Paths: `docs/superpowers/specs/2026-10-21-test-writer-design.md`.
7. `port`, no-wall-clock step 2: `Scripted` on events and its two callers; the first `port`, its proof read (decision 5). Agent: `test-writer`. Paths: `tests/support/scripted.py`, `tests/test_core_checker_run_all.py`, `tests/test_core_runner_budget.py`.
8. `port`, no-wall-clock step 3: `lifeline.py`, its own tests, and the group tests onto it. Agent: `test-writer`. Paths: `tests/support/lifeline.py`, `tests/test_support_lifeline.py`, `tests/test_core_checker_group.py`.
9. `port`, no-wall-clock step 4: the signal tests onto `lifeline.py`; the held-output test, whose hold is at `tests/test_core_checker_signals.py:201`, comes back UNMOVED. Agent: `test-writer`. Paths: `tests/test_core_checker_signals.py`, `tests/test_core_checker_run_all_signals.py`.
10. `stub`: `read_output` raising, and `run`'s `read` parameter accepted and unused (decision 2). Agent: `gatesmith`. Paths: `gates/core/checker.py`.
11. Red: the signal held while `run` reads its outputs, through a reader handed in, with `replaces:` naming step 9's UNMOVED test; the first red step on a `stubgen` view, its proof read (decision 5). Agent: `test-writer`. Paths: `tests/test_core_checker_signals.py`.
12. Build: the output reader, on step 11's red test. Agent: `gatesmith`. Paths: `gates/core/checker.py`.
13. `port`, no-wall-clock step 6: the heavy tests onto `lifeline.py`; the two waiting tests (`tests/test_heavy.py:260`, `:287`) come back UNMOVED. Agent: `test-writer`. Paths: `tests/test_heavy.py`, `tests/test_heavy_checker.py`, `tests/test_heavy_lock.py`, `tests/test_heavy_dash_dash.py`, `tests/test_heavy_leading_dash.py`.
14. `stub`: `WAITING` at the value the no-wall-clock design gives (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:96`, decision 2). Agent: `gatesmith`. Paths: `gates/heavy.py`.
15. Red: one dispatch per waiting behavior, each with `replaces:` naming its UNMOVED test from step 13. Agent: `test-writer`. Paths: `tests/test_heavy.py`.
16. Build: `WAITING`, on step 15's red tests. Agent: `gatesmith`. Paths: `gates/heavy.py`.
17. `port`, no-wall-clock step 8: the pytest gate's cap tests onto `Scripted` through `run_gate`, its given-order tests onto `MEET`. Agent: `test-writer`. Paths: `tests/test_check_pytest_cpus.py`, `tests/test_check_pytest_processes.py`, `tests/test_check_pytest_parallel.py`.
18. `moved`, no-wall-clock step 9: `captured` with no bound of its own, its `lines:` the capture design's lines the no-wall-clock step 1 moved (`docs/superpowers/specs/2026-10-21-no-wall-clock-design.md:85`); the first `moved`, its proof read (decision 5). Agent: `test-writer`. Paths: `tests/support/capture.py`, `tests/test_support_capture.py`.

## Decisions taken

Each entry gives the question in bold, the owner's ruling verbatim, `Adds:` each module, home and step it adds, and `Written in:` each section it touches.

1. **Where does the re-cut no-wall-clock order live?** Ruling: "Do whatever you recommend." Adds: the home "The no-wall-clock work's step order", the no-wall-clock design's **Order**; step 5, an `architect` `rulings` pass writing steps 7 to 18 there; step 6, an `architect` `rulings` pass making steps 7 to 18 here pointers to it. Written in: **Homes**, **Order**.
2. **How does a red test reach a change to a live module?** Ruling: "Do whatever you recommend." Adds: the module `gatesmith` `stub` on a live module, where a new function raises, a new keyword parameter is accepted and unused and a new constant takes the design's value; the home "A production change a test needs"; its spec lines in step 1, its role lines in step 4, and the stubs of steps 10 and 14. Written in: **Modules**, **Homes**, **Order**.
3. **Who writes `CLAUDE.md`'s roster lines?** Ruling: "Do whatever you recommend." Adds: the module `CLAUDE.md` roster lines, with `role-author`'s Writes gaining `CLAUDE.md`'s Roster section; the home "Who writes `CLAUDE.md`'s Roster section"; its row in step 1, step 2 for its role file by the owner's hand, and step 3 for `CLAUDE.md`. Written in: **Modules**, **Homes**, **Order**.
4. **Two shapes or one for test rework?** Ruling: "Do whatever you recommend." Adds: none; the `port` and `moved` shapes stand as two in the `test-writer` module. Written in: **Modules**, **Order**.
5. **What proves the fixed `test-writer`?** Ruling: "Do whatever you recommend." Adds: the module `test-writer`'s proof, line 7 of the agents spec's **Build order**; the home "What proves `test-writer`'s shapes"; that line and `docs/roadmap.md:23` in step 1, and the proof read at steps 7, 11 and 18. Written in: **Modules**, **Homes**, **Order**.
