CHECKPOINT: decision
Plan: .planning/phases/1/PLAN-3.md
Tasks: 0 of 5 (Task 1 half done: routes and D-lines committed, rulings pending)
| Task | Commit | Note |
|---|---|---|
| 1 (routes, D-11..D-37) | 0d08176 | 50 groups each carry a `Route:` line in REVIEW-pass1.md; 27 load-bearing (D-11..D-37 in CONTEXT.md), 23 ask-user. Ruling lines not yet recorded (need the main session). |

Route map (group -> D-NN), load-bearing: G-01 D-11, G-02 D-12, G-03 D-13, G-04 D-14, G-05 D-15, G-06 D-16, G-07 D-17, G-08 D-18, G-10 D-19, G-11 D-20, G-12 D-21, G-14 D-22, G-16 D-23, G-21 D-24, G-22 D-25, G-23 D-26, G-25 D-27, G-26 D-28, G-28 D-29, G-29 D-30, G-30 D-31, G-31 D-32, G-32 D-33, G-33 D-34, G-40 D-35, G-41 D-36, G-50 D-37.
Ask-user: G-09, G-13, G-15, G-17, G-18, G-19, G-20, G-24, G-27, G-34, G-35, G-36, G-37, G-38, G-39, G-42, G-43, G-44, G-45, G-46, G-47, G-48, G-49.

Standing checks run: pre-commit passed; `archon workflow list --json` "errors": []; `archon validate workflows` 4 valid, 23 with errors (the baseline).
Deviations: none
Open items: Route split is planner discretion (PLAN-3 Task 1). A group the owner thinks routed wrong can move to the other route at the ask. G-45 depends on the G-44 ruling.
