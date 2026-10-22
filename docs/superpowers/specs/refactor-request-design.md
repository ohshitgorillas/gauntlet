Status: proposed, for the owner's approval.

## Why

A request to restructure code without changing what it does has no path through Gauntlet. A STRUCTURE job opens only from a finding, and every spec line must start out failing, which a line that pins behavior the code already has cannot do. The pieces of this design (the planner's choice of a refactor path on the outline, with the owner's override; the hand-off of a refactor request to a STRUCTURE job and the candidate it opens with; and a red-run rule for lines that pin existing behavior) share one Candidate record, one opener, one spec line record and one red-run rule.

- **A STRUCTURE job opens from two places only: 2 entries, 4 restatements.** A CoreMissing on a build step (`docs/design.md:94`) and an audit pick (`docs/design.md:100`). The `Shape.STRUCTURE` comment, the opening bullet, the home of `open_structure` and `docs/design.md:32` name those two and no other. A request enters through `gauntlet run <brief.md>` (`docs/roadmap.md:104`) or `gauntlet new` (`docs/roadmap.md:132`), both of the JOB shape.

- **The outline carries one routing flag, and none for a refactor.** The planner's outline returns a shared-structure flag and the owner approves or redirects it (`docs/design.md:38`); `needs_design` is its one reader. Nothing on the outline says a request changes no behavior, so no stage the planner reaches can send a request to a STRUCTURE job.

- **The red-run rule, 3 copies, none with an exception.** "every line `RED`" (`docs/design.md:44`); "A `GREEN` verdict at the red run sends the line to the arbiter" (`docs/design.md:64`); "A test that passes before any implementation exists reopens its spec line" (`docs/design.md:68`).

- **Keeps lines meet that rule with no rule of their own, 3 places.** A STRUCTURE job's SPEC carries each of its candidate's `keeps` lines as a spec line, locked before any port step. A keeps line pins behavior the copies already carry, so its test passes at the red run and reopens under `docs/design.md:68`. The gap holds for every audit pick, not only for a direct request.

- **Two producers of a Candidate, none for a request.** The surveyor's `Survey.candidates` and an implementer's `CoreMissing.candidate`. A direct request has neither, so it has no copies for `uncovered` to check at DESIGN.

- **Nothing marks a spec line as a keeps line.** No document defines a spec line record. The Spec row returns behavior lines `S1…` with `bite:` values (`docs/design.md:41`), and nothing records which of them carries which `keeps` line, so nothing can tell a line that may start out passing from one that may not.

- **No copy of these concerns in code.** `gauntlet/` holds only three empty files, `gauntlet/__init__.py`, `gauntlet/core/__init__.py` and `gauntlet/seams/__init__.py`, and nothing under `gates/` or `tests/` holds a job shape, a candidate or a red-run rule. Every copy above is in the documents the code will be built from.

## Modules

Core imports run `verdicts` ← `red` ← `decide`; `red` imports nothing else of the core. `SpecLine` and `RedVerdict` are M1's answer records (`docs/superpowers/specs/gates-core-design.md:370`): this design stubs only the fields it needs, and M1's design names their other fields and may rename them. `Runner` is M2's process-running seam (`gates-core-design.md:378`). `Outline` and `State` are M1's types (`structure-first-design.md:21`); `is_refactor` lives in `design.py`, which keeps its place in the structure-first chain, `verdicts` ← `design` ← `causes` ← `decide` (`structure-first-design.md:21`). A refactor request opens no new shape: it is a STRUCTURE job (`docs/design.md:102`).

**`gauntlet/core/verdicts.py`** (amended). Gains the keeps mark on a spec line, the juror's verdict per line, the owner's words on a Candidate, the planner's choice of path on the outline (decision 1), and the MISPLACED category (decision 5). It replaces nothing; it adds to the records at `structure-first-design.md:31`-`53`.

