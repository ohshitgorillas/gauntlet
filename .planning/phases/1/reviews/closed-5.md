# Closed review of the pass-5 ruling draft (D-79), G-129 to G-131

Artifact: `git diff HEAD` at `43cb8a4` (specs under `docs/superpowers/specs/`, `CONTEXT.md` D-105 to D-107, `RULINGS.md`, `reviews/homes-4.md`), against `REVIEW-pass5.md` sections 1 to 3 (option (b) for each group). Q1: does the edit close the members' scenario. Q2: does it add a high or medium defect. Lows are not reported. No Archon experiment was run; Archon behaviour is cited from `docs/reference/archon/` only.

## G-129 (D-105)

Q1: yes. The 5.01 scenario is a bash test run dirtying the tree before `pose` or the next cut's `clean`. `retest` now restores the tree (`landing-design.md:173`, "as test-tree, the restore included"), as do `test-tree` (`:74-76`) and `test-head` (`:93`). `pose` no longer reads the porcelain; it reads `$leftover.output.file` (`:216-217`), and node `leftover` runs before `retest` (`:159-167`, `retest` depends on it at `:170`). So a `uv.lock` that `retest` relocks is restored, and `pose` does not read it as `commit-failed`. Writing's node `test` restores after its run (`writing-design.md:512-513`), so the next cut's `clean` (`:337-340`) no longer sees a file that `test` made. The home states the rule at `runtime-model-design.md:144`.

Q2: yes, two mediums: point (1) and point (2) below.

