# gauntlet — repository rules

This file is the repository's rule sheet. Procedure lives in the documents it names, read on demand; nothing here restates them.

## The chain is the owner's to invoke

Whether a task goes through the chain is the owner's call, task by task. An order to work outside it is followed and not argued with, not re-raised later in the session, and not answered with the reason the chain exists. The kit protects an established codebase from shipping a bug, which `README.md` says is what it is for, and the owner is who judges when that is the risk at hand.

## CHANGELOG

`CHANGELOG.md` records what a consumer of this repo sees change: the agent definitions, the lane hooks, the scripts, the documented block shapes and their fields — the things a project that installs this kit as a plugin, and reads `docs/`, gets a different behavior from.

**Tests and test policy never go in it.** Not a test added, removed or rewritten, not a fixture or fake, not a change to how this repo tests itself. Nobody changelogs tests. An entry that would only matter to someone working inside this repo does not belong there at all.

`pair.sh`, `strike-diff.py` and the lane hooks do get entries: they are the product this repo ships, and a consumer running the installed plugin gets a different behavior when they change.

An entry lands under `[Unreleased]` in the same commit as the change it describes, never in a sweep afterwards. Internal-only work skips the file entirely.

## The gates

Green means every gate passes, not just the first. One command runs them:

```
scripts/gates/check-gates.sh
```

It runs `pytest` on `tests/` and the `--self-test` of `plans-lane.py`, `specs-lane.py`, `tests-lane.py`, `reviews-lane.py`, `verdicts-lane.py`, `no-impl-reads.py`, `blind-bash.py`, `gauntlet-off.py`, `bwrap-wrap.py`, `pair-passthrough.py`, `strike-diff.py`, `pair/cli.py`, `cite.py` and `symbol-closure.py`, one after another under `nice -n 19 ionice -c3`. It prints one `PASS` or `FAIL` line per gate with its wall time, saves each gate's output to `state/gates/<gate>.txt`, and exits 1 if any gate failed. Read a failing gate's output from that file rather than running the gate again.

Each `--self-test` prints one `PASS` or `FAIL` per rule that script exists to hold, and they cover cases the suite does not. A hook change that passes `pytest` and fails its own `--self-test` is exactly what this bar catches.

No linter is installed here. `ruff`, `black` and `eslint` appear in the agent definitions as instructions for the project those agents are copied into, not as a bar for this repo; do not run them here and do not add them to a report.

Inside a `.claude/worktrees/*` tree, run that tree's own `scripts/gates/check-gates.sh`. It sets `PYTHONPATH` to the tree it sits in, because without it the suite tests the parent checkout and tells you nothing about the tree you are in.

**The lane hooks stay on and unweakened.** They are the product, so disabling one to land a change ships the defect rather than hiding it. No matcher narrowed, no entry commented out, no `--self-test` left failing. A hook that fires where it should not is a bug to fix in the hook, reported as one.

`GAUNTLET=off` does not touch that rule, and the distinction is the whole of it. The switch is the owner's, thrown on the shell that launches the session, good for that session and recorded nowhere on disk. Weakening a hook in the tree is still forbidden, a `--self-test` left failing is still a defect, and neither becomes legal because an off switch exists. An agent may not propose the switch, set it, or suggest the owner set it — that rule has no exception, and `gauntlet-off.py --bash` denies a `GAUNTLET=` assignment and a nested `claude` invocation to keep the switch out of reach of the session it governs.

## Markdown

Two gates hold every `.md` file in the repo, one this repository's own and one installed:

- **Soft-wrapped.** One paragraph, list item or blockquote per logical line; wrapping is the reader's job. `scripts/gates/md-softwrap.py` blocks a hard-wrapped write, `--check FILE...` reports, `--fix FILE...` reflows. It is wired from `.claude/settings.local.json`.
- **No trivia.** Markdown states what holds now, not what happened: no dated approvals, no round or phase numbers used as positions in history, no corrections that narrate the mistake they fix, no prose whose only content is that something did not change. The `triviajudge` plugin judges the lines a change adds at the end of a turn, and shipped prose is not re-litigated on every touch. This repository carries no trivia gate of its own; install the plugin from `~/dev/triviajudge` with `/plugin`.

Standing reasons are not trivia and are not cut. "Why one writer" in `docs/approved-specs.md` says in present tense why a rule is the rule, and an agent that does not hold that reason weakens the rule the first time it is inconvenient.

The plugin's markdown judge calls the `claude` CLI once per turn that adds markdown, on Haiku, so it costs a few seconds and a small number of tokens; a turn that adds no markdown line makes no call.

`md-softwrap.py` is this repository's own, which is why it sits in `scripts/gates/` and is wired from `settings.local.json`. `hooks/`, `agents/` and `.claude-plugin/plugin.json` are the kit a consumer installs, and nothing that only matters here goes in them. `.claude/settings.json` is not kit and stays empty: a lane wired there beside the manifest fires twice and denies one call twice.

## `tests/` is not yours

`.claude-plugin/plugin.json:15-26` wires `specs-lane.py`, `plans-lane.py` and `tests-lane.py` session-wide, so they bind a session working **on** this repo exactly as they bind one using it. A write to `tests/` from the main agent comes back denied, in this repo, on this repo's own tests. That is the rule working, not a broken tool: a test here changes through an approved spec block and the `scrivener`, like any other. Under `GAUNTLET=off` the enforcement lapses and the write is allowed; the discipline does not lapse with it, because a test that changes outside an approved spec block is an unpinned test whoever was watching.

## Commits

Prefixes in use: `spec:`, `test:`, `feat:`, `fix:`, `docs:`, `merge:`.

`spec: approved block for <x>` is load-bearing rather than cosmetic. The `scrivener` refuses a delta that names no newer `spec:` commit, so that commit is the evidence a changed test is allowed to change. Do not fold an approved block into a `feat:` or a `docs:` commit.

## Where a rule lives, and how it reads

State a rule once, in the file that owns it, and cite it from anywhere else that needs it:

- `docs/testing.md` — binding test policy, numbered. Rules never get renumbered; a new one goes at the end or takes a letter.
- `docs/approved-specs.md`, `docs/plans.md` — the two lane gates and their directories.
- `docs/agents.md` — the roster: what each agent sees, writes, and is hooked with.
- `docs/exemptions.md` — the `EXEMPT` register.
- `README.md` — the entry point and the shape of the chain.

Two prose registers, and an edit matches the file it lands in. `docs/testing.md` and the five agent definitions under `agents/` are caveman-compressed — clipped articles, fragments, dense. `README.md` and the rest of `docs/` are full English. Neither is a style to spread into the other.

`<project>`, `<source dir>`, `<live marker>` and their siblings are template placeholders, left unexpanded on purpose: the docs ship to be copied. Do not fill them in with this repo's own values.
