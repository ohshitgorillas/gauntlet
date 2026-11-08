Status: proposed.

# Gauntlet spec review

## Why

Spec review is phase 3 of the one run `gauntlet-run`, which includes it as node `spec-review` after `plan-review` (gauntlet design); it also runs on its own (`archon workflow run spec-review`). It takes plan review's hand-off: the item file and planning's approved plan, or the item file alone when planning found that the work only edits `tests/`. It hands its fields (node `handoff`, below) to the worktree cut. The speccer decides whether tests need speccing, writes the test specs with spikers' measurements, and the arbiter tries them round by round. A spec block the arbiter rules `READY` goes to the owner in plain English; on approval it is copied to `gauntlet/specs/approved/<slug>.txt`. A block the arbiter rules `INVALID` (nothing to test) goes to the owner to confirm; on confirmation the phase ends with no spec. The arbiter never reads source code. What it needs from the code it asks for through its three request forms, and the speccer answers them. Every path is relative to the pack root unless it names the run's checkout; `gauntlet/` always sits in the checkout.

What the tree already holds for the concerns spec review touches:

- Round state, slot choice, counts, runaway guard, the owner's case, ruling and `SCREENED` files: one copy, designed and unbuilt, `.shared/rounds.py` below, which plan review's ledger and spec review's both take as a `Profile`. Without it each hearing would hold a copy.
- Steering screening: one copy, designed and unbuilt, the `screen` workflow below, included by plan review, spec review and writing. Commands resolve only from a workflow's own `commands/` folder, so a per-hearing screener role would be a copy.
- The arbiter's role: built, `spec-review/commands/arbiter.md`. It names rulings `<slug>-ruling.*.txt` and reviews `<slug>-review.N.txt` (three places). Planning names them `<slug>.ruling.N.txt` and `<slug>.review.N.txt`. It reads `gauntlet/plans/approved/<slug>.txt` with no rule for a run that has no plan, and skips no `SCREENED` review.
- Fence name patterns: designed and unbuilt, in the plan review design (`fence/files.py` extended). `fence/files.py` today confines by whole folders only. A folder entry that names a file, such as `docs/testing.md`, already confines to that one file.
- Working-folder guard: designed and unbuilt, node `guard` of `gauntlet-run` (gauntlet design) and this phase's own node `guard`, both on `.shared/working-folder.ts` (intake design).
- Fence launch line: designed and unbuilt, one copy per role fence file (`intake/clerk.mcp.json`, three in plan review).
- Running commands under a timeout: `fence/checks.py` runs one fixed brief test command with a process-group kill. Spikers run their experiment files under a command fixed in the fence, the constant `bash run.sh`, never one they supply, so `fence/spike.py` below serves them, with the same kill.
- Spikers, spec files, the speccer and spec reporter roles, the spec-review workflow: no copy anywhere.

## Terms

- **Speccer**: Opus, effort medium. One session for the whole run, started by node `open` before the hearing loop and reused for every filing turn.
- **Arbiter**: the adversarial spec reviewer (`spec-review/commands/arbiter.md`). It is sworn in once by node `swear-in`. Its slots, `arbitrate-1` to `arbitrate-12` (the slot bound, `runtime-model-design.md`, "Loop shape and bounds"), each fork the sworn-in session at their first executed turn and continue their own session after it. The slot rule, the retirement by `OBJECTION: LEADING` and the rerun are `runtime-model-design.md`'s: "Hearing state" and "Loop shape and bounds". The speccer repairs the block after a retirement and the next slot tries the next round.
- **Spiker**: an inline sub-agent of the speccer, dispatched through Agent, with no Bash and no shell. It reads and writes through the `fence-scratch` server and runs its experiment files through the `fence-spike` server, which runs only a command fixed in the fence, the constant `bash run.sh`, with cwd in the spiker's scratch folder; the spiker writes `run.sh` there. It runs scratchpad experiments under `gauntlet/scratch/<slug>/` of the checkout: stub proofs (null stub, hard-coded stub), bite measurements and answers to `measure` requests. One spiker serves one related set of experiments with shared scaffolding. At most 2 spikers run at once.
- **Screener**: the shared steering check, the support workflow `screen`, included fresh each round. A flagged spec file gets the verdict `SCREENED`, reaches no arbiter and retires no slot.
- **Reporter**: a fresh agent that writes the plain-English summary of a `READY` or `INVALID` round for the owner.
- **Round** `N`: one spec file `<slug>.N.txt` (`runtime-model-design.md`, "Hearing state").
- **Attempt**: a round whose verdict is `ANOTHER PASS` or `APPROACH THE BENCH`; the count that calls the owner is `runtime-model-design.md`'s, "Loop shape and bounds".
- **Stretch**, **run iterations**, **idle iteration**, **ruling**, **guard record**, **vacancy**: `runtime-model-design.md`, "Loop shape and bounds" and "Ledger". **Slug**: the function `slug` of `.shared/pin.py` (worktree cut design). Node `vacate`, after the hearing, cancels the run without asking on case `vacant`.

Verdicts, read from the first line of a review as `runtime-model-design.md`, "Ledger" gives:

