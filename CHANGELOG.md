# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [SemVer](https://semver.org/), 0.x during pre-release.

## [Unreleased]

### Changed
- The five agents are now named `gauntlet-accountant`, `gauntlet-arbiter`, `gauntlet-detective`, `gauntlet-prosecutor` and `gauntlet-testsmith`. The lane hooks key on the caller's `agent_type`, so the previous generic names meant that an unrelated agent already called `arbiter` or `testsmith` in the host project satisfied a lane check and could write `specs/approved/` or `tests/`. **Breaking for existing installs:** copy the renamed agent files in, delete the old ones, and re-run the four `--self-test` commands.

### Added
- Each lane's `--self-test` now asserts that the unprefixed agent name is denied, so the collision above cannot reappear unnoticed.

## [0.0.1] - 2026-09-09

### Added
- Blind adversarial review workflow: plans and test specs get checked by reviewers that cannot read the implementation, so tests stay grounded in behavior instead of getting patched to pass.
- Enforced lanes: only the approving reviewer can write approved specs or tests, blocking the main agent from weakening or bypassing tests after the fact.
