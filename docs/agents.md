# The roster

Eight agents, and the whole system is the shape of what each one is not allowed to see or write.

| Agent | Sees the code | Writes | Hooks |
| --- | --- | --- | --- |
| `gauntlet-prosecutor` | yes, all of it | `docs/gauntlet/reviews/<slug>.plan.<N>.txt`, `docs/gauntlet/plans/<slug>.txt` | `reviews-lane`, `plans-lane` |
| `gauntlet-detective` | yes, all of it | nothing | `specs-lane`, `tests-lane`, `reviews-lane` |
| `gauntlet-examiner` | yes, all of it | throwaway scripts outside the tree | `specs-lane`, `tests-lane` |
| `gauntlet-arbiter` | **no** | `docs/gauntlet/reviews/<slug>.<N>.txt`, `docs/gauntlet/specs/<slug>.txt` | `no-impl-reads`, `reviews-lane`, `specs-lane` |
| `gauntlet-scrivener` | **no** | `tests/` of its own spec worktree | `no-impl-reads`, `tests-lane`, `specs-lane` |
| `gauntlet-bailiff` | **no** | nothing | `no-impl-reads`, `specs-lane`, `tests-lane`, `plans-lane`, `reviews-lane`, `verdicts-lane` |
| `gauntlet-juror` | **no** | nothing | `no-impl-reads`, `specs-lane`, `tests-lane`, `reviews-lane` |
| the main agent | yes | everything else | all of them, session-wide |

## Who is blind, and why

The `gauntlet-arbiter`, the `gauntlet-scrivener`, the `gauntlet-juror` and the `gauntlet-bailiff` are the four that never read the implementation. Everything else in the repo exists to keep that true.

A reviewer that can read the code will rationalize a spec line that merely describes what the code already does — the line looks true, because it is, and it pins nothing. A test writer that can read the code writes a test that mirrors it: the test and the implementation share the same mistake, so it goes green on a wrong implementation and nobody sees. A certifier that can read the code reads a `GREEN` as the implementation already being right rather than as the test failing to bite, which is the one reading the red run exists to rule out. A post-merge checker that can read the code reads a softened assertion as matching what the code turned out to do, which is exactly the change it is there to catch.

The certifier is also blind to the test it is judging in a second sense: it did not write it. The `gauntlet-scrivener` grading its own red run is the same conflict one stage down from an agent testing its own code, so the run output goes to a fresh agent that holds none of the reasons the test was written the way it was.

Blindness costs something, so it is paid for. The `gauntlet-examiner` measures the values a blind reviewer cannot look up, and the `gauntlet-detective` finds the lines a plan needs to cite. Both can read everything. Neither issues a verdict, which is why letting them see is safe.

## The chain

1. The main agent drafts a plan and sends its grounding questions, all of them, to one `gauntlet-detective`.
2. The `gauntlet-prosecutor` resolves the plan's citations and returns a pass or fail per check and, on `READY` and only then, writes `docs/gauntlet/plans/<slug>.txt`. The owner reads it only on a pass. Rules in `plans.md`.
3. The main agent drafts a spec block. Where a `bite:` value needs a script or a rendered state space, the `gauntlet-examiner` measures it.
4. The `gauntlet-arbiter` runs its checks blind and, on `READY` and only then, writes `docs/gauntlet/specs/<slug>.txt`.
5. The `gauntlet-scrivener` reads that file — refusing any spec path outside the folder — and writes the tests, blind.
6. The tests run red under `scripts/pair.sh red`, and a `gauntlet-juror` reads that saved output against the approved block and returns one verdict per line, blind.
7. The main agent implements against the tests, and never edits them.
8. After `scripts/pair.sh merge`, a `gauntlet-bailiff` reads the `TEST CHECK` brief the script printed against the committed block and returns `PIN`, `SOFT`, `MISSING` or `EXTRA` per behavior line, blind. It is the only round that holds test code, so rules 4, 6, 13 and 14 are checked there and nowhere else.

