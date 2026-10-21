Status: proposed, for the owner's approval.

## Why

A request to restructure code without changing what it does has no path through Gauntlet. A STRUCTURE job opens only from a finding, and every spec line must start out failing, which a line that pins behavior the code already has cannot do. The pieces of this design (a direct entry for a refactor request, the candidate that request opens with, and a red-run rule for lines that pin existing behavior) share one Candidate record, one opener, one spec line record and one red-run rule.

- **A STRUCTURE job opens from two places only: 2 entries, 4 restatements.** A CoreMissing on a build step (`docs/design.md:94`) and an audit pick (`docs/design.md:100`). The `Shape.STRUCTURE` comment (`docs/superpowers/specs/2026-10-20-structure-first-design.md:178`), the opening bullet (`:191`), the home of `open_structure` (`:261`) and `docs/design.md:32` name those two and no other. A request enters through `gauntlet run <brief.md>` (`docs/roadmap.md:104`) or `gauntlet new` (`docs/roadmap.md:132`), both of the JOB shape (`structure-first-design.md:180`).

- **The red-run rule, 3 copies, none with an exception.** "every line `RED`" (`docs/design.md:44`); "A `GREEN` verdict at the red run sends the line to the arbiter" (`docs/design.md:64`); "A test that passes before any implementation exists reopens its spec line" (`docs/design.md:68`).

- **Keeps lines meet that rule with no rule of their own, 3 places.** A STRUCTURE job's SPEC carries each of its candidate's `keeps` lines as a spec line, locked before any port step (`structure-first-design.md:192`, `:260`; `docs/roadmap.md:67`). A keeps line pins behavior the copies already carry, so its test passes at the red run and reopens under `docs/design.md:68`. The gap holds for every audit pick, not only for a direct request.

- **Two producers of a Candidate, none for a request.** The surveyor's `Survey.candidates` (`structure-first-design.md:64`) and an implementer's `CoreMissing.candidate` (`:58`). A direct request has neither, so it has no copies for `uncovered` to check at DESIGN (`:186`).

- **Nothing marks a spec line as a keeps line.** No document defines a spec line record. The Spec row returns behavior lines `S1…` with `bite:` values (`docs/design.md:41`), and nothing records which of them carries which `keeps` line, so nothing can tell a line that may start out passing from one that may not.

- **No copy of these concerns in code.** `gauntlet/` holds only three empty files, `gauntlet/__init__.py`, `gauntlet/core/__init__.py` and `gauntlet/seams/__init__.py`, and nothing under `gates/` or `tests/` holds a job shape, a candidate or a red-run rule. Every copy above is in the documents the code will be built from.

## Modules

Core imports run `verdicts` ← `red` ← `decide`; `red` imports nothing else of the core. `SpecLine` and `RedVerdict` are M1's answer records (`docs/superpowers/specs/2026-10-20-gates-core-design.md:370`): this design stubs only the fields it needs, and M1's design names their other fields and may rename them. `Runner` is M2's process-running seam (`2026-10-20-gates-core-design.md:378`). A refactor request opens no new shape: it is a STRUCTURE job (`docs/design.md:102`).

**`gauntlet/core/verdicts.py`** (amended). Gains the keeps mark on a spec line, the juror's verdict per line, the owner's words on a Candidate, and the MISPLACED category (decision 5). It replaces nothing; it adds to the records at `structure-first-design.md:31`-`53`.

