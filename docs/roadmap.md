# Gauntlet development roadmap

This document orders the work that turns the v0.11.0 design into a running harness. The mechanisms are in [`design.md`](design.md); section numbers below refer to it.

Each milestone states what it builds and a **Done when** check. A milestone is done only when its check passes, and the check is a command or a probe, not a reading of the code.

## Ordering rules

1. **Riskiest assumption first.** The design stands on the launcher: the Agent SDK driving a CLI inside a podman container, with mounts and tool lists as the only enforcement. If that fails, most of the design changes. It is proven before anything is built on it.
2. **Core before seams.** `core/` is pure and tested per branch (§1, §8). Seams stay thin around a core that already exists.
3. **One thin job end to end, then widen.** A job that reaches the land screen with stages missing comes before any stage built in full. A stage not built yet is recorded as skipped and shown as a bypass on the land screen, never silently passed (§1, "A check that did not run never passes").
4. **Test the new code, not the measured platform.** A mount or tool restriction lands with a unit test of the table that builds it. What §4 records as measured is not measured again.
5. **No self-hosting early.** The charter rules Gauntlet out for a codebase getting started. Gauntlet is built conventionally until it is established, and dogfooded last.

## M0. Launcher spikes

Throwaway code that answers the questions the design takes on trust.

- The SDK with `cli_path` set to a wrapper runs `claude` inside `podman run -i`, over stdio, and the in-process SDK MCP tools reach it.
- An empty `tools` list leaves a judge with no tools; `output_format` constrains its answer to the schema.
- The credential proxy injects the API key, and a container with no key reaches the API only through `ANTHROPIC_BASE_URL`.
- `:z` mounts work under SELinux; `:O` overlays discard writes.
- Per-launch container start time and its share of a job's wall clock.

**Done when:** each item has a recorded yes or no with the command that showed it, and every no has a design change written into `design.md`.

## Gates

The quality gates of [`superpowers/specs/2026-10-17-quality-gates-design.md`](superpowers/specs/2026-10-17-quality-gates-design.md), before any product code.

**Done when:** `make check` runs every gate in the spec on an empty `gauntlet/` and passes, and each gate script's own tests pass under it.

## M1. Core and records

- `core/verdicts.py`: answer schemas per role, `COULD NOT JUDGE` blocking like a failure.
- `core/decide.py`: `decide(state, answer)` for the linear stage table of §2, round caps included.
- `seams/job.py`: `state.json` with a row per check run, `trace.jsonl` per launch.
- `gauntlet resume` from `state.json` after a killed harness.
- The gate that blocks shell-command parsing in Gauntlet's own code (§1, the one exception).

**Done when:** every branch of `decide` has a unit test; a harness killed mid-stage resumes to the same next action.

## M2. Launcher and kinds

- `seams/launch.py`: the six kinds of §3, each a fixed mount table and tool list.
- `seams/proxy.py`: the credential proxy.
- Container hardening of §4: non-root, capabilities dropped, `no-new-privileges`, tmpfs home, `setting_sources=[]`, `strict_mcp_config=True`.
- `seams/git.py`: worktree per job, every git command on the host with explicit `--git-dir` and `--work-tree`.

**Done when:** a unit test per kind asserts the mount table and tool list `launch.py` builds match §3 and §4 exactly, with no container started.

## M3. Thin end-to-end job

`gauntlet run <brief.md>` drives outline, plan, spec, stubs, tests, red run, juror, lock, build and land, each with a single agent and no review rounds. Prosecutor, arbiter, examiner, review and bailiff are skipped and shown as bypasses.

- `seams/runner.py`: harness-owned test and gate runs, every runner in `gauntlet.yaml`, harness pytest settings of §4.
- `seams/screens.py`: approval screens and a first land screen.
- Land merges only when the owner's uncommitted changes touch none of the landed files (§6).

**Done when:** a small brief against a fixture repository with Python and JS tests lands a green change, and the land screen lists every skipped stage.

