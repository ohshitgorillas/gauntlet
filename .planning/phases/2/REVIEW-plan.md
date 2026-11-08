{ "findings": [
  { "file": ".planning/phases/2/PLAN-1.md",
    "line": 6,
    "severity": "low",
    "claim": "Plan 1 claims CORE-06 in its requirements, but locked D-06 moves CORE-06's proof and traceability to Phase 4, and no task in any plan edits the ROADMAP or REQUIREMENTS mapping.",
    "failure_scenario": "Phase 2 executes as written: Plan 1 ships working-folder.ts with no proof, the frontmatter and the ROADMAP Phase 2 Requirements line still claim CORE-06, so /cad-audit traces CORE-06 to a phase that by D-06 does not prove it (the CONTEXT flagged assumption names exactly this)." },
  { "file": ".planning/phases/2/PLAN-2.md",
    "line": 84,
    "severity": "low",
    "claim": "The FENCE_HIDE refusal sweep lists every tool except find_files, although D-13 says every tool refuses a hidden path and CORE-02 covers search.",
    "failure_scenario": "Task 4 checks the hide rule on results only. find_files(pattern='*', path='<hidden folder>') then returns the hidden names, or no refusal, and Task 3's suite stays green: its omission tests search from the parent, and its refusal sweep never calls find_files with the hidden path." }
] }