```python
class Category(StrEnum):
    ...  # the five values of the structure-first spec
    MISPLACED = "misplaced"  # code a request moves to a new home, with every caller in `also` (decision 5)


class RedVerdict(StrEnum):  # the juror's verdict per spec line (docs/design.md:44)
    RED = "red"
    ERROR = "error"
    GREEN = "green"
    INVALID = "invalid"
    COULD_NOT_JUDGE = "could-not-judge"


@dataclass(frozen=True)
class SpecLine:  # M1's spec line record; its other fields are M1's
    id: str  # "S1", stable across amendments (docs/design.md:90)
    keeps: str | None = (
        None  # the Candidate.keeps line it carries, verbatim; None on any other line
    )


@dataclass(frozen=True)
class Outline:  # M1's outline answer; its steps, implementers, areas and shared-structure flag are M1's
    structure_only: bool = False  # the planner's choice of path: True when the brief asks to restructure without changing behavior (decision 1)


@dataclass(frozen=True)
class Candidate:  # the structure-first record with one field more
    concern: str
    payoff: str
    risk: str
    keeps: tuple[str, ...]
    why: str | None = None
    asked: str | None = (
        None  # the owner's request verbatim; set only by `cli.run`'s hand-off, from the JOB's brief (decision 6)
    )
```

`finding_problems` checks MISPLACED as it checks MISSING: it needs an `also`, a concern and `blocking` (decision 5).

**`gauntlet/core/red.py`** (new). Which verdict each spec line must have at the red run, whether a spec's keeps lines are exactly its candidate's, and whether each keeps test bites. It replaces the red-run rule at `docs/design.md:44`, `:64` and `:68`.

```python
def expected(line: SpecLine) -> RedVerdict    # GREEN for a keeps line, RED for any other
def red_problems(lines: Sequence[SpecLine], verdicts: Mapping[str, RedVerdict]) -> tuple[str, ...]
def keeps_problems(lines: Sequence[SpecLine], keeps: Sequence[str]) -> tuple[str, ...]
def bite_problems(lines: Sequence[SpecLine], stubbed: Mapping[str, RedVerdict], touched: Collection[str], copies: Sequence[Anchor]) -> tuple[str, ...]   # decision 3
```

- `red_problems` names each line with no verdict and each whose verdict is not `expected(line)`. `INVALID` and `COULD_NOT_JUDGE` are never expected, so they always fail. A keeps line that is RED pins behavior the tree lacks; any other line that is GREEN passes before anything is built. Each named line goes to the arbiter, which rules whether the spec or the test is at fault.
- `keeps_problems` names each of `keeps` that no line carries, each line whose `keeps` is not one of `keeps`, and each of `keeps` carried by two lines. A JOB has no candidate and is checked with `keeps` empty, so any keeps line in its spec fails: only a STRUCTURE spec holds a line that may start out passing.
- `bite_problems` names each path in `touched` that no anchor in `copies` lies in, and each keeps line whose verdict on the stubbed tree is GREEN or absent (decision 3). The stubbed tree is the job tree with the body of each function holding a copy anchor replaced by a raise. The examiner writes those files; the harness's runner runs the keeps tests on them, and the examiner's own account of outcomes never counts.

**`gauntlet/core/causes.py`** (amended). Gains the check that a survey focused on one request answers it with one candidate. It replaces nothing.

```python
def focus_problems(survey: Survey) -> tuple[str, ...]
```

- `focus_problems` names a survey with no candidate and one with more than one. Beside `survey_problems` (`structure-first-design.md:155`), which ties every candidate to a cause and every cause to anchored findings, it holds a direct request to one candidate with at least one copy.

**`gauntlet/core/design.py`** (amended). Gains whether an approved outline sends its request down the STRUCTURE path (decision 1). It replaces nothing and sits beside `needs_design` (`structure-first-design.md:113`), the other reader of the outline.

```python
def is_refactor(outline: Outline, override: bool | None) -> bool
```

- `is_refactor` returns the owner's override where the owner gave one at the outline screen, and the planner's `structure_only` otherwise. `override` is the owner's ruling as M1's State records it, `None` when the owner approved the outline as the planner wrote it.

**`gauntlet/core/decide.py`** (amended rows). The interface is unchanged; these rows join the stage table.

```python
def decide(state: State, answer: Answer) -> Action   # M1's signature; the rows below are added
```

