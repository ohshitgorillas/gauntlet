# Gauntlet

Gauntlet is a set of six subagents that surround the main agent, built around two blind reviewers:

1. An adversarial plan reviewer (`gauntlet-prosecutor`)
2. A discovery locator for plans (`gauntlet-detective`)
3. A blind adversarial spec reviewer (`gauntlet-arbiter`)
4. A measurement agent (`gauntlet-examiner`)
5. A blind test writer (`gauntlet-scrivener`)
6. A blind juror for the red run (`gauntlet-juror`)

"Blind" in this instance means that those agents are forbidden from reading, and therefore making judgment calls based on, implementation.

Together, they ensure that agents are kept in line, honest, and incapable of de-fanging your testing suite. Nothing writes to `<tests dir>/` except the `gauntlet-scrivener`, which takes instructions only from the `gauntlet-arbiter` — and neither can read source code, so tests are grounded in behavior, not implementation, and never patched to pass after the fact.

Gauntlet works best with existing codebases. The `gauntlet-scrivener` writes pytest and `node --test` tests; other stacks are not supported yet.

## Workflow

The workflow enforced by Gauntlet is, as its name implies, quite brutal:

1. You supply an agent with a brief: the problem to solve or feature to add.
2. The main agent sends its discovery questions, all of them, to one `gauntlet-detective`, which returns a `file:line` table and nothing else.
3. The main agent drafts a plan on those pointers and provides it to a `gauntlet-prosecutor`.
4. The `gauntlet-prosecutor` checks the drafted plan for mistakes, errors, inconsistencies, and resolves the plan's citations against the tree to return a pass or fail per check. It may also return a refusal to rule if the main agent is caught trying to game its context or evades a posed question. Any questions the agents cannot answer are escalated to you, who then approves the plan only on a pass. On `READY`, it writes the approved plan to `<gauntlet dir>/plans/approved/`, a folder only it can write to, so a later stage reads the plan from disk rather than inheriting it — the shape is in `docs/plans.md`. Where implementation later settles a value the plan estimated, the plan takes an amendment round rather than a redraft: the amendment carries the command that produced the value, the checks re-run on the amended lines alone, and the reviewer rewrites the file.
5. The main agent drafts a testing spec block. Where a `bite:` value needs a script or a rendered state space, the `gauntlet-examiner` measures it.
6. The main agent supplies its spec block to a `gauntlet-arbiter`.
7. The `gauntlet-arbiter` runs its checks blind: it cannot read the implementation. It evaluates the spec block based on its merits alone and returns verdicts per test proposal. It may also outright refuse the prompt on steering or evasion attempts by the main agent. On `READY`, it sends the approved specs to `<gauntlet dir>/specs/approved/`, a folder only it can write to.
8. The `gauntlet-scrivener`, also blind to implementation, takes its orders only from `<gauntlet dir>/specs/approved/`. A line it cannot test goes back to the `gauntlet-arbiter` instead of getting a weak test; a test that passes against no implementation sends the block back to the main agent for a new spec.
9. Both the `gauntlet-scrivener` and the main agent work concurrently in different branches, the latter on implementation.
10. The tests run red in the `gauntlet-scrivener`'s tree, and green in the implementation branch.
11. A `gauntlet-juror`, blind and spawned fresh for that one run, reads the red run's output against the approved block and returns one verdict per behavior line — `RED`, `ERROR`, `GREEN` or `INVALID`. It writes them to `<gauntlet dir>/verdicts/<slug>.txt`, a folder only it can write to, so the main agent, which has read the code, cannot rule on whether its own tests bit. A turn that leaves a red run unruled does not end: the `Stop` hook names the slug.
12. The main agent has two approaches to a test failing against implementation: fix the code, or send a revised spec back to the `gauntlet-arbiter` for approval. The `gauntlet-scrivener` will refuse any direct attempts by the main agent to weaken the tests to pass at this phase.
13. Once the test suite is green against implementation, the change merges.
14. A `gauntlet-bailiff`, blind and spawned fresh, checks the landed tests against the approved block; a test that no longer matches gets restored from the red commit, or the spec goes back to the main agent. It holds none of the reasons the block was passed, so a softened assertion cannot reach it as permission.

## The approval word

Three points in the chain stop for you: the plan, on `READY` from the `gauntlet-prosecutor`; the spec block, on `READY` from the `gauntlet-arbiter`; and the start of implementation. Each is opened by one word and nothing else.

A message whose first line is exactly `approved` opens the gate it answers. A message whose first line is exactly `approved with revision` opens it too, and everything below that line is an amendment the main agent applies before the work starts. Case is ignored, spelling is not: a misspelling is not the word.

The word anywhere but that first line is not approval — mid-sentence, inside a quotation, inside a pasted block. Neither is "looks good", "yep", "ship it", or silence. A paste that happens to contain the word cannot open a gate, because position, not judgment, is what the main agent checks.

One word opens one artifact as it stands. A plan or a block redrafted after it was approved needs a new one, or an approval slides forward over text you never read. An amendment you supply is your own words and carries itself; a redraft the main agent makes on top of it does not.

An amendment round on an approved plan rewrites the file, so the rewritten plan takes its own word before implementation continues on it. The reviewer blocks beneath it are kept in order, so the text your first word covered is still there to read.

Anything ambiguous holds. The cost of that default is one more line from you, which is cheaper than a stage entered on a sentence that only read like consent.

