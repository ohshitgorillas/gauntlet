# Phase 1 review, pass 1

Date: 2026-11-05
Plan: `.planning/phases/1/PLAN-2.md`
Reviewed: the seven designs under `docs/superpowers/specs/` against `docs/superpowers/specs/contracts.md` (rows H, P, F, S, R, A).

Ids: findings are `1.NN` (pass 1, numbered in this file); groups are `G-NN`. A finding cites `<design>.md:<line>`, the text it is about, and a `contracts.md` row id, or the mark "internal to <design>" when it touches no cross-design contract (CONTEXT AC1).

Sources: (1) Archon feature verdicts, (2) the seven build orders as one graph, (3) one `cad-reviewer` (opus) review per design, (4) groups.

## 1. Archon feature verdicts

Verdicts come from the vendored documentation (D-03) and, for the two rows no doc covers, from the probe record `.planning/phases/1/PROBES.md` (cited below as PROBES.md, section P1-P3; the main session ran the `spiker` probes). The verdict and its citations sit in the verdict column of `contracts.md` section A; this table repeats the outcome.

| Row | Verdict | Finding |
|---|---|---|
| A1-A4, A6-A9 | documented | - |
| A5 | probed (PROBES.md P2) | 1.04 (in section 4), 1.05 withdrawn (section 9) |
| A10 | probed (PROBES.md P1) | 1.03 (in section 6) |
| A11 | unsupported | 1.01, 1.02 |
| A12-A18 | documented | - |
| A19 | unsupported (PROBES.md side finding) | 1.07, 1.08 |
| A20-A28 | documented | - |

Counts: 28 rows; 24 documented, 2 unsupported (A11, A19), 2 probed (A5, A10). The features findings below cite A11 and A19: the equality "unsupported rows = distinct rows the features findings cite" holds (2 = 2). A `probed` row whose probe contradicts a design's stated form carries its finding in that design's section (1.03 in section 6, 1.04 in section 4), as 1.06 does in section 5, because the finding is about that design's text and not about whether Archon has the feature.

Notes that stay inside a documented verdict (no finding, recorded so Plan 3 does not rediscover them):

- A9: instances of `include:` with `fan_out:` share the parent's checkout and run concurrently up to `max_parallel`; instances that write must coordinate their edits (`workflow-language.md:2613-2614`). `writing-design.md:379,386` set `max_parallel: 2` on two writing blocks.
- A20: `mcp:` files found beside the YAML work for a home-scoped workflow only; project, bundled and installed workflows use only the checkout (`mcp-servers.md:95-100`). This pack lives in `~/.archon/workflows/`, so it qualifies; an installed pack (`publishing-plugins.md`) would not.
- A25: "a dry run ends a loop after one iteration" (`gauntlet-intake-design.md:225`) is documented at `cli.md:414` for a tolerated loop only.

### Findings

**1.01** `writing-design.md:268`, row A11 (fences F8, F9).
Text: "Each is launched by `sh -c`, with every `FENCE_*` built from the repository's `env:` in the launch line." Also `writing-design.md:22`: "Unmeasured: whether the repository's `.archon/config.yaml` `env:` reaches an agent node's MCP server processes."
Finding: the MCP guide expands `env` and `headers` values from Archon's process environment, with codebase-scoped env vars on Codex nodes only (`mcp-servers.md:192-194`), and never touches `command` or `args` (`mcp-servers.md:211`). No doc line carries the repository `env:` to a Claude node's MCP server process. The fence launch form for F8 and F9 (`FENCE_TEST_COMMAND=$GAUNTLET_TEST_COMMAND`, `FENCE_TEST_TIMEOUT=${GAUNTLET_TEST_TIMEOUT:-900}`, `:$GAUNTLET_TEST_BASE` "when set") reads variables the documented route does not supply. The `${VAR:-default}` form does not match the expansion pattern (`mcp-servers.md:210`) and a conditional `:$GAUNTLET_TEST_BASE` cannot be written in a JSON `env` value. The design itself calls the route unmeasured.
Fence launch forms judged against `mcp-servers.md`: F1-F7 use literal `env` values plus `${ARCHON_HOME:-$HOME/.archon}` inside `args` that `sh` expands itself (`mcp-servers.md:144,211`): compatible. F8-F11 read the repository's `env:`: not covered.

**1.02** `landing-design.md:332`, row A11 (fences F10, F11).
Text: "launched by `sh -c` with every `FENCE_*` built from the repository's `env:` in the launch line". `landing-design.md:15`: "the repository's `env:` is measured to reach bash nodes only".
Finding: as 1.01 for the mend's fences. The design also contradicts itself: line 15 records the repository's `env:` as measured to reach bash nodes only, and line 332 builds the mend's `FENCE_*` from it for agent nodes' MCP servers.

