# The roster

Six agents, and the whole system is the shape of what each one is not allowed to see or write.

| Agent | Sees the code | Writes | Hooks |
| --- | --- | --- | --- |
| `prosecutor` | yes, all of it | `state/reviews/<slug>.plan.<N>.txt` | `reviews-lane` |
| `detective` | yes, all of it | nothing | `specs-lane`, `tests-lane`, `reviews-lane` |
| `accountant` | yes, all of it | throwaway scripts outside the tree | `specs-lane`, `tests-lane` |
| `arbiter` | **no** | `state/reviews/<slug>.<N>.txt`, `specs/approved/<slug>.txt` | `no-impl-reads`, `reviews-lane`, `specs-lane` |
| `testsmith` | **no** | `tests/` of its own spec worktree | `no-impl-reads`, `tests-lane`, `specs-lane` |
| the orchestrator | yes | everything else | all of them, session-wide |

## Who is blind, and why

The `arbiter` and the `testsmith` are the two that never read the implementation. Everything else in the repo exists to keep that true.

A reviewer that can read the code will rationalize a spec line that merely describes what the code already does — the line looks true, because it is, and it pins nothing. A test author that can read the code writes a test that mirrors it: the test and the implementation share the same mistake, so it goes green on a wrong implementation and nobody sees.

Blindness costs something, so it is paid for. The `accountant` measures the values a blind reviewer cannot look up, and the `detective` finds the lines a plan needs to cite. Both can read everything. Neither issues a verdict, which is why letting them see is safe.

## The chain

1. The author drafts a plan and sends its grounding questions, all of them, to one `detective`.
2. The `prosecutor` resolves the plan's citations and returns a pass or fail per check. The owner reads it only on a pass.
3. The author drafts a spec block. Where a `bite:` value needs a script or a rendered state space, the `accountant` measures it.
4. The `arbiter` runs its checks blind and, on `READY` and only then, writes `specs/approved/<slug>.txt`.
5. The `testsmith` reads that file — refusing any spec path outside the folder — and writes the tests, blind.
6. The tests run red. The author implements against them, and never edits them.

Steps 4 and 5 are the load-bearing pair, which is why a hook and not a convention stands between them: `specs/approved/` is written by the reviewer alone, so the file's existence is the writer's proof that the lines were reviewed. Rules in `approved-specs.md`.

## Verdicts, not grades

None of the reviewers hands back a score. `prosecutor` and `arbiter` return a gate token and a finding per check, and the default on every check is the failing one: a check the reviewer cannot decide fails. That is deliberate. A reviewer with discretion between pass and fail spends it on being agreeable, and an under-cut spec costs more than an over-cut one — the author can argue a cut back cheaply, and nobody ever argues back a line that should not have shipped.

Every reviewer also refuses a brief that steers it: a conclusion offered as settled fact, a ruling on scope, a question addressed to the reviewer, an alternative verdict, its own rules recited back. A rejection burns that agent — the steering is in its context now — so the bare brief goes to a fresh one.
