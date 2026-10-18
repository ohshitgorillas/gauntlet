# Gauntlet

Gauntlet is a strict LLM coding workflow for established codebases where shipping bugs has consequences. It turns your brief into a reviewed plan, a reviewed spec, blind tests, and an implementation that passes them. A program enforces every step; no agent is trusted to follow the rules.

Status: v0.11.0 is a design. The harness is not built yet. See [`docs/charter.md`](docs/charter.md) for purpose, [`docs/design.md`](docs/design.md) for how it works, [`docs/config.md`](docs/config.md) for setting up a repository, and [`docs/roadmap.md`](docs/roadmap.md) for the build order.

## Requirements

- Linux with rootless podman
- Python 3.12 or later
- An Anthropic API key
- A repository with a `gauntlet.yaml` (see [`docs/config.md`](docs/config.md))

## A job, start to finish

```
$ gauntlet new
```

1. **Brief.** You talk with the brief-writer. It reads the code to answer your questions and changes nothing. Type `done` and it shows you the brief; `approve` it.
2. **Outline.** The planner shows the steps, which specialist takes each, and what each touches, before any expensive review. `approve`, or redirect it in your own words.
3. **Plan.** You see one status line per prosecutor round, each naming its file, for example `.gauntlet/jobs/0143/plan.2.objections.md`. A change in direction comes back to you. You approve the plan once it passes.
4. **Spec.** You see the short list of behaviors first, then the arbiter rounds. You approve the final spec.
5. **Tests and red run.** You see status per tester, a red line per test, and the juror's verdict per spec line.
6. **Build.** You see status per plan step and specialist, and the gate results.
7. **Review and bailiff.** You see the findings for each round, then the bailiff's verdict.
8. **Land.** You see the land screen:
   - the diff, split into tests and code;
   - red and green lines;
   - open findings;
   - amendments and bypasses;
   - cost per role.

   `approve` and the harness merges into `main`.

When a job stops, whether at a round cap, at a block, or on your command, you get one screen showing what stopped and both sides.

## Commands

| Command | Does |
|---|---|
| `gauntlet new` | Start a job with a brief conversation |
| `gauntlet run <brief.md>` | Start a job from a brief written elsewhere |
| `gauntlet epic` | Start an effort split into several jobs |
| `gauntlet audit <scope>` | Sweep existing tests against the test policy |
| `gauntlet status [<id>]` | Show where jobs stand |
| `gauntlet stop <id>` | Stop a job at once |
| `gauntlet resume <id>` | Continue a stopped job |
| `gauntlet retry <id> [--note "…"]` | Run the failed stage again |
| `gauntlet accept <id>` | Rule the stopped stage passed |
| `gauntlet edit <id>` | Edit the stage's file or the tree yourself, then `resume` |
| `gauntlet skip <id> <stage>` | Drop a stage |
| `gauntlet eject <id>` | Hand the job's branch and files to you and step out |
| `gauntlet reopen <id> <line>` | Send a spec line back for amendment |

Bypasses are always recorded and shown on the land screen.

## Where things are saved

Everything for a job is in `.gauntlet/jobs/<id>/`: the conversation, brief, every plan and spec round, the red run, verdicts, step logs, reviews, the land screen, and the cost of every agent call. The job's checkout is `tree/`, on branch `gauntlet/<id>`. Epics are in `.gauntlet/epics/<id>/`. The harness keeps `.gauntlet/` out of git through `.git/info/exclude`.
