---
phase: 2
status: complete
completed: 2026-11-08
---

# Phase 2: Test gate and shared layer - Summary

A three-job GitHub Actions gate (`tests`, `fixtures`, `lint`) enforcing the 85/85 coverage policy, fence name patterns, `FENCE_HIDE` and the fence `commit` tool, and the shared `.shared/pin.py`, `.shared/red.py`, `.shared/rounds.py` and `.shared/working-folder.ts` cores with their suites; measured coverage 97.87% lines, 93.14% branches.

## What shipped

- CI gate enforcing the accepted testing policy - `.github/workflows/ci.yml`, `.github/cadence/coverage-policy.json`, `.github/cadence/coverage-report-check.mjs`, `pyproject.toml`, `.planning/config.json`
- `slug` - `.shared/pin.py`, suite `.shared/tests/test_pin.py`, loader `.shared/tests/shared_helpers.py`
- Red-run reader - `.shared/red.py`, suite `.shared/tests/test_red.py`
- Working-folder guard - `.shared/working-folder.ts`
- Fence name patterns and `FENCE_HIDE` - `fence/files.py`, `fence/files_helpers.py`, suites `fence/test_files_patterns.py`, `fence/test_files_hide.py`
- Fence `commit` tool with path recording - `fence/files_commit.py`, suite `fence/test_files_commit.py`; the two D-04 commit rules in `docs/superpowers/specs/runtime-model-design.md` "Commit model"
- Round ledger (`state`, `docket`, `screen`, `record`, `close`) - `.shared/rounds.py`, `.shared/tests/rounds_helpers.py`, `.shared/tests/test_rounds.py`
- `fence/checks.py` characterization tests (D-09) - `fence/test_checks.py`

## Commits

| Plan | Task | Commit | Description |
|---|---|---|---|
| 1 | 1 | 516f0c0 | Enforce the accepted testing policy in GitHub Actions |
| 1 | 2 | 1dc5bf2 | Omit test files from the coverage measurement |
| 1 | 3 | 4a8a7c3 | slug suite, red against a null stub (AC7) |
| 1 | 4 | eaf68a5 | Implement slug in `.shared/pin.py` |
| 1 | 5 | 3f6ee43 | red suite, red against a null stub (AC7) |
| 1 | 6 | 171dea3 | Implement `.shared/red.py` |
| 1 | 7 | 6a89b9e | Add the working-folder guard module |
| 2 | 1 | 78cafcf | Name-pattern suite, red against the literal-folder reading (AC7) |
| 2 | 2 | d3a98f2 | Implement name patterns in the fence |
| 2 | 3 | ea701b2 | FENCE_HIDE suite, red against a fence that ignores it (AC7) |
| 2 | 4 | 3548b3e | Implement FENCE_HIDE in the fence |
| 2 | 5 | b38a777 | State the two commit-tool rules of D-04 in the runtime model |
| 2 | 6 | 0084754 | Commit suite, red against a null stub (AC7) |
| 2 | 7 | 8b92fc0 | Implement the commit tool and path recording |
| 3 | 1 | 3e2fb67 | Ledger-state suite, red against a null stub (AC7) |
| 3 | 2 | 52a6f1a | Implement the ledger state in `rounds.py` |
| 3 | 3 | b048fa5 | docket, screen, record and close suite, red against the stubs (AC7) |
| 3 | 4 | e594138 | Implement docket, screen, record and close; fixes the `guarded()` test helper TypeError from b048fa5 |
| 3 | 5 | 9c83375 | Characterize `fence/checks.py` |

## Deviations

- Plan 3, Task 2 (52a6f1a) was not green: `.shared/tests/test_rounds.py` ran "4 failed, 90 passed" (the `test_next_names_the_author_a_slot_or_vacant` cases with `start` None), although `reports/plan-3.md` records "121 passed". The next test commit, b048fa5, changed those cases' `start` from None to 0 and added `start=0` to `test_next_is_never_vacant_without_a_retiring_verdict`, and its message does not say so. The corrected inputs match `runtime-model-design.md:42,56`; code and tests are right from b048fa5 on. Found by the Phase 2 deep verify.

