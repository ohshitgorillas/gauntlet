# Convergence round 3 - gauntlet-design.md

Reviewer return (cad-reviewer-medium, opus), verbatim. Designs at 87e0734.

```json
{ "findings": [
  { "file": "docs/superpowers/specs/gauntlet-design.md",
    "line": 409,
    "severity": "medium",
    "claim": "Homes row 'The failed task record' contradicts itself and the design's own intake additions. Its Home column says the record is 'read by Clerk', and `:357-371` add a `gauntlet/failed/` listing to intake's `ground`. Its Forbidden column says 'a phase block reading or writing `gauntlet/failed/`', and intake is a phase block (`:158-171`, `:395`). `:371` also says 'Only Clerk reads `gauntlet/failed/`', but `ground.ts` (`:362-363`) lists that folder. Row H24 and seed B09 (contract: who may read the failed record). Mark: matches G-51 (D-38 amendment). The applied ruling was aimed at the ledger's first script node, but its wording forbids the intake block's own ground node and Clerk, so the ruling as applied introduced this contradiction.",
    "failure_scenario": "A builder doing Order step 2 (`intake/scripts/ground.ts`, the `gauntlet/failed/` listing) or step 3 (Clerk's added rule) checks the Homes row. Node `ground` of block `intake` reads `gauntlet/failed/`, which the Forbidden column bans, so the builder or a later review stops on a contradiction inside one design. No real defect is behind the stop (CLAUDE.md 1.4)." },
  { "file": "docs/superpowers/specs/gauntlet-design.md",
    "line": 409,
    "severity": "low",
    "claim": "The same row's Forbidden clause, 'a fence outside `intake/` with `FENCE_READ` covering `gauntlet/failed/` and no `FENCE_HIDE` for it', has no checkout scope. Several tree fences set `FENCE_READ=.` with no `FENCE_HIDE` for `gauntlet/failed`: writing's `divvyer`, `juror`, `reviser` and `reviewer-plan` (`writing-design.md` fence table), the coder's `FENCE_HIDE`, which leaves out `gauntlet/failed`, and `mend-juror.mcp.json` and `mend-review.mcp.json` (`landing-design.md:492-493`). Its Home column says 'every other checkout role'. Rows F9, F10, F1-F4 (seed B09). Mark: new.",
    "failure_scenario": "A builder or reviewer applies the row literally to `write/juror.mcp.json` or `mend/mend-juror.mcp.json`. `FENCE_READ=.` covers the path `gauntlet/failed/`, and these fences have no `FENCE_HIDE` for it. That forces either a stop or `FENCE_HIDE=gauntlet/failed` added to about eight tree fences. Yet no tree ever holds `gauntlet/failed/`: `copy-in` copies only tasks, plans and specs, and the re-mend copy-in copies only the previous tree's `gauntlet/`. That is a stop on a non-issue or wasted work (CLAUDE.md 1.3/1.4)." },
  { "file": "docs/superpowers/specs/gauntlet-design.md",
    "line": 102,
    "severity": "low",
    "claim": "Nodes `land`, `land-2`, `land-3` and `land-4` bind `slug: $pin.output.slug` (`:102`, `:109`, `:116`, `:124`), and `landing-design.md:240` says the same ('A round takes `slug` from node `pin`'). But `pin` is an inner node of the cut phase, whose hand-off is `cut` (`worktree-cut-design.md:127-131`; `cut` prints no slug). The Homes row 'The hand-off between phases' (`:401`) forbids 'a phase reading another phase's inner node'. Rows H16, H17, H23. Mark: new.",
    "failure_scenario": "A review or builder enforcing Homes `:401` on step 10 finds landing (phase 7) reading `$pin.output.slug`, an inner node of phase 4, and stops. One of two fixes is needed and the design picks neither: `cut` hands off `slug`, or the rule excepts `pin`. The same rule is broken by the design's own YAML." },
  { "file": "docs/superpowers/specs/gauntlet-design.md",
    "line": 23,
    "severity": "low",
    "claim": "Nearly every 'Resolved' line citation in the copy list (`:23-34`) is stale at HEAD 87e0734. The self-citations: `gauntlet-design.md:138`, `:139` and `:140` are node `kill`'s id and cancel line and the closing fence, not the phase-file properties. `:141` is blank. `:254` is the mend `handoff` enum. `:308` is the land description. `:380` is a `FENCE_HIDE` comment. `:385` is the hide suite line. `:391` is the `## Homes` heading. The citations into other designs: `gauntlet-intake-design.md:28`, `:122`, `:152`, `:157`, `:165`, `:179`, `:186` and `:260`; `plan-review-design.md:242`, `:249`, `:256`, `:407` and `:413`; `spec-review-design.md:281-286`, `:325`, `:332`, `:339`, `:495` and `:503`; `writing-design.md:366`; `landing-design.md:265` and `:354`. Each lands on unrelated text, such as `effort: medium`, `form: select`, a blank line, or a `with:` line. Only `writing-design.md:19` holds. Seeds B01-B12 (rows H1, H5, H6, H13-H15, A1-A3, R12, S4-S6, H12). Mark: new. G-12/1.18 corrected the bullets' facts, not these later line drifts.",
    "failure_scenario": "A reviewer or builder checks a bullet's 'Resolved' claim by opening the cited line. For example, `spec-review-design.md:325` for the spec-review description shows a `fence/spike.py` comment, and `plan-review-design.md:413` for the hand-off contract shows `form: select`. Each check costs a hunt for the real line, or ends with the claim judged unsupported, across about 30 citations (CLAUDE.md 1.3)." }
] }
```
