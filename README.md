# Gauntlet

Gauntlet is a set of six subagents that surround the main agent, built around two blind reviewers:

1. An adversarial plan reviewer (`prosecutor`)
2. A discovery locator for plans (`detective`)
3. A blind adversarial spec reviewer (`arbiter`)
4. A measurement agent (`examiner`)
5. A blind test writer (`scrivener`)
6. A blind juror for the red run (`juror`)

"Blind" in this instance means that those agents are forbidden from reading, and therefore making judgment calls based on, implementation.

Together, they ensure that agents are kept in line, honest, and incapable of de-fanging your testing suite. Nothing writes to `<tests dir>/` except the `scrivener`, which takes instructions only from the `arbiter` — and neither can read source code, so tests are grounded in behavior, not implementation, and never patched to pass after the fact.

Gauntlet works best with existing, established codebases for which shipping bugs has real consequences. Budding projects are better served by lighter, less restricted workflows.

## Workflow

The workflow enforced by Gauntlet is, as its name implies, quite brutal:

1. You supply an agent with a brief: the problem to solve or feature to add.
2. The main agent sends its discovery questions, all of them, to one `detective`, which returns a `file:line` table and nothing else.
3. The main agent drafts a plan on those pointers and provides it to a `prosecutor`.
4. The `prosecutor` checks the drafted plan for mistakes, errors, inconsistencies, and resolves the plan's citations against the tree to return a pass or fail per check. It may also return a refusal to rule if the main agent is caught trying to game its context or evades a posed question. Any questions the agents cannot answer are escalated to you, who then approves the plan only on a pass. On `READY`, it writes the approved plan to `<gauntlet dir>/plans/approved/`, a folder only it can write to, so a later stage reads the plan from disk rather than inheriting it — the shape is in `docs/plans.md`. Where implementation later settles a value the plan estimated, the plan takes an amendment round rather than a redraft: the amendment carries the command that produced the value, the checks re-run on the amended lines alone, and the reviewer rewrites the file.
5. The main agent drafts a testing spec block. Where a `bite:` value needs a script or a rendered state space, the `examiner` measures it.
6. The main agent supplies its spec block to a `arbiter`.
7. The `arbiter` runs its checks blind: it cannot read the implementation. It evaluates the spec block based on its merits alone and returns verdicts per test proposal. It may also outright refuse the prompt on steering or evasion attempts by the main agent. On `READY`, it sends the approved specs to `<gauntlet dir>/specs/approved/`, a folder only it can write to.
8. The `scrivener`, also blind to implementation, takes its orders only from `<gauntlet dir>/specs/approved/`. A line it cannot test goes back to the `arbiter` instead of getting a weak test; a test that passes against no implementation sends the block back to the main agent for a new spec.
9. Both the `scrivener` and the main agent work concurrently in different branches, the latter on implementation.
10. The tests run red in the `scrivener`'s tree, and green in the implementation branch.
11. A `juror`, blind and spawned fresh for that one run, reads the red run's output against the approved block and returns one verdict per behavior line — `RED`, `ERROR`, `GREEN` or `INVALID`. It writes them to `<gauntlet dir>/verdicts/<slug>.txt`, a folder only it can write to, so the main agent, which has read the code, cannot rule on whether its own tests bit. A turn that leaves a red run unruled does not end: the `Stop` hook names the slug.
12. The main agent has two approaches to a test failing against implementation: fix the code, or send a revised spec back to the `arbiter` for approval. The `scrivener` will refuse any direct attempts by the main agent to weaken the tests to pass at this phase.
13. Once the test suite is green against implementation, the change merges.
14. A `bailiff`, blind and spawned fresh, checks the landed tests against the approved block; a test that no longer matches gets restored from the red commit, or the spec goes back to the main agent. It holds none of the reasons the block was passed, so a softened assertion cannot reach it as permission.

## The approval word

Three points in the chain stop for you: the plan, on `READY` from the `prosecutor`; the spec block, on `READY` from the `arbiter`; and the start of implementation. Each is opened by one word and nothing else.

A message whose first line is exactly `approved` opens the gate it answers. A message whose first line is exactly `approved with revision` opens it too, and everything below that line is an amendment the main agent applies before the work starts. Case is ignored, spelling is not: a misspelling is not the word.

The word anywhere but that first line is not approval — mid-sentence, inside a quotation, inside a pasted block. Neither is "looks good", "yep", "ship it", or silence. A paste that happens to contain the word cannot open a gate, because position, not judgment, is what the main agent checks.

