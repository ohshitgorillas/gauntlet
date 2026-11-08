Status: approved (owner, 2026-11-07).

# Owner control: structured intake, the amicus, and the review before landing

## Why

Gauntlet's implementation half is a black box to the owner. Once plan review approves, writing and landing run until they land or hit an iteration bound, and every failure on the way is ruled by an agent: the juror in writing, `mend-juror` in landing. Nothing shows the owner a run that has gone wrong until it ends.

The owner learned what that costs while driving Cadence. Plans went off the rails for iteration after iteration without the owner noticing, although the owner was in control of every step, because the writing put in front of the owner was too dense to judge and "fine, sure, go ahead" was said by mistake. The signs of a lost agent, as the owner found them:

- It cannot state the problem in a way that is legible or coherent.
- Its guesses stop following the evidence: "something changed this setting", with evidence no one touched it; "maybe it is a network bandwidth issue".
- It keeps the letter of a constraint and breaks its intent.
- It keeps working under a premise the owner never approved, for example keeping tests green that no longer serve any purpose.

Each time, the way out was different: sending the `researcher` agent after real solutions instead of guesses, killing an unapproved premise, rewriting a constraint. It cannot be codified, and it cannot be trusted to LLM judgment, because every agent involved was confident. A human has to unjam it. Letting a system loop on a hallucination spends tokens on work the sequence does not need, a defect under CLAUDE.md 1.3.

This design therefore moves the decision at every implementation failure, and before every landing, to the owner. It also gives the owner's intent a structured, checkable form at intake, so that reviewers can judge scope against something the owner actually stated or confirmed.

## Goals

1. Every writing or landing failure that today goes to a juror stops the run and puts the owner in charge of the next pass.
2. Every landing, failed or clean, meets the owner first, with a short review of whether the work did what was asked and nothing else. A run whose plan lands in several stages meets the owner before each stage lands.
3. Intake produces few, structured items whose goals and fields the owner stated or confirmed, one at a time.
4. Scope is checked against the approved items, mechanically where a script can and by review where it cannot.
5. Plan review and spec review keep running on their own; the owner can set what reviewers escalate.

## Non-goals

- GitHub or any ticket-system integration. Deferred; the item file is shaped like an issue so that a later integration is a copy.
- Changing plan review's or spec review's loops, verdicts or bounds, beyond the escalation rules below.
- Having any agent decide whether a failure is worth the owner's attention.

## Anti-goals

The design fails, even if it works as specified, if:

- Any stop in writing or landing is triggered by an agent's judgment that something looks wrong. Stops are mechanical.
- An agent's explanation is checked, filtered or rewritten by another agent before the owner reads it.
- The owner is asked to approve text too long or dense to judge. A confirmation the owner cannot actually check is the failure this design exists to remove.
- Plan-review technicalities reach the owner. Most plan failures are planner mistakes the reviewers already handle.
- An agent splits one goal into several items on its own.

## 1. Intake: few structured items

### The rule for how many items

One item per goal the owner would accept or reject on its own. The test: "would you ever want one of these done without the other?" If no, they are one item.

- Points sharing a goal, a root cause or the same code are joined into one item.
- Intake strives for as few items as possible. An overarching goal stays one item however large it is; its size is the plan's problem, not intake's. A simple bug fix is one small item.
- A split happens only when the owner answers yes to the test. Clerk never splits on its own.

### The flow from the owner's side

1. The owner states everything at once: bugs, wishes, context, in any order and shape.
2. Clerk proposes the fewest items. Each has a draft goal and the list of the owner's points it absorbs. Clerk asks the test only where two points could plausibly stand alone.
3. The owner merges or splits, usually in one reply.
4. The fields are settled one item at a time. Each item is approved on its own, never as a batch.
5. Clerk asks how the run takes the approved items, with two answers:
   - **Do everything in this run.** Every item goes through one plan, review, write and land.
   - **Defer some.** The owner names the deferred items; they move to a separate item file for a later run, and this run carries the rest.

### Item fields

| Field | Content |
|---|---|
| Id | A stable item id, cited by plan steps. |
| Goal | The core goal, in the owner's words or as Clerk's reading the owner confirmed. |
| Current behavior | Filled by Clerk from the code; the owner checks it. For a new feature, "does not exist". |
| Desired behavior | What it should do once done. |
| Constraints | Limits on how it may be done. |
| Out of scope | What this item does not ask for. |
| Notes | Anything else, including per-item escalation rules (section 4). |

The owner states each goal in their own words, or at least confirms Clerk's reading of it and of every other field. When the owner types a goal, a script records it exactly as typed and Clerk cannot write that field.

### Mechanical checks on intake

- Every field Clerk writes is capped in length (on the order of two or three sentences), checked by a script, so that every confirmation is short enough to judge.
- An empty field holds the word "none", never an empty string, so that "skipped" and "nothing" cannot be confused (the defect pass 3 found as G-112).
- Every point in the owner's opening statement is assigned to exactly one item, checked by a script, so joining items cannot drop a point unseen.

The item file is a local file, one issue-shaped record per item.

## 2. Writing and landing: the amicus

### What changes

Writing's juror (`write/commands/juror.md`) and landing's `mend-juror` (`mend/commands/mend-juror.md`) no longer rule. Both are replaced by one role, the **amicus** (amicus curiae: it briefs the court and has no power to rule; the owner is the bench).

### When it runs

Mechanically, on every case that today goes to a juror: in writing, a red, a writer's contest, a blocked block or a failed commit; in landing, a red in the mend. The existence of the case is the trigger. No agent decides whether the case warrants a stop.

### What it does

