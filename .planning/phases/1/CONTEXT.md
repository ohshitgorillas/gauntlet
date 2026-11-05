# Phase 1: Design review - Context

Gathered: 2026-11-05
Feeds: /cad-plan 1

## Scope boundary

In: the four passes the roadmap names, in order (inventory, review, rulings, convergence) over the seven designs under `docs/superpowers/specs/`; `docs/superpowers/specs/contracts.md`; the phase's review record; every design set `Status: approved`; vendoring Archon's MCP-servers guide as the source for the env verdicts; the PROJECT/ROADMAP/REQUIREMENTS lines a ruling contradicts.
Out: any code, role file, fence change or workflow YAML (Phases 2-7); runtime probes of Archon features (no probe is planned, see D-03); rewriting planning files beyond the lines a ruling contradicts.
Deferred: None
Plan shape: multiple plans, same phase - /cad-plan breaks it down (for example inventory + review, then rulings + convergence).

## Durable decisions

- D-01 (inventory): `docs/superpowers/specs/contracts.md` is one file holding only the cross-design subset (a contract named by two or more designs): hand-off fields, node ids, paths, `FENCE_*` values as a fence x variable matrix, scripts, roles and assumed Archon features, each row citing every design that names it. It is the reference later phases are reviewed against; a path one design alone names is not a row. Evidence: grep over `docs/superpowers/specs/*.md` (182 unique paths, 80 node ids, 17 role files, 19 fences, 9 `FENCE_*` names); `CLAUDE.md` 1.3.
- D-02 (rulings scope): a ruling that contradicts `.planning/PROJECT.md`, `.planning/ROADMAP.md` or `.planning/REQUIREMENTS.md` edits those lines in the same commit as the designs it names. First known case: `PROJECT.md:31` "usable standalone" and ROADMAP Phase 4 criterion 1 (`archon workflow run intake` standalone) against the designs' "included by gauntlet-run only. Not for direct use." (`gauntlet-design.md:114`, `spec-review-design.md:298`). Evidence: owner's answer in this pass.
- D-03 (feature verdicts): every assumed Archon feature gets its verdict from Archon's documentation - `documented` with a `docs/reference/archon/` path:line, or `unsupported` with the design changed. Phase 1 runs no probes; the `spiker` agent runs one only if the review finds a feature no Archon doc covers. Evidence: owner's answers ("everything has been tested or is confirmed by docs", "rtfm").

## Decisions

- D-04 (review record): the review record lives in `.planning/phases/1/`, one dated file per pass (`REVIEW-pass1.md`, ..., `REVIEW-convergence.md`); each finding carries a design file:line anchor and a `contracts.md` entry. `docs/superpowers/specs/` holds only the designs and `contracts.md`. Evidence: cadence `cadence-core/references/review-triggers.md:186`; `.planning/ROADMAP.md:29-31`.
- D-05 (ruling mechanics): a load-bearing ruling is written as a D-NN line in this file before `/cad-decision-review` runs on it (that skill takes a CONTEXT D-NN line or a PROJECT Key Decisions row); every other ruling goes through the ask-user seam and is recorded against its group in the review record. Evidence: cadence `cadence-core/workflows/decision-review.md:3-27`.
- D-06 (inventory seed): the gauntlet design's copy list (`gauntlet-design.md:21-36`) seeds the inventory as claims to check, not ground truth; bullets already stale include "Standalone phase workflows: 3" (line 23) and "guard nodes: 3", against `gauntlet-design.md:114`, `plan-review-design.md:12,244`, `spec-review-design.md:15,298`. Each bullet ends marked resolved with the design line or ruling that resolved it. Evidence: as cited.
- D-07 (build orders): the seven `## Order` sections are reviewed as one dependency graph keyed `<design>:step N`, judged for cycles and steps needing an unbuilt file; known overlap: writing step 8 and gauntlet step 4 both write `gauntlet-tree.yaml` nodes `paths` and `write`. Evidence: `gauntlet-design.md:361-373`, `writing-design.md:533-542`, `landing-design.md:377-384`, `worktree-cut-design.md:206-210`.
- D-08 (documented features): the vendored docs already settle `include:` + `fan_out:` (`workflow-language.md:2550-2622`), `include:` in a `loop_group` body (`loop-nodes.md:729-810`), `isolation:` only on `workflow:` (`workflow-language.md:2073`), `$INPUTS` left of `when:` rejected inside include (`:1906-1915`), `returns:` (`:1788-1792`), `worktree:` dropped under include (`:1565-1570`), `with:` (`:91`, `:94`, `:1141`) and `context: { resume }` (`:111`).
- D-09 (vendored guide): `docs/reference/archon/mcp-servers.md` is vendored from coleam00/Archon `dev`, `packages/docs-web/src/content/docs/guides/mcp-servers.md`, so the env verdicts cite a tracked file. Evidence: `docs/reference/archon/workflow-language.md:128` links `/guides/mcp-servers/`, not vendored until now.
- D-10 (landing open decision): the landing design's "Decisions for the owner" (checkout moved after the mend's rebase) enters pass 3 as a finding group like any other, not ruled ahead of the review. Evidence: `landing-design.md:386-388`.

