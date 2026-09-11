# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [SemVer](https://semver.org/), 0.x during pre-release.

## [Unreleased]

### Added
- A tests-only lane. A change confined to `tests/` skips the plan gate, the red run and the post-merge review round, all three of which exist to police an implementation phase that a tests-only change does not have. The block still goes through the blind reviewer, and the main agent still never writes `tests/`.
- `kind: repair`, for a test that violates `docs/testing.md` but pins behavior worth keeping. One line carries both halves: the target to excise with the rule it breaks and its quoted assertion, and the replacement behavior with the `as:` name it must land under.
- `scripts/excision-diff.py`, the mechanical merge check that replaces the reviewer round for those two kinds. It compares the landed `tests/` diff against the approved block by test name and by quoted assertion text, scoped to the target test's own body so a sibling parametrize case sharing the assertion does not hold the target open. It never reads `replace:` prose.

### Changed
- The five agents are now named `gauntlet-accountant`, `gauntlet-arbiter`, `gauntlet-detective`, `gauntlet-prosecutor` and `gauntlet-testsmith`. The lane hooks key on the caller's `agent_type`, so the previous generic names meant that an unrelated agent already called `arbiter` or `testsmith` in the host project satisfied a lane check and could write `specs/approved/` or `tests/`. **Breaking for existing installs:** copy the renamed agent files in, delete the old ones, and re-run the four `--self-test` commands.

### Added
- Each lane's `--self-test` now asserts that the unprefixed agent name is denied, so the collision above cannot reappear unnoticed.

## [0.0.1] - 2026-09-09

### Added
- Blind adversarial review workflow: plans and test specs get checked by reviewers that cannot read the implementation, so tests stay grounded in behavior instead of getting patched to pass.
- Enforced lanes: only the approving reviewer can write approved specs or tests, blocking the main agent from weakening or bypassing tests after the fact.