No hook enforces this, the same gap `docs/exemptions.md` states for the `EXEMPT` register: the word arrives in a message, and a `PreToolUse` matcher sees tool calls. The rule is what the main agent holds, not what the tree makes impossible.

## The tests-only lane

A change confined to `<tests dir>/` does not pay implementation prices. Bring a failing test that violates `docs/testing.md` — a wall-clock wait, a hostname, an assertion copied out of the source — and the chain is four steps, not fourteen:

1. The main agent drafts a `motion: strike` block (the test goes) or a `kind: repair` block (the test goes, and one line names the behavior that replaces it). A strike line cites the rule the test breaks, or — where the test breaks none and the behavior it pins is one the owner dropped — quotes the owner's sentence that dropped it.
2. The `gauntlet-arbiter` reviews it against the test file, which it is allowed to read, and writes `<gauntlet dir>/specs/approved/<slug>.txt` on `READY`.
3. The `gauntlet-scrivener` removes the targets and writes the replacements.
4. `scripts/strike-diff.py` checks the landed diff against the approved block at merge.

No plan gate, no red run, no juror, no post-merge review round. The `Stop` hook fires on a red run that exists and never on the absence of one, so it stays silent here. Those three exist to police an implementation phase, and a tests-only change has none. What still holds is the part that matters: the main agent never writes `<tests dir>/`, and never decides on its own that a test it finds inconvenient pins nothing.

See `docs/agents.md` for what each agent is allowed to see and write, and `docs/approved-specs.md` for the hook that makes step 7 and step 8 a fact on disk rather than a step that happened somewhere in the transcript.

## Setup

Clone this repository and copy its `.claude/` directory (agents, hooks, and `settings.json`) into the target project. `.claude/settings.json` wires `plans-lane.py`, `specs-lane.py`, `tests-lane.py`, `reviews-lane.py` and `verdicts-lane.py` session-wide, so they bind the main agent and every subagent, and wires `verdicts-lane.py --stop` as a `Stop` hook, which blocks a turn that leaves a red run unruled; `no-impl-reads.py` is wired only per-agent, from the `hooks:` frontmatter of `gauntlet-arbiter.md`, `gauntlet-scrivener.md`, `gauntlet-juror.md` and `gauntlet-bailiff.md` — see `docs/approved-specs.md` for why. `gauntlet-off.py` is wired beside them on three events, and carries the owner's switch: `GAUNTLET=off claude` starts one session with the seven lane hooks and the `Stop` gate silent, which is how the owner works outside the chain — repairing a lane file, demoing the kit, working on the hooks themselves — without weakening a hook in the tree. It is thrown on the shell that launches the session and nowhere else: inside a session with the gauntlet on, `gauntlet-off.py --bash` denies a `GAUNTLET=` assignment and a nested `claude` invocation, and an agent may never propose the switch. Every claim below about a lane denying a write is a claim about a session with the gauntlet on. After copying, check the lanes:

```
python3 .claude/hooks/plans-lane.py --self-test
python3 .claude/hooks/specs-lane.py --self-test
python3 .claude/hooks/tests-lane.py --self-test
python3 .claude/hooks/reviews-lane.py --self-test
python3 .claude/hooks/verdicts-lane.py --self-test
python3 .claude/hooks/no-impl-reads.py --self-test
python3 .claude/hooks/blind-bash.py --self-test
python3 .claude/hooks/gauntlet-off.py --self-test
python3 scripts/strike-diff.py --self-test
python3 scripts/cite.py --self-test
```

Each prints one `PASS` or `FAIL` per line it exists to hold. A `FAIL` means the lane is not binding, and the gate it enforces is not there.

`.claude/hooks/blind-reads.json` is what a project writes down for the kit, and it carries three directories. `tests_dir` is the blind writer's lane, `tests` by default, and what `<tests dir>` means wherever the agent definitions say it. `gauntlet_dir` is where the chain's artifacts live, `gauntlet` by default, and what `<gauntlet dir>` means wherever a definition or a doc says it. `docs_dir` is the prose a blind agent may read, `docs` by default. The structure under `gauntlet_dir` is not a project's to move: the four lanes are always `specs/approved`, `plans/approved`, `reviews` and `verdicts` beneath it. It carries four more keys beside the directories: `target_branch` and `gate_command`, the branch a finished pair lands on and the command that has to pass before it does, `main` and `make check` by default; and `pytest_command` and `node_command`, the invocations `scripts/blind.sh test` and `scripts/pair.sh red` run, `.venv/bin/pytest` and `node --test` by default.

Every hook and every script reads those through one reader, `python3 .claude/hooks/shell_shapes.py --config <key>`, which answers the three keys and the four derived lanes — `specs_lane`, `plans_lane`, `reviews_lane`, `verdicts_lane` — and is also how to see what a project's copy resolved to. `no-impl-reads.py` lets a blind agent read the file itself, since its definition names those directories only as `<tests dir>` and `<docs dir>`.

The three names must be usable and pairwise disjoint: each repo-relative and normalized, none of them the root, absolute or walking out, and none equal to, under, or over another. A set that fails any of those moves nothing — every key falls back to its default together, rather than half a layout being applied. Per-key fallback would not be safe here: `tests_dir` naming `docs` is legal read alone and collides the moment the default `docs_dir` fills in, which would put the writer's lane over the prose it reads.

Nothing else is in the file: the runners are `.venv/bin/pytest` and `node --test` in the two scripts, the lint gates are `ruff`, `black` and `eslint` (each skipped where not installed), and the agent names are the kit, copied verbatim. A project with another runner edits the script.