## `scripts/pair.sh`

The script that moves a block between the reviewer, the writer and the tree. Three subcommands, and their stdout is contract:

| Invocation | stdout | when |
| --- | --- | --- |
| `pair.sh open <slug>` | `OPEN .claude/worktrees/<slug>-spec` | the approved spec's reviewer section is byte-identical to the newest `docs/gauntlet/reviews/<slug>.<N>.txt` |
| `pair.sh open <slug>` | `MISMATCH docs/gauntlet/reviews/<slug>.<N>.txt` | those two texts differ, and no worktree is cut |
| `pair.sh red <slug>` | the saved output's path | after the suite has run in the spec worktree |
| `pair.sh merge <slug>` | `TEST CHECK <slug>` and the brief beneath it | `kind:` is `new`, `characterization` or `refactor` |
| `pair.sh merge <slug>` | the `scripts/excision-diff.py` verdict lines | `kind:` is `excision` or `repair` |

`open` refuses on mismatch because the spec file is editable after the reviewer passed it, and the round file is not: the comparison is what makes the approved block the reviewed block rather than the latest one. `red` removes the whole-file excision targets, which the lane hook denies every agent, and leaves single-test targets to the writer's `Edit`. `merge` routes on `kind:` because the two tests-only kinds have no implementation phase, so the blind post-merge reviewer round has no window to watch and the mechanical check takes it.

## The tests-only lane

A change confined to `tests/` — a test that violates `docs/testing.md` and has to go, or to be replaced — skips steps 1 and 2 entirely. No `gauntlet-detective`, no plan, no `gauntlet-prosecutor`, no owner plan approval.

1. The main agent drafts a `kind: excision` or `kind: repair` block and sends it to a `gauntlet-arbiter`.
2. The reviewer resolves each line's quoted assertion against the test file itself — `tests/` is open to it, and the implementation is not what these lines rest on — and writes `docs/gauntlet/specs/<slug>.txt` on `READY`.
3. The `gauntlet-scrivener` removes the targets and writes the replacements its `as:` fields name.
4. `scripts/excision-diff.py`, run by `scripts/pair.sh merge`, checks the landed diff against the block by name and by quoted assertion text. There is no red run and no post-merge reviewer round: neither kind has an implementation phase, so the window those two watch does not exist.

The plan gate is what the lane drops, and it drops it because the gate resolves citations into the implementation. These lines cite `tests/`.

Steps 4 and 5 are the load-bearing pair, which is why a hook and not a convention stands between them: `docs/gauntlet/specs/` is written by the reviewer alone, so the file's existence is the writer's proof that the lines were reviewed. Rules in `approved-specs.md`.

## Verdicts, not grades

None of the reviewers hands back a score. `gauntlet-prosecutor` and `gauntlet-arbiter` return a gate token and a finding per check, and the default on every check is the failing one: a check the reviewer cannot decide fails. That is deliberate. A reviewer with discretion between pass and fail spends it on being agreeable, and an under-cut spec costs more than an over-cut one — the main agent can argue a cut back cheaply, and nobody ever argues back a line that should not have shipped.

Every reviewer also refuses a brief that steers it: a conclusion offered as settled fact, a ruling on scope, a question addressed to the reviewer, an alternative verdict, its own rules recited back. A steering rejection burns that agent — the steering is in its context now — so the bare brief goes to a fresh one.

The other rejection, `EVASION`, runs the opposite way, and deliberately. A reviewer calls it on a re-review when the main agent's return neither did the named repair nor supplied the missing citation. Burning the reviewer there would reward the evasion: a fresh one holds none of the findings that were evaded, so the main agent would get a clean slate and could run the same evasion again. So an `EVASION` call leaves the reviewer open, holding its findings, and the main agent answers that call back to the same reviewer, by `SendMessage`, with the repair or the citation. An answer that evades again gets a second `EVASION` call from the same reviewer. Only steering replaces a reviewer.
