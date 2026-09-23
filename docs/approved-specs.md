# The approved-spec lane

`<gauntlet dir>/specs/approved/` holds the spec blocks that passed adversarial review. It is the boundary between "someone wants this behavior" and "this behavior is the contract", and the blind `scrivener` works from nothing else.

## The rule

One directory, one writer.

- **`<gauntlet dir>/specs/approved/<slug>.txt` is written by the `arbiter` and by no one else.** Not the main agent, not the `scrivener`, not the person driving the session through an agent. `hooks/lanes.py` denies every other hand at the tool call, in any session the owner has not started with `GAUNTLET=off`.
- **A file appears there only when that reviewer's gate verdict is `READY`.** The reviewer writes the block it just passed, verbatim, with its own per-line verdicts beneath it. An `ANOTHER PASS` or `ESCALATE` round writes nothing.
- **The `scrivener` reads from there and refuses a spec path anywhere else.** The path being under `<gauntlet dir>/specs/approved/` is the writer's proof that the behavior it is about to pin survived review; a draft handed to it directly is a spec that skipped the gate.
- **Reads are open.** Any agent, and the shell, may read the folder. The lane governs writing.
- **Drafts sit under the stage, not in the lane.** `<gauntlet dir>/specs/` is the stage; the lane is `<gauntlet dir>/specs/approved/` inside it, and `<gauntlet dir>/specs/drafts/<slug>.txt` is the main agent's own, gitignored, and open to every hand that writes. Nothing about drafting is restricted; the lane governs only the folder a block reaches after review. The blind agents cannot read the drafts, because `no-impl-reads.py` closes every part of `<gauntlet dir>/` but its three leaves, so a draft reaches the `arbiter` only as text in its brief.

## Why one writer

The `scrivener` is blind on purpose: a test written by the agent that wrote the code mirrors the code, and goes green on an implementation that is wrong in exactly the way the main agent was wrong. The spec block is the only thing standing between that agent's intent and the test that will certify it.

So if the main agent can write the spec file, the blindness buys nothing. The main agent states the behavior it already implemented, drops it in the folder, and the writer faithfully pins the mistake. Review becomes a step that happened somewhere in the transcript rather than a fact on disk.

Making the folder the reviewer's alone turns approval into evidence. The presence of `<gauntlet dir>/specs/approved/<slug>.txt` means one specific agent, which never read the implementation and whose default verdict is `STRICKEN`, decided those lines earn the tests they will produce. Nothing else can put that file there, so nothing else can claim it.

That proof is a proof about sessions run under the chain. `GAUNTLET=off` silences the lane, and a file written into it by any hand is afterwards indistinguishable from one the reviewer wrote — which is the honest reading for anyone who cannot tell how a given file got there, and the reason a session with the gauntlet off should not run the chain.

## What the reviewer writes

The approved file carries the block as approved and the verdicts that approved it. Its `brief:` section copies the approved plan's `brief:` verbatim, word for word — it is not redrafted, summarized or reworded at this stage.

```
slug: <slug>
kind: new | characterization | refactor, or motion: strike | amend | rehome
brief:
> <the owner's words that asked for this work>

1. <behavior as the caller sees it>
   kills: <a wrong implementation a user would notice, which this line rejects>
   bite: <the value HEAD produces at this input, measured, with the command>
   existing: none, <the grep that produced it> | <tests dir>/<file>::<test>

--- reviewer ---
READY
discriminates: <differential | anchor+edges | sweep> on <surface>
1  ADMITTED
```

`STRICKEN` lines are dropped rather than recorded as cut: the file is the surviving contract, and the writer's one-test-per-line rule counts what is in it. An `AMENDED` line stays, since it names a test that changes.

## The brief to the reviewer

Before every round that will carry verdicts, the main agent calls `mcp__plugin_gauntlet_pair__review` with the block's slug. The call returns one line, `REVIEW <gauntlet dir>/reviews/<slug>.<N>.txt`, and the brief carries that line word for word.

