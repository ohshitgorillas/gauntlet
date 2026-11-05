---
phase: 1
plan: 1
requirements:
  - REV-04
files:
  - docs/superpowers/specs/contracts.md
---

# Phase 1: Design review - Plan 1: Contract inventory

## Goal

One contract inventory, `docs/superpowers/specs/contracts.md`, names every cross-design contract of the seven designs under `docs/superpowers/specs/` with every design that names it, so the review in Plan 2 judges each finding against one reference.

## Must be true when done

- `docs/superpowers/specs/contracts.md` exists and is tracked, with one section each for node references and hand-off fields, paths, fences, scripts and roles, and assumed Archon features.
- Every row names a contract two or more designs name, and cites each of those designs by `<design>.md:<line>`; no row cites one design alone, except the six Archon features the roadmap names.
- The fences appear as one fence x `FENCE_*` matrix, each cell giving the value each design states, so two designs disagreeing on one fence variable are visible in one row.
- Every bullet of the gauntlet design's copy list (`gauntlet-design.md`, the list after "The phase designs contain these copies:") has seeded at least one row, and each seeded row names its bullet.
- No design file, planning file or workflow file changed in this plan.

## Context

- D-01 binds the content: only the cross-design subset (a contract named by two or more designs), each row citing every design that names it; a path one design alone names is not a row. CONTEXT counts 182 unique paths, 80 node ids, 17 role files, 19 fences and 9 `FENCE_*` names across the designs; most do not qualify.
- D-06 binds the seed: the copy list is claims to check, not ground truth; bullets already stale include "Standalone phase workflows: 3" and "guard nodes: 3" against `gauntlet-design.md:114`, `plan-review-design.md:12,244`, `spec-review-design.md:15,298`. This plan seeds rows from them; Plan 2 judges them and Plan 3 marks them resolved.
- Inventory only: no row carries a finding or a verdict. Disagreements are recorded as the differing values each design states, cited; judging them is Plan 2's review.
- Standing checks for every task (CLAUDE.md 1.8 and 4.2): before the commit, `.venv/bin/pre-commit run -c .pre-commit/config.yaml --all-files` passes, and from the pack root `archon workflow list --json` shows `"errors": []` and `archon validate workflows` reports no error under the pack root beyond the 23 non-pack `No default provider` errors CONTEXT records as baseline.
- Testing scope for every task: the change is documentation; no automated test applies and none is added. The evidence is the grep checks each Verify names; testing stops there.

## Tasks

### Task 1: Inventory skeleton seeded from the copy list

- **Files:** docs/superpowers/specs/contracts.md
- **Action:** Create `contracts.md` with a short head stating what it is (the cross-design contract subset of the seven designs, D-01), the citation form every row uses (`<design>.md:<line>`, one per naming design), and the row-id scheme: each row carries a stable id whose letter names its section (H node references and hand-off fields, P paths, F fences, S scripts, R roles, A Archon features), numbered within the section. The ids are planner's discretion, recorded here so Plan 2's findings and Plan 3's rulings cite rows by id. Give the five sections their headings and column headers; the fence section is a matrix with one row per fence file and one column per `FENCE_*` name. Then read `gauntlet-design.md` from the top through the end of the copy list and seed, for each copy-list bullet, the rows its claim names (for example, the hand-off bullet seeds the three `handoff` node rows, the `gauntlet/failed/` bullet seeds the four fence rows it lists, the role-reuse bullet seeds the four role rows), each row tagged with the bullet it came from and cited from the design lines that actually name it today, read in each design, not copied from the bullet's count. A bullet whose claim no longer matches the designs still seeds its rows with the current citations; its staleness is Plan 2's finding, not a note here. Do not add a section for the copy list itself: D-01 admits contract rows only.
- **Verify:** `git ls-files docs/superpowers/specs/contracts.md` prints the path; `grep -n '^## ' docs/superpowers/specs/contracts.md` shows the five section headings; for each of the 12 bullets of the copy list, a grep for that bullet's tag in `contracts.md` returns at least one row, and every `<design>.md:<line>` citation in a seeded row, read with `sed -n '<line>p'`, shows the contract the row names. Plus the standing checks.

### Task 2: Node references and hand-off fields

- **Files:** docs/superpowers/specs/contracts.md
- **Action:** Fill section H. A row enters when a node id one design defines is named by another design: an `include:` block id, a `depends_on` or `when:` target, a `$<node>.output.<field>` reference, a `handoff` node and each field it hands off, the tree run's nodes the cut and landing read, and `.metadata.approval.childRunId`-style run fields two designs rely on. Each row names the node id, the defining design and workflow file, the fields where it is a hand-off, and every design that names it with its line. Where two designs give a hand-off different fields (the gauntlet design's per-phase hand-off lists against each phase design's own `handoff` node), the row shows each design's field list in its own cell, cited. Correct any seeded H row whose citations Task 1 took from the bullet's wording.
- **Verify:** Running `grep -oh '\$[a-z][a-z0-9-]*\.output\.[a-z_]*' docs/superpowers/specs/*-design.md | sort -u` and, for each reference, checking which design defines the node: every reference whose node is defined in a different design from one that uses it has an H row naming it (miss count 0). Every hand-off the gauntlet design's phase list names (intake through landing) has an H row citing both the gauntlet design and the phase design. Plus the standing checks.

