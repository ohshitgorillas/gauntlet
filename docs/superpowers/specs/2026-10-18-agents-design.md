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
| `test-writer` | `tests/` | — | opus | high | Spec mode only. Reads `docs/`, the spec, the stub's interface, never `gauntlet/`. Holds every test-shape gate of the quality spec. Shadows the user-scope one by name. |
| `mutant-hunter` | `tests/` | **own** | opus | medium | One surviving mutant per dispatch. Kills it with a test written from documented behavior, or rules it equivalent and reports the code for rewrite. Never edits `gauntlet/`. |
| `core-builder` | `gauntlet/core/` | `test-writer` | opus | high | Pure functions, no I/O imports, decision as return value, one test per branch. Turns the red test green without touching it. |
| `seam-builder` | `gauntlet/seams/` | `test-writer` | opus | high | Thin I/O around core. Process runner as parameter. Real git and fs in tests; podman and the API never. Git only in `git.py`. |
| `gatesmith` | gate scripts under `gates/`, `pyproject.toml`, `uv.lock`, `Makefile`, pre-commit, `.gitignore` | `test-writer` | opus | high | One gate from the quality spec per dispatch, with its own tests, wired into `make check`; the scaffold the first gate needs is one step with no red test. No ignore, exclude or override, ever. |
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

## Build order

One agent per dispatch, one diff read, one commit. `role-author` gets no red test; the dispatch proof of the agent it writes is the acceptance line.

1. `CLAUDE.md` and `role-author`, both hand-written.
2. `role-author` writes `diff-reviewer`, `test-reviewer`. Proof: a steered brief returns `REJECTED: STEERING` quoting the line; a clean brief on a planted shortcut returns one anchored finding.
3. `role-author` writes `test-writer`, `mutant-hunter`. Proof: on one quality-spec gate behavior, `COMMANDS` shows no read under `gauntlet/`, and the red run fails on an assertion.
4. `role-author` writes `spiker`, `gatesmith`. Proof: `spiker` closes one remaining M0 item with `podman ps -a` showing its container gone; `gatesmith` lands one gate with `make check` green.
5. `role-author` writes `core-builder`, `seam-builder`. Proof: a test per agent that its body names only paths inside its scope. Live proof at M1 for `core-builder` and M2 for `seam-builder`.
