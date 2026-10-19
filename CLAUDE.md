# Gauntlet — agent rules

Rules for building Gauntlet. What Gauntlet is and how it works lives in `docs/`: [`charter.md`](docs/charter.md), [`design.md`](docs/design.md), [`config.md`](docs/config.md), [`roadmap.md`](docs/roadmap.md), and the specs under `docs/superpowers/specs/`. Conduct for every agent under `~/dev` is in `~/dev/CLAUDE.md` and is not restated here.

## Gates

- `make check` is the gate, defined by `docs/superpowers/specs/2026-10-17-quality-gates-design.md`. It runs before every commit, in full, unpiped. A commit report names each gate the spec lists that `make check` does not run.
- No suppression, exemption, baseline, threshold or exclusion, ever. A gate says no; the fix is the code. There is no owner-approved exemption path in this repository.

## Tests first

- Every behavior gets its red test before its code, from whoever the *Red test* column below names, and the red run is the proof. A test is never edited to pass.
- The test writer reads `docs/`, the spec and the `stubgen` interface view of the stub, never `gauntlet/` or `gates/`. Expected values come from the documents, never from running the code.
- Reviewers are blind: a brief to `diff-reviewer` or `test-reviewer` carries the diff scope and nothing else. A brief that says what the change is for is refused, and the bare brief goes to a fresh reviewer.

## Roster

Agents live in `.claude/agents/`, one per craft, each confined to the paths in *Writes*. `role-author` writes every other agent. Design and proofs: `docs/superpowers/specs/2026-10-18-agents-design.md`.

| Agent | Writes | Red test |
|---|---|---|
| `role-author` | `.claude/agents/`, `roles/`, `.gauntlet/skills/` | **none** |
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
- Spikes live in the scratchpad and never in the tree. What `docs/design.md` §4 records as measured is not measured again.
- Markdown is written with `Write` or `Edit`, soft-wrapped: one paragraph, list item or table row per line.
