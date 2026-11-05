# Gauntlet

## What This Is

Gauntlet is an Archon workflow pack that takes a task from the owner's idea to a landed commit through one run, `archon workflow run gauntlet-run`: intake with Clerk, an adversarial plan review, an adversarial spec review, a worktree cut, test-first writing in the tree, a mend after rebase, and a fast-forward landing on the checkout. Every agent works inside a fence (an MCP file server confined by environment variables), and the owner answers each pause on the run's id. It is for the owner alone, on this host, across every repository Archon scans.

## Core Value

One command lands one task on the checkout with tests that bite, and no agent ever writes outside the folders its phase allows.

## Requirements

### Validated

- ✓ `fence/files.py`: a stdio MCP file server rooted at `CLAUDE_PROJECT_DIR`, confined by `FENCE_READ`, `FENCE_WRITE`, `FENCE_DENY`, `FENCE_COPY` and `FENCE_ONCE`, with `read_file`, `list_directory`, `find_files`, `grep`, `write_file`, `edit_file`, `copy_file` and `delete_file`; `.archon`, `.claude` and `.git` never writable; reads capped at 500 lines - pre-Cadence
- ✓ `fence/checks.py`: an MCP server that runs `FENCE_TEST_COMMAND` under `FENCE_TEST_TIMEOUT` and returns output capped at 200 lines / 20000 chars - pre-Cadence
- ✓ Fence suites `fence/test_files.py` and `fence/test_files_write.py`, run per `docs/testing.md` with `uv run --no-project --with 'mcp>=1.2,<2' --with pytest pytest -q fence` - pre-Cadence
- ✓ `spec-review/commands/arbiter.md`: the spec review's test-reviewer role, verdict grammar and per-spec checks - pre-Cadence
- ✓ `docs/testing.md`: the binding testing policy for Python suites and workflow fixtures - pre-Cadence
- ✓ filepawl length and directory-count gate wired through `.pre-commit/config.yaml` and `pyproject.toml` (cap 500 / tests 800, dircount 15 / 30) - pre-Cadence
- ✓ Seven designs under `docs/superpowers/specs/` (gauntlet, intake, plan review, spec review, worktree cut, writing, landing), each with modules, homes and a build order, all `Status: proposed` - pre-Cadence
- ✓ Archon reference docs vendored under `docs/reference/archon/` - pre-Cadence

### Active

Milestone v0.10.0: the full seven-phase run, built from the designs once they survive an adversarial review.

- [ ] Every design reviewed adversarially for cross-design consistency and snags, each finding ruled on, each design `Status: approved`
- [ ] Every role file the designs name written under its workflow's `commands/`
- [ ] The shared Python and TypeScript layer the phases depend on: fence name patterns, `FENCE_HIDE`, the fence `commit` tool, `.shared/rounds.py`, `.shared/red.py`, `.shared/working-folder.ts`, `.shared/task-format.md`
- [ ] Intake, plan review and spec review usable standalone and as blocks of `gauntlet-run`
- [ ] The worktree cut, the tree run and the run's end on a defective plan
- [ ] Writing in the tree: test writers, code writers, juror, revisions, the sealed final commit
- [ ] The mend and the landing: rebase, verify, repair, the owner's gate, ff-only merge, record copy, tree removal
- [ ] Every workflow fixture passes `archon workflow test`; `archon workflow list --json` and `archon validate workflows` are clean from the pack root

### Out of Scope

- A push, PR or any remote change made by Gauntlet - the designs forbid it in landing's home, and `CLAUDE.md` 4.4 forbids it on this host
- A phase sending the run back to an earlier phase - the gauntlet design's phase-order home forbids it; a wrong plan or spec is an approved revision inside writing
- Gauntlet removing the tree or its branch on `fail`, `kill`, leave or any stop - the landing design keeps them for the owner, removed only by `archon complete <branch> --force`
- Scaffolding in Python, Bash or any language that replaces an Archon feature - `CLAUDE.md` 1.1; a missing Archon feature is reported, not worked around (1.2)
- A phase as a `workflow:` child except the cut's `tree` node - the gauntlet design: a phase enters the run by `include:`

