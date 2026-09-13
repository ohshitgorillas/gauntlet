# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versioning: [SemVer](https://semver.org/), 0.x during pre-release.

## [Unreleased]

### Added
- `gauntlet-juror`, a blind agent spawned once per red run. It reads the approved block and the run output, and returns one verdict per behavior line — `RED`, `ERROR`, `GREEN` or `INVALID` — so a red run is certified by an agent that never saw the implementation.
- `gauntlet-bailiff`, a blind agent spawned once per merged block. It takes the `TEST CHECK` brief `scripts/pair.sh merge` prints and returns `PIN`, `SOFT`, `MISSING` or `EXTRA` per behavior line, plus a row per test-policy violation.
- `verdicts-lane.py`. The `gauntlet-juror` writes `gauntlet/verdicts/<slug>.txt`; nothing else can write there, the main agent included. A turn that ends with an uncertified or stale red run is blocked, and every outstanding slug is named. A project that never runs `scripts/pair.sh red` never sees the gate.
- `scripts/pair.sh merge` writes its evidence to `state/merge/<slug>.txt` instead of stdout, and the bailiff reads it from there. An absent or empty file is a `NO EVIDENCE` verdict: run `merge` again and spawn a fresh bailiff.
- "The approval word" in `README.md`. The plan, the spec block and the start of implementation each wait for a message whose first line is exactly `approved`, or exactly `approved with revision` with the amendments below it. The word anywhere else in a message, and every softer phrase, holds the chain. No hook enforces it.
- `.claude/hooks/blind-bash.py` and `scripts/blind.sh`. A blind agent's shell is one command: `blind.sh test <path>`, `blind.sh status <slug>` and `blind.sh show <commit> <slug>`, each running under `bwrap` with the filesystem read-only apart from the agent's own lane. The hook matches the whole command text against one anchored pattern per subcommand, with a per-subcommand argument grammar, and denies everything else by name rather than by analysis — a second command appended, a command or an environment assignment in front, a slug that walks out of its directory, or a commit argument carrying its own `:path`. It fails closed on the caller key, so it is wired from the `gauntlet-scrivener` and `gauntlet-bailiff` frontmatter alone and never session-wide. A consumer copying `.claude/` now needs `bwrap` on the host and `scripts/blind.sh` beside it.
- `.claude/hooks/blind-reads.json` carries a `runner_invocations` key, read by every lane hook through `shell_shapes`. A declaration is an entry path, the fixed argument words after it, and the path prefix its one remaining argument sits under, and the classifier keys it on the whole invocation and its arity: a command word in front of the entry, a write beside it, a second argument, or an argument that normalizes outside the prefix is not a run. This repository declares `scripts/blind.sh test <path under tests/>`, so a blind agent's suite run stops reading as a write to the test lane. Two bounds are code rather than data: a declared prefix resolving to or under a lane directory is dropped, and the one argument is normalized before it is tested. A repo that declares nothing keeps the runner table it has today.
- `.claude/hooks/bwrap-wrap.py`, which answers every `Bash` call with an `updatedInput` carrying the caller's command text byte for byte inside a `bwrap` invocation. No hook reads the command to decide what to do with it: the text travels on stdin through a here-document, so a command substitution, a here-document of the caller's own or a second command appended survives unaltered, and what changes is the filesystem the command sees rather than the command. Three profiles keyed on `agent_type` — passthrough for the two blind agents whose one command runs its own `bwrap`; reviewer, read-only everywhere with a tmpfs over the reviewers' lane; and default, where the repository, `~/.cache` and the session's own `/tmp` are writable and every lane directory in every checkout is bound back read-only along with `state/red`, `state/merge`, `.claude/`, `scripts/`, `.git/hooks` and `.git/config`. `/run/user` is masked, which closes the D-Bus route to `systemd --user`. The worktree bind list is rebuilt on every call, because a cached one names a tree that has since been removed and `bwrap` fails the whole invocation on a missing bind source. A consumer copying `.claude/` needs `bwrap` on the host; the hook fails closed with a named reason when it is absent.
- `.claude/hooks/pair-passthrough.py`, the one carve-out from that wrap. `scripts/pair.sh` writes lane files by design, so it runs unwrapped, and this module holds the decision in its own file rather than inside the wrapper — a wrapper choosing its own exceptions would be a classifier again. One anchored whole-string pattern per subcommand with a slug grammar: a second command appended, a command or an assignment in front, or a slug that walks out of its directory does not match and is wrapped like anything else.
- `.claude/hooks/gauntlet-off.py` and the `GAUNTLET` switch. `GAUNTLET=off claude` runs one session with the seven lane hooks and the `Stop` gate silent, so the owner can work outside the chain without weakening a hook in the tree. The switch is `bypassed()` in `shell_shapes.py`, read from `os.environ` at the top of each hook's `main()` and never from a payload, so no subagent can forge it and every `--self-test` still reports what the hooks decide. The hook speaks on three events: a `SessionStart` banner naming what is silent, a `UserPromptSubmit` line carried every turn, and a `PreToolUse` denial of a `GAUNTLET=` assignment or a nested `claude` invocation, which keeps the switch out of reach of the session it governs. That denial matches the head word of a command rather than its text, so a path under `.claude/` passes. `scripts/gates/check-gates.sh` scrubs `GAUNTLET` from every gate's environment, so a gate report is about the hooks as wired rather than about however the session was started.
- `scripts/pair.sh restore <slug> <rev>`, which puts the approved block for `<slug>` back as it stood at `<rev>` and prints `RESTORED <path> <rev>`. It is the `git restore --source` step `docs/approved-specs.md` carves out of the lane classifier by hand, given a name, so the one shell shape that may write an approved block lives in the script rather than in a transcript.
- `scripts/pair.sh impl checkout <slug>` and `scripts/pair.sh impl merge <slug>`, which cut the implementation tree beside the spec tree and merge it back. `checkout` prints `IMPL .claude/worktrees/<slug>-impl` and leaves an already-cut tree on the commit it is on, so a second call never discards the implementation in progress in it. `merge` prints `MERGED <slug> <commit>`, where `<commit>` is the primary checkout's HEAD and holds the implementation tree's tip as an ancestor.
- `scripts/cite.py`, a citation resolver for a plan draft. `--check` resolves every backticked `path:line` against the tree and exits 1 on one that does not, `--fix` fills a number from its quoted anchor where the anchor is unique in the file.

