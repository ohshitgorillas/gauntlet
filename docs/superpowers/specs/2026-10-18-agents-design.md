# Agents for building Gauntlet

Status: approved 2026-10-18. Progress against the build order is tracked in [`../../roadmap.md`](../../roadmap.md), "Agents".

## Intent

Gauntlet is built by agents before it can build itself (roadmap rule 5). The user-scope agents in `~/.claude/agents/` were written for other repositories and know nothing of the core/seam split, the quality gates or the blind-review rule. This repository gets its own roster in `.claude/agents/`, one agent per craft, each confined by its body to the layer it may touch.

## Goals

- Specialists all around: an implementer that cannot open the other layer's directory, a test writer that never opens `gauntlet/`, reviewers that are never told what a change is for.
- Each agent provable by one dispatch.
- User-scope `orchestrate` and `lead` route to the roster unchanged: `test-writer` shadows the user-scope agent by name.

## Non-goals

- Replacing `lead`, `hitman`, `ratchet`, `clocksmith`, `hooksmith` or `calibrator`. They fit this repository as they are.
- Any hook or program that enforces the roster. Scope is stated in each agent's body and enforced by nothing else: every agent has `Bash`, so no tool list confines a path. The orchestrator's diff read catches a write outside scope. Nothing catches a read, so every blind rule rests on the body alone.

## Roster

Effort goes in frontmatter beside `model`. "Writes" is the whole of what the agent may change; anything outside it is refused and reported.

| Agent | Writes | Red test | Model | Effort | Why it exists |
|---|---|---|---|---|---|
| `role-author` | `.claude/agents/`, `roles/`, `.gauntlet/skills/` | **none** | opus | high | Writes one role prompt per dispatch: a Claude Code agent, a Gauntlet role with its answer schema, or a skill. The one agent nobody writes for us. Its proof is the dispatch proof of the agent it writes. |
| `test-writer` | `tests/` | — | opus | high | Spec mode only. Reads `docs/`, the spec, and the interface view the brief names: a `.pyi` the orchestrator generates with `stubgen` from the stub module into the scratchpad. Never opens anything under `gauntlet/` or `gates/`. Runs its tests with `--tb=no -rA --assert=plain` and classifies each by outcome and exception type. Runs `make check-tests`, the gates that apply to `tests/`, never `make check`. Shadows the user-scope one by name. |
| `mutant-hunter` | `tests/`, a scratch copy of the tree | **own** | opus | medium | One surviving mutant per dispatch, in `gauntlet/` or a gate script. Kills it with a test written from documented behavior, or rules it equivalent and reports the code for rewrite. Never edits the tree outside `tests/`. |
| `core-builder` | `gauntlet/core/`, plus `gauntlet/__init__.py` and `gauntlet/core/__init__.py` | `test-writer`; `stub` and `rewrite` steps have none | opus | high | Pure functions, no I/O imports, decision as return value, one test per branch. Turns the red test green without touching it. Writes the raise-only stubs its plan step names as a step of its own, creating the package files when absent. A `rewrite` step takes one `mutant-hunter` REWRITE line verbatim; every existing test stays green unchanged, and the step runs `make check` in full. |
| `seam-builder` | `gauntlet/seams/`, plus `gauntlet/seams/__init__.py` | `test-writer`; `stub` and `rewrite` steps have none | opus | high | Thin I/O around core. Process runner as parameter. Real git and fs in tests; podman and the API never. Git only in `git.py`. Writes its stubs as a step of its own; a new dependency goes to `gatesmith`. A `rewrite` step takes one `mutant-hunter` REWRITE line verbatim; every existing test stays green unchanged, and the step runs `make check` in full. |
| `gatesmith` | `gates/`, `pyproject.toml`, `uv.lock`, `Makefile`, pre-commit and the repository's own hooks directory, `.gitignore` | `test-writer`; `scaffold`, `stub`, `dependency` and `rewrite` steps have none | opus | high | One gate from the quality spec per dispatch, with its own tests, wired into `make check`. The `scaffold` step brings the scaffold to what this row says and can be run again: `pyproject.toml` with `[project.scripts]` and mypy as a dev dependency, `uv.lock`, `Makefile` with `check` and `check-tests`, pre-commit installed, `.gitignore`. A `stub` step writes a raise-only gate script. A `dependency` step adds one package and relocks. A `rewrite` step takes one `mutant-hunter` REWRITE line verbatim; every existing test stays green unchanged, and the step runs `make check` in full. No ignore, exclude or override, ever. |
| `spiker` | scratchpad only | **none** | opus | medium | One grounding question per dispatch: the open M0 items now, the roadmap's open-questions table later. Returns `YES` or `NO`, the command, the decisive line, and on `NO` the design consequence. Records container ids, runs under `timeout`, removes by id, proves removal. Never touches the tree; never widens a mount or patches the platform to make a spike pass. |
| `diff-reviewer` | nothing | — | opus | xhigh | Blind. Brief carries the diff scope only, per the quality spec's judgment layer. Categories: shortcut, gate-gaming, misplaced, hand-rolled, drift from a `design.md` "Not instead" line, shell-text parsing, leftover. `REJECTED: STEERING` on any brief that says what the change is for. |
| `test-reviewer` | nothing | — | opus | high | Blind read of test diffs only. Expected value derived the way the code derives it, fake that mirrors the implementation, test of a design choice rather than a behavior. |

