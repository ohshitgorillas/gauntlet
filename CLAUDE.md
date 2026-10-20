# Gauntlet — agent rules

Rules for building Gauntlet. What it is and how it works lives in `docs/`: [`charter.md`](docs/charter.md), [`design.md`](docs/design.md), [`config.md`](docs/config.md), [`roadmap.md`](docs/roadmap.md), and the specs in `docs/superpowers/specs/`.

## Gates

- `make check` is the gate, defined by `docs/superpowers/specs/2026-10-17-quality-gates-design.md`. It runs before every commit, in full, unpiped. A commit report names each gate the spec lists that `make check` does not run.
- No suppression, exemption, baseline, threshold or exclusion, ever. A gate says no; the fix is the code. No exemption path exists, owner-approved or not.

## Tests first

- Every behavior gets its red test before its code, from whoever the *Red test* column names; the red run is the proof. A test is never edited to pass.
- The test writer reads `docs/`, the spec and the `stubgen` interface view of the stub, never `gauntlet/` or `gates/`. Expected values come from the documents, never from running the code.
- Reviewers are blind: a brief to `diff-reviewer` or `test-reviewer` carries the diff scope and nothing else. A brief that says what the change is for is refused; the bare brief goes to a fresh reviewer.

## Roster

Agents live in `.claude/agents/`, one per craft, each confined to the paths in *Writes*. `role-author` writes every other agent. Design and proofs: `docs/superpowers/specs/2026-10-18-agents-design.md`.

| Agent | Writes | Red test |
|---|---|---|
| `role-author` | `.claude/agents/`, `roles/`, `.gauntlet/skills/` | **none** |
| `architect` | one design file per dispatch under `docs/superpowers/specs/` | **none** |
| `test-writer` | `tests/` | — |
| `mutant-hunter` | `tests/`, a scratchpad copy of the tree | **own** |
| `core-builder` | `gauntlet/core/`, `gauntlet/__init__.py`, `gauntlet/core/__init__.py` | `test-writer`; none for a `stub`, `rewrite` or `finding` step |
| `seam-builder` | `gauntlet/seams/`, `gauntlet/seams/__init__.py` | `test-writer`; none for a `stub`, `rewrite` or `finding` step |
| `gatesmith` | `gates/`, `pyproject.toml`, `uv.lock`, `Makefile`, pre-commit and `.git/hooks`, `.gitignore` | `test-writer`; none for `scaffold`, `stub`, `dependency`, `rewrite` or `finding` |
| `spiker` | scratchpad only | **none** |
| `diff-reviewer` | nothing | — |
| `test-reviewer` | nothing | — |

User-scope `lead`, `hitman`, `ratchet`, `clocksmith`, `hooksmith` and `calibrator` apply here unchanged. A step no agent above owns goes to `general-purpose` with its red test from `test-writer`. A change confined to `docs/` takes no red test.

## Layout

- `gauntlet/core/` is pure: no I/O imports, one unit test per branch, every decision a return value. `gauntlet/seams/` is thin I/O around it and takes its process runner as a parameter. Only `seams/git.py` runs git. Layout and contracts: `docs/design.md` §8 and the gates spec.
- Spikes live in the scratchpad, never the tree. What `docs/measured.md` records is not measured again.
- Markdown is written with `Write` or `Edit`, soft-wrapped: one paragraph, list item or table row per line, blank lines between paragraphs.

## Docs agents load

- Byte caps: this file 4,000; a role file 16,000, its `description:` 600; `HANDOFF.md` 6,000; `queue.md` 5,000; `~/dev/gauntlet-harness-rules.md` 12,000; the plan 16,000. A block: 600 characters (queue line 300, role file 1,500, `docs/` 2,000). The doc-budget hook checks each write; fix by cutting or moving text. Only the owner raises a cap.
- They hold only live rules and state. Logs, dated events, PIDs, session ids, scratchpad paths, timings, pass counts and resolved findings go to `~/dev/gauntlet-log/<date>.md`, append-only, never named in a read instruction.
- A ruling is written once, at its home (behavior: its spec; roster: agents spec and role; process: rules file; scope: job brief), replacing what it supersedes; elsewhere, a pointer. `HANDOFF.md` is rewritten whole at each clear; a closed job leaves `queue.md`.