1. Works out why the run failed.
2. Explains it to the owner in plain language, or attempts to. Its explanation goes to the owner unchecked by any other agent; an explanation that does not hold together is itself evidence the owner reads.
3. Discusses the way forward for the next pass with the owner.

### The owner's choices

- **Run again with direction.** The owner's direction is recorded as a file, and the next pass's agents are bound by it. A direction held only in chat would be lost on resume.
- **Back to planning.** Gauntlet exits cleanly and prints the command for the next plan review, for the owner to copy into the terminal.

The `DEFECTIVE` verdict is removed; ending on a defective plan is the owner's "back to planning" choice. The verdicts `TESTS`, `CODE`, `SPEC` and `PLAN` are no longer issued by an agent; which part gets reworked is part of the owner's direction.

## 3. The review before landing

There is a review before implementation and none after it. This closes the gap.

- It runs before every landing, failed or clean.
- It is short, because the review before implementation is already extensive. Its question: did the workers faithfully implement the requested features and fix the bugs as instructed, and nothing else? Are there shortcuts that need to be redone properly?
- It reads each approved item against its own fields, the plan steps with the item ids they cite, and the marks of the mechanical scope checks below.
- It rules on nothing. Its answer goes to the owner through the amicus, and the owner chooses: land, run again with direction, or back to planning.

### Staged plans

Some work needs one part landed before the next part can start. The plan names those parts as **stages**, in landing order; a plan with no such dependency is one stage. Plan review reviews the stages with the rest of the plan. The divvyer cuts blocks and waves within a stage, never across one.

Each stage writes, then meets the owner through the amicus with this review scoped to the stage's own plan steps and items, then lands. The next stage starts only after it lands. At each stage the owner chooses: land and go on, run the stage again with direction, or back to planning, where the stages not yet landed are replanned and the landed ones stay.

### Mechanical scope checks

- Every plan step cites an item id from the approved item file. A script checks it; a step that cites no id is marked as added scope.
- Every block's diff stays inside the block's `paths` (writing's block record). A script compares them; a change outside is marked.

The review covers what a script cannot, such as a step that cites an item and does not serve it.

## 4. Plan review and spec review: escalation rules

The loops stay as they are. Reviewers keep `APPROACH THE BENCH` and decide when an issue warrants the owner.

Escalation is only for decisions the owner can act on. A plan that breaks an item's constraints or out-of-scope field is a defect: the reviewer rejects it to the planner, and it never reaches the owner.

The owner can add escalation rules in their own words, for example "escalate any decision about the public API":

- **Repo-wide rules** live in the repository's configuration and apply to every run in it.
- **Per-item rules** live in the item's Notes field, for example "for this plan, escalate decisions about X to me".

Reviewers receive both, verbatim, beside the built-in criteria.

## Constraints

- Archon's features are used directly, with no scaffolding (CLAUDE.md 1.1). A missing Archon feature is reported to the owner, not worked around (1.2).
- No node, stop or check spends tokens on work the sequence does not need (1.3), and none stops the sequence over a technicality (1.4). The amicus stop is not a technicality: it is the owner's ruling on a failure an agent would otherwise rule on alone.
- Every owner-facing text is plain and short enough to judge.

## Decided by the owner

- Intake items are as few as possible, issues joined where they can be, an overarching goal never split if it can be avoided; the test for a split is the one in section 1.
- Item fields: goal, current and desired behavior, constraints, out of scope, notes. The owner states or confirms each goal and each field.
- The amicus replaces both jurors, triggered by every juror case, and also meets the owner before every landing.
- The owner's choices at the amicus: run again with direction, or back to planning with a printed command.
- `DEFECTIVE` is removed.
- The owner's direction is a recorded file binding the next pass; no agent checks the amicus's explanation; landing's `mend-juror` goes the same way.
- A short post-implementation review before every landing, with the question stated in section 3.
- The amicus and that review meet the owner before every landing, including each stage of a plan that lands in several stages, not only once at the end of the run.
- Plan review and spec review keep their loops; reviewers keep `APPROACH THE BENCH`; escalation rules are repo-wide, with per-item rules in Notes.
- Constraint and out-of-scope breaches in a plan are the reviewer's to reject, not the owner's to hear.
- GitHub integration is deferred.
- Intake ends by asking how the run takes the items: everything in this run, or defer some to a separate item file for the next run.

## The orchestrator's calls

- The name **amicus**.
- The **out of scope** field. (The owner approved the field list with it.)
- Clerk fills in current behavior from the code.
- The length cap on Clerk-written fields, the "none" rule and the point-assignment check.
- Plan steps cite item ids, and block diffs are compared against block `paths`.
- The item file is local and issue-shaped.
- The plan, not the divvyer, names the stages, so plan review sees them; the divvyer cuts within a stage.
- Back to planning reruns plan review over the same approved item file, with the amicus's record and the owner's direction attached, so the planner sees why the last plan failed.

## Left to the builder

- The item file's name, format and location, and how intake hands it to plan review in place of today's task file.
- How the verbatim goal is captured. The manual gives a `loop_group` wait's answer as `$LOOP_PREV.<wait-id>.output.text` (`docs/reference/archon/loop-nodes.md:122`); this is untested.
- How the amicus discussion runs as an Archon wait, and the form of the direction file and how the next pass reads it.
- The exact back-to-planning command.
- The key that holds repo-wide escalation rules.
- How the review before landing is placed relative to landing's blocks.
- The exact field-length cap.

## Effect on the roadmap

This changes the intake, writing and landing designs, and plan review's and spec review's reviewer briefs. Phase 1 (design review) is replanned after this design is approved; rounds 1 to 3 of its review ran over the designs this one changes.
