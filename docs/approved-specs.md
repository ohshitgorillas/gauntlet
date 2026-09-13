# The approved-spec lane

`docs/gauntlet/specs/` holds the spec blocks that passed adversarial review. It is the boundary between "someone wants this behavior" and "this behavior is the contract", and the blind `gauntlet-scrivener` works from nothing else.

## The rule

One directory, one writer.

- **`docs/gauntlet/specs/<slug>.txt` is written by the `gauntlet-arbiter` and by no one else.** Not the main agent, not the `gauntlet-scrivener`, not the person driving the session through an agent. `hooks/specs-lane.py` denies every other hand at the tool call.
- **A file appears there only when that reviewer's gate verdict is `READY`.** The reviewer writes the block it just passed, verbatim, with its own per-line verdicts beneath it. An `ANOTHER PASS` or `ESCALATE` round writes nothing.
- **The `gauntlet-scrivener` reads from there and refuses a spec path anywhere else.** The path being under `docs/gauntlet/specs/` is the writer's proof that the behavior it is about to pin survived review; a draft handed to it directly is a spec that skipped the gate.
- **Reads are open.** Any agent, and the shell, may read the folder. The lane governs writing.
- **Drafts live beside it, not in it.** `docs/gauntlet/drafts/specs/<slug>.txt` is the main agent's own, gitignored, and open to every hand. Nothing about drafting is restricted; the lane governs only the folder a block reaches after review.

## Why one writer

The `gauntlet-scrivener` is blind on purpose: a test written by the agent that wrote the code mirrors the code, and goes green on an implementation that is wrong in exactly the way the main agent was wrong. The spec block is the only thing standing between that agent's intent and the test that will certify it.

So if the main agent can write the spec file, the blindness buys nothing. The main agent states the behavior it already implemented, drops it in the folder, and the writer faithfully pins the mistake. Review becomes a step that happened somewhere in the transcript rather than a fact on disk.

Making the folder the reviewer's alone turns approval into evidence. The presence of `docs/gauntlet/specs/<slug>.txt` means one specific agent, which never read the implementation and whose default verdict is `STRICKEN`, decided those lines earn the tests they will produce. Nothing else can put that file there, so nothing else can claim it.

## What the reviewer writes

The approved file carries the block as approved and the verdicts that approved it:

```
slug: <slug>
kind: new | characterization | refactor | excision | repair
brief:
> <the owner's words that asked for this work>

1. <behavior as the caller sees it>
   kills: <a wrong implementation a user would notice, which this line rejects>
   bite: <the value HEAD produces at this input, measured, with the command>
   existing: none, <the grep that produced it> | tests/<file>::<test>

--- reviewer ---
READY
discriminates: <differential | anchor+edges | sweep> on <surface>
1  ADMITTED  <input> -> <outcome>; ...
```

`STRICKEN` lines are dropped rather than recorded as cut: the file is the surviving contract, and the writer's one-test-per-line rule counts what is in it. An `AMENDED` line stays, since it names a test that changes.

## Changing an approved spec

An approved file is amended the same way it was created: the revised block goes back to a `gauntlet-arbiter`, and the reviewer that returns `READY` rewrites the file. A test changes only because the line it pins changed, and a line changes only in that folder.

Reverting is the exception the shell keeps: `git restore --source <rev> -- docs/gauntlet/specs/<file>` passes the hook, because it copies a commit rather than typing a spec.

## Wiring

Session-wide, in `.claude/settings.json`, so the lane binds the main agent and every subagent. That file also carries `tests-lane.py` and `reviews-lane.py` on the same matcher, since all three lanes bind the same way; only the `specs-lane.py` entry is shown here:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PROJECT_DIR}\"/.claude/hooks/specs-lane.py"
          }
        ]
      }
    ]
  }
}
```

`no-impl-reads.py` is the exception: it is wired only from the `hooks:` frontmatter of the blind agents — `gauntlet-arbiter.md`, `gauntlet-scrivener.md`, `gauntlet-juror.md` and `gauntlet-bailiff.md` — never session-wide — a session-wide read-block would blind the main agent itself, which has to read the implementation to adjudicate a failing test.

The same `specs-lane.py` script is wired again from the `hooks:` frontmatter of every agent that could reach the folder — `gauntlet-arbiter.md`, `gauntlet-scrivener.md`, `gauntlet-examiner.md`, `gauntlet-detective.md`, `gauntlet-juror.md`, `gauntlet-bailiff.md` — so the lane holds even where a build does not apply session hooks to subagent calls.

Copy the whole `hooks/` directory, not the one file. `specs-lane.py` imports `shell_shapes.py` from beside it, and it has three siblings that enforce the other half of the same rule: `plans-lane.py`, which holds this same one-directory-one-writer rule for the plan gate one stage earlier (`docs/gauntlet/plans/`, the `gauntlet-prosecutor` alone — rules in `plans.md`); `tests-lane.py`, which keeps every hand but the blind writer's off `tests/`; and `reviews-lane.py`, which keeps a reviewer's verdict a file the reviewer wrote. `reviews-lane.py` is the one that must know about both lanes: it confines each reviewer to `docs/gauntlet/reviews/`, so it carries the explicit carve-outs that let the `gauntlet-arbiter` write `docs/gauntlet/specs/` and the `gauntlet-prosecutor` write `docs/gauntlet/plans/`, each and nothing else besides. Ship them together or a reviewer is locked out of the folder reserved for it.

Nothing in `hooks/` depends on anything outside `hooks/`. There is no allowlist to import, no budget to configure, no repo layout assumed.

Check them after wiring. Each prints one `PASS` or `FAIL` per line it exists to hold:

```
python3 .claude/hooks/plans-lane.py --self-test
python3 .claude/hooks/specs-lane.py --self-test
python3 .claude/hooks/tests-lane.py --self-test
python3 .claude/hooks/reviews-lane.py --self-test
python3 .claude/hooks/no-impl-reads.py --self-test
```

## Failure modes it accepts

The hook keys off the caller's `agent_type`, which is present only on subagent calls. An absent key reads as the main agent and is denied. If a build omits the key for subagents too, the `gauntlet-arbiter` is denied along with everyone else: the lane fails closed, no unreviewed spec reaches the writer, and the denial message names the file to fix.
