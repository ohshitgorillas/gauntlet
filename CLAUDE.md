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

It runs `pytest` on `tests/` under `coverage`, the `--self-test` of every hook and script that offers one, the `--check` of every gate under `scripts/gates/`, and the lint gates `ruff check`, `black --check`, `mypy hooks scripts`, `vulture` and `shellcheck` over the shell scripts, one after another under `nice -n 19 ionice -c3`. `scripts/gates/wiring/gates-wired.py` fails when a gate script exists that the array does not name, so the array is the list. It prints one `PASS` or `FAIL` line per gate with its wall time, saves each gate's output to `state/gates/<gate>.txt`, and exits 1 if any gate failed. Read a failing gate's output from that file rather than running the gate again.

Each `--self-test` prints one `PASS` or `FAIL` per rule that script exists to hold, and they cover cases the suite does not. A hook change that passes `pytest` and fails its own `--self-test` is exactly what this bar catches.

`ruff`, `black`, `mypy`, `vulture` and `coverage` live in `.venv/bin` and are configured in `pyproject.toml`; `shellcheck` is the host's. They are gates here, run through `check-gates.sh` like the rest. `eslint` appears in the agent definitions as an instruction for a project those agents are copied into and is not a bar for this repo. `mypy` runs on `hooks/` and `scripts/` only: the suite under `tests/` is untyped on purpose and is held by `ruff`'s `PT` rules instead. `vulture` holds the same two directories, and for a reason of its own: `tests/` keeps its own copies of kit constants and pytest reaches a class no line references, so a sweep there reports names that are alive.

Inside a `.claude/worktrees/*` tree, run that tree's own `scripts/gates/check-gates.sh`. It sets `PYTHONPATH` to the tree it sits in, because without it the suite tests the parent checkout and tells you nothing about the tree you are in.

**The lane hooks stay on and unweakened.** They are the product, so disabling one to land a change ships the defect rather than hiding it. No matcher narrowed, no entry commented out, no `--self-test` left failing. A hook that fires where it should not is a bug to fix in the hook, reported as one.

`GAUNTLET=off` does not touch that rule, and the distinction is the whole of it. The switch is the owner's, thrown on the shell that launches the session, good for that session and recorded nowhere on disk. Weakening a hook in the tree is still forbidden, a `--self-test` left failing is still a defect, and neither becomes legal because an off switch exists. An agent may not propose the switch, set it, or suggest the owner set it — that rule has no exception. No hook reads a shell command, so nothing holds the switch inside the session but this rule.

## No hook reads a shell command

No hook decides a `Bash` call by parsing its text. A reading of a command string is undecidable — an env prefix, a here-document, a command substitution, a function, an `xargs` — and a list of spellings leaves the next spelling open. `bwrap-wrap.py` carries the text into the wrap byte for byte and reads nothing in it; what holds a shell is the mount table it sees, chosen by the caller's `agent_type`. An agent whose shell would need a reading to hold holds no `Bash`. A carve-out from the wrap by command text is a reading, and there is none.

## Markdown

Two gates hold every `.md` file in the repo, one this repository's own and one installed:

- **Soft-wrapped.** One paragraph, list item or blockquote per logical line; wrapping is the reader's job. `scripts/gates/code/md-softwrap.py` blocks a hard-wrapped write, `--check FILE...` reports, `--fix FILE...` reflows. It is wired from `.claude/settings.local.json`.
- **No trivia.** Markdown states what holds now, not what happened: no dated approvals, no round or phase numbers used as positions in history, no corrections that narrate the mistake they fix, no prose whose only content is that something did not change. The `triviajudge` plugin judges the lines a change adds at the end of a turn, and shipped prose is not re-litigated on every touch. This repository carries no trivia gate of its own; install the plugin from `~/dev/triviajudge` with `/plugin`.

Standing reasons are not trivia and are not cut. "Why one writer" in `docs/approved-specs.md` says in present tense why a rule is the rule, and an agent that does not hold that reason weakens the rule the first time it is inconvenient.

The plugin's markdown judge calls the `claude` CLI once per turn that adds markdown, on Haiku, so it costs a few seconds and a small number of tokens; a turn that adds no markdown line makes no call.

`md-softwrap.py` is this repository's own, which is why it sits in `scripts/gates/` and is wired from `settings.local.json`. `hooks/`, `agents/` and `.claude-plugin/plugin.json` are the kit a consumer installs, and nothing that only matters here goes in them. `.claude/settings.json` is not kit and stays empty: a lane wired there beside the manifest fires twice and denies one call twice.

## `tests/` is not yours

`.claude-plugin/plugin.json:12-20` wires `lanes.py` session-wide, and the tests row is one of its five lanes, so it binds a session working **on** this repo exactly as it binds one using it. A write to `tests/` from the main agent comes back denied, in this repo, on this repo's own tests. That is the rule working, not a broken tool: a test here changes through an approved spec block and the `scrivener`, like any other. Under `GAUNTLET=off` the enforcement lapses and the write is allowed; the discipline does not lapse with it, because a test that changes outside an approved spec block is an unpinned test whoever was watching.

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

Two prose registers, and an edit matches the file it lands in. `docs/testing.md` and the eight agent definitions under `agents/` are caveman-compressed — clipped articles, fragments, dense. `README.md` and the rest of `docs/` are full English. Neither is a style to spread into the other.

`<project>`, `<source dir>`, `<live marker>` and their siblings are template placeholders, left unexpanded on purpose: the docs ship to be copied. Do not fill them in with this repo's own values.
