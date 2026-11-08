# Closed review of the pass-6 ruling draft (D-79)

Reviewed: `git diff HEAD` at HEAD `19d4e1b` (the six designs named in the brief, `contracts.md`, CONTEXT.md D-109 and D-110, RULINGS.md "Pass 6 rulings", `reviews/homes-4.md`) against `REVIEW-pass6.md` sections 1 to 3 (findings 6.01 to 6.06, groups G-132 to G-137, each ruled (b)). Archon behaviour is cited from `docs/reference/archon/` only. No experiment ran. Lows are not reported.

## G-132 (D-109): `next` is `vacant` first

1. Closes the scenario: yes. `docs/superpowers/specs/runtime-model-design.md:42` makes `vacant` win whoever owes the round. So `docket` reads case `vacant` in the same iteration as the twelfth LEADING review, `until_bash` ends the loop, and `defend` (gated `next != 'vacant'`, `plan-review-design.md:343`) never runs. The pins are at `plan-review-design.md:477`, `spec-review-design.md:532` and `spec-review-design.md:118`.
2. New high or medium defect: no.

## G-133: the commit tool reads `-z -uall -- <listed paths>`

1. Closes the scenario: yes. `docs/superpowers/specs/runtime-model-design.md:136` makes porcelain name `tests/auth/test_login.py` by its own path, so the path is kept and committed. The pin is at `writing-design.md:66`.
2. New high or medium defect: no. Block `paths` list files (`writing-design.md:26`), so the rule that keeps "each listed path the output names" does not depend on the listed entry being a directory.

## G-134 (D-110): node `settle`

1. Closes the scenario: yes. `docs/superpowers/specs/landing-design.md:59-68` saves and restores the failed mender's edit before `rebase`. `landing-design.md:71` puts `rebase` after `settle`, so `rebase` no longer meets the dirty tree. On an unmoved checkout, `landing-design.md:229` and `:232` open `commit-failed` in iteration 1 and name the patch. A later mender starts on a clean tree. The home is `runtime-model-design.md:119` and `:143`. The patch name `settle.<s>.patch`, with `s` one above the highest, overwrites no earlier patch. Skipping `settle` while a rebase is in progress is correct: a mender runs only after a successful `rebase`, so a failed mender's edit and a stopped rebase never coexist in the tree, and the skip leaves the owner's conflict resolution untouched.
2. New high or medium defect: yes, medium. A patch that `settle` writes on one resume is lost from the owner's view whenever that resume fails before `repair`'s first `pose`.
   - Anchors: `docs/superpowers/specs/landing-design.md:229`, `:232` and `:66-67`; `runtime-model-design.md:143`.
   - Scenario, step 1: `mend-code` edits tracked `src/a.py` and fails on a provider error. Meanwhile the checkout gains a commit.
   - Step 2, the first resume: `settle` writes `settle.1.patch`, restores the tree and prints `file` = that path. `rebase` then conflicts and exits 1 (`landing-design.md:76-77`).
   - Step 3: the owner resolves the conflict, runs `git rebase --continue`, and resumes again.
   - Step 4, the second resume: `settle` is `always_run`, so it is evaluated again and does not replay its earlier output (`docs/reference/archon/workflow-language.md:115`, `:993-1006`). It finds a clean tree and prints `file` "". The same happens if the owner resumes while the rebase is still stopped: the skip prints "".
   - Step 5: in iteration 1, `pose` reads `$settle.output.file` "". It opens no `commit-failed` and leaves `settle.1.patch` out of the amicus case's files.
   - Step 6: the case is computed from the rebased tree alone. If that tree is green, the case is `review` and `land` is offered. The owner is never told that the mender's work was saved and removed from the tree.
   - Why it is introduced: no other node and no other reader names `.settle.*`. `copy-in` even excludes these patches (`landing-design.md:459`). The ruling's stated outcome, "first iteration of the group opens case `commit-failed` from that patch" (`runtime-model-design.md:119`), fails on the moved-checkout path that the finding itself describes.
   - Test gap: the `settled` fixture (`landing-design.md:301`) pins only a single resume.

## G-135: node `baseline` restores the tree

1. Closes the scenario: yes. `docs/superpowers/specs/worktree-cut-design.md:194-195` ends the run with the restore, so a relocked `uv.lock` is gone before the first block's `clean`. The home's list is at `runtime-model-design.md:145`, and the Homes rows are at `worktree-cut-design.md:279` and `writing-design.md:637`. The tree is clean at `baseline`: only `copy-in` and `settings` write it, and both write under the ignored `gauntlet/`.
2. New high or medium defect: no.

## G-136: the direction's N is one above the highest move

1. Closes the scenario: yes. `docs/superpowers/specs/writing-design.md:215-216` and `:225` give the direction the N that `docket` gave the amicus record (`:205`). The amicus record counts as no move (`:35`, `:48`), and `record` is the body's first node, so no move is written between `docket`'s naming and `record`. `discuss` iterations do not change the highest move either. So `direction.8.md` and `amicus.8.md` share N, and `close` hands off an existing file. The pin is at `:232`.
2. New high or medium defect: no. The direction file matches the move form `<slug>.<kind>.N.<ext>` (`:29`) and is not excluded the way the amicus record is. So the next cut takes N 9, and no later "since the latest direction" comparison ties.

## G-137: the no-plan first cut is `INPUTS_SPEC` and its approved revisions

1. Closes the scenario: yes. `docs/superpowers/specs/writing-design.md:28` and `:169` give a non-empty cause on the `plan` "" route. `INPUTS_SPEC` is an absolute tree path (`gauntlet-design.md:331`), which fits the "tree paths" form of the cause. `:244` tells the divvyer to cut the specs alone, and `:607` adds the fixture. On the first cut ("no direction and no round") no spec revision of this stage can exist yet, so adding "its approved revisions" is harmless.
2. New high or medium defect: no.

## Findings (reviewer schema)

```json
{ "findings": [
  { "file": "docs/superpowers/specs/landing-design.md",
    "line": 229,
    "severity": "medium",
    "claim": "pose reads only the current resume's $settle.output.file, so a settle patch written on a resume that then fails before repair (a rebase conflict) is never counted as commit-failed nor named to the owner.",
    "failure_scenario": "mend-code fails with src/a.py edited; the checkout moves; resume 1: settle writes settle.1.patch and restores, rebase conflicts, exit 1; the owner continues the rebase and resumes; settle is always_run (workflow-language.md:115, :993-1006), finds a clean tree and prints file \"\"; pose in iteration 1 opens no commit-failed, the files omit settle.1.patch, and on a green rebased tree the owner is offered land with the mender's saved work never mentioned." }
] }
```