## Context

- Stack: Python 3.12+ scripts (`# /// script` headers, `mcp>=1.2,<2`, standard library otherwise), bun TypeScript scripts, Archon workflow YAML, Markdown role files, `*.mcp.json` fences. `pyproject.toml` is not a package; it pins filepawl and pre-commit for the gates.
- Layout rules from `CLAUDE.md` 1.7: one direct YAML per workflow folder, no YAML directly in the root or a non-dot top-level folder, and the folder is live - Archon loads it as written. `.pre-commit/` is a dot folder for that reason.
- Built: `fence/` (5 files, 2 suites), `spec-review/commands/arbiter.md`. Everything else the designs name is unbuilt; the gauntlet design's own copy list (section "The phase designs contain these copies") records the inconsistencies the designs already know about between each other.
- History: 22 commits over 2026-11-04 and 2026-11-05, no tags. The owner reports two earlier incarnations (a plugin, then a custom harness) before this Archon-workflow form; the version continues from them at 0.10.0.
- Known rough edges the designs flag for the builder: whether Archon's `sandbox:` can limit a `file` node's writes; whether `include:` with `fan_out:` works inside a `loop_group` body; whether the repository's `env:` reaches fenced MCP servers; the landing design's open "Decisions for the owner" (a checkout that moves after the mend's rebase).
- No CI: there is no `.github/` directory. Gates are local: the fence suite and `.pre-commit run -c .pre-commit/config.yaml --all-files`.
- Host: Opal is production (`CLAUDE.md` 2); any process is owned by PID and nothing saturates a core or a gigabyte without disclosure.

## Constraints

- **Tests**: every test follows `docs/testing.md` (one assertion, public surface, no wall clock, red run proves bite) - a test that breaks a rule there is rejected in review even when it passes
- **File size**: filepawl caps a source file at 500 lines (800 for tests) and a directory at 15 files (30 for tests) - the pre-commit gate refuses otherwise
- **Archon only**: use Archon features directly; no scaffolding without the owner's approval - `CLAUDE.md` 1.1
- **Token waste and non-issue stops are defects**: an approach that spends tokens the sequence does not need, or lets a run stop over a technicality, condemns its file - `CLAUDE.md` 1.3 to 1.5
- **Commits**: finished work that passes the gates is committed in the same turn, by named path; never pushed - `CLAUDE.md` 4
- **Layout**: `archon workflow list --json` and `archon validate workflows` judge every tree change - `CLAUDE.md` 1.8

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Gauntlet is an Archon workflow pack, not a plugin or a custom harness | Third incarnation; Archon's runs, worktrees, approvals and includes replace hand-built orchestration | - pending |
| One run, phases as included blocks (`d509af0`) | An included block runs inside the run, so `$ARGUMENTS` reaches Clerk and pauses answer on one id; a `workflow:` child cannot reach the existing tree | - pending |
| Writing and the mend are blocks of the tree run, not of `gauntlet-run` | An agent runs in its run's checkout and no node field sets another folder, so tree work must run in the tree's own run | - pending |
| Agents are confined by `fence/files.py`, driven by `FENCE_*` environment variables | One confinement for every role; `FENCE_DENY` applies to writes only, `FENCE_HIDE` (unbuilt) will refuse reads | ✓ good |
| Landing is `git merge --ff-only`, no squash, no merge commit, no push | The writers' commits and `<slug>: final` reach the checkout as they stand; the owner publishes | - pending |
| One red rule in `.shared/red.py` | Writing's `stage.py` and the mend's `verify.py` must agree on what red means; a second comparison is forbidden | - pending |
| Tests bound by `docs/testing.md` | Adapted from hqptuner2's policy; the arbiter reads it as its opening prompt | ✓ good |
| Roles: planner, analyzer, verifier and reviewer on opus; executor and plan checker on sonnet | Plans and reviews are paid for by every dispatch that reads them; execution is the largest spend | - pending |

---
*Last updated: 2026-11-05 after /cad-adopt*
