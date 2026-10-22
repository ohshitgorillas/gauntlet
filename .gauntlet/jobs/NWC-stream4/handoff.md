# NWC stream 4: handoff

Branch `nwc-build`, rebased on main at `28c6d73`. Design: `docs/superpowers/specs/2026-10-21-no-wall-clock-design.md`, its Order.

## State

- Order steps 1 to 27 are landed on `nwc-build`. Next step: 28 (`port`, `test_second_run_waits` and `test_waits_on_flock` in `tests/test_heavy.py` read the wrapper's `WAITING` line in place of `_settle`).
- Nothing is uncommitted or half-done.
- Step 33's spike runs on a host that lacks `nproc` and `timeout`; a Linux host with coreutils has both, so the spike cannot run there and is a stop to report.

## Open

- `tests/test_heavy_waiting.py` module docstring says the test calls `acquire` in its own thread; `acquire` runs on the main thread. No finding names it yet.
- No pre-commit hook is installed in a fresh clone (`.git/hooks/pre-commit` absent, `core.hooksPath` unset), so `make check` is run by hand before each commit.

## Standing instructions

- One step per dispatch, to the agent the step names, with the brief its role requires. Merge back-to-back steps of the same kind into one job: a run of red steps is one `test-writer` red brief of several behaviors; a run of ports is one job; a run of docs steps is one docs job; a stub folds into the red job after it only when the same agent writes both. Test jobs and build jobs stay apart. A merged job stays one diff of about 300 changed lines at most with one test command proving it; split a longer run at a step boundary. Name the step numbers each commit covers.
- Stub and red steps land in the commit of the build step that turns them green; every other step is its own commit.
- Models: Sonnet for port, moved and docs-only steps and every reviewer pass on them; Opus for red steps, module steps, spikes and architect passes. Effort: medium on every dispatch.
- Reviews: `diff-reviewer` on any diff touching `gates/` and `test-reviewer` on any diff touching `tests/`, each briefed with the diff scope only. A builder's change outside the step's scope (code with no red test of this step) is undone before landing.
- `make check` runs before each commit, in full, unpiped, as an unprivileged user (tests of unreadable files cannot fail as root), on uv's managed Python 3.12.13. Commit with hooks on, never `--no-verify`. Push `nwc-build` after every commit.
- At a rebase onto main, keep main's `.claude/agents/gatesmith.md` over the branch's.
- A step its role refuses, a spike that cannot run on the host, or a needed design decision is a stop: push what is committed and report.
