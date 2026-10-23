Status: proposed, for the owner's approval.

## Why

A red step writes the red test for one behavior against a `stubgen` view of a stub. A `finding` step fixes upheld findings, keeps every test green, and changes no expected value. Support-helper ports and document-driven test changes use the shapes below.


A step no shape owns falls to `CLAUDE.md:33`: "A step no agent above owns goes to `general-purpose` with its red test from `test-writer`." The owner bars `general-purpose` from this work.

Three places define or route test work outside the `test-writer` row. `docs/superpowers/plans/structure-first-plan.md:29` defines a support-helper step in a plan: a helper "written in C2a beside its own tests, which pass at once". The gates core design sends a test whose expected value a spec amendment moved to "the queued R-tw-moved shape", which no roster row holds. `CLAUDE.md:33` sends any step the roster does not own, test steps included, to `general-purpose`. `docs/roadmap.md:23` records the red-test step in its `stubgen` form as unproven.

The precedent for a helper beside its own tests is in the tree: `tests/test_support_capture.py:55` imports the helper it tests. The shared helpers have callers: `tests/support/scripted.py` at `tests/test_core_checker_run_all.py:22` and `tests/test_core_runner_budget.py:25`.

## Modules

### `test-writer`: four step shapes

Its job is every write under `tests/` except a mutant kill, each in one of four shapes: red, `finding`, `port` and `moved`. `port` and `moved` are two shapes, not one, since their done-checks oppose: one keeps every claim and expected value, the other changes exactly those a quoted line moved (decision 4). The shapes live in its agents-spec row and decisions; its role file `.claude/agents/test-writer.md` holds the same shapes, since a roster ruling's home is "agents spec and role" (`CLAUDE.md:45`). Every shape runs `make check-tests` with `FILES` set to the files it wrote or changed, never `make check`, and reads no path under `gauntlet/` or `gates/`. It replaces the plan's helper step (`docs/superpowers/plans/structure-first-plan.md:29`), the queued shape and, for test work, the fallback at `CLAUDE.md:33`.

The red step keeps its shape and gains one optional line:

```text
red
behavior: <one behavior, in the words of the owner or a document>
view: <the .pyi stubgen made from the stub module, in the scratchpad>
replaces: <a test id a port step reported UNMOVED for this behavior>   # optional; that test is removed in the same dispatch
# done: each new test red from a run with --tb=no -rA --assert=plain, as AssertionError or NotImplementedError
```

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

Its job is to give a red test a name to call on a module that already holds code, so the red run reads `AssertionError` or `NotImplementedError`. It lands in the commit of the build that turns its red tests green.

```text
stub
step: <the design step's text>
paths: <each stub path>
# a new function: its body is raise NotImplementedError
# a new keyword parameter on a live function: accepted and unused, its default as the design gives it
# a new constant: the value the design gives it
```

### `CLAUDE.md` roster lines (decision 3)

Its job is to route every step that writes under `tests/` to an agent that owns a shape for it, and to keep the roster lines with one writer: `role-author`, whose Writes gains `CLAUDE.md`'s Roster section, since the roster is its craft (`CLAUDE.md:18`). The routing line replaces the fallback at `CLAUDE.md:33` for those steps; a step outside `tests/` that no agent owns keeps that route. `role-author`'s row gains the section in the agents spec and in `CLAUDE.md` (`CLAUDE.md:22`). Its role file gains it by the owner's hand, since `role-author` writes every other agent (`CLAUDE.md:18`) and was itself hand-written. Each edit fits `CLAUDE.md`'s 4,000-byte cap (`CLAUDE.md:43`); the headroom under it is unmeasured.

```text
A step that writes under `tests/` goes to `test-writer`, or to `mutant-hunter` for a surviving mutant, and never to `general-purpose`; one that fits no shape stops and is reported.
| `role-author` | `.claude/agents/`, `roles/`, `.gauntlet/skills/`, `CLAUDE.md`'s Roster section | **none** |
```

### `test-writer`'s proof (decision 5)

Each shape requires proof on its first live dispatch, with no separate proof dispatch; the agents spec's **Build order** and `docs/roadmap.md` hold the proof requirements and outstanding status.