### Task 3: Paths named by two or more designs

- **Files:** docs/superpowers/specs/contracts.md
- **Action:** Fill section P with every file or folder path, including pattern paths such as `gauntlet/plans/<slug>.<N>.txt`, that two or more designs name: which design writes it, which reads it, and the line each names it on. Group a path family (one pattern, many instances) into one row rather than a row per instance. Exclude scripts, role files and fence files, which sections S, R and F hold, so no contract has two rows. A path one design alone names is not a row, even when it looks important (D-01).
- **Verify:** Extract each design's backticked path tokens (tokens holding a `/` or ending in `.md`, `.txt`, `.json`, `.yaml`, `.py` or `.ts`), deduplicate per design, and count the designs naming each: every token counted in two or more designs that is not a script, role or fence file is covered by a P row (miss count 0), and no P row cites fewer than two designs. Plus the standing checks.

### Task 4: Fence x variable matrix

- **Files:** docs/superpowers/specs/contracts.md
- **Action:** Fill section F. A fence (`*.mcp.json`) enters when two or more designs name it or state one of its `FENCE_*` values; for those, read every design's statement of it. One row per fence file, one column per `FENCE_*` name the designs use (CONTEXT counts nine, `FENCE_HIDE`, `FENCE_COMMIT` and `FENCE_TEST_*` among them), each cell holding the value each naming design gives, cited. A cell where two designs give different values holds both, each cited, so the disagreement is one row. Also record, per row, how the designs say the fence receives its variables (the `env:` block or a `sh -c` launch line building values from the repository's `env:`), cited, because the MCP env route is an assumed Archon feature Plan 2 judges.
- **Verify:** `grep -oh '[a-z-]*/[a-z-]*\.mcp\.json' docs/superpowers/specs/*-design.md | sort | uniq -c` lists the fences; every fence named by two or more designs has an F row (miss count 0); `grep -oh 'FENCE_[A-Z_]*' docs/superpowers/specs/*-design.md | sort -u` lists the variables, and every one of them that any F-row fence sets appears as a matrix column. Plus the standing checks.

### Task 5: Scripts and roles with the folder each resolves from

- **Files:** docs/superpowers/specs/contracts.md
- **Action:** Fill sections S and R. A script (`<workflow>/scripts/*.py|*.ts`, `.shared/*`) or role file (`<workflow>/commands/*.md`) enters when two or more designs name it. Each row names the file, the workflow folder it must resolve from, the design that owns it, every design that calls, imports or reuses it with the line, and the resolution rule the designs rely on (the copy list states commands resolve only from a workflow's own `commands/` and named scripts only from its own `scripts/`; cite where each design states or depends on that). Cover the shared cores later phases import (`.shared/red.py`, `.shared/rounds.py`, `.shared/working-folder.ts`, `.shared/task-format.md`) and every one of the 17 role files that two or more designs name.
- **Verify:** `grep -oh '[a-z.-]*/\(scripts\|commands\)/[a-z-]*\.\(py\|ts\|md\)\|\.shared/[a-z-]*\.\(py\|ts\|md\)' docs/superpowers/specs/*-design.md`, counted per design: every file named in two or more designs has an S or R row (miss count 0), and each row names a resolving folder. Plus the standing checks.

### Task 6: Assumed Archon features

- **Files:** docs/superpowers/specs/contracts.md
- **Action:** Fill section A. The six features the roadmap's inventory pass names are rows whatever their design count, because roadmap criterion 4 requires each to carry a verdict: `include:` with `fan_out:` inside a `loop_group`, `sandbox:` on a `file` node, `isolation:`, `env:` reaching an MCP server, `$INPUTS` in `when:`, and `returns:`. Any other Archon feature enters under D-01's two-design rule; D-08 names candidates (`worktree:` dropped under `include:`, `with:`, `context: { resume }`). Each row names the feature, the exact form each design assumes, and every design that assumes it with the line. Leave a verdict column empty: verdicts are Plan 2's Task 2, from the docs only (D-03).
- **Verify:** Section A holds a row for each of the six named features; for each other row, a grep of its feature form over the seven designs hits two or more designs, matching the row's citations; the verdict column is present and empty in every row. Plus the standing checks.

## Notes

- Plans 1, 2 and 3 run in that order and share `contracts.md`, so `/cad-execute` takes them sequentially; the split follows the 8-task ceiling and CONTEXT's plan-shape directive.
- Choice recorded: the six roadmap-named features enter section A even where one design alone assumes them (`sandbox:` is named only in `spec-review-design.md`, `fan_out:` only in `writing-design.md`), because ROADMAP Phase 1 pass 1 lists them and criterion 4 requires a verdict for each. D-01's two-design rule governs every other row.
- No CI task in this plan: see Plan 2's Notes for the testing-policy deviation, recorded once for the phase.