On the first round, the brief carries the whole block inline beneath that line, from the `slug:` line to the last behavior line. A path to the draft is not a block: `no-impl-reads.py` denies the `arbiter` every read of `<gauntlet dir>/specs/drafts/`, so a brief that names the draft file instead of carrying it gets a round that runs no check, writes nothing and names the path it could not read. The `arbiter` stays open after such a round, and the main agent resends the block inline to it. Re-review rounds take the shape `agents/arbiter.md` states, and go to the same `arbiter` by `SendMessage`.

## Changing an approved spec

An approved file is amended the same way it was created: the revised block goes back to a `arbiter`, and the reviewer that returns `READY` rewrites the file. A test changes only because the line it pins changed, and a line changes only in that folder.

A rewritten file is a new artifact, so the owner's approval of the one before it does not carry: `approved` is given again against the file as it now stands.

Reverting is the exception the shell keeps: `git restore --source <rev> -- <gauntlet dir>/specs/approved/<file>` passes the hook, because it copies a commit rather than typing a spec.

## Wiring

Session-wide, in `.claude-plugin/plugin.json`, so the lane binds the main agent and every subagent. One entry carries every lane: `lanes.py` holds the specs lane, the plans lane, the tests lane, the reviewers' lane and the verdicts lane as rows of one table, so the wiring names one command rather than one per lane.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit|Read|Grep",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}\"/hooks/lanes.py"
          }
        ]
      }
    ]
  }
}
```

The matcher carries `Read` and `Grep` because one lane blocks reads as well as writes: a reviewer is kept out of the round files in its own lane. No lane hook is wired on `Bash` and none reads a command string; a shell is held out of a lane by the mount table `bwrap-wrap.py` builds, which binds every lane directory read-only. Both read the same lane set, from `lane_config.lane_dirs()`: a lane the table holds and the mount table leaves writable is a lane a shell walks into, so `lanes.py --self-test` fails on any difference between the two.

One hook runs after a write rather than before it. `lane-audit.py` is wired `PostToolUse` on `Write|Edit|NotebookEdit`, takes the path the harness reports as changed, and asks the same table about that path. A file the table refuses, changed by a call the gate admitted, means the two disagree about one path, and the hook prints one named line saying so. It never blocks and it cannot: the write has happened. What it buys is that a path the lane compared wrongly is a line in the next run instead of a hole nobody finds.

`no-impl-reads.py` is wired session-wide too, and gated on the caller instead. It carries a `BLIND` tuple — the five blind agents — and a caller outside it passes unjudged. That is what makes session wiring safe for it: a session-wide read block with no such gate would blind the main agent itself, which has to read the implementation to adjudicate a failing test. No hook reads a shell command: a blind agent whose shell would need holding holds no `Bash`, and runs what it needs through the `blind` MCP server's typed tools instead (`docs/agents.md`).

Gate on the caller, not on where the hook is wired, because a plugin-shipped agent definition runs no `hooks:` frontmatter of its own. Frontmatter wiring reaches nothing once the kit ships as a plugin, so a hook that binds one agent binds it by reading `agent_type` or it binds nobody.

Session wiring is the whole of the wiring, and that is a known gap. The kit used to wire the specs lane a second time from the `hooks:` frontmatter of every agent that could reach the folder, so the lane held even where a build did not apply session hooks to subagent calls; a plugin runs no per-agent frontmatter, so that second copy is gone and cannot come back. A build that stops applying session hooks to subagent calls now has no lane at all.

The `agent_type` gate has a fail direction, and it is the opposite of the lane hook's. The reviewers' row of `lanes.py` answers an absent `agent_type` by over-denying, which leaks nothing: a reviewer loses a write it would have been allowed. `no-impl-reads.py` cannot do that, because the main agent is itself the caller that carries no `agent_type`, so an absent key must pass. A build that stopped supplying the key for subagents would hand the blind agents the implementation rather than deny them. Guarding by caller identity is what packaging costs; guarding by wiring scope failed closed and does not survive it.

Copy the whole `hooks/` directory, `hooks/lib/` included, not the one file. `lanes.py` imports `lane_config.py` from `hooks/lib/` beneath it, and it holds four more rows that enforce the other half of the same rule: the plans lane, which holds this same one-directory-one-writer rule for the plan gate one stage earlier (`<gauntlet dir>/plans/approved/`, the `prosecutor` alone — rules in `plans.md`); the tests lane, which keeps every hand but the blind writer's off `<tests dir>/`; the verdicts lane, which keeps a red run's certificate a file the `juror` wrote; and the reviewers' lane, which keeps a reviewer's verdict a file the reviewer wrote. That last row is the one that must know about two lanes at once: it confines each reviewer to `<gauntlet dir>/reviews/`, so it carries the `second` field that lets the `arbiter` also write `<gauntlet dir>/specs/approved/` and the `prosecutor` also write `<gauntlet dir>/plans/approved/`, each and nothing else besides.

Nothing in `hooks/` imports anything outside `hooks/`, and one thing in it runs something outside the kit entirely: `bwrap-wrap.py` puts every `Bash` call inside `bubblewrap`, so `bwrap` on the host is a hard dependency a consumer takes on with the kit, and an absent or unusable binary is a named denial on every `Bash` call rather than a command that runs unwrapped. There is no allowlist to import and no budget to configure, and the one repo layout the hooks know is the one a repo writes down for itself: `blind-reads.json`, beside the hooks in `hooks/`, carrying eight keys, three of them directories. `tests_dir` is the writer's lane, which is what `<tests dir>` means everywhere it is written; `gauntlet_dir` is the base every lane in this document sits under, which is what `<gauntlet dir>` means everywhere it is written; `docs_dir` is the prose a blind agent may read. Each defaults to the name the kit ships — `tests`, `gauntlet`, `docs` — which is why the file may be absent. The shape under `gauntlet_dir` is not a repo's to name: `specs/approved`, `plans/approved`, `reviews` and `verdicts` are the kit's identity, and so are the agent names.

A repo that moves one of the three moves it everywhere at once, because every hook resolves the path through `lane_config.py` rather than typing it, and every script reaches the same table through `shell_shapes.py --config <key>`. What bounds the file is that the three names must be pairwise disjoint — none equal to, under, or over another, none the root or an absolute path — and that a set failing the check moves nothing at all rather than moving part of a layout. `lane_config.py` says why the fallback is all-or-nothing: a name that is legal read alone can still land on the default another key would have taken.

Check them after wiring. Each prints one `PASS` or `FAIL` per line it exists to hold:

```
python3 hooks/lanes.py --self-test
python3 hooks/no-impl-reads.py --self-test
python3 hooks/bwrap-wrap.py --self-test
python3 hooks/lane-audit.py --self-test
python3 hooks/blind-write.py --self-test
python3 hooks/gauntlet-off.py --self-test
python3 hooks/kit-probe.py --self-test
python3 scripts/mcp/blind_server.py --self-test
python3 scripts/mcp/blind_write_server.py --self-test
python3 scripts/mcp/pair_server.py --self-test
```

## Failure modes it accepts

The hook keys off the caller's `agent_type`, which is present only on subagent calls. An absent key reads as the main agent and is denied. `bwrap-wrap.py` reads the same key without gating on it: the key picks a profile and an absent one is the main agent, which takes the default profile, so a build that omits the key wraps a subagent as the main agent rather than letting it out. `sudo` does not run in a wrapped shell, because `bwrap` sets `NO_NEW_PRIVS`, and no command is carved out of the wrap. If a build omits the key for subagents too, the `arbiter` is denied along with everyone else: the lane fails closed, no unreviewed spec reaches the writer, and the denial message names the file to fix. That is the disposition a session with the gauntlet on gets.

The one failure mode accepted by choice rather than tolerated is the owner's switch. Under `GAUNTLET=off` the lane fails open, deliberately, on an environment variable, and an unreviewed spec does reach the writer. The switch belongs to the hand that launches the session; no agent inside a running session may propose it or set it. `CLAUDE.md` carries the rule, `README.md` carries it for a consumer installing the plugin.