```python
class Category(StrEnum):
    ...                                # the five values of the structure-first spec
    MISPLACED = "misplaced"            # code a request moves to a new home, with every caller in `also` (decision 5)

class RedVerdict(StrEnum):             # the juror's verdict per spec line (docs/design.md:44)
    RED = "red"; ERROR = "error"; GREEN = "green"; INVALID = "invalid"; COULD_NOT_JUDGE = "could-not-judge"

@dataclass(frozen=True)
class SpecLine:                        # M1's spec line record; its other fields are M1's
    id: str                            # "S1", stable across amendments (docs/design.md:90)
    keeps: str | None = None           # the Candidate.keeps line it carries, verbatim; None on any other line

@dataclass(frozen=True)
class Candidate:                       # the structure-first record with one field more
    concern: str
    payoff: str
    risk: str
    keeps: tuple[str, ...]
    why: str | None = None
    asked: str | None = None           # the owner's request verbatim; set only by `cli.run`, on a direct request
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

**`gauntlet/core/decide.py`** (amended rows). The interface is unchanged; these rows join the stage table.

```python
def decide(state: State, answer: Answer) -> Action   # M1's signature; the rows below are added
```

- SPEC: a spec with any `keeps_problems` against the job's candidate's `keeps`, empty for a JOB, is a failed round under `caps.spec`, beside the arbiter's rulings.
- RED_RUN: the gate is `red_problems` returning nothing. Each line it names goes to the arbiter.
- Between RED_RUN and LOCK, a STRUCTURE job with keeps lines runs the bite check (decision 3): the examiner returns the stubbed files, `run_stubbed` runs the keeps tests on them, and each line `bite_problems` names goes to the arbiter. Until M4 builds the examiner, the check is recorded as skipped and shown as a bypass on the land screen.

**`gauntlet/seams/cli.py`** (amended). Gives `gauntlet run` its structure form, the direct entry of a refactor request (decision 1). It replaces nothing and sits beside `audit` (`structure-first-design.md:219`).

```python
def run(brief: Path, *, structure: bool = False) -> int   # gauntlet run <brief.md> [--structure]
```

- With `--structure`, `run` launches the surveyor over the checkout with the brief's text as its focus, then the grouper (decision 2). A survey that fails `survey_problems` or `focus_problems` is `COULD NOT JUDGE` and opens no job. `write_survey` (`structure-first-design.md:203`) writes the survey as any structure audit's. The survey screen shows the brief, then the one candidate. On the owner's approval, `run` sets the candidate's `asked` to the brief's text and opens the job through `open_structure` with its cause's anchors as the copies. The job runs as every STRUCTURE job does: DESIGN first, nothing skipped.
- Without `--structure`, until M3f builds the JOB path, `run` opens no job and returns nonzero, saying the feature path is not built (decision 4).

**`gauntlet/seams/screens.py`** (amended). The survey screen shows a direct request's words above its candidate. It replaces nothing.

```python
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
roles/planner.md    reader   answer: spec lines; in a STRUCTURE job, each keeps line carried by one SpecLine with `keeps` verbatim
roles/examiner.md   scratch  answer: the stubbed files, path to whole text, each function holding a copy anchor raising   (decision 3)
```

**`tests/support/answers.py`** (amended). Builders for the records above. It replaces nothing.

```python
def spec_line(*, id: str = ..., keeps: str | None = ...) -> SpecLine
def candidate(*, concern: str = ..., keeps: tuple[str, ...] = ..., why: str | None = ..., asked: str | None = ...) -> Candidate
```

## Homes

| Concern | Home | Forbids elsewhere |
|---|---|---|
| The shape a request opens as | the command the owner runs: `run(brief, structure=True)` in `gauntlet/seams/cli.py` (decision 1) | A role, `decide` or another seam choosing or changing a job's shape. A plain `run` opening a STRUCTURE job. A new shape for a refactor request. |
| The candidate and copies a direct request opens with | the surveyor's focused survey, checked by `survey_problems` and `focus_problems` (decision 2) | A brief-writer, planner, architect or seam writing a Candidate or naming copies for a request. |
| The owner's words on a STRUCTURE job | `Candidate.asked`, set only by `cli.run` from the brief's text | A second field or file carrying the request into the job. A role rewriting it. |
| Opening the job | `open_structure` in `gauntlet/seams/job.py` (`structure-first-design.md:261`) | `run` making a job folder itself. |
| Which verdict a spec line needs at the red run | `expected` and `red_problems` in `gauntlet/core/red.py` | The rule restated at `docs/design.md:44`, `:64` and `:68`. A juror, seam or role deciding which lines may start out passing. |
| Which spec lines are keeps lines | `SpecLine.keeps`, checked against the candidate's `keeps` by `keeps_problems` | A keeps line in a JOB's spec. A keeps line the candidate does not carry. Any other field marking a line as one that may pass at the red run. |
| Whether a keeps test bites | `bite_problems` over `run_stubbed`'s run (decision 3) | A keeps line locked on a GREEN run alone once M4 lands. The examiner's own report of outcomes counted as the run. |
| A code move or rename as a finding | `Category.MISPLACED` (decision 5) | A move recorded as COPY or MISSING. |
| Test builders for these records | `tests/support/answers.py` | A builder or seed helper inside a test file. |

## Order

Each code step follows the repository's chain: stub, red tests from `test-writer` against the `stubgen` view, build, blind reviews and `make check`, one commit per chain. RQ-C1 to RQ-C3 wait on the structure-first plan's C1 to C3 and on M1's design naming the spec line and juror verdict records; RQ-C4 and RQ-C5 wait on its C5; RQ-S1 to RQ-S3 on its S1 to S3 and S4 to S6.

| Step | Milestone | Agent | Writes |
|---|---|---|---|
| RQ-D1 | before M1 | `general-purpose` (docs only, no red test) | `docs/design.md`, `docs/roadmap.md`, `docs/superpowers/specs/2026-10-20-structure-first-design.md`, `docs/superpowers/plans/structure-first-plan.md` |
| RQ-C1 stub | M1 | `core-builder` | `gauntlet/core/verdicts.py`, `gauntlet/core/red.py`, `gauntlet/core/causes.py` |
| RQ-C2 red | M1 | `test-writer` | `tests/support/answers.py`, `tests/test_core_red.py`, `tests/test_core_causes_focus.py` |
| RQ-C3 build | M1 | `core-builder` | `gauntlet/core/red.py`, `gauntlet/core/causes.py` |
| RQ-C4 red | M1 | `test-writer` | `tests/test_core_decide_keeps.py` |
| RQ-C5 build | M1 | `core-builder` | `gauntlet/core/decide.py` |
| RQ-R1 | M3s | `role-author` | `roles/surveyor.md`, `roles/planner.md` |
| RQ-S1 stub | M3s | `seam-builder` | `gauntlet/seams/cli.py`, `gauntlet/seams/screens.py` |
| RQ-S2 red | M3s | `test-writer` | `tests/test_seams_cli_run_structure.py`, `tests/test_seams_screens_asked.py` |
| RQ-S3 build | M3s | `seam-builder` | `gauntlet/seams/cli.py`, `gauntlet/seams/screens.py` |
| RQ-R2 | M4 | `role-author` | `roles/examiner.md` |
| RQ-S4 stub | M4 | `seam-builder` | `gauntlet/seams/runner.py` |
| RQ-S5 red | M4 | `test-writer` | `tests/test_seams_runner_stubbed.py` |
| RQ-S6 build | M4 | `seam-builder` | `gauntlet/seams/runner.py` |
| RQ-C6 red | M4 | `test-writer` | `tests/test_core_decide_bite.py` |
| RQ-C7 build | M4 | `core-builder` | `gauntlet/core/decide.py` |

RQ-D1 writes this design into the documents. In `docs/design.md`: the Red run row's gate (`:44`) and the notes at `:64` and `:68` say every line at the verdict `expected` gives, RED or GREEN for a keeps line, with a pointer to `core/red.py`; `:32`, "Reopening the spec" (`:94`) and "Audit jobs" (`:100`) add `gauntlet run <brief.md> --structure` as the third opener of a STRUCTURE job; §8 adds `red.py` and the structure form of `run` (`:288`). In the structure-first spec, at their home, `Category` (`:31`-`36`) gains MISPLACED, `Candidate` (`:47`-`53`) gains `asked`, `survey_screen` (`:213`) gains `asked`, and the SPEC bullet (`:192`) points to `keeps_problems` and `red_problems`, each with a pointer to this design. In the structure-first plan, C2b's exact `Category` values (`structure-first-plan.md:65`) gain `misplaced`, and C1 and S4 to S6 point to the RQ steps. In `docs/roadmap.md`, the milestone changes below.

| Milestone | Change |
|---|---|
| M1 | Builds `core/red.py`, `focus_problems`, and the SPEC and RED_RUN rows. Done when every branch of `red_problems`, `keeps_problems`, `bite_problems` and `focus_problems` has a unit test. |
| M3s | `gauntlet run <brief.md> --structure` beside `audit --structure`; a bare `run` refuses until M3f. Done when a fixture brief asking to give the three-file concern one home yields one candidate whose `asked` is the brief, a STRUCTURE job at DESIGN, its keeps lines GREEN at the red run and passing its gate, and a landed job with `uncovered` empty; when a bare `run` opens no job and returns nonzero; and when a JOB-shape spec holding a keeps line fails a round. |
| M4 | The examiner's stubbed files and `run_stubbed`. Done when a keeps test that still passes with the copies stubbed goes to the arbiter. |
| M3f | Replaces the bare `run` refusal with the JOB path. |

## Decisions for the owner

1. **Who marks a request as a refactor.** Recommend: the owner, by `gauntlet run <brief.md> --structure`; a plain `run` never opens a STRUCTURE job. Alternative: the planner flags an outline "structure only", and `decide` moves the job from the JOB shape to the STRUCTURE shape after OUTLINE. Cost of the recommendation: the owner names the shape on each request, and a refactor run without the flag takes the JOB path, where `red_problems` sends its GREEN lines to the arbiter. Cost of the alternative: a role decides which of its job's spec lines may start out passing, so it sets the bar its own red run is judged by; `FIRST` no longer fixes a job's stages, and `decide` gains a shape-change row. Launch cost of either: unmeasured.

2. **Where a request's candidate and copies come from.** Recommend: the surveyor, focused on the brief, checked by `survey_problems` and `focus_problems` and shown on the survey screen. Alternative: the brief itself, or the brief-writer, names the concern, the keeps lines and the copies, and `run` builds the Candidate from them. Cost of the recommendation: a surveyor and a grouper launch before the job opens, unmeasured. Cost of the alternative: a second producer of a Candidate whose copies no check resolves before M4's prosecutor (`docs/roadmap.md:73`), so `uncovered` at DESIGN rests on an unchecked list.

3. **How a keeps test proves it bites.** Recommend: the stubbed-tree run of `bite_problems` from M4, each keeps test failing with the copies stubbed. Alternative: the juror's ruling at the red run and the bailiff's `PIN` after BUILD, with no stubbed run. Cost of the recommendation: one examiner launch and one test run per STRUCTURE job, unmeasured, and stub writing in each language rests on the examiner. Cost of the alternative: a keeps test that passes whatever the copies do is locked at LOCK, and a port step can purge the behavior it claims to keep before the bailiff, built at M6, reads it.

4. **When the direct entry lands.** Recommend: M3s, beside `audit --structure`, with a bare `run` refusing until M3f, as a bare `audit` refuses until M10 (`structure-first-design.md:349`). Alternative: M3f, with the rest of `gauntlet run`. Cost of the recommendation: RQ-R1 and RQ-S1 to RQ-S3 and a refusal branch at M3s, unmeasured. Cost of the alternative: no refactor request reaches Gauntlet until after the structure pilot (M7s); the red-run rule for keeps lines lands at M1 either way, since audit picks need it.

5. **A refactor with no copy: a move, a rename or a split.** Recommend: a MISPLACED category, the code at its current home as the anchor and every caller in `also`, ported as a copy is. Alternative: no new category; `focus_problems` refuses such a request, which yields no cause, and no job opens. Cost of the recommendation: one more `Category` value, one more `finding_problems` branch, and plan C2b's exact values list changes. Cost of the alternative: the simplest refactors stay outside Gauntlet, and a request for one stops at the survey screen.
