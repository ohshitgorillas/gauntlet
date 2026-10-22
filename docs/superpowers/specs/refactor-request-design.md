Status: proposed, for the owner's approval.

## Why

A request to restructure code without changing what it does has no direct STRUCTURE path: the existing openers are a CoreMissing or an audit pick (`docs/design.md:94`, `docs/design.md:100`). The proposed outline routing and hand-off share one Candidate record and one opener. M1 defines per-line RED/GREEN marks and unchanged existing tests (`docs/superpowers/specs/m1-core-records-design.md:163`, `:626`). Routing, MISPLACED and examiner extensions require separate owner approval.

- **A STRUCTURE job opens from two places only: 2 entries, 4 restatements.** A CoreMissing on a build step (`docs/design.md:94`) and an audit pick (`docs/design.md:100`). The `Shape.STRUCTURE` comment (`docs/superpowers/specs/structure-first-design.md:198`), opening bullet (`:211`) and `open_structure` home (`:281`) name those two; the workflow summary is at `docs/design.md:32`. A request enters through `gauntlet run <brief.md>` (`docs/roadmap.md:108`) or `gauntlet new` (`docs/roadmap.md:136`), both of the JOB shape (`docs/superpowers/specs/structure-first-design.md:200`).

- **The outline carries one routing flag, and none for a refactor.** The planner's outline returns a shared-structure flag and the owner approves or redirects it (`docs/design.md:38`); `needs_design` reads that flag (`docs/superpowers/specs/structure-first-design.md:133`). Nothing on the outline says a request changes no behavior, so no stage the planner reaches can send a request to a STRUCTURE job.

- **The red-run rule, 3 copies, none with an exception.** "every line `RED`" (`docs/design.md:44`); "A `GREEN` verdict at the red run sends the line to the arbiter" (`docs/design.md:64`); "A test that passes before any implementation exists reopens its spec line" (`docs/design.md:68`).

- **Kept behaviors and starting verdicts have separate homes.** Each Candidate.keeps claim must appear in its STRUCTURE spec before porting (`docs/superpowers/specs/structure-first-design.md:212`). M1 requires an explicit RED or GREEN mark on every line; a kept claim can have either mark, and GREEN preserves approved existing test ids unchanged (`docs/superpowers/specs/m1-core-records-design.md:163`). This applies without inferring permission from the job shape.

- **Two producers of a Candidate, none for a request.** The surveyor's `Survey.candidates` (`gauntlet/core/verdicts.py:67`) and an implementer's `CoreMissing.candidate` (`gauntlet/core/verdicts.py:56`). A direct request has neither, so it has no copies for `uncovered` to check at DESIGN.

- **One spec record and one starting-verdict validator.** M1 defines SpecLine.start, SpecLine.tests and TestStart in records.py (`docs/superpowers/specs/m1-core-records-design.md:104`, `:141`), and red_problems and binding_problems in red.py (`:626`). This proposal consumes those contracts; it introduces no second mark or validator.

- **Candidate already has one code home.** Candidate, CoreMissing and Survey are defined at `gauntlet/core/verdicts.py:41`, `:56` and `:67`. M1 retains these definitions and introduces the composite records separately (`docs/superpowers/specs/m1-core-records-design.md:25`, `:79`); routing reuses them.

## Modules

M1 owns the import graph: domain records feed records.py, red.py imports records, and decide imports the pure homes (`docs/superpowers/specs/m1-core-records-design.md:23`). SpecLine, TestStart, RedVerdict, Outline and State live in records.py (`:79`); Candidate stays in verdicts.py (`:25`). The interfaces below use those definitions. Runner is M2's process seam (`docs/superpowers/specs/gates-core-design.md:402`). A refactor request uses the existing STRUCTURE shape (`docs/superpowers/specs/structure-first-design.md:198`).

**`gauntlet/core/verdicts.py`** (proposed amendment). Gains Candidate.asked and Category.MISPLACED on the existing records (`gauntlet/core/verdicts.py:16`, `:41`). It defines no spec mark or composite answer.

```python
class Category(StrEnum):
    ...  # the five values of the structure-first spec
    MISPLACED = "misplaced"  # code a request moves to a new home, with every caller in also

@dataclass(frozen=True)
class Candidate:  # the structure-first record with one field more
    concern: str
    payoff: str
    risk: str
    keeps: tuple[str, ...]
    why: str | None = None
    asked: str | None = None  # exact JOB brief text; cli.run is the sole writer
```

