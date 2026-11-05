# Phase 1 review, pass 1

Date: 2026-11-05
Plan: `.planning/phases/1/PLAN-2.md`
Reviewed: the seven designs under `docs/superpowers/specs/` against `docs/superpowers/specs/contracts.md` (rows H, P, F, S, R, A).

Ids: findings are `1.NN` (pass 1, numbered in this file); groups are `G-NN`. A finding cites `<design>.md:<line>`, the text it is about, and a `contracts.md` row id, or the mark "internal to <design>" when it touches no cross-design contract (CONTEXT AC1).

Sources: (1) Archon feature verdicts, (2) the seven build orders as one graph, (3) one `cad-reviewer` (opus) review per design, (4) groups.

## 1. Archon feature verdicts

Verdicts come from the vendored documentation only (D-03). The verdict and its `docs/reference/archon/` citations sit in the verdict column of `contracts.md` section A; this table repeats the outcome.

| Row | Verdict | Finding |
|---|---|---|
| A1-A4, A6-A9 | documented | - |
| A5 | pending probe | 1.04, 1.05 |
| A10 | pending probe | 1.03 |
| A11 | unsupported | 1.01, 1.02 |
| A12-A28 | documented | - |

Counts: 28 rows; 25 documented, 1 unsupported (A11), 2 pending probe (A5, A10). The equality "unsupported rows = distinct rows the findings below cite" is open until the probes return: the findings cite A5, A10 and A11. A row whose probe finds the feature works has its finding withdrawn and is recorded `probed`; a row whose probe finds it does not work becomes `unsupported` and keeps its finding.

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

**1.03** `spec-review-design.md:361`, row A10.
Text: "sandbox: <enabled; filesystem writes allowed only under gauntlet/scratch/ of the checkout>". Also `:482`, `:499`.
Finding: the only documented `sandbox:` filesystem key is `denyWrite` (`workflow-language.md:250-261`); `sandbox:` passes unknown keys through unchecked (`workflow-language.md:2967`); no doc line gives a write allow-list or says the sandbox confines the `Bash` of a `Task` sub-agent (the spiker). Status: probe requested of the main session (spiker); the result becomes the verdict `probed`.

**1.04** `gauntlet-intake-design.md:117`, row A5.
Text: "Claude Code sets the server's `CLAUDE_PROJECT_DIR` to its own working directory ... and overrides any value the config gives".
Finding: no file under `docs/reference/archon/` names `CLAUDE_PROJECT_DIR`. The fence root of every fence rests on it (`plan-review-design.md:226`, `spec-review-design.md:269`, `writing-design.md:268`). Status: probe requested.

**1.05** `landing-design.md:11`, row A5.
Text: "`fence/files.py` and `fence/checks.py` root at `CLAUDE_PROJECT_DIR`, the agent's folder".
Finding: as 1.04.

## 2. Build orders as one graph

(Plan 2 Task 3.)

## 3. gauntlet-design.md

(Plan 2 Task 4.)

## 4. gauntlet-intake-design.md

(Plan 2 Task 4.)

## 5. plan-review-design.md

(Plan 2 Task 4.)

Seeded by Task 2, to be kept or dropped when the reviewer returns:

**1.06** `plan-review-design.md:264`, internal to plan-review-design.md.
Text: `allowed_tools: [Task, "Bash(uv run --script *cite.py *)"]` (also `:301`).
Finding: no doc under `docs/reference/archon/` shows a `Bash(<pattern>)` specifier in `allowed_tools` (`workflow-language.md:621-643` lists plain tool names). The defense's confinement to `cite.py` rests on it. One design names it, so it has no `contracts.md` row.

## 6. spec-review-design.md

(Plan 2 Task 4.)

## 7. worktree-cut-design.md

(Plan 2 Task 4.)

## 8. writing-design.md

(Plan 2 Task 4.)

## 9. landing-design.md

(Plan 2 Task 4.)

## 10. Groups

(Plan 2 Task 5.)
