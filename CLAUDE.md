# gauntlet — agent conduct

Gauntlet is an Archon workflow pack. This repository root is the pack root, and it lives in `~/.archon/workflows/gauntlet/`, which the live Archon install scans for every repository on this host. `~/dev/CLAUDE.md` does not load here; the rules of it that apply are restated in sections 2 and 3.

## 1. The pack

**1.1 No scaffolding.** Use Archon's features directly, always. No scaffolding in any language (Python, Bash, shell one-liners or otherwise) without the owner's approval.
**1.2 A missing Archon feature is the owner's problem.** Stop and report the gap; the owner files a feature request or decides how to deal with it (a patch script, or a different route altogether).
**1.3 Token waste is a defect.** An approach, fix, node or rule that spends tokens on work the sequence does not need is a defect, however correct the rest of the file.
**1.4 A stop on a non-issue is a defect.** An approach, fix, node, gate or check that lets the sequence stop over a technicality or a non-issue is a defect, however correct the rest of the file.
**1.5 One such defect condemns the whole file.** The owner removes that file from the drive and from git history, whatever else it holds. Write every file so that no rule of kind 1.3 or 1.4 lives in it.
**1.6 Tests follow `docs/testing.md`.** Read it before writing or changing any test or workflow fixture.
**1.7 Every file here is live.** Archon loads this folder as you write it, half-built or not. A workflow folder is `<workflow>/` with exactly one direct YAML; no other YAML sits directly in the root or in a non-dot top-level folder. Layout rules: `docs/reference/archon/global-workflows.md` and `workflow-language.md`.
**1.8 Archon judges the layout.** After any change to the tree, run `archon workflow list --json` and `archon validate workflows` from the root; a discovery error is fixed in the layout, never hidden.

## 2. Host

**2.1 Opal is production.** This host (Fedora, 18 cores, zsh) runs hqplayerd and the services `/srv/CLAUDE.md` lists. No task here justifies degrading them; pinning cores, filling memory or disk or leaving processes behind is damage, reported in the message where you find it.
**2.2 Disclose and never saturate.** Name any action reaching a full core for 10 s or 1 GB before it runs. The `host-footprint` skill holds the mechanics.
**2.3 Own every process you start.** Record its PID, kill by PID never by pattern, verify with `ps -p`, and report the result.
**2.4 Hooks stay on and unweakened.** A hook is not disabled, bypassed, narrowed or edited to let an action through without the owner's say-so. A misfiring hook is reported.

## 3. Work and reporting

**3.1 Correct beats done.** Weakening a test, suppressing a failure, faking a result or shrinking the task to get a pass is a defect. If you can't reach the correct fix, stop and report exactly what remains.
**3.2 Do it properly; never ask for a shortcut.** Take the proper fix unasked, and name each such choice in the report.
**3.3 A decision request states cause, evidence and confidence.** An unverified cause never goes to the owner. Read the specs and this file before asking, and say what you checked.
**3.4 Never absorb an unknown symptom** into a gate, threshold, baseline or exemption; a firing gate is evidence.
**3.5 Report plainly.** Say a skipped step was skipped, quote failing output by its shortest decisive line, offer no next step, and say done when done.

## 4. Commits

**4.1 Commit finished work unasked.** Work that is complete and passes the gates is committed in the same turn.
**4.2 Never commit a failing gate.** Leave it uncommitted and ask, quoting the failing line.
**4.3 Commit only your own paths,** by name with `git add <path>`, and report the paths left uncommitted.
**4.4 Never push.** No push, force-push, published branch, PR or remote change unless the owner says so that turn.

## 5. Gates

- Fence suite: `uv run --no-project --with 'mcp>=1.2,<2' --with pytest pytest -q fence`.
- Pre-commit: `uv sync` once, then `.venv/bin/pre-commit run -c .pre-commit/config.yaml --all-files`. The config sits in a dot directory so Archon does not parse it as a workflow.
