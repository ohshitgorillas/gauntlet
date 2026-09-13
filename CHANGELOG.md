# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versioning: [SemVer](https://semver.org/), 0.x during pre-release.

## [Unreleased]

### Added
- `gauntlet-juror`, a blind agent spawned once per red run. It reads the approved block and the run output, and returns one verdict per behavior line — `RED`, `ERROR`, `GREEN` or `INVALID`.
- `verdicts-lane.py`. The `gauntlet-juror` writes `docs/gauntlet/verdicts/<slug>.txt`, tracked; nothing else can write there, the main agent included.
- `verdicts-lane.py --stop`, wired as a `Stop` hook. A turn ending with a red run in `state/red/` that has no verdict, or a verdict older than the run it answers, is blocked and every outstanding slug is named. An empty red run is blocked with its own message. No `state/red/` means no block, so a project that never runs `scripts/pair.sh red` never sees it.
- `scripts/cite.py`, a citation resolver for a plan draft. `--check` resolves every backticked `path:line` against the tree and exits 1 on one that does not, `--fix` fills a number from its quoted anchor where the anchor is unique in the file. A bare continuation and a path outside the checkout print a row whether or not they fail.

**Breaking for existing installs:** re-copy `.claude/` and re-run the `--self-test` commands, which are now eight.

### Changed
- The `gauntlet-arbiter` returns `ADMITTED`, `AMENDED` or `STRICKEN` per behavior line, and its default verdict is `STRICKEN`.

### Fixed
- `pair.sh red` runs the suite verbose, so the saved output names every test that passed as well as every test that failed.

## [0.1.0] - 2026-09-10

### Added
- `docs/gauntlet/` as the base for every agent write: `plans/`, `specs/`, `reviews/`, `drafts/{plans,specs}/`. Plans and specs tracked, the other two gitignored.
- `plans-lane.py`. The `gauntlet-prosecutor` writes the approved plan to `docs/gauntlet/plans/<slug>.txt` on `READY`; nothing else can write there.
- `docs/plans.md`, the stage-1 plan shape.
- A tests-only lane: `kind: excision` and `kind: repair` blocks skip the plan gate, the red run and the post-merge round.
- `scripts/pair.sh` — `open`, `red`, `merge` — and `scripts/excision-diff.py`, the mechanical merge check for the two tests-only kinds.
- Each lane's `--self-test` asserts that an unprefixed agent name is denied.

### Changed
- Approved specs moved to `docs/gauntlet/specs/`, reviewer rounds to `docs/gauntlet/reviews/`. `state/` holds the red run alone. `reviews-lane.py` carves out one folder per reviewer.
- `no-impl-reads.py` denies `docs/gauntlet/` and re-allows `docs/gauntlet/specs/`, both ahead of the allow list, so plans, drafts and rounds stay closed to the blind agents.
- `EVASION` no longer burns the reviewer; only `STEERING` does.
- The five agents are prefixed `gauntlet-`, since the lane hooks key on `agent_type`.

**Breaking for existing installs:** re-copy `.claude/` and re-run the `--self-test` commands.

### Fixed
- Lane writes slipping through behind a harmless head word: `cd tests && rm t.py`, `find tests -delete`, `node -e`, a write after a newline or `&`.
- Blind reads through `node -e`, `python -c`, an unrooted `grep -rn x .`, or a source file under a directory named `docs`, `tests` or `specs`.
- Lanes now hold outside a git checkout, including the write that creates the lane directory.

## [0.0.1] - 2026-09-09

### Added
- Blind adversarial review workflow: plans and test specs get checked by reviewers that cannot read the implementation, so tests stay grounded in behavior instead of getting patched to pass.
- Enforced lanes: only the approving reviewer can write approved specs or tests, blocking the main agent from weakening or bypassing tests after the fact.