**`gauntlet/core/records.py`** (M1 contract; proposed Outline extension). SpecLine and its verdict types use M1's definitions (`docs/superpowers/specs/m1-core-records-design.md:104`, `:141`); only Outline.structure_only belongs to the routing proposal. The start mark and preserved ids are visible to the owner as part of spec approval (`:163`).

```python
class TestStart(StrEnum):
    RED = "red"; GREEN = "green"

class RedVerdict(StrEnum):
    RED = "red"; ERROR = "error"; GREEN = "green"
    INVALID = "invalid"; COULD_NOT_JUDGE = "could-not-judge"

@dataclass(frozen=True)
class SpecLine:
    id: str
    claim: str
    bite: str
    start: TestStart
    tests: tuple[str, ...] = ()  # approved existing ids for GREEN

@dataclass(frozen=True)
class Outline:
    steps: tuple[Step, ...]
    areas: tuple[str, ...]
    shared_structure: bool = False
    structure_only: bool = False  # proposed planner choice, subject to owner override
```

Every line explicitly declares its start mark, with no default. GREEN names nonempty, unique existing test ids whose tests pass unchanged on the old and new code. RED requires failing behavioral assertions. Neither Candidate.keeps nor STRUCTURE implies GREEN; missing or invalid marks fail SPEC, and changing the mark or preserved ids needs spec approval again. M1 owns this contract (`docs/superpowers/specs/m1-core-records-design.md:163`).

**`gauntlet/core/red.py`** (M1 contract; proposed examiner extension). M1 owns starting verdicts and preserved-test bindings (`docs/superpowers/specs/m1-core-records-design.md:626`). It replaces the red-run rule at `docs/design.md:44`, `:64` and `:68`. The examiner adds only bite_problems, subject to separate approval.

```python
def red_problems(spec: Spec, judgment: RedJudgment,
                 bindings: Sequence[TestBinding]) -> tuple[str, ...]: ...
def binding_problems(spec: Spec, answer: TestAnswer,
                     baselines: Sequence[TestSnapshot]) -> tuple[str, ...]: ...
def bite_problems(lines: Sequence[SpecLine], stubbed: Mapping[str, RedVerdict], touched: Collection[str], copies: Sequence[Anchor], keeps: Sequence[str]) -> tuple[str, ...]: ...
```

- red_problems requires one row per approved line, exact bound ids and the declared starting verdict. Missing, duplicate or unknown rows, wrong ids, ERROR, INVALID and COULD_NOT_JUDGE fail; neither a RED on a GREEN line nor a GREEN on a RED line changes the mark. Mismatches go to the arbiter under the juror cap (`docs/superpowers/specs/m1-core-records-design.md:637`).
- The binding contract requires exact owner-selected GREEN ids and a nonblank harness baseline for each preserved test. LOCK and LAND require harness evidence that complete test definitions, decorators and parametrization equal their snapshots. Final runs require every line GREEN (`docs/superpowers/specs/m1-core-records-design.md:639`).
- Proposed bite_problems identifies kept lines by claim membership in keeps, independently of their start mark. It names each touched path without a copy anchor and each kept line whose stubbed verdict is GREEN or absent. The examiner supplies files with copy-bearing function bodies replaced by raises; the harness runs their tests. This check supplements M1's source-preservation checks and remains unapproved.

**`gauntlet/core/causes.py`** (proposed amendment). Gains the check that a survey focused on one request answers it with one candidate. finding_problems checks MISPLACED as MISSING: also anchors, a concern and blocking are required. It replaces nothing.

```python
def focus_problems(survey: Survey) -> tuple[str, ...]: ...
```

- `focus_problems` names a survey with no candidate and one with more than one. Beside `survey_problems` (`docs/superpowers/specs/structure-first-design.md:168`), which ties every candidate to a cause and every cause to anchored findings, it holds a direct request to one candidate with at least one copy.

**`gauntlet/core/design.py`** (proposed amendment). Gains whether an approved outline sends its request down the STRUCTURE path. Its Outline annotation uses a type-only records import, preserving M1's runtime dependency direction. It replaces nothing and sits beside `needs_design` (`docs/superpowers/specs/structure-first-design.md:133`), the other reader of the outline.