- OUTLINE: an approved outline for which `is_refactor` holds goes to neither DESIGN nor PLAN; the next action is the focused survey. On the owner's approval of its candidate the JOB ends at OUTLINE as handed off, its `state.json` naming the STRUCTURE job it opens, and that job starts at DESIGN by `FIRST` (decision 6). A survey that is `COULD NOT JUDGE`, or a declined candidate, stops the JOB at its stop screen. Any other approved outline goes on by the OUTLINE row of `structure-first-design.md:185`.
- SPEC: a spec with any `keeps_problems` against the job's candidate's `keeps`, empty for a JOB, is a failed round under `caps.spec`, beside the arbiter's rulings.
- RED_RUN: the gate is `red_problems` returning nothing. Each line it names goes to the arbiter.
- Between RED_RUN and LOCK, a STRUCTURE job with keeps lines runs the bite check (decision 3): the examiner returns the stubbed files, `run_stubbed` runs the keeps tests on them, and each line `bite_problems` names goes to the arbiter. Until M4 builds the examiner, the check is recorded as skipped and shown as a bypass on the land screen.

**`gauntlet/seams/cli.py`** (amended). Gives `gauntlet run` the hand-off of a refactor request to a STRUCTURE job (decisions 1, 6). It replaces nothing and opens a STRUCTURE job only through `open_structure`.

```python
def run(brief: Path) -> int   # gauntlet run <brief.md>
```

- When `decide` returns the focused survey after OUTLINE, `run` launches the surveyor over the checkout with the brief's text as its focus, then the grouper (decision 2). A survey that fails `survey_problems` or `focus_problems` is `COULD NOT JUDGE`. `write_survey` (`structure-first-design.md:203`) writes the survey as any structure audit's. The survey screen shows the brief, then the one candidate. On the owner's approval, `run` sets the candidate's `asked` to the brief's text and opens the STRUCTURE job through `open_structure` with its cause's anchors as the copies. That job runs as every STRUCTURE job does: DESIGN first, nothing skipped.
- `run` takes no flag that sets the path: the owner overrides the planner's choice at the outline screen alone (decision 8).

**`gauntlet/seams/screens.py`** (amended). The outline screen shows the planner's choice of path and takes the owner's override of it (decision 1); the survey screen shows a direct request's words above its candidate. `outline_screen` is the outline's approval screen (`docs/design.md:38`), named here with the path it gains. It replaces nothing.

```python
def outline_screen(outline: Outline) -> Screen   # steps, implementers, areas and flag, then the planner's path; approve, redirect, or override the path
def survey_screen(survey: Survey, causes: Sequence[Cause], asked: str | None = None) -> Screen   # with asked: the request, then the one candidate; approve or decline
```

**`gauntlet/seams/runner.py`** (amended, decision 3). Runs keeps tests on the stubbed tree. It replaces nothing.

```python
def run_stubbed(tree: Path, files: Mapping[str, str], ids: Sequence[str], runner: Runner) -> Mapping[str, RedVerdict]
```

- `run_stubbed` writes `files` (path to whole text) onto a scratch overlay of `tree`, runs `ids` with every runner in `gauntlet.yaml` and the harness's own pytest settings (`docs/design.md:186`), and maps pass to GREEN, fail to RED and error to ERROR. The keys of `files` are the `touched` that `bite_problems` checks.

**`roles/`** (amended). Three roles gain a duty; each runs in its existing kind (`docs/design.md:110`-`115`).

```text
roles/surveyor.md   reader   answer: Survey; given a focus, one candidate for the request, findings COPY, MISSING, MISPLACED   (decisions 2, 5)
roles/planner.md    reader   answer: Outline with `structure_only` set when the brief asks to restructure without changing behavior   (decision 1); spec lines, in a STRUCTURE job each keeps line carried by one SpecLine with `keeps` verbatim
roles/examiner.md   scratch  answer: the stubbed files, path to whole text, each function holding a copy anchor raising   (decision 3)
```

**`tests/support/answers.py`** (amended). Builders for the records above. It replaces nothing.

