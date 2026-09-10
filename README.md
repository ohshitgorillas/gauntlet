# Gauntlet

Gauntlet is a set of five agents built around two blind reviewers:

1. An adversarial plan reviewer (`prosecutor`)
2. A grounding locator for plans (`detective`)
3. A blind adversarial spec reviewer (`arbiter`)
4. A measurement agent (`accountant`)
5. A blind test writer (`testsmith`)

"Blind" in this instance means that those agents are forbidden from reading, and therefore making judgment calls based on, implementation.

Together, they ensure that agents are kept in line, honest, and incapable of de-fanging your testing suite. Agents cannot write to `tests/` except through the Testsmith, who takes instructions only from the Arbiter — and neither can read source code, so tests are grounded in behavior, not implementation, and never patched to pass after the fact.

Gauntlet works best with existing codebases.

## Workflow

The workflow enforced by Gauntlet is, as its name implies, quite brutal:

1. You supply an agent with a brief: the problem to solve or feature to add.
2. The orchestrator drafts a plan and sends its grounding questions to a `detective`.
3. The agent drafts a plan and provides it to a `prosecutor`.
4. The `prosecutor` checks the drafted plan for mistakes, errors, inconsistencies, and resolves the plan's citations against the tree to return a pass or fail per check. It may also return a refusal to rule if the orchestrator is caught trying to game its context or evades a posed question. Any questions the agents cannot answer are escalated to you, who then approves the plan only on a pass.
5. The orchestrator drafts a testing spec block. Where a `bite:` value needs a script or a rendered state space, the `accountant` measures it.
6. The agent supplies its spec block to an `arbiter`.
7. The `arbiter` runs its checks blind: it cannot read the implementation. It evaluates the spec block based on its merits alone and returns verdicts per test proposal. It may also outright refuse the prompt on steering or evasion attempts by the orchestrator. On `READY`, it sends the approved specs to `specs/approved/`, a folder only it can write to.
8. The `testsmith`, also blind to implementation, takes its orders only from `specs/approved/`. A line it cannot test goes back to the `arbiter` instead of getting a weak test; a test that passes against no implementation sends the block back to the orchestrator for a new spec.
9. Both testsmith and orchestrator work concurrently in different branches, the latter on implementation.
10. The tests run red in the `testsmith`'s tree, and green in the implementation branch.
11. The orchestrator has two approaches to a test failing against implementation: fix the code, or send a revised spec back to the `arbiter` for approval. The `testsmith` will refuse any direct attempts by the orchestrator to weaken the tests to pass at this phase.
12. Once the test suite is green against implementation, the change merges. 
13. The `arbiter` checks the landed tests against the block it approved; a test that no longer matches gets restored from the red commit, or the spec goes back to the orchestrator.

See `docs/agents.md` for what each agent is allowed to see and write, and `docs/approved-specs.md` for the hook that makes step 5 and step 6 a fact on disk rather than a step that happened somewhere in the transcript.

## Setup

Copy `.claude/` (agents, hooks, and `settings.json`) into the target project. `.claude/settings.json` wires `specs-lane.py`, `tests-lane.py` and `reviews-lane.py` session-wide, so they bind the orchestrator and every subagent; `no-impl-reads.py` is wired only per-agent, from the `hooks:` frontmatter of `arbiter.md` and `testsmith.md` — see `docs/approved-specs.md` for why. After copying, check the lanes:

```
python3 .claude/hooks/specs-lane.py --self-test
python3 .claude/hooks/tests-lane.py --self-test
python3 .claude/hooks/reviews-lane.py --self-test
python3 .claude/hooks/no-impl-reads.py --self-test