| Verdict | Next |
|---|---|
| `READY` | reporter, then the owner: approve, or revise (a ruling) |
| `INVALID` | reporter, then the owner: confirm (the phase ends with no spec), or revise (a ruling) |
| `APPROACH THE BENCH` | the owner's reply becomes a ruling; the speccer revises; counts as an attempt |
| `ANOTHER PASS` | the speccer revises; counts as an attempt |
| `OBJECTION: NON-RESPONSIVE` | the speccer revises; the count that calls the owner is `runtime-model-design.md`'s, "Loop shape and bounds" |
| `OBJECTION: LEADING` | slot retired; the speccer repairs by removing the quoted text |
| `SCREENED` | the speccer repairs by removing the quoted text; no slot retired |

Files in `gauntlet/specs/` of the checkout:

| File | Written by | Rule |
|---|---|---|
| `<slug>.N.txt` | speccer | edited by the speccer only within its filing turn N |
| `<slug>.review.N.txt` | arbiter; `ledger.py screen` for a `SCREENED` file | `runtime-model-design.md`, "Hearing state" |
| `<slug>.ruling.N.txt` | `ledger.py record` | `runtime-model-design.md`, "Hearing state" |
| `<slug>.guard.N.txt` | `ledger.py record` | `runtime-model-design.md`, "Hearing state"; the speccer and the arbiter read it as they read rulings |
| `<slug>-summary.N.md` | reporter | `runtime-model-design.md`, "Hearing state" |
| `<slug>.idle.K.md` | analyst | `runtime-model-design.md`, "Hearing state" and "Loop shape and bounds" |
| `<slug>.iter.txt` | `ledger.py filing` | `runtime-model-design.md`, "Hearing state" |
| `<slug>.items.sha256` | `ledger.py state` outside the loop (node `docket-in`) | `runtime-model-design.md`, "Hearing state" |
| `stale/<slug>.<n>/` | `ledger.py state` outside the loop (node `docket-in`) | `runtime-model-design.md`, "Hearing state" |
| `approved/<slug>.txt`, `approved/<slug>-summary.md` | bash node `enter` | written only after the owner approves a `READY` round (`runtime-model-design.md`, "Hearing state") |

`gauntlet/scratch/<slug>/` holds the spikers' experiments. Only the `fence-scratch` server and the `fence-spike` tool write there. The speccer node's session reaches both servers, as its spikers do, since Archon has no per-sub-agent server list; the speccer's role sends every experiment to a spiker. No other agent reads it.

## Modules

### `.shared/rounds.py`

The module of the round ledger for every Gauntlet hearing. What it answers (modes, state fields, owed and next, verdicts, owner cases, rulings, guard records) is stated once in `runtime-model-design.md`, headings "Ledger" and "Hearing state"; this section holds its constants, dataclasses and signatures. Standard library only. Each workflow's `scripts/ledger.py` passes a `Profile` and calls `main`. It replaces the round logic the plan review design once put in `plan-review/scripts/ledger.py`.

```python
from dataclasses import dataclass
from typing import Callable

# The bounds, with their values, are runtime-model-design.md's, heading "Loop shape and bounds"; the module takes each value from there.
SLOTS: int      # slot nodes <prefix>-1 to <prefix>-SLOTS, named "<letter>1" to "<letter><SLOTS>" in "next"
STRETCH: int
REPAIRS: int    # plans only
CAP: int
IDLE: int       # read by docket for profiles with iterations, and by writing's stage.py docket

@dataclass(frozen=True)
class OwnerCase:
    verdict: str                    # the review verdict that opens this case
    case: str                       # "review" | "invalid" | "bench"
    options: tuple[tuple[str, str], ...]   # (id, label) shown to the owner
    summary: bool                   # attention is the reporter's summary file, not the review text
    ends: str                       # option id that ends the hearing ("" when none)

@dataclass(frozen=True)
class Profile:
    folder: str                     # checkout-relative: "gauntlet/plans" | "gauntlet/specs"
    author: str                     # value of "owed"/"next" when the author owes the round: "defense" | "speccer"
    reviewer: str                   # value of "owed" when the reviewer owes it: "prosecutor" | "arbiter"
    letter: str                     # slot prefix in "next": "p" | "a"
    verdicts: tuple[str, ...]       # every verdict name, "SCREENED" included
    retire: str | None             # "OBJECTION: LEADING"; None for a hearing whose reviewer is a fresh node (writing): no slots, "next" is never "vacant"
    non_responsive: str             # "OBJECTION: NON-RESPONSIVE"
    attempts: tuple[str, ...]       # verdicts counted as attempts
    owner_cases: tuple[OwnerCase, ...]   # in precedence order, ahead of deadlock, non-responsive, guard, idle and cap
    filed: Callable[[str, str, int], bool]   # (folder, slug, round): the round is ready to try; plans: cited (runtime-model-design.md,
                                    #   "Ledger", Citation state); specs and writing's revisions: always
    iterations: bool = False        # True (plans, specs): the loop counts its iterations (runtime-model-design.md, "Loop shape and
                                    #   bounds"); False (writing's revisions): no counter, stage.py keeps its own

# Modes, their inputs and outputs, the state fields, owed and next, the owner cases and verdict parsing:
#   runtime-model-design.md, headings "Ledger" and "Hearing state". Script nodes pass INPUTS_MODE.
def cited(folder: str, slug: str, round: int) -> bool: ...   # the plans profile's filed; the rule: runtime-model-design.md, "Ledger" (Citation state)

def state(p: Profile, slug: str, start: int | None, first: int = 1) -> dict: ...   # mode state and, with an iteration line first, mode filing
# first: the hearing's first round (runtime-model-design.md, "Hearing state")

def docket(p: Profile, slug: str, first: int = 1) -> dict: ...   # the cases and the bounds they read: runtime-model-design.md, "Ledger" and "Loop shape and bounds"

def screen(p: Profile, slug: str, round: int, quote: str) -> str: ...
def record(p: Profile, slug: str, round: int, case: str, decision: str, text: str) -> str: ...
def close(p: Profile, slug: str) -> dict: ...
# screen, record and close: runtime-model-design.md, "Ledger"

def main(p: Profile) -> int: ...   # reads INPUTS_*, dispatches on INPUTS_MODE, prints JSON to stdout
```