One word opens one artifact as it stands. A plan or a block redrafted after it was approved needs a new one, or an approval slides forward over text you never read. An amendment you supply is your own words and carries itself; a redraft the main agent makes on top of it does not.

An amendment round on an approved plan rewrites the file, so the rewritten plan takes its own word before implementation continues on it. The reviewer blocks beneath it are kept in order, so the text your first word covered is still there to read.

Anything ambiguous holds. The cost of that default is one more line from you, which is cheaper than a stage entered on a sentence that only read like consent.

No hook enforces this, the same gap `docs/exemptions.md` states for the `EXEMPT` register: the word arrives in a message, and a `PreToolUse` matcher sees tool calls. The rule is what the main agent holds, not what the tree makes impossible.

## The tests-only lane

A change confined to `<tests dir>/` does not pay implementation prices. Bring a failing test that violates `docs/testing.md` — a wall-clock wait, a hostname, an assertion copied out of the source — and the chain is four steps, not fourteen:

1. The main agent drafts a `motion: strike` block (the test goes), a `motion: amend` block (the test goes, and one line names the behavior that replaces it), or a `motion: rehome` block (the assertion survives byte-identical while what surrounds it moves, to another file or in place). A strike line cites the rule the test breaks, or — where the test breaks none and the behavior it pins is one the owner dropped — quotes the owner's sentence that dropped it. A rehome line cites neither: it names the fact outside the test directory that moved.
2. The `arbiter` reviews it against the test file, which it is allowed to read, and writes `<gauntlet dir>/specs/approved/<slug>.txt` on `READY`.
3. The `scrivener` removes the targets and writes the replacements.
4. `${CLAUDE_PLUGIN_ROOT}/scripts/strike-diff.py` checks the landed diff against the approved block at merge.

No plan gate, no red run, no juror, no post-merge review round. The `Stop` hook fires on a red run that exists and never on the absence of one, so it stays silent here. Those three exist to police an implementation phase, and a tests-only change has none. What still holds is the part that matters: the main agent never writes `<tests dir>/`, and never decides on its own that a test it finds inconvenient pins nothing.

A brief that puts `<tests dir>/` in scope names the structure line the change takes: `motion: strike`, `motion: amend`, `motion: rehome`, or a `kind:` block through the full chain. A brief that cannot name one is not ready to put tests in scope. The route is the decision, and a brief that leaves it to the agent holding the file is how a test gets edited in place.

See `docs/agents.md` for what each agent is allowed to see and write, and `docs/approved-specs.md` for the hook that makes step 7 and step 8 a fact on disk rather than a step that happened somewhere in the transcript.

## Setup

Install the kit as a plugin. `.claude-plugin/marketplace.json` at the root of this repository declares it, so `/plugin marketplace add ohshitgorillas/gauntlet` and then `/plugin install gauntlet@gauntlet` puts it in front of a project without copying anything into it; `/plugin marketplace add <path to a clone>` does the same from disk. `agents/` is found by convention, and `.claude-plugin/plugin.json` carries the hook wiring inline rather than leaving it to the project's `.claude/settings.json` — a consumer's `settings.json` stays the consumer's. The manifest wires `lanes.py` session-wide, one hook holding all five lanes as rows, so it binds the main agent and every subagent, and wires `lanes.py --stop` as a `Stop` hook, which blocks a turn that leaves a red run unruled; `no-impl-reads.py` and `blind-bash.py` are wired session-wide beside it and gated on the caller instead, each judging the agents in its own `BLIND` tuple and letting every other caller through unjudged — see `docs/approved-specs.md` for why no agent definition wires a hook of its own. `bwrap-wrap.py` is wired on `Bash` beside `blind-bash.py`, which is where the kit's one dependency outside Python lands: every command that is not carved out runs inside `bwrap`, so a consumer installing this plugin needs `bubblewrap` on the host, and a `Bash` call is denied with a named reason where the binary is absent or cannot run there. `lane-audit.py` is wired `PostToolUse` on the three write tools: it asks the lane table about the file the harness reports as changed, and prints one named line where a write the table refuses was admitted and landed — an audit of the lane's path comparison, which never blocks and never decides anything. `gauntlet-off.py` is wired beside them on three events, and carries the owner's switch: `GAUNTLET=off claude` starts one session with `lanes.py`, `no-impl-reads.py`, `blind-bash.py` and the `Stop` gate silent, which is how the owner works outside the chain — repairing a lane file, demoing the kit, working on the hooks themselves — without weakening a hook in the tree. It is thrown on the shell that launches the session and nowhere else: inside a session with the gauntlet on, `gauntlet-off.py --bash` denies a `GAUNTLET=` assignment and a nested `claude` invocation, and an agent may never propose the switch. Every claim below about a lane denying a write is a claim about a session with the gauntlet on. Each command names `${CLAUDE_PLUGIN_ROOT}`, the installed plugin's own root, so nothing in the wiring depends on where the project sits. An earlier release told a consumer to copy `.claude/` instead: a project that did, and then installs the plugin, wires every lane twice and gets two denials for one call, so those entries come out of `.claude/settings.json` at install. After installing, check the lanes from a clone:

```
python3 hooks/lanes.py --self-test
python3 hooks/no-impl-reads.py --self-test
python3 hooks/blind-bash.py --self-test
python3 hooks/gauntlet-off.py --self-test
python3 hooks/bwrap-wrap.py --self-test
python3 hooks/lane-audit.py --self-test
python3 hooks/pair-passthrough.py --self-test
python3 scripts/strike-diff.py --self-test
python3 scripts/cite.py --self-test
python3 scripts/init.py --self-test
```

Each prints one `PASS` or `FAIL` per line it exists to hold. A `FAIL` means the lane is not binding, and the gate it enforces is not there.

`.claude/blind-reads.json` is what a project writes down for the kit, and `python3 scripts/init.py` writes it: one deliberate step at install, which also creates the lane skeleton under `gauntlet_dir`. It is required. A file that is there and parses is the project's word, and `{}` is a word like any other — it asks for the values below and gets them; an absent or malformed file is a fault, denied by every hook and exited non-zero by the reader, with the path named. It carries three directories. `tests_dir` is the blind writer's lane, `tests` by default, and what `<tests dir>` means wherever the agent definitions say it. `gauntlet_dir` is where the chain's artifacts live, `gauntlet` by default, and what `<gauntlet dir>` means wherever a definition or a doc says it. `docs_dir` is the prose a blind agent may read, `docs` by default. The structure under `gauntlet_dir` is not a project's to move: the four lanes are always `specs/approved`, `plans/approved`, `reviews` and `verdicts` beneath it. It carries four more keys beside the directories: `target_branch` and `gate_command`, the branch a finished pair lands on and the command that has to pass before it does, `main` and `make check` by default; and `pytest_command` and `node_command`, the invocations `scripts/blind.sh test` and `${CLAUDE_PLUGIN_ROOT}/scripts/pair.sh red` run, `.venv/bin/pytest` and `node --test` by default. The eighth key is `unwrapped_commands`, the project's own word about which commands run outside the sandbox: a mapping from the exact command text to the paths that command reads, empty by default. A command runs unwrapped only where the declaration carries its whole text as typed, and every path under its `reads` is bound read-only inside every wrapped profile, so no wrapped shell can rewrite the input of the one command that runs outside the wrap. A `reads` path that does not resolve in the checkout voids that declaration and the command is wrapped like any other, rather than leaving the project holding a guarantee the mount table does not make. The ninth key is `extra_binds`, a list of paths the project wants writable inside a wrapped shell on top of the checkout, empty by default: a package cache, a build cache or a scratch tree that sits outside the checkout. Every path outside the checkout is readable already, so the key adds only write access, and it adds it to the author's profile and not to a blind reviewer's. An entry is dropped, silently and on its own, where it is not absolute, where its source is not live, or where it stands over a path the profile protects — the masks over `/run/user` and `/tmp`, the `/dev` and `/proc` mounts, `~/.gitconfig`, and the checkout or any worktree, from either side. A malformed list voids the whole key, as a malformed `unwrapped_commands` does, and a path outside every checkout is in no lane, so the project's word is the only thing holding it.

Every hook and every script reads those through one reader, `python3 hooks/shell_shapes.py --config <key>`, which answers the nine keys and the four derived lanes — `specs_lane`, `plans_lane`, `reviews_lane`, `verdicts_lane` — and is also how to see what a project's copy resolved to. `no-impl-reads.py` lets a blind agent read the file itself, since its definition names those directories only as `<tests dir>` and `<docs dir>`.

The three names must be usable and pairwise disjoint: each repo-relative and normalized, none of them the root, absolute or walking out, and none equal to, under, or over another. A set that fails any of those moves nothing — every key falls back to its default together, rather than half a layout being applied. Per-key fallback would not be safe here: `tests_dir` naming `docs` is legal read alone and collides the moment the default `docs_dir` fills in, which would put the writer's lane over the prose it reads.

Nothing else is in the file: the lint gates are `ruff`, `black` and `eslint` (each skipped where not installed), and the agent names are the kit, copied verbatim. A project with another runner names it as `pytest_command` or `node_command` rather than editing the two scripts.
