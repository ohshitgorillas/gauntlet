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

Throwaway code that answers the questions the design takes on trust. Answers live under "Measured" in `design.md` §4 (rule 4). Open: none.

**Done when:** each item has a recorded yes or no with the command that showed it, and every no has a design change written into `design.md`.

## Agents

The roster of [`superpowers/specs/2026-10-18-agents-design.md`](superpowers/specs/2026-10-18-agents-design.md) in `.claude/agents/`, each agent written by `role-author` and accepted by one dispatch proof. All ten are written. Proofs passed: `diff-reviewer`, `test-reviewer`, `spiker`, and `gatesmith`, with the scaffold and the suppression gate landed and `make check` green. Proofs outstanding: `test-writer` passed only in its earlier stub-reading form, and its `stubgen` interface-view form is unproven; `mutant-hunter` needs the mutation gate and a surviving mutant; `core-builder` and `seam-builder` take a scope test on the body now and a live dispatch at M1 and M2; `architect` takes the step-6 proof of the agents spec.

**Done when:** every agent has passed the dispatch proof its row in the spec names.

## Gates

The quality gates of [`superpowers/specs/2026-10-17-quality-gates-design.md`](superpowers/specs/2026-10-17-quality-gates-design.md), before any product code.

**Done when:** `make check` runs every gate in the spec on an empty `gauntlet/` and passes, and each gate script's own tests pass under it.

## M1. Core and records

- `core/verdicts.py`: every answer schema and the anchor type, `COULD NOT JUDGE` blocking like a failure; the `Anchor`, `Finding`, `Candidate`, `CoreMissing` and `Survey` records.
- `core/design.py`: the design record and `design_problems`, `home_of`, `uncovered`.
- `core/causes.py`: findings grouped into causes and routed to one fix each: `finding_problems`, `partition_problems`, `route`, `survey_problems`.
- `core/schedule.py`: `startable`, which of a job's steps or of the structure jobs may run beside which.
- `core/decide.py`: `decide(state, answer)` for the stage table of §2, round caps included, with the Design, review-by-cause and structure-job rows. The structure-job rows are the ones its tests walk; `FIRST` and `SKIPPED` hold all three shapes as data.
- `seams/job.py`: `state.json` with a row per check run, `trace.jsonl` per launch.
- `gauntlet resume` from `state.json` after a killed harness.
- The gate that blocks shell-command parsing in Gauntlet's own code (§1, the one exception).

**Done when:** every branch of `design_problems`, `uncovered`, `finding_problems`, `partition_problems`, `route`, `survey_problems` and `startable`, and of `decide` on the rows a structure job walks, has a unit test; a harness killed mid-stage resumes to the same next action.

## M2. Launcher and kinds

- `seams/launch.py`: the six kinds of §3, each a fixed mount table and tool list.
- `seams/proxy.py`: the credential proxy.
- Container hardening of §4: non-root, capabilities dropped, `no-new-privileges`, tmpfs home, `setting_sources=[]`, `strict_mcp_config=True`.
- `seams/git.py`: worktree per job, every git command on the host with explicit `--git-dir` and `--work-tree`.

**Done when:** a unit test per kind asserts the mount table and tool list `launch.py` builds match §3 and §4 exactly, with no container started.

## M3s. Thin structure job

`gauntlet audit <scope> --structure` on a fixture repository drives surveyor, grouper, survey screen, owner selection, and one structure job through design, plan, spec with the keeps lines, stubs, tests, red run, lock, build under `startable`, review and land. Design runs one architect and no rounds. Prosecutor, arbiter, examiner, repo reviewers, structure reviewer and bailiff are skipped and shown as bypasses.

- `seams/runner.py`: harness-owned test and gate runs, every runner in `gauntlet.yaml`, harness pytest settings of §4.
- `seams/screens.py`: approval screens, the design screen, the survey screen and a first land screen.
- The survey screen shows candidates ranked by payoff and risk and what is sound; the owner selects, and one structure job opens per selected candidate, run as separate jobs one after another.
- A structure job ports every copy and lands only when `uncovered` is empty at the end of its Review. The surveyor also runs in a structure job's Review.
- Land merges only when the owner's uncommitted changes touch none of the landed files (§6).

**Done when:** a fixture repository with one concern copied in three files and no core yields three anchors in one cause and one candidate with its payoff, risk and keeps; a design whose `uncovered` is empty at Design; spec lines for the keeps locked before any port step; a landed job that adds the home, ports every caller and leaves `uncovered` empty at the end of Review; a fixture with two such concerns, both selected, yields two jobs, the second starting after the first ends; and the land screen lists every skipped stage.

## M4. Adversarial loops and owner controls

- Prosecutor rounds on the plan, with citation resolution, `ESCALATE: LEAVE` and `REFUSE`.
- Arbiter rounds on the spec, with `bite:` values measured by the examiner in a scratch container.
- Prosecutor rounds on the design under `caps.design`, with every copy anchor resolved against the tree as plan citations are.
- The stop screen, and `stop`, `retry`, `accept`, `edit`, `skip` and `eject` (§6), each recorded.

**Done when:** a fixture brief with a planted out-of-scope change gets it cut or escalated, a round cap reached stops the job on one screen showing both sides, and each owner command appears on the land screen; a design citing a copy anchor that does not resolve fails a round; and a spec that drops a `keeps` line is rejected by the arbiter.

## M5. Tester isolation