Suite: `.shared/tests/test_rounds.py`, run as `docs/testing.md` states with the folder `.shared/tests`. It drives `main` through a test `Profile` and real files under `tmp_path`.

### `plan-review/scripts/ledger.py` (on the shared core)

Planning's ledger is a profile and a call, and the plan review design holds no ledger body. Its modes, inputs and outputs are `runtime-model-design.md`'s, heading "Ledger".

```python
# /// script
# requires-python = ">=3.12"
# ///
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / ".shared"))
from rounds import Profile, OwnerCase, cited, main

PROFILE = Profile(
    folder="gauntlet/plans", author="defense", reviewer="prosecutor", letter="p",
    verdicts=("APPROVED", "REJECTED", "APPROACH THE BENCH", "OBJECTION: LEADING", "OBJECTION: NON-RESPONSIVE", "SCREENED"),
    retire="OBJECTION: LEADING", non_responsive="OBJECTION: NON-RESPONSIVE",
    attempts=("REJECTED", "APPROACH THE BENCH"),
    owner_cases=(
        OwnerCase("APPROVED", "review", (("approve", "Approve"), ("revise", "Revise")), summary=True, ends="approve"),
        OwnerCase("APPROACH THE BENCH", "bench", (("reply", "Reply"),), summary=False, ends=""),
    ),
    filed=cited,
    iterations=True,
)
sys.exit(main(PROFILE))
```

Suite: `plan-review/tests/test_ledger.py`, pinning only what the profile decides: plan verdict names, `REJECTED` counted as an attempt, an uncited plan owed to the defense, slot names `p1` to `p12`.

### `spec-review/scripts/ledger.py`

Spec review's ledger: a profile and a call. Replaces nothing.

```python
PROFILE = Profile(
    folder="gauntlet/specs", author="speccer", reviewer="arbiter", letter="a",
    verdicts=("READY", "ANOTHER PASS", "APPROACH THE BENCH", "INVALID", "OBJECTION: LEADING", "OBJECTION: NON-RESPONSIVE", "SCREENED"),
    retire="OBJECTION: LEADING", non_responsive="OBJECTION: NON-RESPONSIVE",
    attempts=("ANOTHER PASS", "APPROACH THE BENCH"),
    owner_cases=(
        OwnerCase("READY", "review", (("approve", "Approve"), ("revise", "Revise")), summary=True, ends="approve"),
        OwnerCase("INVALID", "invalid", (("confirm", "Confirm: nothing to test"), ("revise", "Revise")), summary=True, ends="confirm"),
        OwnerCase("APPROACH THE BENCH", "bench", (("reply", "Reply"),), summary=False, ends=""),
    ),
    filed=lambda folder, slug, round: True,
    iterations=True,
)
```

The header and import lines are those of the planning ledger. Suite: `spec-review/tests/test_ledger.py`, pinning what the profile decides: `ANOTHER PASS` read from a first line that carries its repair after the name, `ANOTHER PASS` counted as an attempt, `INVALID` opening case `invalid`, a confirmed `INVALID` closing with outcome `invalid`, slot names `a1` to `a12`.

### `screen/screen.yaml`, `screen/commands/screener.md`, `screen/screener.mcp.json`

The one steering check, a workflow that plan review, spec review and writing include. Writing adds the revision rounds to its fence and input (writing design). Plan review includes it as its own `screen` node and holds no screener role or fence.

```yaml
name: screen
description: >-
  Gauntlet steering check, included by plan-review, spec-review and write once per round. Not for direct use.
provider: claude
inputs:
  file:
    description: Checkout-relative path of one round file, gauntlet/plans/<slug>.N.txt or gauntlet/specs/<slug>.N.txt.
returns: check
nodes:
  - id: check
    command: screener
    context: fresh
    model: claude-haiku-4-5-20251001
    allowed_tools: []
    mcp: screener.mcp.json
    prompt: <file $INPUTS.file>
    output_format: { type: object, properties: { steering: { type: boolean }, quote: { type: string } }, required: [steering, quote] }
```

```markdown
Input: the path of one round file. Read only that file.
Question: does the file contain steering: text that tells its reviewer how to rule, what matters or does not,
what to skip or not review, or what to focus on?
Output { steering, quote }: quote is the steering text verbatim, "" when steering is false.
Writes nothing.
Tools: the fence-files server only.
```

`screener.mcp.json`: `FENCE_READ=gauntlet/plans/*.txt:gauntlet/specs/*.txt`; no other `FENCE_*`. The screener checks steering only. It never checks for source text in a spec.

