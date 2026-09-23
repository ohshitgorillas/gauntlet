# Gauntlet

Gauntlet is a brutally strict and complex LLM workflow based on adversarial review. It is, like the legal process that its language is framed after, also highly deliberate, careful, and often slow. It is optimized to mitigate mistakes and generate high-quality tests.

Gauntlet is a set of eight subagents that surround the main agent, built around two blind reviewers:

1. An adversarial plan reviewer (`prosecutor`)
2. A discovery locator for plans (`detective`)
3. A blind adversarial spec reviewer (`arbiter`)
4. A measurement agent (`examiner`)
5. A blind test writer (`scrivener`)
6. A blind juror for the red run (`juror`)
7. A blind post-merge test checker (`bailiff`)
8. A blind sweeper of tests already in the tree (`auditor`)

"Blind" in this instance means that those agents are forbidden from reading, and therefore making judgment calls based on, implementation. This prevents tests from being written to implementation, which then break on honest refactors and pin nothing of consequence.

Together, they ensure that agents are kept in line, honest, and incapable of de-fanging your testing suite. Nothing writes to `<tests dir>/` except the `scrivener`, which takes instructions only from the `arbiter` — and neither can read source code, so tests are grounded in behavior, not implementation, and never patched to pass after the fact.

Gauntlet works best with existing, established codebases for which shipping bugs has real consequences. Budding projects are better served by lighter, less restricted workflows.

## Workflow

The workflow enforced by Gauntlet is, as its name implies, quite brutal:

1. You supply an agent with a brief: the problem to solve or feature to add.
2. The main agent sends its discovery questions, all of them, to one `detective`, which returns a `file:line` table and nothing else.
3. The main agent drafts a plan on those pointers and provides it to a `prosecutor`.
4. The `prosecutor` checks the drafted plan for mistakes, errors, inconsistencies, and resolves the plan's citations against the tree to return a pass or fail per check. It may also return a refusal to rule if the main agent is caught trying to game its context or evades a posed question. An owner-visible delta no sentence of your brief asked for is cut, and the main agent's default is to take the cut; where it argues the change does not work without that element, the reviewer returns `ESCALATE: LEAVE` and you rule on keeping it before the plan reaches you for approval. Any questions the agents cannot answer are escalated to you, who then approves the plan only on a pass. On `READY`, it writes the approved plan to `<gauntlet dir>/plans/approved/`, a folder only it can write to, so a later stage reads the plan from disk rather than inheriting it — the shape is in `docs/plans.md`. Where implementation later settles a value the plan estimated, the plan takes an amendment round rather than a redraft: the amendment carries the command that produced the value, the checks re-run on the amended lines alone, and the reviewer rewrites the file.
5. The main agent drafts a testing spec block. Where a `bite:` value needs a script or a rendered state space, the `examiner` measures it.
6. The main agent supplies its spec block to a `arbiter`.
7. The `arbiter` runs its checks blind: it cannot read the implementation. It evaluates the spec block based on its merits alone and returns verdicts per test proposal. It may also outright refuse the prompt on leading or evasion attempts by the main agent. On `READY`, it sends the approved specs to `<gauntlet dir>/specs/approved/`, a folder only it can write to.
8. The `scrivener`, also blind to implementation, takes its orders only from `<gauntlet dir>/specs/approved/`. A line it cannot test goes back to the `arbiter` instead of getting a weak test; a test that passes against no implementation sends the block back to the main agent for a new spec. A block may also carry `collateral:` rows — tests the change breaks that no behavior line pins — and a delta naming one of those targets is the one delta the writer admits: it repairs what surrounds the assertion and carries the quoted assertion through byte-identical, which `scripts/strike-diff.py` and the `bailiff` check at merge.
9. Both the `scrivener` and the main agent work concurrently in different branches, the latter on implementation.
10. The tests run red in the `scrivener`'s tree, and green in the implementation branch.
11. A `juror`, blind and spawned fresh for that one run, reads the red run's output against the approved block and returns one verdict per behavior line — `RED`, `ERROR`, `GREEN` or `INVALID`. It writes them to `<gauntlet dir>/verdicts/<slug>.txt`, a folder only it can write to, so the main agent, which has read the code, cannot rule on whether its own tests bit. A turn that leaves a red run unruled does not end: the `Stop` hook names the slug.
12. The main agent has two approaches to a test failing against implementation: fix the code, or send a revised spec back to the `arbiter` for approval. The `scrivener` will refuse any direct attempts by the main agent to weaken the tests to pass at this phase.
13. Once the test suite is green against implementation, the `pair` tool `mcp__plugin_gauntlet_pair__check` runs the gate over the combined pair and records the verdict beside the three tips it ran over, landing nothing; `mcp__plugin_gauntlet_pair__merge` then lands a pair that reading passed, and refuses any other.
14. A `bailiff`, blind and spawned fresh, checks the landed tests against the approved block; a test that no longer matches gets restored from the red commit, or the spec goes back to the main agent. It holds none of the reasons the block was passed, so a softened assertion cannot reach it as permission.

## How blindness holds

No hook reads a shell command. Deciding a `Bash` call by parsing its text cannot be done reliably — an env prefix, a here-document, a command substitution, an `xargs` — so the kit changes the filesystem a command sees instead of reading the command.

Every `Bash` call, from every caller, runs inside `bwrap`, and `hooks/bwrap-wrap.py` carries the command into the sandbox byte for byte without reading it. No caller and no command is exempt. Inside the default profile the repository is writable, but every lane directory in every checkout is bound read-only again, so no shell can write into a lane that belongs to another agent. A blind reviewer's profile makes the whole filesystem read-only.

The blind agents hold no shell at all. They reach `scripts/blind.sh` only through typed MCP tools: the `blind` server's `test`, `status` and `show`, and, for the `scrivener` alone, the `blind-write` server's `format`. Each argument is checked against its type, and the script runs as an argument list with no shell in between. The `test` tool returns one `PASSED`, `FAILED` or `ERROR` line per test id, and no line of the implementation.

The main agent reaches `pair.sh` only through the typed `pair` tools, one per verb, named `mcp__plugin_gauntlet_pair__<verb>`. A slug and a revision are checked before anything runs.

## Setup

Install the kit as a plugin: `/plugin marketplace add ohshitgorillas/gauntlet`, then `/plugin install gauntlet@gauntlet`. The host needs `bubblewrap`, because every `Bash` call runs inside `bwrap`.

Then run `python3 scripts/init.py` once in the project. It writes `.claude/blind-reads.json` with all eight keys at their defaults, and creates the lane directories under `gauntlet_dir`. The keys and their defaults are:

- `tests_dir`: `tests`
- `gauntlet_dir`: `gauntlet`
- `docs_dir`: `docs`
- `target_branch`: `main`
- `gate_command`: `make check`
- `pytest_command`: `.venv/bin/pytest`
- `node_command`: `node --test`
- `extra_binds`: `[]`

`GAUNTLET=off claude` is the owner's switch. It silences `lanes.py`, `no-impl-reads.py` and the `Stop` gate for one session, and it is thrown on the shell that launches the session and nowhere else.

