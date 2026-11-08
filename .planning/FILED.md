# Filed: issues this repository's gates opened

Written by `issue-filing.mjs file` when a gate's finding is ACCEPTED and filed
on the tracker, read by `planning.mjs recall` beside CAPTURE.md. One `- ` row
per filed issue: the date, the provider, the repository slug, the finding's
(file, claim) fingerprint and the issue's title. No finding body - a row is a
pointer to an issue, not a copy of it, and NOTHING here is a queue. A declined
finding is never written here; its record is a row in DECLINED.md beside this
file, which is deliberately outside the recall corpus. A line that is not a row
is skipped, so a note added here mints no recall entry.

A row carrying the word `unconfirmed` before its colon is a create this
repository could not confirm landed - the forge may hold that issue and may not.
It is kept so a later fire does not file the same finding twice; delete the row
once you have looked, and nothing else here is unverified.

- 2026-11-08 github ohshitgorillas/gauntlet a65c9e50f716e564: [cadence a65c9e50f716e564] Node `record` copies only `gauntlet/write/`, `gauntlet/revisions/` and the approved rev files into the checkout. Node `remove` then runs `archon complete --force` on the lan
- 2026-11-08 github ohshitgorillas/gauntlet 3307ed5485f79960: [cadence 3307ed5485f79960] Writing has no counterpart to the mend's `settle`. `result` is specified to write `<slug>.blocks.<move>.json` (which closes the wave) and to save the leftover patch, with no
- 2026-11-08 github ohshitgorillas/gauntlet 180228073a728614: [cadence 180228073a728614] Node `baseline` ends with the tree restore of runtime-model-design.md:145 (`git restore --source=HEAD ... -- :/` and `git clean -fd -- :/`). That rule is justified as safe o
- 2026-11-08 github ohshitgorillas/gauntlet e5426ab16b1c4361: [cadence e5426ab16b1c4361] The set-aside moves 'every file of the slug' into `stale/<slug>.<n>/` (the ledger on an item-hash change, and `gauntlet-run`'s `back`). But the naming `<slug>-summary.N.md`
