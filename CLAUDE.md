# gauntlet — repository rules

This file is the repository's rule sheet. Procedure lives in the documents it names, read on demand; nothing here restates them.

## CHANGELOG

`CHANGELOG.md` records what a consumer of this repo sees change: the agent definitions, the lane hooks, the scripts, the documented block shapes and their fields — the things someone copying `.claude/` and `docs/` into their own project gets a different behavior from.

**Tests and test policy never go in it.** Not a test added, removed or rewritten, not a fixture or fake, not a change to how this repo tests itself. Nobody changelogs tests. An entry that would only matter to someone working inside this repo does not belong there at all.

`pair.sh`, `excision-diff.py` and the lane hooks do get entries: they are the product this repo ships, and a consumer copying `.claude/` gets a different behavior when they change.

An entry lands under `[Unreleased]` in the same commit as the change it describes, never in a sweep afterwards. Internal-only work skips the file entirely.

## The gates

Green means all nine, not just the first:

```
.venv/bin/pytest tests -q
python3 .claude/hooks/plans-lane.py --self-test
python3 .claude/hooks/specs-lane.py --self-test
python3 .claude/hooks/tests-lane.py --self-test
python3 .claude/hooks/reviews-lane.py --self-test
python3 .claude/hooks/verdicts-lane.py --self-test
python3 .claude/hooks/no-impl-reads.py --self-test
python3 scripts/excision-diff.py --self-test
python3 scripts/cite.py --self-test
```

Each `--self-test` prints one `PASS` or `FAIL` per rule that script exists to hold, and they cover cases the suite does not. A hook change that passes `pytest` and fails its own `--self-test` is exactly what this bar catches.

No linter is installed here. `ruff`, `black` and `eslint` appear in the agent definitions as instructions for the project those agents are copied into, not as a bar for this repo; do not run them here and do not add them to a report.

Inside a `.claude/worktrees/*` tree, run the suite as `PYTHONPATH=$(pwd) .venv/bin/pytest tests -q`, or it tests the parent checkout and tells you nothing about the tree you are in.

**The lane hooks stay on and unweakened.** They are the product, so disabling one to land a change ships the defect rather than hiding it. No matcher narrowed, no entry commented out, no `--self-test` left failing. A hook that fires where it should not is a bug to fix in the hook, reported as one.

## Markdown

Two gates hold every `.md` file in the repo, wired from `.claude/settings.local.json` and living in `scripts/gates/`:

- **Soft-wrapped.** One paragraph, list item or blockquote per logical line; wrapping is the reader's job. `scripts/gates/md-softwrap.py` blocks a hard-wrapped write, `--check FILE...` reports, `--fix FILE...` reflows.
- **No trivia.** Markdown states what holds now, not what happened: no dated approvals, no round or phase numbers used as positions in history, no corrections that narrate the mistake they fix, no prose whose only content is that something did not change. `scripts/gates/check_md_trivia.py` judges the lines a change adds — `--stop` at the end of a turn, `--head` for the last commit — and shipped prose is not re-litigated on every touch.

Standing reasons are not trivia and are not cut. "Why one writer" in `docs/approved-specs.md` says in present tense why a rule is the rule, and an agent that does not hold that reason weakens the rule the first time it is inconvenient.

The trivia gate calls the `claude` CLI once per turn that adds markdown, on Haiku, so it costs a few seconds and a small number of tokens; a turn that adds no markdown line makes no call.

Both gates are this repository's own, which is why they sit in `scripts/gates/` and are wired from `settings.local.json`. `.claude/hooks/` and `.claude/settings.json` are the kit a consumer copies, and nothing that only matters here goes in them.

## `tests/` is not yours

`.claude/settings.json:5-17` wires `specs-lane.py`, `plans-lane.py` and `tests-lane.py` session-wide, so they bind a session working **on** this repo exactly as they bind one using it. A write to `tests/` from the main agent comes back denied, in this repo, on this repo's own tests. That is the rule working, not a broken tool: a test here changes through an approved spec block and the `gauntlet-testsmith`, like any other.

## Commits

Prefixes in use: `spec:`, `test:`, `feat:`, `fix:`, `docs:`, `merge:`.

`spec: approved block for <x>` is load-bearing rather than cosmetic. The `gauntlet-testsmith` refuses a delta that names no newer `spec:` commit, so that commit is the evidence a changed test is allowed to change. Do not fold an approved block into a `feat:` or a `docs:` commit.

## Where a rule lives, and how it reads

State a rule once, in the file that owns it, and cite it from anywhere else that needs it:

- `docs/testing.md` — binding test policy, numbered. Rules never get renumbered; a new one goes at the end or takes a letter.
- `docs/approved-specs.md`, `docs/plans.md` — the two lane gates and their directories.
- `docs/agents.md` — the roster: what each agent sees, writes, and is hooked with.
- `docs/exemptions.md` — the `EXEMPT` register.
- `README.md` — the entry point and the shape of the chain.

Two prose registers, and an edit matches the file it lands in. `docs/testing.md` and the five agent definitions under `.claude/agents/` are caveman-compressed — clipped articles, fragments, dense. `README.md` and the rest of `docs/` are full English. Neither is a style to spread into the other.

`<project>`, `<source dir>`, `<live marker>` and their siblings are template placeholders, left unexpanded on purpose: the docs ship to be copied. Do not fill them in with this repo's own values.