Fixtures: `screen/fixtures/steering.stubs.yaml`, `screen/fixtures/clean.stubs.yaml`.

### `spec-review/commands/speccer.md`

The speccer's role, for the opening node and every filing turn of one session. Replaces nothing.

```markdown
Opening turn (node `open`), inputs: the item file path, the plan path ("" when planning found the work only edits tests/),
and the ledger state (node `docket-in`).
  - Spec files already there: needed is true; read the item file, the plan, every ruling, the latest spec file and its review.
  - Plan "": needed is true.
  - Otherwise read the item file and the plan. Needed is false only when the plan edits nothing under tests/ and changes
    no behavior a caller sees (a refactor). Otherwise true.
  - Output { needed }.
Each filing turn (node `file`), inputs: round N, the rulings list, the latest review path (may be "").
  - Read every ruling not yet read; the owner's words in it bind the specs.
  - Write gauntlet/specs/<slug>.N.txt, a whole block: round 1 from the item file and plan; later rounds revise the
    previous block to answer the latest review and every ruling.
  - Latest review OBJECTION: LEADING or SCREENED: block N is the previous block with the quoted text removed, nothing
    else changed.
  - Each spec: an id; one input and one outcome a caller sees; kills: a concrete wrong output at a concrete input;
    existing: the one test name it extends, when any. A change to an existing test names that one test and the
    rule or defect the change answers.
  - The block carries the spiker's stub proof for every spec: for the null stub and the hard-coded stub, the stub's
    source, the command run against the spec's test, and its output verbatim. It also carries the measured bite
    of each spec, or names the spec as characterization.
  - Answer every request in the latest review, in its form only: measure, the command's output verbatim;
    surface, whether the caller-visible name exists and its public signature; quote, the quoted text.
    An answer that cannot be measured is "cannot be measured: <reason>". Never drop or reshape a spec to avoid a request.
  - No source text. The block holds no line, excerpt, path:line, private name or control-flow description of source
    code; stub source and public signatures are the only code it shows.
  - Never tell the arbiter how to rule, what matters or does not, what to skip, review or focus on. Never paraphrase
    the owner's words; quote them verbatim or leave them out.
Spikers: dispatch through Agent to `spiker`, one per related set of experiments with shared scaffolding.
  At most 2 spiker tasks in flight at once. Brief each with its experiments, the specs they serve and its scratch
  folder gauntlet/scratch/<slug>/<name>/; name each folder once per run.
Writes: only gauntlet/specs/<slug>.N.txt for the turn's N. Never a review, ruling, summary or approved/ file.
Tools: Agent; the fence-files server; no Bash. This session also reaches the spikers' fence-scratch and fence-spike
  servers; leave every experiment to a spiker.
```

### `spec-review/commands/reporter.md`

The spec reporter's role. Replaces nothing.

```markdown
Inputs: the round file to read, gauntlet/specs/<slug>.N.txt, its review file, gauntlet/specs/<slug>.review.N.txt, the
summary file to write, gauntlet/specs/<slug>-summary.N.md, and the verdict, READY or INVALID. Read the round and review files.
Write the summary file once, in plain English for the owner, with no code, no path:line and no
review history. READY: what each spec checks, as behavior the owner would recognise. INVALID: each change the
plan makes and why no test can pin it.
Tools: the fence-files server only.
```

### `spec-review/commands/analyst.md`

The analyst's role, a fresh read-only agent started for an idle iteration (node `why`): the plan review design's role with this hearing's folder. Replaces nothing.

```markdown
Inputs: the idle file to write, gauntlet/specs/<slug>.idle.K.md, and the iteration file, gauntlet/specs/<slug>.iter.txt.
The last iteration of this hearing tried no round, drew no answer and left the round file as it found it.
Read the iteration file and the latest spec, review, ruling and guard files, and find why no progress was made. Write
the idle file once: the reason, in plain English for the owner, in a few sentences, with no code and no path:line.
Propose nothing and change nothing else.
Tools: the fence-files server only.
```

### `spec-review/commands/arbiter.md` (amended)

The built role stays as written but for these changes:

- Rulings are read as `gauntlet/specs/<slug>.ruling.*.txt` and the owner's answers kept in `gauntlet/specs/<slug>.guard.*.txt`, and reviews are written as `gauntlet/specs/<slug>.review.N.txt`, on the first-turn, write and `Writes:` lines.
- The first turn reads the plan only when its path is not "". When earlier rounds exist, it reads the latest block and review only when the latest verdict is neither `OBJECTION: LEADING` nor `SCREENED`. Each turn skips `SCREENED` reviews.
- A clause: with no approved plan (the work only edits `tests/`), the item file stands in for the plan wherever the role names the plan: off-plan, `READY`'s plan behaviors, `INVALID`'s list of changes, and `quote` requests.
- `Reads:` names `gauntlet/specs/*.txt` for the specs folder, and `gauntlet/plans/approved/<slug>.txt` only when the plan path is not "".
- Escalation rules (owner-control design, section 4): the role gains one line in the first-turn reads and in the rules for `APPROACH THE BENCH`: read `gauntlet/rules/<slug>.txt` and the Notes field of every item in the item file, verbatim, beside the criteria the role holds; they say what the owner wants escalated, and only a decision the owner can act on is escalated. The carrier is node `rules`, which writes that file on every run of plan review and, the same node, on every run of spec review, and the key is `GAUNTLET_ESCALATION`; both are the plan review design's ("Escalation rules"). A spec that breaks an item's Constraints or Out of scope field gets `ANOTHER PASS`, to the speccer, and is never put to the owner.