**1.07** `plan-review-design.md:264`, row A19 (also `:301`, `:165`, `:170`).
Text: `allowed_tools: [Task, "Bash(uv run --script *cite.py *)"]`; `:165` "Detectives: dispatch through Task to `detective` for code reading."
Finding: `archon validate` warns "Tool 'Task' was renamed to 'Agent' in the claude SDK — the old name is silently ignored at runtime" (PROBES.md, side finding), while the vendored docs still show `Task` (`workflow-language.md:657`). With `Task` ignored, the defense node gets no sub-agent dispatch and the `detective` never runs. The probe's working form is `Agent` (PROBES.md section P1). Confidence: the warning text is the tool's own; a run with `Task` alone was not made.

**1.08** `spec-review-design.md:359`, row A19 (also `:24`, `:239`, `:243`).
Text: `allowed_tools: [Task, Bash]  # Bash for the spikers; the role forbids the speccer's own Bash`; `:239` "Spikers: dispatch through Task to `spiker`".
Finding: as 1.07, for the `spiker`. `writing-design.md:530` names `Task` as a tool a writer node must not hold: with the name renamed, the row should name both words or the new one.

Findings raised by the probes (1.03, 1.04, 1.06) are filed in their design sections because they concern that design's text: 1.03 in section 6, 1.04 in section 4, 1.06 in section 5. 1.05 is withdrawn; it is listed in section 9.

## 2. Build orders as one graph

(Plan 2 Task 3.)

## 3. gauntlet-design.md

(Plan 2 Task 4.)

## 4. gauntlet-intake-design.md

(Plan 2 Task 4.)

Seeded by Task 2 from the probe record, to be kept when the reviewer returns:

**1.04** `gauntlet-intake-design.md:117`, row A5.
Text: "Claude Code sets the server's `CLAUDE_PROJECT_DIR` to its own working directory, the run's checkout, and overrides any value the config gives, so the config sets none."
Finding: false as written. PROBES.md section P2: Claude Code sets `CLAUDE_PROJECT_DIR` to the cwd only when the MCP config gives no value; a config `env` value wins (`/bogus` stayed `/bogus`). The pack still works because every config sets none, but the stated reason does not hold: nothing in Claude Code stops a config from relocating the fence root of F1-F11, so "the config sets none" is a rule the pack must keep and test, not a guarantee. Same claim stands behind `plan-review-design.md:226`, `spec-review-design.md:269`, `writing-design.md:268` ("sets no `CLAUDE_PROJECT_DIR`").

## 5. plan-review-design.md

(Plan 2 Task 4.)

Seeded by Task 2, to be kept or dropped when the reviewer returns:

**1.06** `plan-review-design.md:264`, row A19 (the `allowed_tools` row naming this line; the `Bash(<pattern>)` form itself has no row of its own).
Text: `allowed_tools: [Task, "Bash(uv run --script *cite.py *)"]` (also `:301`, and `:170` "Bash for exactly the cite.py command above and no other command").
Finding: no doc under `docs/reference/archon/` shows a `Bash(<pattern>)` specifier in `allowed_tools` (`workflow-language.md:621-643` lists plain tool names). PROBES.md section P3: `archon validate` accepts the specifier, but at runtime Bash is removed entirely ("No such tool available: Bash"), not limited to matching commands. The defense can run no command, `cite.py` included, so the cite check cannot run and the confinement the design builds on it does not exist. A `Bash(...)` rule set through `settings`/permissions was not tested.

## 6. spec-review-design.md

(Plan 2 Task 4.)

Seeded by Task 2 from the probe record, to be kept when the reviewer returns:

**1.03** `spec-review-design.md:361`, row A10.
Text: "sandbox: <enabled; filesystem writes allowed only under gauntlet/scratch/ of the checkout>". Also `:482`, `:499`.
Finding: PROBES.md section P1: there is no pure write allow-list. `filesystem.allowWrite` is accepted but only adds writable paths; the checkout stays writable (a direct and a sub-agent `echo > outside.txt` both succeeded). Confinement holds only with `denyWrite` listing every other path (deny beats allow), and it does reach the Bash of a sub-agent spawned from the node. The design's form cannot confine the spiker to `gauntlet/scratch/` as written, and a new top-level file not on a `denyWrite` list stays writable. Globs in `denyWrite` were not tested. The documented keys are `workflow-language.md:250-261`. `:499` already tells the builder to stop and report if the sandbox cannot limit the writes.

## 7. worktree-cut-design.md

(Plan 2 Task 4.)

## 8. writing-design.md

(Plan 2 Task 4.)

## 9. landing-design.md

(Plan 2 Task 4.)

Withdrawn by Task 2:

**1.05** `landing-design.md:11`, row A5. Dropped: the quoted text "`fence/files.py` and `fence/checks.py` root at `CLAUDE_PROJECT_DIR`, the agent's folder" states only the part PROBES.md section P2 confirms (the variable is the cwd when the config gives none). The false clause is in `gauntlet-intake-design.md:117` (finding 1.04).

## 10. Groups

(Plan 2 Task 5.)