Point (1), seal: yes, medium.
- RUN-10 (`.planning/REQUIREMENTS.md:46`) and ROADMAP criterion 2 (`.planning/ROADMAP.md:83`) are both conditional: "a clean tree gets no final commit". A `seal` that always writes `nothing` does not break their letter, so on that count there is no defect.
- In a real run, the seal can no longer commit anything. `result` restores every uncommitted change after each wave (`runtime-model-design.md:140`). `test` restores after its run (`:144`; `writing-design.md:512-513`). `state` puts `seal` right after a run ("no seal since the latest run: seal", `writing-design.md:171`), and nothing in between writes outside the ignored `gauntlet/`. So `seal` always sees a clean tree (`runtime-model-design.md:148`). The D-78 subject and the summary body (`:150`) never reach the branch. The summaries do still reach the owner through `show`.
- The defect is what replaced the seal's commit. Before the draft, the seal committed what writers left uncommitted (`:149`). One such case is a committed block's extras: the commit tool commits only the paths it is handed (`:132-135`). Now `result` patches those extras and restores them away, a committed block's extras explicitly included (`:140`; `writing-design.md:186-188`). But the patch is "named in the amicus case's files when a case opens". `state` opens no case for a leftover patch: its cases are contest, commit-failed or blocked in the blocks file, red, and seal failure (`writing-design.md:160-165`). `final-review` does not read `gauntlet/write/` leftover patches either (`landing-design.md:229-231`).
- Scenario: a coder edits `src/a.py` and `src/b.py`, both inside its `paths`, and commits with `[src/a.py]`, so the outcome is `committed`. `result` writes `leftover.<move>.patch` holding `b.py` and restores it away. `test` is green because `b.py` is a config or doc that no test covers. `seal` writes `nothing`, the review before landing sees only `a.py`, and the owner lands. The `b.py` work is silently gone from the branch, and no node tells the owner. Before the draft, `seal` would have committed it as `<slug>: final` (RUN-10's purpose), or the next block's `clean` would have marked it `blocked` (a visible case).
- Anchor: `runtime-model-design.md:140` ("The patch is named in the amicus case's files when a case opens").

Point (2), residual: yes, medium. This was not introduced by the draft, but the draft does not close it. Its premises at `runtime-model-design.md:140` and `:142` ("every uncommitted change at this check is that mender's own") and the new fixture branch at `landing-design.md:286` encode it.
- Every writer and both menders run the brief command in-session through `fence/checks.py` (`writing-design.md:638`). That run has no restore: D-105 restores only bash runs (`runtime-model-design.md:144`).
- Writing scenario: the brief command is `uv run pytest` and `uv.lock` is tracked. In a wave of blocks b1 and b2 (`max_parallel: 1`), b1's coder calls `fence-checks`, which relocks `uv.lock`, and commits its own paths. `result` runs only after the whole wave (`:140`). So b2's `clean` (`writing-design.md:337-340`) sees `uv.lock` outside b2's `paths` and prints `blocked` with grounds `uv.lock`. The amicus gets a false `blocked` case. The owner directs `code`, and the carried b2 runs in the next wave. If that wave has another block after a checks.py-running writer, the same thing happens again, so each owner turn advances only one block per wave. This is a stop on a non-issue (CLAUDE.md 1.4).
- Mend scenario: `mend-code` calls `fence-checks` (`uv.lock` relocked) and commits its fix. `leftover` (`landing-design.md:159-167`) sees `uv.lock`, writes `leftover.<n>.patch` and prints its path. `pose` (`:216-217`) reads `commit-failed` though the mend is committed and green, and the amicus briefs a failed commit that did not happen. The fixture codifies this (`:286`, "a mender that committed with an edit left over ... case `commit-failed`"). The owner can escape by answering `again`: `leftover`'s `when` skips it (`:162`), `retest` restores, and the case can reach `review`. But every `rework-code` or `rework-tests` iteration in such a repository costs one false `commit-failed` turn, one amicus turn and one owner answer.
- Anchors: `runtime-model-design.md:142`, `writing-design.md:337-340`, `landing-design.md:216-217`.

## G-130 (D-106)

Q1: yes. Every block record now holds `stage` (`writing-design.md:42`, `:185`; contracts H49 at `contracts.md:69`). `changes` prints `blocks`: the tree's blocks files whose records hold `stage` equal to `$INPUTS.stage` (`landing-design.md:132-136`). `final` is handed `$changes.output.blocks` in place of the glob (`:231`), and the role text says the earlier stages' files are not handed to it (`:514`). A stage-1 `blocks.4.json` that `copy-in` brought into stage 2 holds `stage` 1, so it is not handed to stage 2's `final`.
Q2: no. Tried and refuted: a back to planning restarting the stage count at 1 (`back.py` moves every `gauntlet/write/` file of the slug into `stale/`, `gauntlet-design.md:193-195`, and the glob does not recurse into `stale/`); a slug that is a prefix of another (`<slug>.blocks.` is dot-delimited); `result` lacking the stage (`INPUTS_STAGE` is a block input in `stage.py`'s env, `writing-design.md:113`); an empty list (`blocks ""`, `landing-design.md:135`).

## G-131 (D-107)

Q1: yes. (a) The defense reads `<slug>.txt` and then each `<slug>.rev<N>.txt` in order of N, from the `approved/` folder of the highest-numbered `stale/<slug>.<m>/` (`plan-review-design.md:152-155`). That is the P3 definition of the approved plan. (b) The layout is stated in the home: `runtime-model-design.md:44` says a file's path under `stale/<slug>.<n>/` equals its path under the folder and no `approved/` file is flattened; the table row is at `:27`. `back.py`'s comment points to it (`gauntlet-design.md:195-196`), and `test_back.py` fails on a flattened file (`:202`). H55 is widened (`contracts.md:71`).
Q2: no. Tried and refuted: `m` differing per folder (`gauntlet-design.md:195`; the defense reads `gauntlet/plans/stale/` only); the ledger's item-hash set-aside taking the highest number after a back (the back also moves `<slug>.items.sha256`, so `docket-in` finds it absent and sets nothing aside, `runtime-model-design.md:44`).

## Findings

```json
{ "findings": [
  { "file": "docs/superpowers/specs/runtime-model-design.md",
    "line": 140,
    "severity": "medium",
    "claim": "G-129: result now patches and restores a committed block's uncommitted extras, but no state rule opens a case for a leftover patch, and test restores too, so seal always sees a clean tree; work a writer left uncommitted, which the seal used to commit as <slug>: final, is now silently dropped from the branch.",
    "failure_scenario": "Coder edits src/a.py and src/b.py inside its paths and commits [src/a.py] (outcome committed); result writes leftover.<move>.patch for b.py and restores it; test is green; seal writes nothing (runtime-model-design.md:148); no amicus case (writing-design.md:160-165); final-review reads only changes and this stage's blocks files; the owner lands without b.py and is never told." },
  { "file": "docs/superpowers/specs/runtime-model-design.md",
    "line": 142,
    "severity": "medium",
    "claim": "G-129 residual: a writer's or mender's in-session fence/checks.py run of the brief command is not restored, so leftover and clean still read its tree changes as an agent's.",
    "failure_scenario": "Brief command uv run pytest, uv.lock tracked. Writing: b1's coder runs fence-checks (uv.lock relocked) and commits; in the same wave, b2's clean (writing-design.md:337-340) marks b2 blocked on uv.lock, a false amicus case each wave. Mend: mend-code runs fence-checks and commits; leftover (landing-design.md:159-167) writes a patch; pose (:216-217) reads commit-failed on a committed, green mend; every rework iteration costs a false case and an owner turn (fixture :286 encodes it)." }
] }
```