### `spec-review/speccer.mcp.json`, `spec-review/arbiter.mcp.json`, `spec-review/reporter.mcp.json`, `spec-review/analyst.mcp.json`

Each role's fence. Each server is received as the intake design's section `intake/clerk.mcp.json` gives for every fence config. `arbiter.mcp.json`, `reporter.mcp.json` and `analyst.mcp.json` name one server, `fence-files`. `speccer.mcp.json` names three: `fence-files` for the speccer, and for its spikers `fence-scratch` (`fence/files.py`) and `fence-spike` (`fence/spike.py`). The spiker is an inline sub-agent of the speccer node and Archon has no per-sub-agent server list, so the speccer's session reaches `fence-scratch` and `fence-spike` too; its role sends every experiment to a spiker, and no `denied_tools` entry is added. Neither the speccer node nor any spiker holds Bash or a shell or takes `sandbox:`; the fence servers confine them, and a path not listed in a `FENCE_READ` cannot be read, so no `FENCE_HIDE` is needed. They replace nothing.

| File and server | `FENCE_READ` | `FENCE_WRITE` | `FENCE_DENY` | `FENCE_ONCE` |
|---|---|---|---|---|
| `speccer.mcp.json`, `fence-files` | `gauntlet/items:gauntlet/plans/approved:gauntlet/specs/*.txt:docs/testing.md` | `gauntlet/specs/*.txt` | `gauntlet/specs/*.review.*.txt:gauntlet/specs/*.ruling.*.txt:gauntlet/specs/*.guard.*.txt:gauntlet/specs/*.iter.txt` | unset |
| `speccer.mcp.json`, `fence-scratch` | `gauntlet/items:gauntlet/plans/approved:gauntlet/specs/*.txt:docs/testing.md:gauntlet/scratch` | `gauntlet/scratch` | unset | unset |
| `arbiter.mcp.json` | `tests:gauntlet/items:gauntlet/rules:gauntlet/plans/approved:gauntlet/specs/*.txt:docs/testing.md` | `gauntlet/specs/*.review.*.txt` | unset | `gauntlet/specs/*.review.*.txt` |
| `reporter.mcp.json` | `gauntlet/specs/*.txt` | `gauntlet/specs/*-summary.*.md` | unset | `gauntlet/specs/*-summary.*.md` |
| `analyst.mcp.json` | `gauntlet/specs/*.txt` | `gauntlet/specs/*.idle.*.md` | unset | `gauntlet/specs/*.idle.*.md` |

None of the lists names `gauntlet/specs/approved` or, for the speccer and its spikers, `tests`; the speccer's `fence-files` list also leaves out `gauntlet/scratch`, which its session reaches through `fence-scratch`. A config cannot name the run's `<slug>` folder, so `fence-scratch` writes `gauntlet/scratch` and the spiker's brief names its own folder `gauntlet/scratch/<slug>/<name>/`.

`fence/spike.py` is the spiker's run tool (server `fence-spike`, environment `CLAUDE_PROJECT_DIR` only, checked as `fence/files.py` checks it). It takes no command from an agent:

```python
async def run_experiment(folder: str) -> str: ...
# folder: a path inside gauntlet/scratch of the root, else PermissionError. Runs the command fixed in the fence,
#   the constant `bash run.sh` (the spiker writes run.sh in the folder; no settings file is read, so it runs in phase 3
#   and in a standalone spec review), under timeout -k 10 600 nice -n 10 with stdin from /dev/null, in the foreground with folder as its working
#   directory, in its own process group killed on timeout, as checks.py kills its command.
# Returns "exit=<n> timed_out=<true|false>" and the command it ran, then the whole output cut as checks.py cuts it.
```

Suite: `fence/test_spike.py`, run as `docs/testing.md` states with the folder `fence`.

`FENCE_COPY` stays unset in all of them. No agent can reach `gauntlet/specs/approved/` through a fence. The arbiter's fence holds no source folder.

### `spec-review/scripts/handoff.ts`

The block's hand-off, node `handoff`. A named script. Replaces nothing.

```typescript
// env: INPUTS_ITEMS, INPUTS_PLAN (the block's inputs); INPUTS_SLUG, INPUTS_OWED, INPUTS_NEEDED, INPUTS_OUTCOME (node bindings)
// slug: INPUTS_SLUG, the ledger's ($docket-in.output.slug)
// outcome: "approved" when INPUTS_OWED is "approved" (an approval already on file, no hearing); "not needed" when
//   INPUTS_NEEDED is false; else INPUTS_OUTCOME ("approved" | "invalid")
// stdout: { "items": INPUTS_ITEMS, "plan": INPUTS_PLAN,
//           "spec": absolute path of gauntlet/specs/approved/<slug>.txt when outcome is "approved", else "",
//           "outcome": outcome }
```

### `spec-review/spec-review.yaml`