- Interface view from the repository's `interface` commands, trimmed to the names the plan touches.
- `run_tests`: outcome and exception type per id, nothing else.
- Collateral rows: byte-identical check on the quoted assertion.
- `test_lint` on tester files.

**Done when:** a tester probe finds no source file and no traceback through any tool, and a collateral repair that changes the quoted assertion is refused.

## M6. Review, bailiff and full land

- Repo reviewers on the harness-supplied diff. The structure reviewer joins every job's Review, with the design on a job that has one and for copied code alone on a job that does not.
- `finding_problems` drops a finding that does not stand. The grouper groups the findings that stand into causes, and each cause is routed to one fix, replacing per-finding routing.
- Bailiff with `PIN` / `UNPINNED` per line and `HELD` / `ALTERED` per collateral row.
- Full land screen: diff split into tests and code, red and green lines, open findings, amendments and bypasses, cost per role.

**Done when:** the M3s fixture job runs every stage with no bypass, and a planted softened assertion is ruled `UNPINNED`; a planted copy of a design home's logic yields one COPY finding anchored at both places, one cause and one fix step whose diff removes the copy, and the next round holds no instance of it; and a job without a design that copies a function already in the tree yields one COPY finding and a fix step whose diff calls the existing function.

## M7s. Structure pilot

Run Gauntlet's audit and structure jobs on a real, established repository, for example `hqptuner`.

**Done when:** an audit and three structure jobs land, and every stop, bypass and owner edit they needed is written up as a defect or a design change.

## M3f. Thin feature job

`gauntlet run <brief.md>` drives outline, design, plan, spec, stubs, tests, red run, juror, lock, build and land, each with a single agent and no review rounds, on the runner, screens and land of M3s. Prosecutor, arbiter, examiner, review and bailiff are skipped and shown as bypasses.

- The planner's outline carries the shared-structure flag. Design runs between Outline and Plan with one architect and no rounds when the flag is set, and Stubs writes the design's stubs first.

**Done when:** a small brief against a fixture repository with Python and JS tests lands a green change, and the land screen lists every skipped stage; a fixture brief whose outline flags shared structure shows a design screen and leaves `design.md`; and a bug-fix fixture brief whose outline leaves the flag unset shows Design skipped by rule on the land screen.

## M7f. Feature pilot

Run Gauntlet on a real, established repository with a small change, for example `hqptuner`.

**Done when:** three jobs land, and every stop, bypass and owner edit they needed is written up as a defect or a design change.

## M8. Reopen

`core/reopen.py` and the reopen flow of §2: any role's `spec_defect`, `gauntlet reopen <id> <line>`, rerun of the Tests, Red run, Lock, Build, Review and Bailiff stages for the affected lines and steps only, `caps.reopen`.

Reopen covers Design: a DesignChange amends the job's own design and reruns the touched steps. A CoreMissing on a `blocked` step opens a structure job, shows its reason, and holds only the steps `startable` withholds; one on a `complete` or `partial` step becomes an offer on the land screen. Until M12, the structure job starts when the feature job has no startable step left.

**Done when:** a reopen on one spec line reruns only that line's tests and the steps that serve it, and the amendment shows on the land screen; a DesignChange on one step reruns only the steps the amendment touches; a three-step fixture job whose second step is blocked on a CoreMissing builds its disjoint third step, opens one structure job, and after that job lands runs the second step from Stubs and lands; and a fixture job whose step offers a candidate lands with no structure job opened after the owner declines it.

## M9. Brief conversation and discovery

`gauntlet new` with the brief-writer, and the detective answering the planner's questions in one batch.

**Done when:** a job started by conversation lands, and the discovery table's citations all resolve against the tree.

## M10. Audit jobs

`gauntlet audit <scope>`: the auditor per test file, selected rows becoming a job that starts at Spec and skips Stubs, Build and Review.

**Done when:** an audit of a fixture test file with a planted policy violation yields a `STRIKE` or `AMEND` row, and that row lands as a job.

## M11. Repo roles and skills

Loading `.gauntlet/roles/` and `.gauntlet/skills/`, routing by description, and validation that a role body cannot widen its kind or answer schema.

**Done when:** a repo implementer and repo tester sharing a skill each take a step and a spec line in one job, and a role file that claims extra tools launches with its kind's tools only.

## M12. Epics

`gauntlet epic`: split with one prosecutor round, `core/schedule.py`, parallel jobs only on non-overlapping declared files, structure jobs, audit picks and spawns alike, run under `startable` (one job per candidate, parallel on disjoint declared files, in sequence on overlapping ones, a spawned one starting at once beside its feature job), revision by a fresh coordinator, `open_job` / `job_status` / `job_record`.

**Done when:** a three-job fixture epic with one dependency runs the two independent jobs in parallel, starts the dependent job from `main` after its dependency lands, and lands all three; and two selected structure candidates on disjoint files run in parallel while two on overlapping files run in sequence.

## M13. Self-hosting

Gauntlet builds its own next change.

**Done when:** a change to Gauntlet lands through Gauntlet with no bypass.

## Open questions

These are decided by evidence from the milestone named, not ahead of it.

| Question | Settled by |
|---|---|
| Is a fresh container per launch fast enough, or is a warm pool needed, and does a pool break "removed when the launch ends"? | M0 timing, M3s wall clock |
| What do round caps of 2 cost per job in tokens, and do real plans pass inside them? | M7s trace |
| Does the trimmed interface view give testers enough to write tests that collect? | M5, M7 |
| Does `stubgen` handle the pilot repository's dynamic modules? | M5 |