Otherwise plans executed as written. Execution path: the parallel worktree attempt for Plans 1 and 2 halted `blocked` before Task 1 with no commits, because the host names worktree branches `worktree-agent-*` and the dispatch assigned `cadence/phase-2-plan-<k>`; all three plans then ran sequentially in the main tree.

## Open items

- AC2 / CI is human-verify at /cad-verify (D-10): push the branch and read `tests`, `fixtures`, `lint` and both coverage figures on Actions. The `fixtures` job is untested: nobody has checked that `archon workflow test` works on a runner with no provider configured.
- `archon validate workflows` reports "4 valid, 23 with errors" (`No default provider: set 'defaultAssistant'`), all on other workflows and host config; the count is unchanged by this phase and `archon workflow list --json` shows `"errors": []`.
- `risk_surface` plan-1 finding, medium, confirmed and not fixed, declined by the owner (`.planning/DECLINED.md`): `.shared/working-folder.ts:40` treats any ignore-rule source whose basename is `.gitignore` as a repo `.gitignore`, so a global excludes file at e.g. `~/.gitignore` makes `requireIgnored({committed:true})` fail where the design says it passes.
- Fence `commit` tool: on a failed commit it returns every executable `pre-commit`, `prepare-commit-msg` and `commit-msg` in the hooks folder, not the one that failed (narrowing needs output parsing, which D-04 forbids). A failing `rev-parse`, `status` or `add` raises `CalledProcessError` instead of returning `exit=<n>`. A hanging hook holds the commit lock with no timeout.
- Untested branches: `fence/files_commit.py` rename branch of the porcelain parse (line 45) and second-attempt break (68->79); `.shared/rounds.py` `_refusal` branches beyond a bogus mode (lines 362, 364, 366). `rounds.py` has no slug-collision handling beyond the `.md` rule for `-summary.` files.
- `.shared/rounds.py` is 399 lines, one under filepawl's 400-line watch line.
- Runtime model vs spec-review-design signatures (runtime model governs): `close` takes `start`; `state` gets a `filing` keyword; `docket` gets `start` and `base` keywords; the functions return named TypedDicts.
- Runtime-model tension: twelve consecutive `OBJECTION: LEADING` reviews also make `stretch` 12, so `owed` reads `owner` (guard) with no guard record in the hearing; `next` reads `vacant` either way. The suite pins `owed` = author at the twelfth LEADING with a guard record at round 5.
- Choices made where the runtime model is open (Plan 3 report): `owed` order approved, ended, owner, author, reviewer; rulings parsed only from their `Case:` and `Decision:` lines; guard entries one JSON line each; iteration lines `<round> <owed> <guards> <repairs>`; exit 2 for unusable inputs, exit 1 only for an existing review or ruling.
- Temp directories left under `/tmp` because the host hook blocks `rm -rf`: `/tmp/wf.5NRLhI`, `/tmp/tmp.TH5ww6JfhA`, `/tmp/tmp.yMcacKsz5z`, `/tmp/tmp.94D7WlEyEY`, `/tmp/cad-adj-7Qo0vD`. No processes left running.

## Goal check

The commits plausibly deliver the phase goal. The policy gate exists as three Actions jobs (516f0c0, `.github/workflows/ci.yml`) with the 85/85 thresholds held in `.github/cadence/coverage-policy.json`, and Plan 3's report records the coverage check exiting 0 at 97.87% lines and 93.14% branches with no threshold lowered and nothing excluded (9c83375); the shortfall Plan 1 measured (71.87/80.85, `fence/checks.py` at 0%) is closed. Every named shared piece has a commit and a suite: fence name patterns (d3a98f2), `FENCE_HIDE` (3548b3e), the fence `commit` tool (8b92fc0), `.shared/rounds.py` (52a6f1a, e594138), `.shared/red.py` (171dea3) and `.shared/working-folder.ts` (6a89b9e); the final run reported fence 135 passed and `.shared/tests` 218 passed, and each implementation follows a red commit (AC7). What is not shown here: the gate has never run on Actions, so its first real figure and the `fixtures` job on a provider-less runner are unverified, and `working-folder.ts` carries one confirmed, declined defect (global excludes file named `.gitignore`).

complete locally, not CI-verified