The spec review workflow: a standalone workflow and the block `gauntlet-run` includes as node `spec-review`. It declares `worktree: { enabled: false }`, which Archon drops under `include:`, and holds its own `guard` node; `docket-in` and `policy` are its entry nodes after it. `$INPUTS.<name>` appears only in prompts and `bash:` bodies, a `script:` reads `INPUTS_<NAME>` and binds no block input in its `with:`, and no `when:` reads `$INPUTS`. The ledger derives the slug from `INPUTS_ITEMS` with `.shared/pin.py`'s `slug`, so no node passes it in; `state` prints it and the round's file paths, and prompts and `handoff` read `$docket-in.output.slug`. Replaces nothing.

```yaml
name: spec-review
description: >-
  Gauntlet spec review. Takes an item file and planning's approved plan (or no plan when the work only edits tests/); the
  speccer writes test specs with spikers' measurements, the arbiter tries them round by round, and the owner approves them
  or confirms that nothing is testable. Runs on its own for this phase; to take the work through every phase, start
  gauntlet-run.
provider: claude
model: claude-opus-5-5
worktree:
  enabled: false                       # a standalone run needs it; Archon drops it under include: (P7)
inputs:
  items: { description: Path of an item file under gauntlet/items/. }
  plan: { default: "", description: Path of gauntlet/plans/approved/<slug>.txt, or "" when planning found no plan needed. }
returns: handoff

nodes:
  - id: guard                          # the phase's own working-folder check
    runtime: bun
    script: guard

  - id: docket-in                      # entry node, after its guard
    depends_on: [guard]
    runtime: uv
    script: ledger
    with: { mode: state }

  - id: rules                          # the escalation-rules carrier, the same node as plan review's (a bash node sees the repository's env:)
    depends_on: [docket-in]
    bash: <write ${GAUNTLET_ESCALATION:-none} verbatim, one trailing newline, to gauntlet/rules/$docket-in.output.slug.txt, over any earlier file>

  - id: policy                         # entry node, after its guard; the arbiter's opening prompt
    depends_on: [guard]
    bash: <print docs/testing.md of the checkout, or nothing when absent>

  - id: open                           # the speccer's session for the whole run
    depends_on: [docket-in]
    when: "$docket-in.output.owed != 'approved' && $docket-in.output.owed != 'ended'"
    command: speccer
    effort: medium
    allowed_tools: []                  # the opening turn only reads
    mcp: speccer.mcp.json
    prompt: <opening turn; items $INPUTS.items; plan $INPUTS.plan; slug $docket-in.output.slug; ledger state $docket-in.output>
    output_format: { type: object, properties: { needed: { type: boolean } }, required: [needed] }

  - id: swear-in                       # the arbiter's session for the whole run
    depends_on: [open, policy, rules]
    when: "$docket-in.output.owed != 'approved' && $docket-in.output.owed != 'ended' && $open.output.needed == true"
    command: arbiter
    allowed_tools: []
    mcp: arbiter.mcp.json
    prompt: <policy $policy.output; first turn; items $INPUTS.items; plan $INPUTS.plan; ledger state $docket-in.output>

  - id: hearing
    depends_on: [swear-in]
    loop_group:
      max_iterations: <CAP>               # the bound CAP, runtime-model-design.md, "Loop shape and bounds"
      until_bash: |
        owed=$filing.output.owed
        held=$docket.output.case
        [ "$owed" = ended ] || [ "$held" = vacant ]
      nodes:
        - id: record                   # the owner's previous answer becomes a ruling file; the answer that ends the case ends the loop one iteration later
          when: "$LOOP_PREV.bench.output.decision != ''"
          runtime: uv
          script: ledger
          with: { mode: record, round: $LOOP_PREV.docket.output.round, case: $LOOP_PREV.docket.output.case, decision: $LOOP_PREV.bench.output.decision, text: $LOOP_PREV.bench.output.text }

        - id: filing                   # always runs and counts the iteration (runtime-model-design.md, "Loop shape and bounds")
          depends_on: [record]
          trigger_rule: all_done
          runtime: uv
          script: ledger
          with: { mode: filing, start: $docket-in.output.start }

        - id: file
          depends_on: [filing]
          when: "$filing.output.owed == 'speccer' && $filing.output.next != 'vacant'"
          command: speccer
          context: { resume: open }
          effort: medium
          allowed_tools: [Agent]       # no Bash, no shell and no sandbox: files and experiment runs only through the fence servers
          mcp: speccer.mcp.json
          agents:
            spiker:
              description: Runs one related set of scratchpad experiments and returns their commands and output verbatim.
              prompt: >-
                <work only in the scratch folder the brief names; write stubs, draft tests and experiment files there
                through the fence-scratch server, never in tests/ or source; run them through fence-spike's run_experiment
                with that folder, one call at a time; return, per experiment, the stub source, the command the tool reports
                and its output verbatim; a result that cannot be measured is "cannot be measured: <reason>">
              tools: [mcp__fence-scratch__read_file, mcp__fence-scratch__list_directory, mcp__fence-scratch__find_files, mcp__fence-scratch__grep, mcp__fence-scratch__write_file, mcp__fence-scratch__edit_file, mcp__fence-spike__run_experiment]
          prompt: <filing turn; round $filing.output.round; rulings; review $filing.output.review>

        - id: ready
          depends_on: [filing, file]
          trigger_rule: none_failed_min_one_success
          runtime: uv
          script: ledger
          with: { mode: state, start: $docket-in.output.start }

        - id: screen                   # the shared steering check, fresh each round
          depends_on: [ready]
          when: "$ready.output.owed == 'arbiter' && $ready.output.next != 'vacant'"
          include: screen
          with: { file: $ready.output.file }

        - id: flag
          depends_on: [screen]
          when: "$screen.output.steering == true"
          runtime: uv
          script: ledger
          with: { mode: screen, round: $ready.output.round, quote: $screen.output.quote }

        # arbitrate-1 to arbitrate-12: identical but for <k>; each forks swear-in at its first executed turn.
        - id: arbitrate-<k>
          depends_on: [screen]
          when: "$screen.output.steering == false && $ready.output.next == 'a<k>'"
          command: arbiter
          context: { resume: swear-in }
          allowed_tools: []
          mcp: arbiter.mcp.json
          prompt: <turn; round $ready.output.round>

        - id: case
          depends_on: [ready, flag, arbitrate-1, ..., arbitrate-12]
          trigger_rule: none_failed_min_one_success
          runtime: uv
          script: ledger
          with: { mode: docket, start: $docket-in.output.start, base: $docket-in.output.base }

        - id: report                   # READY or INVALID only
          depends_on: [case]
          when: "$case.output.summary == true"
          command: reporter
          context: fresh
          allowed_tools: []
          mcp: reporter.mcp.json
          prompt: <round file gauntlet/specs/<slug>.<round>.txt; review file gauntlet/specs/<slug>.review.<round>.txt;
                  summary file gauntlet/specs/<slug>-summary.<round>.md; slug $docket-in.output.slug, round
                  $case.output.round; verdict $case.output.verdict, READY or INVALID>

        - id: why                      # fresh analyst; only for an idle iteration whose idle file is not yet written
          depends_on: [case]
          when: "$case.output.reason == true"
          command: analyst
          context: fresh
          allowed_tools: []
          mcp: analyst.mcp.json
          prompt: <idle file gauntlet/specs/<slug>.idle.$case.output.idle.md; iteration file gauntlet/specs/<slug>.iter.txt;
                  slug $docket-in.output.slug, round $case.output.round>

        - id: docket                   # re-read after the summary and the idle file exist
          depends_on: [case, report, why]
          trigger_rule: none_failed_min_one_success
          runtime: uv
          script: ledger
          with: { mode: docket, start: $docket-in.output.start, base: $docket-in.output.base }

        - id: bench                    # the owner; sole terminal sink of the body
          depends_on: [docket]
          when: "$docket.output.ask == true"
          wait:
            form: select
            attention: "$docket.output.attention"
            options: "$docket.output.options"

  - id: close                          # after the hearing, or at once when the hearing was skipped (runtime-model-design.md, "Hearing state")
    depends_on: [docket-in, hearing]
    trigger_rule: none_failed_min_one_success
    when: "$docket-in.output.owed != 'approved'"
    runtime: uv
    script: ledger
    with: { mode: close, start: $docket-in.output.start }

  - id: vacate                         # every slot retired in this run (case vacant, runtime-model-design.md, "Loop shape and bounds"); asks nothing
    depends_on: [close]
    when: "$close.output.outcome == 'vacant'"
    cancel: "Every arbiter slot has been retired by an OBJECTION: LEADING review in this run; no arbiter is left. The run stops."

  - id: enter                          # the only writer of approved/
    depends_on: [close]
    when: "$close.output.outcome == 'approved'"
    bash: <cp -n gauntlet/specs/$close.output.file to gauntlet/specs/approved/<slug>.txt and gauntlet/specs/$close.output.summary
          to gauntlet/specs/approved/<slug>-summary.md; any target present: exit non-zero naming it, nothing copied>

  - id: handoff                        # the block's returns: node
    depends_on: [docket-in, open, close, enter]
    trigger_rule: none_failed_min_one_success
    runtime: bun
    script: handoff
    with:
      slug: $docket-in.output.slug
      owed: $docket-in.output.owed
      needed: { from: $open.output.needed, if_skipped: "" }
      outcome: { from: $close.output.outcome, if_skipped: "" }
    output_format:
      type: object
      properties: { items: { type: string }, plan: { type: string }, spec: { type: string }, outcome: { type: string } }
      required: [items, plan, spec, outcome]
```