```python
def spec_line(*, id: str = ..., keeps: str | None = ...) -> SpecLine
def outline(*, structure_only: bool = ...) -> Outline
def candidate(*, concern: str = ..., keeps: tuple[str, ...] = ..., why: str | None = ..., asked: str | None = ...) -> Candidate
```

## Homes

| Concern | Home | Forbids elsewhere |
|---|---|---|
| Whether a request is a refactor | the planner's `Outline.structure_only`, which the owner's override at the outline screen replaces, read only by `is_refactor` in `gauntlet/core/design.py` (decision 1) | Any other role, `decide` or a seam choosing it. A STRUCTURE path the owner has not seen on the outline screen. A flag or second screen where the owner sets it (decision 8). A new shape for a refactor request. |
| The candidate and copies a direct request opens with | the surveyor's focused survey after an approved refactor outline, checked by `survey_problems` and `focus_problems` (decision 2) | A brief-writer, planner, architect or seam writing a Candidate or naming copies for a request. |
| The owner's words on a STRUCTURE job | `Candidate.asked`, set only by `cli.run`'s hand-off from the JOB's brief | A second field or file carrying the request into the job. A role rewriting it. |
| Opening the STRUCTURE job a refactor request becomes | `open_structure` in `gauntlet/seams/job.py` (`structure-first-design.md:261`), after the JOB ends handed off (decision 6) | `run` making a job folder itself. A JOB going on past OUTLINE as a STRUCTURE job. |
| Which verdict a spec line needs at the red run | `expected` and `red_problems` in `gauntlet/core/red.py` | The rule restated at `docs/design.md:44`, `:64` and `:68`. A juror, seam or role deciding which lines may start out passing. |
| Which spec lines are keeps lines | `SpecLine.keeps`, checked against the candidate's `keeps` by `keeps_problems` | A keeps line in a JOB's spec. A keeps line the candidate does not carry. Any other field marking a line as one that may pass at the red run. |
| Whether a keeps test bites | `bite_problems` over `run_stubbed`'s run (decision 3) | A keeps line locked on a GREEN run alone once M4 lands. The examiner's own report of outcomes counted as the run. |
| A code move or rename as a finding | `Category.MISPLACED` (decision 5) | A move recorded as COPY or MISSING. |
| Test builders for these records | `tests/support/answers.py` | A builder or seed helper inside a test file. |

## Order

Each code step follows the repository's chain: stub, red tests from `test-writer` against the `stubgen` view, build, blind reviews and `make check`, one commit per chain. RQ-C1 to RQ-C3 wait on the structure-first plan's C1 to C3 and on M1's design naming the spec line and juror verdict records; RQ-C4 and RQ-C5 wait on its C5; RQ-C8 to RQ-C12 on its feature-phase C4a and C4b OUTLINE bullet (`docs/superpowers/plans/structure-first-plan.md:144`-`145`) and on M1's design naming `Outline`; RQ-R1 and RQ-S1 to RQ-S3 on its S1 to S6 and on M3f's `run` and outline screen (decision 7).

