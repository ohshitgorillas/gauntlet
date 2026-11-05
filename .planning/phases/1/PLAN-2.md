---
phase: 1
plan: 2
requirements:
  - REV-01
  - REV-04
files:
  - docs/reference/archon/mcp-servers.md
  - docs/superpowers/specs/contracts.md
  - .planning/phases/1/REVIEW-pass1.md
---

# Phase 1: Design review - Plan 2: First review pass

## Goal

The owner can read one adversarial review of the seven designs that names every cross-design inconsistency and snag, each finding anchored to a design file and line and to a `contracts.md` row, grouped so one ruling closes every occurrence of one disagreement.

## Must be true when done

- `.planning/phases/1/REVIEW-pass1.md` exists, dated, with findings from four sources: the Archon feature verdicts, the seven build orders as one graph, and one `cad-reviewer` (opus) review per design.
- Every finding carries a `<design>.md:<line>` anchor that shows the text it is about, and a `contracts.md` row id.
- Every row in `contracts.md` section A carries a verdict from Archon's documentation: `documented` with a `docs/reference/archon/` path:line, or `unsupported` with the doc line and the finding it raised.
- The findings are deduplicated into groups, one per disagreement, each keyed to its `contracts.md` row, listing every design line where it occurs; every copy-list bullet and the landing design's open decision sit in a group.
- `docs/reference/archon/mcp-servers.md` is tracked.
- No design file changed in this plan.

## Context

- Runs after Plan 1; reads `contracts.md` and cites its row ids (H, P, F, S, R, A).
- D-03 and D-08: verdicts come from the docs; Phase 1 runs no probe, and the `spiker` agent runs one only for a feature no Archon doc covers. D-08's doc lines are starting points to re-read, not verdicts to copy. D-09: the MCP-servers guide is vendored so the env verdicts cite a tracked file.
- D-04: the review record lives in `.planning/phases/1/`, one dated file per pass; designs and `contracts.md` alone sit under `docs/superpowers/specs/`. D-06: the copy list is claims to check. D-07: the seven `## Order` sections are reviewed as one graph keyed `<design>:step N`. D-10: the landing design's "Decisions for the owner" is a finding group like any other.
- CONTEXT's flagged assumptions expect findings, not settled contracts, on the fence env route (`writing-design.md:22,268`, `landing-design.md:332`) and on `sandbox:` (`spec-review-design.md:361,482,499`).
- Finding ids are `1.NN` (pass 1, numbered); group ids are `G-NN`. Planner's discretion, recorded here so Plan 3's rulings cite them.
- Standing checks and testing scope: as Plan 1's Context states (pre-commit and the two `archon` commands before each commit; documentation only, no automated test applies, the Verify greps are the evidence).

## Tasks

### Task 1: Vendor Archon's MCP-servers guide

- **Files:** docs/reference/archon/mcp-servers.md
- **Action:** Fetch `packages/docs-web/src/content/docs/guides/mcp-servers.md` from `coleam00/Archon` at branch `dev` (D-09), for example with `gh api -H 'Accept: application/vnd.github.raw' 'repos/coleam00/Archon/contents/packages/docs-web/src/content/docs/guides/mcp-servers.md?ref=dev'`, and write it unchanged to `docs/reference/archon/mcp-servers.md`, frontmatter included, as the other vendored pages keep theirs. Name the source repository, branch and path in the commit message. Do not edit, trim or summarise it: verdicts cite its lines. The fetch is a network read of a public file the owner decided to vendor in D-09; if the sandbox refuses the network, return a `blocked` checkpoint naming the refused command rather than writing the page from memory.
- **Verify:** `git ls-files docs/reference/archon/mcp-servers.md` prints the path; `head -3` shows a `title:` frontmatter line as `workflow-language.md` does; `grep -n 'Environment Variable Expansion' docs/reference/archon/mcp-servers.md` returns a heading line. Plus the standing checks.

### Task 2: Archon feature verdicts

- **Files:** docs/superpowers/specs/contracts.md, .planning/phases/1/REVIEW-pass1.md
- **Action:** Create `REVIEW-pass1.md` with its date and a section per finding source (features, build orders, one per design, groups). For each section A row of `contracts.md`, read the vendored doc that governs the form the designs assume and write the verdict into the row: `documented` citing the `docs/reference/archon/` path:line that confirms that exact form, or `unsupported` citing the line that refuses or contradicts it. A composed form (`include:` with `fan_out:` inside a `loop_group` body) is `documented` when each half is documented at its own line and no doc line refuses the composition; cite both. Every `unsupported` verdict is also a finding in the features section, one per assuming design, anchored to that design's line and citing the row. For the MCP env route, judge each fence's launch form recorded in section F against the vendored guide's environment-expansion rules. Where no `docs/reference/archon/` file covers a feature at all, file the finding and return a `decision` checkpoint whose Need asks the main session to run the `spiker` agent on that one feature (D-03); on continuation, record the probe's result as that row's verdict `probed`, citing the probe record, the one case roadmap criterion 4 names. Do not run a probe yourself and do not mark a row `documented` from a doc that only mentions the field.
- **Verify:** Every section A row holds `documented`, `unsupported` or `probed`, with a citation; each `docs/reference/archon/<file>:<line>` cited, read with `sed -n '<line>p'`, shows the feature the row names; the count of `unsupported` rows equals the number of distinct rows the features section's findings cite. Plus the standing checks.