```python
def is_refactor(outline: Outline, override: bool | None) -> bool: ...
```

- `is_refactor` returns the owner's override where the owner gave one at the outline screen, and the planner's `structure_only` otherwise. `override` is the owner's ruling as M1's State records it, `None` when the owner approved the outline as the planner wrote it.

**`gauntlet/core/decide.py`** (M1 rows reused; proposed routing and examiner rows). The interface is unchanged; OUTLINE and the examiner check extend it.

```python
def decide(state: State, answer: Answer) -> Action: ...   # M1's signature
```

- OUTLINE: an approved outline for which `is_refactor` holds goes to neither DESIGN nor PLAN; the next action is the focused survey. On the owner's approval of its candidate the JOB ends at OUTLINE as handed off, its `state.json` naming the STRUCTURE job it opens, and that job starts at DESIGN by `FIRST`. A survey that is `COULD NOT JUDGE`, or a declined candidate, stops the JOB at its stop screen. Any other approved outline goes on by the OUTLINE row of `docs/superpowers/specs/structure-first-design.md:205`.
- M1's SPEC, TESTS, RED_RUN, LOCK and LAND rules are consumed unchanged (`docs/superpowers/specs/m1-core-records-design.md:731`, `:733`, `:739`). SPEC preserves each Candidate.keeps claim and validates every line's explicit mark and ids before owner approval. Approval captures baselines before stubs or test work; starting runs retain the old implementations exercised by GREEN tests. No keeps_problems or expected function is added here.
- Examiner extension, requiring separate approval: between RED_RUN and LOCK, a STRUCTURE job with kept claims uses run_stubbed for their tests and bite_problems with the candidate's keeps. Problems go to the arbiter; unavailable execution requires an explicit bypass. M1's unchanged-test contract is independent of this extension.

**`gauntlet/seams/cli.py`** (proposed amendment). Gives `gauntlet run` the hand-off of a refactor request to a STRUCTURE job. It replaces nothing and opens a STRUCTURE job only through `open_structure`.

```python
def run(brief: Path) -> int: ...   # gauntlet run <brief.md>
```

- When `decide` returns the focused survey after OUTLINE, `run` launches the surveyor over the checkout with the brief's text as its focus, then the grouper. A survey that fails `survey_problems` or `focus_problems` is `COULD NOT JUDGE`. `write_survey` (`docs/superpowers/specs/structure-first-design.md:223`) writes the survey as any structure audit's. The survey screen shows the brief, then the one candidate. On the owner's approval, `run` sets the candidate's `asked` to the brief's text and opens the STRUCTURE job through `open_structure` with its cause's anchors as the copies. That job runs as every STRUCTURE job does: DESIGN first, nothing skipped.
- `run` takes no flag that sets the path: the owner overrides the planner's choice at the outline screen alone.

**`gauntlet/seams/screens.py`** (proposed amendment). The outline screen shows the planner's choice of path and takes the owner's override of it; the survey screen shows a direct request's words above its candidate. `outline_screen` is the outline's approval screen (`docs/design.md:38`), named here with the path it gains. It replaces nothing.

```python
def outline_screen(outline: Outline) -> Screen: ...   # steps, implementers, areas and flag, then the planner's path; approve, redirect, or override the path
def survey_screen(survey: Survey, causes: Sequence[Cause], asked: str | None = None) -> Screen: ...   # with asked: the request, then the one candidate; approve or decline
```

**`gauntlet/seams/runner.py`** (proposed amendment). Runs keeps tests on the stubbed tree. It replaces nothing.

```python
def run_stubbed(tree: Path, files: Mapping[str, str], ids: Sequence[str], runner: Runner) -> Mapping[str, RedVerdict]: ...
```

- `run_stubbed` writes `files` (path to whole text) onto a scratch overlay of `tree`, runs `ids` with every runner in `gauntlet.yaml` and the harness's own pytest settings (`docs/design.md:186`), and maps pass to GREEN, fail to RED and error to ERROR. The keys of `files` are the `touched` that `bite_problems` checks.

**`roles/`** (proposed amendment). Three roles gain a duty; each runs in its existing kind (`docs/design.md:110`, `:112`, `:114`).

