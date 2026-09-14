# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versioning: [SemVer](https://semver.org/), 0.x during pre-release.

## [Unreleased]

### Added
- `gauntlet-juror`, a blind agent spawned once per red run. Returns `RED`, `ERROR`, `GREEN` or `INVALID` per behavior line.
- `gauntlet-bailiff`, a blind agent spawned once per merged block. Returns `PIN`, `SOFT`, `MISSING` or `EXTRA` per behavior line, plus a row per test-policy violation.
- `verdicts-lane.py`. Only the `gauntlet-juror` writes `gauntlet/verdicts/<slug>.txt`. A turn that ends with an uncertified or stale red run is blocked. A project that never runs `scripts/pair.sh red` never sees the gate.
- `.claude/hooks/blind-bash.py` and `scripts/blind.sh`. A blind agent's shell is one command: `blind.sh test <path>`, `blind.sh status <slug>`, `blind.sh show <commit> <slug>`, each under `bwrap` with the filesystem read-only apart from the agent's own lane. Wired from the `gauntlet-scrivener` and `gauntlet-bailiff` frontmatter, never session-wide. Needs `bwrap` on the host.
- `.claude/hooks/bwrap-wrap.py`. Every `Bash` call is replaced with the same command inside `bwrap`, carried on stdin through a here-document. Three profiles keyed on `agent_type`: passthrough for the two blind agents, reviewer (read-only, tmpfs over the reviewers' lane), and default (repository, `~/.cache` and `/tmp` writable; every lane directory, `state/red`, `state/merge`, `.claude/`, `scripts/`, `.git/hooks`, `.git/config` read-only; `/run/user` masked). Needs `bwrap` on the host; fails closed when it is absent.
- `.claude/hooks/pair-passthrough.py`, the one carve-out from that wrap: `scripts/pair.sh` runs unwrapped.
- `.claude/hooks/gauntlet-off.py` and the `GAUNTLET` switch. `GAUNTLET=off claude` runs one session with the seven lane hooks and the `Stop` gate silent. Read from `os.environ`, never from a payload. A `GAUNTLET=` assignment or a nested `claude` invocation is denied inside such a session.
- `.claude/hooks/blind-reads.json` carries a `runner_invocations` key: an entry path, its fixed argument words, and the prefix its one remaining argument sits under. This repository declares `scripts/blind.sh test <path under tests/>`. A repo that declares nothing keeps the runner table it has today.
- `scripts/pair.sh restore <slug> <rev>`, printing `RESTORED <path> <rev>`.
- `scripts/pair.sh impl checkout <slug>` and `impl merge <slug>`, printing `IMPL .claude/worktrees/<slug>-impl` and `MERGED <slug> <commit>`.
- `scripts/pair.sh review <slug>` and `review plan <slug>`, printing the one path the next round is written to with `<N>` one more than the highest on disk.
- `scripts/pair.sh merge` writes its evidence to `state/merge/<slug>.txt` instead of stdout. An absent or empty file is a `NO EVIDENCE` verdict.
- `scripts/cite.py`. `--check` resolves every backticked `path:line` against the tree and exits 1 on one that does not; `--fix` fills a number from its quoted anchor.
- "The approval word" in `README.md`. Plan, spec block and start of implementation each wait for a message whose first line is exactly `approved`, or `approved with revision` with the amendments below it. No hook enforces it.

**Breaking for existing installs:** re-copy `.claude/` and re-run the `--self-test` commands.

### Changed
- The `gauntlet-arbiter` returns `ADMITTED`, `AMENDED` or `STRICKEN` per behavior line; default `STRICKEN`.
- The post-merge test check leaves the `gauntlet-arbiter` for the `gauntlet-bailiff`. Brief and output format unchanged.
- The `gauntlet-detective`, `gauntlet-juror` and `gauntlet-examiner` are pinned to Sonnet.
- The `gauntlet-prosecutor` takes an amendment round on an approved plan. Checks run on the amended lines alone; every other check prints `carried`. On `READY` it rewrites `gauntlet/plans/approved/<slug>.txt`, keeping every reviewer block oldest first, and the rewritten plan takes a new approval word. A spec amendment stays a full re-review.
- The `gauntlet-arbiter` and `gauntlet-prosecutor` no longer exempt a host conduct block from the framing count.
- The gauntlet's artifacts leave `docs/` for `gauntlet/`: `plans/approved/`, `plans/drafts/`, `specs/approved/`, `specs/drafts/`, `reviews/`, `verdicts/`. The lane hooks, agent definitions, `scripts/` and `.gitignore` move with them; re-copy `.claude/` and `docs/` both.
- A blind agent's allowlist is `docs/`, `tests/`, `state/` and `gauntlet/specs/approved/`, with the `gauntlet/` base denied entire. No denied subtree nests inside an allowed root.
- Every hook fails closed on a payload it cannot decide. A payload that is not JSON, is not an object, names `tool_name` as something other than a string, or carries the field the hook has to read (`command`, `file_path`, `notebook_path`, `path`, `cwd`, `agent_type`) as the wrong type is denied, naming the hook and the field; so is a call whose verdict raises. Each hook refuses only for the tools it decides, so a malformed call of somebody else's tool still passes. A payload a gate cannot read is the one that most needs deciding, and coercing its fields to benign defaults is what lets it through.
- `bwrap-wrap.py` denies a `Bash` call it cannot build a sandbox for, rather than letting the command run unwrapped.
- `bwrap-wrap.py` runs `bwrap` once, on a trivial profile, before it rewrites anything. A `bwrap` that is on `PATH` but cannot run here -- user namespaces off, a seccomp or LSM policy refusing the setup -- is a named denial quoting what `bwrap` said, instead of every `Bash` call in the session dying at exec. The denial for an absent `bwrap` is unchanged.
- `bwrap-wrap.py` binds each writable worktree with `--bind-try`. A tree cut between the worktree listing and the exec costs its own writability rather than killing the whole command.
- The `Stop` gate reports a red run whose file cannot be read as a complaint. A run this gate cannot open is one nobody can be shown a verdict for, so it is a complaint and not a file to step over.

## [0.1.0] - 2026-09-10

### Added
- `gauntlet/` as the base for every agent write: `plans/`, `specs/`, `reviews/`, `drafts/{plans,specs}/`. Plans and specs tracked, the other two gitignored.
- `plans-lane.py`. Only the `gauntlet-prosecutor` writes `gauntlet/plans/approved/<slug>.txt`.
- `docs/plans.md`, the stage-1 plan shape.
- A tests-only lane: `kind: excision` and `kind: repair` blocks skip the plan gate, the red run and the post-merge round.
- `scripts/pair.sh` — `open`, `red`, `merge` — and `scripts/excision-diff.py`, the mechanical merge check for the two tests-only kinds.

### Changed
- Approved specs moved to `gauntlet/specs/approved/`, reviewer rounds to `gauntlet/reviews/`. `state/` holds the red run alone. `reviews-lane.py` carves out one folder per reviewer.
- `no-impl-reads.py` denies `gauntlet/` and re-allows `gauntlet/specs/approved/`, so plans, drafts and rounds stay closed to the blind agents.
- `EVASION` no longer burns the reviewer; only `STEERING` does.
- The five agents are prefixed `gauntlet-`, since the lane hooks key on `agent_type`.

**Breaking for existing installs:** re-copy `.claude/` and re-run the `--self-test` commands.

### Fixed
- Lane writes slipping through behind a harmless head word.
- Blind reads through an interpreter's `-e`/`-c`, an unrooted `grep -rn x .`, or a source file under a directory named `docs`, `tests` or `specs`.
- Lanes now hold outside a git checkout, including the write that creates the lane directory.

## [0.0.1] - 2026-09-09

### Added
- Blind adversarial review workflow: plans and test specs get checked by reviewers that cannot read the implementation.
- Enforced lanes: only the approving reviewer can write approved specs or tests.