```text
7. `role-author` rewrites `test-writer` with the `port` and `moved` shapes and red's `replaces:` line. Proof: the first live dispatch of each shape, its `COMMANDS` showing no read under `gauntlet/` or `gates/`; for `port`, each KEPT test's assert statements unchanged in the diff; for the red step on a `stubgen` view, each test's summary line showing `AssertionError` or `NotImplementedError`, as step 3 reads it. A failed proof stops the work its dispatch serves until the role is fixed.
```

## Homes

| Concern | Its one home | What it forbids elsewhere |
|---|---|---|
| `test-writer`'s step shapes | Its row and decisions, with `.claude/agents/test-writer.md` holding the same shapes | A step shape defined in a plan or a design; the plan and the gates core design become pointers. A test brief outside the four shapes |
| Who writes under `tests/` | The roster: `test-writer`, and `mutant-hunter` for a surviving mutant, routed by `CLAUDE.md` (decision 3) | `general-purpose`, a builder or the coordinator writing any path under `tests/` |
| What `test-writer` reads of own code | The `stubgen` view the orchestrator generates into the scratchpad | A read under `gauntlet/` or `gates/`; source quoted in a brief |
| A helper's interface under `tests/support/` | The approved design's stubs for that helper | A `.pyi` brief for a helper; an interface the step chooses where a design gives one |
| Changing an expected value or removing a test | The `moved` step, each change resting on a quoted document line | A `port`, `finding` or red step that changes an expected value or removes a test, save a red step's `replaces:` of a test a port reported UNMOVED |
| A production change a test needs | The builder's `stub` step, then a red step, then the build, in one commit (decision 2) | A port that writes outside `tests/`; a test that keeps a clock wait because the seam is missing; a red test against a name the tree lacks |
| A test step's gate run | `make check-tests` with `FILES` set | `make check` from `test-writer` |
| Who writes `CLAUDE.md`'s Roster section | `role-author`, as scoped at `CLAUDE.md:22` (decision 3) | A roster line written by any other agent; `role-author` writing any other section of `CLAUDE.md`, or its own role file |
| What proves `test-writer`'s shapes | The agents spec's **Build order** line 7, read on each shape's first live dispatch (decision 5) | A proof dispatch on a scratch test; a second dispatch of a shape whose first failed its proof |

A test step that fits none of the four shapes stops and reports it. It goes to no `general-purpose` agent and no builder, and the shapes are extended only by a design change.

## Order

Each step lands green under `make check` before the next starts.

1. The shapes into the spec: `port` and `moved` in `test-writer`'s row and decisions (decision 4), red's `replaces:` line, the `stub` step on a live module in `gatesmith`'s row and the stub decision (`docs/superpowers/specs/agents-design.md:32`, `:47`, decision 2), `CLAUDE.md`'s Roster section in `role-author`'s row (`:26`, decision 3), the build-order proof line 7 and the outstanding proofs at `docs/roadmap.md:23` (decision 5), and pointers from the plan and the gates core design. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/specs/agents-design.md`, `docs/superpowers/specs/gates-core-design.md`, `docs/superpowers/plans/structure-first-plan.md`, `docs/roadmap.md`.
2. `role-author`'s role file gains `CLAUDE.md`'s Roster section (decision 3). Agent: none; the owner, by hand, since `role-author` writes every other agent (`CLAUDE.md:18`). Paths: `.claude/agents/role-author.md`.
3. The routing line and `role-author`'s widened row at `CLAUDE.md:22` (decision 3). Agent: `role-author`. Paths: `CLAUDE.md`.
4. The role files to match step 1. Agent: `role-author`. Paths: `.claude/agents/test-writer.md`, `.claude/agents/gatesmith.md`.

## Decisions taken

Each entry gives the question, or for a ruling no open decision covered a name for the structure, in bold; the owner's ruling verbatim; `Adds:` each module, home and step it adds; and `Written in:` each section it touches.

3. **Who writes `CLAUDE.md`'s roster lines?** `role-author`'s Writes includes `CLAUDE.md`'s Roster section, with the home "Who writes `CLAUDE.md`'s Roster section". Its row belongs in step 1, its role file is written by the owner's hand in step 2, and `CLAUDE.md` in step 3. Defined in: **Modules**, **Homes**, **Order**.
4. **Two shapes or one for test rework?** `port` and `moved` are two shapes in the `test-writer` module. Defined in: **Modules**, **Order**.