```text
roles/surveyor.md   reader   answer: Survey; given a focus, one candidate for the request, findings COPY, MISSING, MISPLACED
roles/planner.md    reader   answer: Outline with `structure_only` set when the brief asks to restructure without changing behavior; spec lines use M1's approved per-line start and existing test ids, with every candidate.keeps claim carried verbatim
roles/examiner.md   scratch  answer: the stubbed files, path to whole text, each function holding a copy anchor raising
```

**`tests/support/answers.py`** (proposed amendment). Builders for the records above. It replaces nothing.

```python
def outline(*, structure_only: bool = ...) -> Outline: ...
def candidate(*, concern: str = ..., keeps: tuple[str, ...] = ..., why: str | None = ..., asked: str | None = ...) -> Candidate: ...
```

## Homes

| Concern | Home | Forbids elsewhere |
|---|---|---|
| Whether a request is a refactor | the planner's `Outline.structure_only`, which the owner's override at the outline screen replaces, read only by `is_refactor` in `gauntlet/core/design.py` | Any other role, `decide` or a seam choosing it. A STRUCTURE path the owner has not seen on the outline screen. A flag or second screen where the owner sets it. A new shape for a refactor request. |
| The candidate and copies a direct request opens with | the surveyor's focused survey after an approved refactor outline, checked by `survey_problems` and `focus_problems` | A brief-writer, planner, architect or seam writing a Candidate or naming copies for a request. |
| The owner's words on a STRUCTURE job | `Candidate.asked`, set only by `cli.run`'s hand-off from the JOB's brief | A second field or file carrying the request into the job. A role rewriting it. |
| Opening the STRUCTURE job a refactor request becomes | `open_structure` in `gauntlet/seams/job.py` (`docs/superpowers/specs/structure-first-design.md:281`), after the JOB ends handed off | `run` making a job folder itself. A JOB going on past OUTLINE as a STRUCTURE job. |
| Starting-verdict mark and preserved ids | M1's SpecLine.start, SpecLine.tests and TestStart in `gauntlet/core/records.py`; red_problems and binding_problems in `gauntlet/core/red.py` | A second mark or validator, job-shape or keeps inference, or changing approved marks/ids without spec approval; replaces `docs/design.md:44`, `:64`, `:68`. |
| Kept behavior coverage | Candidate.keeps claims carried verbatim in the STRUCTURE spec, validated by M1's SPEC row | SpecLine.keeps, a second keeps validator, or treating a kept claim as permission to start GREEN. |

| Concern | Home | Forbids elsewhere |
|---|---|---|
| Unchanged existing tests | M1's State.baselines and harness checks before LOCK and LAND | Agent-supplied snapshots, modifying a preserved test, or a GREEN verdict alone proving source identity. |
| Whether a keeps test bites (proposed) | `bite_problems` over `run_stubbed`'s run | Agent-certified test outcomes or source identity. |
| A code move or rename as a finding | `Category.MISPLACED` | A move recorded as COPY or MISSING. |
| Test builders for these records | `tests/support/answers.py` | A builder or seed helper inside a test file. |

## Order

M1's design owns the mark, baseline, binding and starting-verdict work (`docs/superpowers/specs/m1-core-records-design.md:1004`, `:1037`, `:1046`, `:1050`). Those steps build once there; no RQ step duplicates them. New behavior still follows stub, red tests from test-writer against stubgen interfaces, build, blind reviews and make check before a commit. Approved GREEN tests remain unchanged and pass on both implementations.

All RQ steps below require separate approval of this proposal. Routing lands at M3f and the examiner extension at M4; neither is M1 work. RQ-C1 to RQ-C3 reuse the structure-first core; RQ-C8 to RQ-C12 wait on its feature-phase OUTLINE work (`docs/superpowers/plans/structure-first-plan.md:144`, `:145`). RQ-R1 and RQ-S1 to RQ-S3 wait on M3f's run and outline screen (`docs/roadmap.md:108`). Each row writes at most five files.

| Step | Milestone | Agent | Writes |
|---|---|---|---|
| RQ-D1 | before routing | `general-purpose` (docs only, no red test) | `docs/design.md`, `docs/roadmap.md`, `docs/superpowers/specs/structure-first-design.md`, `docs/superpowers/plans/structure-first-plan.md` |
| RQ-C1 stub | M3f | `core-builder` | `gauntlet/core/verdicts.py`, `gauntlet/core/causes.py` |
| RQ-C2 red | M3f | `test-writer` | `tests/support/answers.py`, `tests/test_core_causes_focus.py` |
| RQ-C3 build | M3f | `core-builder` | `gauntlet/core/causes.py` |