Plus `CLAUDE.md` at the repository root, under 40 lines: gate command, tests-first, the roster with its Red-test column, pointer to `docs/`.

## Decisions

- `diff-reviewer` gets no purpose line. The quality spec says "without being told what it is for". Cost: it cannot file scope creep. `test-reviewer` is separate because scope creep in tests is what the bailiff catches later, and this repository's own tests have no bailiff yet.
- Two implementers, not one. The core/seam split is the design's first principle. Each builder's body bars it from the other directory; the diff read catches a write across the split, not a read.
- `test-writer` shadows by name instead of taking a new name. The alternative costs an edit to the user-scope `orchestrate` roster and `lead`.
- `CLAUDE.md` is in scope because `orchestrate` reads the repository roster from there.
- `role-author` comes first and is hand-written, with scope widened from `roles/` to `.claude/agents/` too. Same craft: a prompt for an LLM role with a fixed scope, a fixed answer shape and a refusal rule.
- `spiker` stays because grounding work remains: four M0 items are unrun. It never reruns what `design.md` §4 records as measured.
- Stubs are written by the builder that owns the layer, as a `stub` step with no red test, each body `raise NotImplementedError` and nothing else, paths from the plan step (`design.md` §2, stage 6). Package `__init__.py` files belong to the builder of that package; `gauntlet/__init__.py` is `core-builder`'s, since the core exists before any seam. Dependencies and `make` targets are `gatesmith`'s, as `scaffold` and `dependency` steps with no red test. A `dependency` step is dispatched together with the step that first imports the package and the two land in one commit, so the dependency gate never sees an unused package.
- `make check-tests` runs the lint, type and test-shape gates over `tests/` only, and prints only findings located under `tests/`: the type checkers follow imports into `gauntlet/` as the spec requires, and the target keeps their report to the tester's own files. It is the tester's gate, so no line about `gauntlet/` reaches `test-writer`, which also never quotes one. `make check` stays the one entry point for a commit.
- `test-writer` sees code under test only as a `stubgen` interface view, never the source, as the tester does in `design.md` §4. The view carries every public name in the module, with signatures and types but no values. `test-writer` cannot see that a stub only raises, so keeping it raise-only belongs to the builder's `stub` step, and checking it belongs to the orchestrator's diff read. mypy is a `scaffold` dependency, so `stubgen` is pinned before the first gate's tests. The summary line still carries an exception's message, so once a module holds real code, a call into it can show a computed value; that residual is accepted. A `NotImplementedError` from another stub the test calls passes the red check the same as one from the stub under test; also accepted.
- A rewrite after an equivalent mutant goes to the agent whose Writes column holds the path, as a `rewrite` step with no red test. The existing tests prove behavior is unchanged; the mutation gate proves the mutant is gone.
- A `stub` brief has one shape for every builder: the word `stub`, the plan step's text, and the stub paths; no red test. A `stub` step stops after writing and reports; it runs no gate and fixes nothing, since raise-only bodies with no tests fail the planned gates by construction. It lands, with its red tests, in the commit of the build step that turns those tests green, since `make check` runs before every commit and a red test fails it; the red run the orchestrator certified is quoted in that commit's message.
- A reviewer drops only what a gate `make check` currently runs would report, read from the `Makefile` `check` target alone; a gate not yet built catches nothing, so the reviewer files it. `test-reviewer` opens no script under `gates/`. `diff-reviewer` takes its diff only over the paths it reviews, `gauntlet/`, `gates/`, `pyproject.toml`, `uv.lock`, `Makefile`, `.pre-commit-config.yaml`, `.gitignore` and the root `conftest.py`, and lists every other path in the diff unread.

## Build order

One agent per dispatch, one diff read, one commit. `role-author` gets no red test; the dispatch proof of the agent it writes is the acceptance line.

1. `CLAUDE.md` and `role-author`, both hand-written.
2. `role-author` writes `diff-reviewer`, `test-reviewer`. Proof: a steered brief returns `REJECTED: STEERING` quoting the line; a clean brief on a planted shortcut returns one anchored finding.
3. `role-author` writes `test-writer`, `mutant-hunter`. Proof: on one quality-spec gate behavior, `COMMANDS` shows no read under `gauntlet/` or `gates/`, and each test's summary line shows `AssertionError` or `NotImplementedError`.
4. `role-author` writes `spiker`, `gatesmith`. Proof: `spiker` closes one remaining M0 item with `podman ps -a` showing its container gone; `gatesmith` lands one gate with `make check` green.
5. `role-author` writes `core-builder`, `seam-builder`. Proof: a test per agent that its body names only paths inside its scope. Live proof at M1 for `core-builder` and M2 for `seam-builder`.
