# The stage-1 plan

A plan is what the owner approves before any behavior is specified. It is prose, not a spec block: it says what is wrong, what changes, and what it costs, in enough detail that a reviewer can resolve every claim it makes against the tree.

## Where a plan lives

| Path | Written by | When | Tracked |
| --- | --- | --- | --- |
| `docs/gauntlet/drafts/plans/<slug>.txt` | the main agent | while drafting, every round | no |
| `docs/gauntlet/plans/<slug>.txt` | `gauntlet-prosecutor` | on `READY`, and only then | yes |
| `docs/gauntlet/reviews/<slug>.plan.<N>.txt` | `gauntlet-prosecutor` | every round that carries checks | no |

One directory, one writer, the same rule `docs/approved-specs.md` states for the spec gate one stage later. `hooks/plans-lane.py` denies every other hand at the tool call, so the presence of `docs/gauntlet/plans/<slug>.txt` is the evidence that those words passed the plan gate — not a claim in a transcript.

The approved plan is tracked because a later stage reads it from disk. That is the whole point of the artifact: a fresh agent picking the chain up at implementation reads the plan it is implementing rather than inheriting it from a conversation that may not exist any more.

## The shape

The plan opens with two metadata lines and the owner's brief, then six sections. A reviewer reads `slug:` and `grounding:` as metadata, never as framing.

```
slug: <slug>
grounding: gauntlet-detective

brief:
> <the owner's words that asked for this work, verbatim, one `> ` per line>

## What is wrong
## What the owner sees change
## Which files get touched, and roughly how
## Caller-side delta
## What it costs
## Open questions
```

- **`brief:`** is the owner's words and nothing else. Quote every sentence that asked for work, including the ones that changed the owner's mind: a plan that quotes only the final instruction hides the reversal that produced it. Where a later sentence overrides an earlier one, both are quoted and the plan says which it followed.
- **What is wrong** states the defect or the want, with citations. A claim about the tree carries `file:line`.
- **What the owner sees change** is the delta as the owner experiences it, not as the diff expresses it.
- **Which files get touched, and roughly how** names files and the shape of the change in each. It is not a diff, and it is not a promise of line counts.
- **Caller-side delta** applies where anything outside the changed files has to change with them — an interface, a path, an agent's own instructions. `none` where nothing does.
- **What it costs** names the work the change forces, the tests it breaks, and what was deliberately left out, with the owner's own words where a scope instruction produced the cut.
- **Open questions** is `None` or a numbered list. A question here reaches the owner; a question addressed to the reviewer is a steering tell and burns the round.

## Grounding

The pointers a plan cites come from one `gauntlet-detective` round: every question in one brief, a `file:line` table back. The main agent does not read half the tree to write a plan, and the reviewer resolves the citations that come back.

## The gate

`gauntlet-prosecutor` reads the plan prose and resolves its citations. Its gate token is one of `READY`, `ANOTHER PASS`, `ESCALATE` or `ESCALATE: QUESTION`, and the default on every check is the failing one. `PASS` and `FAIL` are per-check tokens beneath the gate line, never the gate itself.

The owner reads the plan only on `READY`. Rounds before that are between the main agent and the reviewer, and they are cheap; a plan passed carelessly costs the owner directly.
