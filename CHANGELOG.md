# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [SemVer](https://semver.org/), 0.x during pre-release.

## [Unreleased]

### Added
- A tests-only lane. A change confined to `tests/` skips the plan gate, the red run and the post-merge review round, all three of which exist to police an implementation phase that a tests-only change does not have. The block still goes through the blind reviewer, and the main agent still never writes `tests/`.
- `kind: repair`, for a test that violates `docs/testing.md` but pins behavior worth keeping. One line carries both halves: the target to excise with the rule it breaks and its quoted assertion, and the replacement behavior with the `as:` name it must land under.
- `scripts/pair.sh`, which three documented steps already rested on and which had never been written. `open <slug>` cuts the spec worktree, and refuses when the approved block's reviewer section no longer matches the newest round file — the spec is editable after approval and the round file is not, so comparing them is what makes the block that reaches the writer the block that was reviewed. `red <slug>` runs the suite there, saves the output, and removes the whole-file excision targets the lane hook denies every agent. `merge <slug>` routes on `kind:`: the blind post-merge round for the three implementation kinds, `scripts/excision-diff.py` for the two tests-only ones. `docs/agents.md` carries the subcommand table, so a blind writer reads those literals as contract rather than copying them out of the script.
- `scripts/excision-diff.py`, the mechanical merge check that replaces the reviewer round for those two kinds. It compares the landed `tests/` diff against the approved block by test name and by quoted assertion text, scoped to the target test's own body so a sibling parametrize case sharing the assertion does not hold the target open. It never reads `replace:` prose.

### Changed
- An `EVASION` rejection no longer burns the reviewer. Only `STEERING` does. A reviewer calls `EVASION` on a re-review whose return neither did the named repair nor supplied the missing citation; replacing the reviewer there handed the main agent a fresh one that held none of the evaded findings, and so a free second run at the same evasion. The call now leaves the reviewer open with its findings, and the main agent answers it back to that same reviewer, which can call `EVASION` again on an answer that evades again.
- The five agents are now named `gauntlet-accountant`, `gauntlet-arbiter`, `gauntlet-detective`, `gauntlet-prosecutor` and `gauntlet-testsmith`. The lane hooks key on the caller's `agent_type`, so the previous generic names meant that an unrelated agent already called `arbiter` or `testsmith` in the host project satisfied a lane check and could write `specs/approved/` or `tests/`. **Breaking for existing installs:** copy the renamed agent files in, delete the old ones, and re-run the four `--self-test` commands.

### Added
- Each lane's `--self-test` now asserts that the unprefixed agent name is denied, so the collision above cannot reappear unnoticed.

### Fixed
- The lanes let writes into `tests/` and `specs/approved/` through whenever a command opened with a harmless-looking word: `cd tests && rm t.py`, `find tests -delete`, `node -e` writing a file, a write after a newline or a `&`. All are denied now.
- The blind reviewers could read the implementation after all — through `node -e` or `python -c`, through an unrooted `grep -rn x .`, or through any source file sitting under a directory named `docs`, `tests` or `specs`. All three roads are closed.
- The lanes hold in a directory that is not a git checkout yet, including the write that first creates `specs/approved/`.

## [0.0.1] - 2026-09-09

### Added
- Blind adversarial review workflow: plans and test specs get checked by reviewers that cannot read the implementation, so tests stay grounded in behavior instead of getting patched to pass.
- Enforced lanes: only the approving reviewer can write approved specs or tests, blocking the main agent from weakening or bypassing tests after the fact.