| Step | Milestone | Agent | Writes |
|---|---|---|---|
| RQ-D1 | before M1 | `general-purpose` (docs only, no red test) | `docs/design.md`, `docs/roadmap.md`, `docs/superpowers/specs/structure-first-design.md`, `docs/superpowers/plans/structure-first-plan.md` |
| RQ-C1 stub | M1 | `core-builder` | `gauntlet/core/verdicts.py`, `gauntlet/core/red.py`, `gauntlet/core/causes.py` |
| RQ-C2 red | M1 | `test-writer` | `tests/support/answers.py`, `tests/test_core_red.py`, `tests/test_core_causes_focus.py` |
| RQ-C3 build | M1 | `core-builder` | `gauntlet/core/red.py`, `gauntlet/core/causes.py` |
| RQ-C4 red | M1 | `test-writer` | `tests/test_core_decide_keeps.py` |
| RQ-C5 build | M1 | `core-builder` | `gauntlet/core/decide.py` |
| RQ-R2 | M4 | `role-author` | `roles/examiner.md` |
| RQ-S4 stub | M4 | `seam-builder` | `gauntlet/seams/runner.py` |
| RQ-S5 red | M4 | `test-writer` | `tests/test_seams_runner_stubbed.py` |
| RQ-S6 build | M4 | `seam-builder` | `gauntlet/seams/runner.py` |
| RQ-C6 red | M4 | `test-writer` | `tests/test_core_decide_bite.py` |
| RQ-C7 build | M4 | `core-builder` | `gauntlet/core/decide.py` |
| RQ-C8 stub | M3f | `core-builder` | `gauntlet/core/verdicts.py`, `gauntlet/core/design.py` |
| RQ-C9 red | M3f | `test-writer` | `tests/support/answers.py`, `tests/test_core_design_is_refactor.py` |
| RQ-C10 build | M3f | `core-builder` | `gauntlet/core/design.py` |
| RQ-C11 red | M3f | `test-writer` | `tests/test_core_decide_hand_off.py` |
| RQ-C12 build | M3f | `core-builder` | `gauntlet/core/decide.py` |
| RQ-R1 | M3f | `role-author` | `roles/surveyor.md`, `roles/planner.md` |
| RQ-S1 stub | M3f | `seam-builder` | `gauntlet/seams/cli.py`, `gauntlet/seams/screens.py` |
| RQ-S2 red | M3f | `test-writer` | `tests/test_seams_cli_run_hand_off.py`, `tests/test_seams_screens_outline_path.py`, `tests/test_seams_screens_asked.py` |
| RQ-S3 build | M3f | `seam-builder` | `gauntlet/seams/cli.py`, `gauntlet/seams/screens.py` |

RQ-D1 writes this design into the documents. In `docs/design.md`: the Outline row (`:38`) returns the planner's structure-only choice and its gate reads "you approve, redirect or override the path"; the Red run row's gate (`:44`) and the notes at `:64` and `:68` say every line at the verdict `expected` gives, RED or GREEN for a keeps line, with a pointer to `core/red.py`; `:32`, "Reopening the spec" (`:94`) and "Audit jobs" (`:100`) add the hand-off of an approved refactor outline as the third opener of a STRUCTURE job; §8 adds `red.py` and `run`'s hand-off (`:288`). In the structure-first spec, at their home, `Category` (`:31`-`36`) gains MISPLACED, `Candidate` (`:47`-`53`) gains `asked`, `needs_design` (`:113`) gains `is_refactor` beside it, the OUTLINE row (`:185`) points to the hand-off, `survey_screen` (`:213`) gains `asked`, and the SPEC bullet (`:192`) points to `keeps_problems` and `red_problems`, each with a pointer to this design. In the structure-first plan, C2b's exact `Category` values (`structure-first-plan.md:65`) gain `misplaced`, C1 and S4 to S6 point to the RQ steps, and the feature phase's C4a and C4b OUTLINE bullets (`:144`-`145`) point to RQ-C8 to RQ-C12. In `docs/roadmap.md`, the milestone changes below.

| Milestone | Change |
|---|---|
| M1 | Builds `core/red.py`, `focus_problems`, and the SPEC and RED_RUN rows. Done when every branch of `red_problems`, `keeps_problems`, `bite_problems` and `focus_problems` has a unit test. |
| M4 | The examiner's stubbed files and `run_stubbed`. Done when a keeps test that still passes with the copies stubbed goes to the arbiter. |
| M3f | The planner's outline carries the structure-only choice, the outline screen takes the owner's override of it, and an approved refactor outline hands off to a STRUCTURE job (decisions 1, 6, 7). Done when a fixture brief asking to give the three-file concern one home yields an outline marked structure only, one candidate whose `asked` is the brief, a JOB ended at OUTLINE as handed off, a STRUCTURE job at DESIGN, its keeps lines GREEN at the red run and passing its gate, and a landed job with `uncovered` empty; when the owner's override on that outline sends the brief down the JOB path; and when a JOB-shape spec holding a keeps line fails a round. |

## Decisions taken

Each entry names the question put to the owner in bold, then the owner's ruling verbatim, then `Adds:`, each module, home and step the ruling adds, and `Written in:`, each section it touches.