## Acceptance criteria

- [ ] AC1: `docs/superpowers/specs/contracts.md` exists and every cross-design contract (hand-off field, node id, path, `FENCE_*` value, script, role, assumed Archon feature) has a row naming each design that names it; every finding in `.planning/phases/1/REVIEW-*.md` cites a `contracts.md` entry and a design `file:line`
- [ ] AC2: Every finding group in the review record carries exactly one owner ruling, and for each ruling `git log` shows a single commit editing every design it names - plus `contracts.md` when the ruling changes a contract, and any PROJECT/ROADMAP/REQUIREMENTS line it contradicts
- [ ] AC3: `.planning/phases/1/REVIEW-convergence.md` records a full pass over all seven edited designs with zero findings not already ruled, committed after the last ruling commit in `git log`
- [ ] AC4: Every assumed-Archon-feature row in `contracts.md` carries a verdict `documented` (citing a `docs/reference/archon/` path:line) or `unsupported` (citing the commit that changed the design), none open; `docs/reference/archon/mcp-servers.md` is tracked
- [ ] AC5: `grep -l '^Status: approved' docs/superpowers/specs/*-design.md` lists all seven designs, and each bullet of the gauntlet design's copy list is marked resolved, citing the design line or ruling that resolved it
- [ ] AC6: After the last commit, `archon workflow list --json` shows `"errors": []` and `archon validate workflows` reports no error under the pack root (the 23 non-pack `No default provider` errors are the baseline)

## Flagged assumptions

- Archon's MCP-servers guide ("Environment Variable Expansion") says MCP `env`/`headers` values expand from Archon's process environment, codebase-scoped env vars only on Codex nodes, and `command`/`args` are never expanded. The designs' `sh -c` launch lines building `FENCE_*` from the repository's `env:` (`writing-design.md:22,268`, `landing-design.md:332`) are therefore expected to be a pass-2 finding, not a settled contract - Likely; if wrong: the fence env route is kept on an unread doc.
- `sandbox:` on spec review's `file` node (`spec-review-design.md:361,482`, step 6 at `:499`) confining the spiker's Bash writes to `gauntlet/scratch/` has a doc verdict; if no Archon or Claude Code doc confirms a write allow-list, the review files it as a finding against the design - Likely; if wrong: spec review is approved on a confinement nothing documents.
- `include:` + `fan_out:` inside a `loop_group` body (writing's `tests`/`code`, `writing-design.md:374-386`) is documented by composition of two documented features, confirmed by an `archon validate workflows` load - Likely; if wrong: Phase 6's parallel writers fail to load.
- `archon validate workflows` currently reports 23 errors, all `No default provider: set 'defaultAssistant'` in non-pack workflows - Confident; if wrong: AC6's baseline is misread.