## M4. Adversarial loops and owner controls

- Prosecutor rounds on the plan, with citation resolution, `ESCALATE: LEAVE` and `REFUSE`.
- Arbiter rounds on the spec, with `bite:` values measured by the examiner in a scratch container.
- The stop screen, and `stop`, `retry`, `accept`, `edit`, `skip` and `eject` (§6), each recorded.

**Done when:** a fixture brief with a planted out-of-scope change gets it cut or escalated, a round cap reached stops the job on one screen showing both sides, and each owner command appears on the land screen.

## M5. Tester isolation

- Interface view from the repository's `interface` commands, trimmed to the names the plan touches.
- `run_tests`: outcome and exception type per id, nothing else.
- Collateral rows: byte-identical check on the quoted assertion.
- `test_lint` on tester files.

**Done when:** a tester probe finds no source file and no traceback through any tool, and a collateral repair that changes the quoted assertion is refused.

## M6. Review, bailiff and full land

- Repo reviewers on the harness-supplied diff; findings without file:line and failure scenario dropped; blocking findings routed to the step's implementer.
- Bailiff with `PIN` / `UNPINNED` per line and `HELD` / `ALTERED` per collateral row.
- Full land screen: diff split into tests and code, red and green lines, open findings, amendments and bypasses, cost per role.

**Done when:** the M3 fixture job runs every stage with no bypass, and a planted softened assertion is ruled `UNPINNED`.

## M7. First pilot

Run Gauntlet on a real, established repository with a small change, for example `hqptuner`.

**Done when:** three jobs land, and every stop, bypass and owner edit they needed is written up as a defect or a design change.

## M8. Reopen

`core/reopen.py` and the reopen flow of §2: any role's `spec_defect`, `gauntlet reopen <id> <line>`, rerun of stages 7 to 12 for the affected lines and steps only, `caps.reopen`.

**Done when:** a reopen on one spec line reruns only that line's tests and the steps that serve it, and the amendment shows on the land screen.

## M9. Brief conversation and discovery

`gauntlet new` with the brief-writer, and the detective answering the planner's questions in one batch.

**Done when:** a job started by conversation lands, and the discovery table's citations all resolve against the tree.

## M10. Audit jobs

`gauntlet audit <scope>`: the auditor per test file, selected rows becoming a job that starts at stage 5 and skips stages 6, 10 and 11.

**Done when:** an audit of a fixture test file with a planted policy violation yields a `STRIKE` or `AMEND` row, and that row lands as a job.

## M11. Repo roles and skills

Loading `.gauntlet/roles/` and `.gauntlet/skills/`, routing by description, and validation that a role body cannot widen its kind or answer schema.

**Done when:** a repo implementer and repo tester sharing a skill each take a step and a spec line in one job, and a role file that claims extra tools launches with its kind's tools only.

## M12. Epics

`gauntlet epic`: split with one prosecutor round, `core/schedule.py`, parallel jobs only on non-overlapping declared files, revision by a fresh coordinator, `open_job` / `job_status` / `job_record`.

**Done when:** a three-job fixture epic with one dependency runs the two independent jobs in parallel, starts the dependent job from `main` after its dependency lands, and lands all three.

## M13. Self-hosting

Gauntlet builds its own next change.

**Done when:** a change to Gauntlet lands through Gauntlet with no bypass.

## Open questions

These are decided by evidence from the milestone named, not ahead of it.

| Question | Settled by |
|---|---|
| Is a fresh container per launch fast enough, or is a warm pool needed, and does a pool break "removed when the launch ends"? | M0 timing, M3 wall clock |
| How does the container reach the host proxy under rootless networking without opening other host ports? | M0 |
| What do round caps of 2 cost per job in tokens, and do real plans pass inside them? | M7 trace |
| Does the trimmed interface view give testers enough to write tests that collect? | M5, M7 |
| Does `stubgen` handle the pilot repository's dynamic modules? | M5 |