1. **Who marks a request as a refactor.** "Let me override the planner's choice of path in the refactor request design"
   - Adds: `Outline.structure_only` in `gauntlet/core/verdicts.py`; `is_refactor` in `gauntlet/core/design.py`; the OUTLINE hand-off row in `gauntlet/core/decide.py`; `outline_screen` in `gauntlet/seams/screens.py`; the planner's structure-only duty in `roles/planner.md`; the `outline` builder in `tests/support/answers.py`; the home "Whether a request is a refactor"; steps RQ-C8 to RQ-C12.
   - Written in: Why, Modules (`core/verdicts.py`, `core/design.py`, `core/decide.py`, `seams/cli.py`, `seams/screens.py`, `roles/`, `tests/support/answers.py`), Homes ("Whether a request is a refactor", "The candidate and copies a direct request opens with", "The owner's words on a STRUCTURE job", "Opening the STRUCTURE job a refactor request becomes"), Order (RQ-D1, RQ-C8 to RQ-C12, RQ-R1, RQ-S1 to RQ-S3, M3f), Decisions for the owner (6, 8).

2. **Where a request's candidate and copies come from.** "Where you and the Architect both agree is fine with me. I want you to bring me conflicts."
   - Adds: none; the surveyor's focused survey, `focus_problems` and `survey_screen`'s `asked` hold as recommended, the survey running after an approved refactor outline (decision 1).
   - Written in: Modules (`core/causes.py`, `seams/cli.py`, `seams/screens.py`, `roles/`), Homes ("The candidate and copies a direct request opens with").

3. **How a keeps test proves it bites.** "Where you and the Architect both agree is fine with me. I want you to bring me conflicts."
   - Adds: none; `bite_problems`, `run_stubbed`, the examiner's duty and the bite row hold as recommended.
   - Written in: Modules (`core/red.py`, `core/decide.py`, `seams/runner.py`, `roles/`), Homes ("Whether a keeps test bites"), Order (RQ-R2, RQ-S4 to RQ-S6, RQ-C6, RQ-C7, M4).

4. **When the direct entry lands.** "Where you and the Architect both agree is fine with me. I want you to bring me conflicts."
   - Adds: none. The recommended M3s entry rests on a `--structure` flag that ruling 1 leaves no place for: the planner's choice lives on the outline, which lands at M3f. That conflict goes to the owner as decision 7.
   - Written in: Order (M3f), Decisions for the owner (7).

5. **A refactor with no copy: a move, a rename or a split.** "Where you and the Architect both agree is fine with me. I want you to bring me conflicts."
   - Adds: none; `Category.MISPLACED` and its `finding_problems` branch hold as recommended.
   - Written in: Modules (`core/verdicts.py`, `roles/`), Homes ("A code move or rename as a finding"), Order (RQ-D1).

6. **How an approved refactor outline becomes a STRUCTURE job.** "Where you and the Architect both agree is fine with me. I want you to bring me conflicts."
   - Adds: none; the hand-off holds as recommended: the JOB ends at OUTLINE as handed off once the owner approves the focused survey's candidate, and `open_structure` opens a STRUCTURE job that starts at DESIGN by `FIRST`.
   - Written in: Modules (`core/verdicts.py` `asked`, `core/decide.py` OUTLINE row, `seams/cli.py`), Homes ("The owner's words on a STRUCTURE job", "Opening the STRUCTURE job a refactor request becomes"), Order (M3f).

7. **When the refactor path lands.** "Yes, we should definitely be doing that not twice. Do it once, do it properly."
   - Adds: none; the refactor path lands once, at M3f, with `gauntlet run`'s Outline stage and the feature-phase outline steps C4a and C4b, as recommended, and no thin M3s `run` is built ahead of it.
   - Written in: Order (the waits paragraph, RQ-C8 to RQ-C12, RQ-R1, RQ-S1 to RQ-S3, M3f).

8. **Whether the owner may name the path up front.** "Where you and the Architect both agree is fine with me. I want you to bring me conflicts."
   - Adds: none; `run` takes no flag that sets the path, and the outline screen is the one place the owner overrides the planner's choice, as recommended.
   - Written in: Modules (`seams/cli.py`), Homes ("Whether a request is a refactor").