**Breaking for existing installs:** re-copy `.claude/` and re-run the `--self-test` commands, which are now twelve.

### Changed
- The `gauntlet-arbiter` returns `ADMITTED`, `AMENDED` or `STRICKEN` per behavior line, and its default verdict is `STRICKEN`.
- The post-merge test check leaves the `gauntlet-arbiter` and becomes the `gauntlet-bailiff`'s own round. The reviewer that passed a block no longer judges the tests that landed against it: a fresh agent holds none of the reasons the block was passed, so a softened assertion cannot reach it as permission. The brief and the output format are unchanged.
- The `gauntlet-detective`, `gauntlet-juror` and `gauntlet-examiner` are pinned to Sonnet. Their work is mechanical — a file:line table, a verdict matched against run output, a measured value — so the level is fixed rather than inherited from whatever the calling session runs.
- The `gauntlet-prosecutor` takes an amendment round on an approved plan, where implementation settles a value the plan estimated. The amendment carries the command that produced the value and the reviewer re-runs it; the checks run on the amended lines alone and every other check prints `carried` from the plan file's own reviewer block, so a fresh reviewer can take the round. On `READY` it rewrites `gauntlet/plans/approved/<slug>.txt`, keeping every reviewer block in order, oldest first, and the rewritten plan takes a new approval word. A spec amendment is unchanged and stays a full re-review.
- The `gauntlet-arbiter` and `gauntlet-prosecutor` no longer exempt a host conduct block from the framing count. A brief that authorizes no command carries no conduct block, so neither reviewer spends definition on weighing one at zero.

- The gauntlet's artifacts leave `docs/` for a `gauntlet/` base of their own: `gauntlet/plans/approved/`, `gauntlet/plans/drafts/`, `gauntlet/specs/approved/`, `gauntlet/specs/drafts/`, `gauntlet/reviews/` and `gauntlet/verdicts/`. The lane hooks, the agent definitions, `scripts/pair.sh`, `scripts/blind.sh`, `scripts/excision-diff.py` and `.gitignore` move with them, so a consumer copying `.claude/` gets the new layout and re-copies both. A draft now sits under its stage rather than beside it; the lane is the `approved/` directory inside the stage, and the prefix test that guards the lane already excludes the drafts.
- A blind agent's allowlist is `docs/`, `tests/`, `state/` and `gauntlet/specs/approved/`, with the `gauntlet/` base denied entire. The carve-out inside `docs/` is gone, so `docs/` is readable the whole way down and no denied subtree nests inside an allowed root — the hole that let a sweep rooted at `docs/` return artifacts its own paths denied. `no-impl-reads.py --self-test` computes that invariant over `DEFAULT_ALLOW` and every `allow` entry in `blind-reads.json`, so a repo that re-opens the base fails the check rather than the blindness.

### Fixed
- The lane hooks no longer count a read-only git command as a write. `git grep`, `git ls-tree`, `git cat-file`, `git rev-list`, `git shortlog`, `git reflog`, `git merge-base` and `git describe` naming a lane pass, the way `git log` does. A git stage carrying `--output`, `git grep -O` and the writing `reflog` forms (`write`, `delete`, `drop`, `expire`) count as writes, so `git diff --output=tests/x` is denied.
- `scripts/pair.sh red` runs the suite verbose, so the saved output names every test that passed as well as every test that failed.

## [0.1.0] - 2026-09-10

### Added
- `gauntlet/` as the base for every agent write: `plans/`, `specs/`, `reviews/`, `drafts/{plans,specs}/`. Plans and specs tracked, the other two gitignored.
- `plans-lane.py`. The `gauntlet-prosecutor` writes the approved plan to `gauntlet/plans/approved/<slug>.txt` on `READY`; nothing else can write there.
- `docs/plans.md`, the stage-1 plan shape.
- A tests-only lane: `kind: excision` and `kind: repair` blocks skip the plan gate, the red run and the post-merge round.
- `scripts/pair.sh` — `open`, `red`, `merge` — and `scripts/excision-diff.py`, the mechanical merge check for the two tests-only kinds.
- Each lane's `--self-test` asserts that an unprefixed agent name is denied.

### Changed
- Approved specs moved to `gauntlet/specs/approved/`, reviewer rounds to `gauntlet/reviews/`. `state/` holds the red run alone. `reviews-lane.py` carves out one folder per reviewer.
- `no-impl-reads.py` denies `gauntlet/` and re-allows `gauntlet/specs/approved/`, both ahead of the allow list, so plans, drafts and rounds stay closed to the blind agents.
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