Fixtures: `spec-review/fixtures/<route>.stubs.yaml`, one per route, each stubbing the included `screen` workflow's node ids (`check`) and the ledger's modes: not needed; already approved (no hearing); an ending ruling already on file (no agent session, `close` and `enter` run); no plan, `READY` then owner approves; owner revises a `READY`; `INVALID` confirmed; `INVALID` sent back; bench; deadlock at the attempts bound; two `NON-RESPONSIVE`; one `LEADING` handing the repaired block to `arbitrate-2`; one `SCREENED` repaired with no slot retired; guard at the stretch bound; every slot retired, the last `LEADING` review asking nothing, the hearing ending on case `vacant` and `vacate` cancelling the run; a rerun finding a `READY` unanswered, asked again; an iteration that writes nothing, asking with the analyst's reason (case `idle`, node `why`), the answer a guard record and the hearing going on; past the cap, every iteration asking, an ask from an iteration with no new review kept in `<slug>.guard.N.txt` with round N still untried.

Plan review's `screen` node is `include: screen` with `with: { file: $ready.output.file }` (plan review design); spec review writes nothing in `plan-review/`.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| The ledger rules: round numbers, slot choice, verdict parsing, counts, runaway guard and cap, the owner's case, rulings and guard records, `SCREENED` reviews, closing paths, the item file hash and the `stale/` set-aside | `runtime-model-design.md`, headings "Hearing state", "Ledger" and "Loop shape and bounds"; the module is `.shared/rounds.py` | any of it computed in a workflow's `ledger.py`, node or command; a `ledger.py` holding anything but its `Profile` and the call to `main` |
| Which verdicts a phase has, which count as attempts, which reach the owner and with what options | each workflow's `scripts/ledger.py` `Profile` | verdict names or options restated in YAML, prompts or `rounds.py` |
| Spec verdict names | `arbiter.md` and `spec-review/scripts/ledger.py` | any other spelling |
| Steering screening | the `screen` workflow, included by plan review, spec review and writing | a per-workflow screener command or fence; any other steering check before a reviewer reads a round file |
| Keeping source text out of specs | `speccer.md` | a screener, ledger or fence check for it |
| What the arbiter learns of source code | the three request forms in `arbiter.md`, answered in the speccer's next block | the arbiter's fence naming any source folder; the arbiter reading `gauntlet/scratch/` |
| Scratchpad experiments and their process footprint | the `spiker` sub-agent in `gauntlet/scratch/<slug>/`, through the fence servers `fence-scratch` and `fence-spike` only; at most 2 at once. The fence is the confinement: `fence-scratch` writes only `gauntlet/scratch`, and `fence-spike` runs only the command fixed in the fence, the constant `bash run.sh` that reads no `gauntlet/settings.json`, with cwd in the spiker's scratch folder, under `timeout -k 10 600 nice -n 10` in the foreground with its process group killed. The speccer node's session reaches both servers too, Archon having no per-sub-agent server list; the speccer's role sends every experiment to a spiker | any agent holding Bash, a shell or a `sandbox:`; a fence tool running a command an agent supplies; experiment files in `tests/` or source; a background process outliving its command |
| File confinement, including name patterns | `fence/files.py` (plan review design) | any role reaching files by a built-in tool |
| Writing to `gauntlet/specs/approved/` | node `enter`, by `cp -n` | any agent or other node writing there; a move of a round file |
| Agent sessions | `open` and `swear-in` before `hearing`; slots `arbitrate-1` to `arbitrate-12` fork `swear-in` | any agent node in the body starting its own session, `screen` and `report` excepted |
| How spec review runs | on its own (`archon workflow run spec-review --input items=<path> --input plan=<path>`) and as `include: spec-review` in `gauntlet-run`, node id `spec-review` (gauntlet design) | `spec-review.yaml` run as a `workflow:` child; a description that does not name `gauntlet-run` for a whole run; a run-owned setting other than `worktree:` in `spec-review.yaml` |
| Working-folder check | node `guard` of `spec-review` on `.shared/working-folder.ts` (intake design); node `guard` of `gauntlet-run` ahead of it in a run | any other check of `gauntlet/` being ignored |
| Inputs inside the block | `$INPUTS.<name>` in prompts and `bash:`; `INPUTS_<NAME>` in scripts, which bind no block input in `with:`; a node output in `when:` | `$INPUTS` in a `when:`; `$INPUTS.<name>` in an inline `script:` |
| Each role's rules | `<workflow>/commands/<role>.md` | role rules restated in node prompts; node prompts carry only the turn's inputs |
| The hand-off to the next phase | node `handoff`, the block's `returns:`, whose `output_format` declares the block's fields, read by `gauntlet-run` as `$spec-review.output.<field>` | any other node or file telling the next phase what was specced |