### Task 3: Build orders as one dependency graph

- **Files:** .planning/phases/1/REVIEW-pass1.md
- **Action:** Read the seven `## Order` sections and write into the build-orders section a compact edge list, one line per step keyed `<design>:step N`, naming the steps it needs and the files it writes. From that graph, file a finding for each cycle, each step that needs a file no step of any order builds and the tree does not hold today (built today: `fence/` and `spec-review/commands/arbiter.md`), each step that needs a step ordered after it, and each file two steps write without one ordered after the other or with different node lists for the same file (D-07's known case: writing step 8 and gauntlet step 4 both write `gauntlet-tree.yaml` nodes `paths` and `write`). Anchor each finding to the step lines it concerns and cite the `contracts.md` row of the file or node at issue.
- **Verify:** The edge list holds one line per numbered step across the seven `## Order` sections (its line count equals the count of numbered lines under those headings, from `perl -ne 'print if /^## Order/../^## (?!Order)/' docs/superpowers/specs/*-design.md | grep -c '^[0-9]'`); the `gauntlet-tree.yaml` overlap from D-07 appears as a finding or is stated resolved with both step lines quoted. Plus the standing checks.

### Task 4: Adversarial review of each design

- **Files:** .planning/phases/1/REVIEW-pass1.md
- **Action:** This task is a review point the executor cannot run: it has no agent tool and `cad-reviewer` cannot write. Return a `decision` checkpoint whose Need asks the main session to dispatch `cad-reviewer` at opus seven times, one per design, as ROADMAP pass 2 states. Each dispatch carries the design under review, the other six designs, `contracts.md` and `CLAUDE.md` sections 1.3 to 1.5 (the token-waste and non-issue-stop defects are snags), and asks for every inconsistency with another design and every snag, each with a `<design>.md:<line>` anchor, the quoted text, and the `contracts.md` row id it concerns or the contract a missing row would hold; feature verdicts and build orders are out of its brief, Tasks 2 and 3 cover them. On continuation, write each returned finding into its design's section with a `1.NN` id. Check every anchor with `sed -n`: a wrong line is corrected to the line holding the quoted text; a finding whose quoted text exists in no design is listed under its section as dropped, with the reason, never silently removed.
- **Verify:** Seven design sections each hold the findings of one dispatch, or state that the dispatch returned none; every anchor in them, read with `sed -n '<line>p'`, contains the text its finding quotes (mismatch count 0); every finding names a row id or a missing contract. Plus the standing checks.

### Task 5: Deduplicate and group by inventory row

- **Files:** .planning/phases/1/REVIEW-pass1.md, docs/superpowers/specs/contracts.md
- **Action:** Group the findings of all sections so one group holds one disagreement: findings about the same `contracts.md` row and the same conflict join one `G-NN` group, which lists its member findings, every design line where the disagreement occurs, a one-sentence statement of it, and each value the designs give, cited, as the options a ruling chooses between. A finding about a contract two or more designs name but no row holds adds that row to `contracts.md` under D-01 and cites it. A finding confined to one design's internals cites the row of the hand-off, path, fence, script, role or feature it affects; one that affects no row is grouped under its design as internal and named so in the group. Map each of the 12 copy-list bullets (D-06) to the group that judges it; bullets the designs already resolve form one group whose members each quote the resolving design line (CONTEXT names "Standalone phase workflows: 3" and "guard nodes: 3" against `gauntlet-design.md:114`, `plan-review-design.md:12,244`, `spec-review-design.md:15,298`). The landing design's "Decisions for the owner" is a group of its own (D-10). The two known planning contradictions under D-02 (`PROJECT.md` "usable standalone" and ROADMAP Phase 4 criterion 1 against `gauntlet-design.md:114` and `spec-review-design.md:298`) are named on the group they belong to.
- **Verify:** Every `1.NN` id appears in exactly one group (a grep over the groups section finds each once); every group names a `contracts.md` row id that exists in `contracts.md`, or states it is internal to one design; each of the 12 copy-list bullets and the landing open decision appears in a group. Plus the standing checks.

## Notes

- Tasks 2 and 4 stop for the main session. Task 4's checkpoint is the route by which `cad-reviewer` (opus) reviews the designs, as ROADMAP pass 2 requires: the executor has no agent tool and the reviewer has no write tool. Task 2 stops only when a feature has no Archon doc.
- Testing-policy deviation, recorded once for the phase: the dispatch asks the first task of this phase's plan to build the CI jobs (`tests`, `fixtures`, `lint`). No plan here does. ROADMAP Phase 2's goal and its criterion 1 assign that gate to Phase 2. Phase 1 CONTEXT's scope boundary leaves code and workflow files out. This phase changes documentation only, so a coverage job built here would gate nothing it changes. `.github/cadence/coverage-policy.json` is already tracked.
- Finding-to-row tension: CONTEXT AC1 asks every finding to cite a `contracts.md` entry, and D-01 admits no row a single design alone names. A snag internal to one design that touches no cross-design contract therefore has no row to cite. Task 5 groups it as internal to its design rather than inventing a row; AC1 and ROADMAP criterion 1 were amended at plan time to admit that mark (plan review finding).
