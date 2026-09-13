# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versioning: [SemVer](https://semver.org/), 0.x during pre-release.

## [Unreleased]

### Added
- `gauntlet-juror`, a blind agent spawned once per red run. It reads the approved block and the run output, and returns one verdict per behavior line — `RED`, `ERROR`, `GREEN` or `INVALID` — so a red run is certified by an agent that never saw the implementation.
- `gauntlet-bailiff`, a blind agent spawned once per merged block. It takes the `TEST CHECK` brief `scripts/pair.sh merge` prints and returns `PIN`, `SOFT`, `MISSING` or `EXTRA` per behavior line, plus a row per test-policy violation.
- `verdicts-lane.py`. The `gauntlet-juror` writes `docs/gauntlet/verdicts/<slug>.txt`; nothing else can write there, the main agent included. A turn that ends with an uncertified or stale red run is blocked, and every outstanding slug is named. A project that never runs `scripts/pair.sh red` never sees the gate.
- `scripts/pair.sh merge` writes its evidence to `state/merge/<slug>.txt` instead of stdout, and the bailiff reads it from there. An absent or empty file is a `NO EVIDENCE` verdict: run `merge` again and spawn a fresh bailiff.
- "The approval word" in `README.md`. The plan, the spec block and the start of implementation each wait for a message whose first line is exactly `approved`, or exactly `approved with revision` with the amendments below it. The word anywhere else in a message, and every softer phrase, holds the chain. No hook enforces it.
- `.claude/hooks/blind-bash.py` and `scripts/blind.sh`. A blind agent's shell is one command: `blind.sh test <path>`, `blind.sh status <slug>` and `blind.sh show <commit> <slug>`, each running under `bwrap` with the filesystem read-only apart from the agent's own lane. The hook matches the whole command text against one anchored pattern per subcommand, with a per-subcommand argument grammar, and denies everything else by name rather than by analysis — a second command appended, a command or an environment assignment in front, a slug that walks out of its directory, or a commit argument carrying its own `:path`. It fails closed on the caller key, so it is wired from the `gauntlet-scrivener` and `gauntlet-bailiff` frontmatter alone and never session-wide. A consumer copying `.claude/` now needs `bwrap` on the host and `scripts/blind.sh` beside it.
- `.claude/hooks/blind-reads.json` carries a `runner_invocations` key, read by every lane hook through `shell_shapes`. A declaration is an entry path, the fixed argument words after it, and the path prefix its one remaining argument sits under, and the classifier keys it on the whole invocation and its arity: a command word in front of the entry, a write beside it, a second argument, or an argument that normalizes outside the prefix is not a run. This repository declares `scripts/blind.sh test <path under tests/>`, so a blind agent's suite run stops reading as a write to the test lane. Two bounds are code rather than data: a declared prefix resolving to or under a lane directory is dropped, and the one argument is normalized before it is tested. A repo that declares nothing keeps the runner table it has today.
- `scripts/cite.py`, a citation resolver for a plan draft. `--check` resolves every backticked `path:line` against the tree and exits 1 on one that does not, `--fix` fills a number from its quoted anchor where the anchor is unique in the file.

**Breaking for existing installs:** re-copy `.claude/` and re-run the `--self-test` commands, which are now nine.

### Changed
- The `gauntlet-arbiter` returns `ADMITTED`, `AMENDED` or `STRICKEN` per behavior line, and its default verdict is `STRICKEN`.
- The post-merge test check leaves the `gauntlet-arbiter` and becomes the `gauntlet-bailiff`'s own round. The reviewer that passed a block no longer judges the tests that landed against it: a fresh agent holds none of the reasons the block was passed, so a softened assertion cannot reach it as permission. The brief and the output format are unchanged.
- The `gauntlet-detective`, `gauntlet-juror` and `gauntlet-examiner` are pinned to Sonnet. Their work is mechanical — a file:line table, a verdict matched against run output, a measured value — so the level is fixed rather than inherited from whatever the calling session runs.
- The `gauntlet-prosecutor` takes an amendment round on an approved plan, where implementation settles a value the plan estimated. The amendment carries the command that produced the value and the reviewer re-runs it; the checks run on the amended lines alone and every other check prints `carried` from the plan file's own reviewer block, so a fresh reviewer can take the round. On `READY` it rewrites `docs/gauntlet/plans/<slug>.txt`, keeping every reviewer block in order, oldest first, and the rewritten plan takes a new approval word. A spec amendment is unchanged and stays a full re-review.
- The `gauntlet-arbiter` and `gauntlet-prosecutor` no longer exempt a host conduct block from the framing count. A brief that authorizes no command carries no conduct block, so neither reviewer spends definition on weighing one at zero.

### Fixed
- The lane hooks no longer count a read-only git command as a write. `git grep`, `git ls-tree`, `git cat-file`, `git rev-list`, `git shortlog`, `git reflog`, `git merge-base` and `git describe` naming a lane pass, the way `git log` does. A git stage carrying `--output`, `git grep -O` and the writing `reflog` forms (`write`, `delete`, `drop`, `expire`) count as writes, so `git diff --output=tests/x` is denied.
- `scripts/pair.sh red` runs the suite verbose, so the saved output names every test that passed as well as every test that failed.

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