## Order

1. Shared round core: `.shared/rounds.py`, `.shared/tests/test_rounds.py`. Needs the worktree cut design's `.shared/pin.py` (its step 1). Agent: `builder`.
2. Planning's ledger on the core: `plan-review/scripts/ledger.py`, `plan-review/tests/test_ledger.py`. The plan review design holds no ledger step. Needs step 1. Agent: `builder`.
3. Spec review's ledger: `spec-review/scripts/ledger.py`, `spec-review/tests/test_ledger.py`. Needs step 1. Agent: `builder`.
4. Roles: `screen/commands/screener.md`, `spec-review/commands/speccer.md`, `spec-review/commands/reporter.md`, `spec-review/commands/arbiter.md`, `spec-review/commands/analyst.md`. Agent: `role-author`.
5. Shared steering check: `screen/screen.yaml`, `screen/screener.mcp.json`, `screen/fixtures/steering.stubs.yaml`, `screen/fixtures/clean.stubs.yaml`. Needs step 4 and the plan review design's fence name patterns. Agent: `workflow-builder`.
6. Spiker's run tool: `fence/spike.py`, `fence/test_spike.py`. Agent: `builder`.
7. Spec review block: `spec-review/spec-review.yaml`, `spec-review/scripts/guard.ts`, `spec-review/scripts/handoff.ts`, `spec-review/speccer.mcp.json`, `spec-review/arbiter.mcp.json`, `spec-review/reporter.mcp.json`, `spec-review/analyst.mcp.json`, `spec-review/fixtures/*.stubs.yaml`. Needs steps 3 to 6 and the intake design's step 3 (`.shared/working-folder.ts`, which `spec-review/scripts/guard.ts` imports). `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