| Step | Milestone | Agent | Writes |
|---|---|---|---|
| RQ-R2 | M4 | `role-author` | `roles/examiner.md` |
| RQ-S4 stub | M4 | `seam-builder` | `gauntlet/seams/runner.py` |
| RQ-S5 red | M4 | `test-writer` | `tests/test_seams_runner_stubbed.py` |
| RQ-S6 build | M4 | `seam-builder` | `gauntlet/seams/runner.py` |
| RQ-C6a stub | M4 | `core-builder` | `gauntlet/core/red.py` |
| RQ-C6b red | M4 | `test-writer` | `tests/test_core_red_bite.py` |
| RQ-C6 red | M4 | `test-writer` | `tests/test_core_decide_bite.py` |
| RQ-C7 build | M4 | `core-builder` | `gauntlet/core/red.py`, `gauntlet/core/decide.py` |

| Step | Milestone | Agent | Writes |
|---|---|---|---|
| RQ-C8 stub | M3f | `core-builder` | `gauntlet/core/verdicts.py`, `gauntlet/core/records.py`, `gauntlet/core/design.py` |
| RQ-C9 red | M3f | `test-writer` | `tests/support/answers.py`, `tests/test_core_design_is_refactor.py` |
| RQ-C10 build | M3f | `core-builder` | `gauntlet/core/design.py` |
| RQ-C11 red | M3f | `test-writer` | `tests/test_core_decide_hand_off.py` |
| RQ-C12 build | M3f | `core-builder` | `gauntlet/core/decide.py` |
| RQ-R1 | M3f | `role-author` | `roles/surveyor.md`, `roles/planner.md` |
| RQ-S1 stub | M3f | `seam-builder` | `gauntlet/seams/cli.py`, `gauntlet/seams/screens.py` |
| RQ-S2 red | M3f | `test-writer` | `tests/test_seams_cli_run_hand_off.py`, `tests/test_seams_screens_outline_path.py`, `tests/test_seams_screens_asked.py` |
| RQ-S3 build | M3f | `seam-builder` | `gauntlet/seams/cli.py`, `gauntlet/seams/screens.py` |

RQ-D1 synchronizes routing only after proposal approval. M1's documentation step already owns the RED/GREEN workflow and records/red layout (`docs/superpowers/specs/m1-core-records-design.md:1004`).

In `docs/design.md`, the Outline row (`:38`) gains the planner's structure-only choice and owner override; the entry summary (`:32`), CoreMissing text (`:94`) and audit text (`:100`) gain the approved-outline hand-off as the third STRUCTURE opener, and the CLI layout (`:288`) gains that hand-off.

In `docs/superpowers/specs/structure-first-design.md`, Category (`:32`) gains MISPLACED, Candidate (`:53`) gains asked, needs_design (`:133`) gains is_refactor beside it, the OUTLINE row (`:205`) points to the hand-off, and survey_screen (`:233`) gains asked. Its SPEC bullet (`:212`) points to M1 for the start marks, preserved ids and kept-claim coverage.

RQ-D1's plan targets are Category's values (`docs/superpowers/plans/structure-first-plan.md:65`) for misplaced and the feature-phase OUTLINE steps (`:144`, `:145`) for RQ-C8 to RQ-C12. The routing scope belongs at `docs/roadmap.md:106`; the separately authorized examiner scope belongs at `docs/roadmap.md:73`.

| Milestone | Scope and completion |
|---|---|
| M1 | Uses the approved records/red/decide and unchanged-test contract from `docs/superpowers/specs/m1-core-records-design.md:1075`; this proposal adds no M1 work. |
| M4 (proposed) | Examiner stubbed files, run_stubbed and bite_problems; the arbiter receives any kept line whose test remains GREEN with its copies stubbed. |
| M3f (proposed) | Outline routing, owner override, focused survey, MISPLACED and hand-off. A refactor fixture reaches STRUCTURE/DESIGN with one candidate carrying the original request and lands with uncovered empty. Its approved GREEN tests pass unchanged on old and new code; RED lines start RED and finish GREEN. An owner override selects the JOB path without changing per-line marks. |
