Status: proposed.

# Gauntlet intake round

## Why

Intake turns the owner's task into one concrete, well-specced task file and hands its path to plan review. It runs on its own (`archon workflow run intake`) and is the first phase of `gauntlet-run`, the workflow for a whole run, which includes it as block `intake`; `gauntlet-design.md` gives the run, its `guard` node and how phases join. Two routes reach intake: the run's `file` input names a markdown file the owner wrote, or the owner hammers the task out with Clerk, the task specialist. A run started from the Archon web UI ("What should Archon work on?") has a blank `file` and takes the Clerk route. Both routes end in the same hand-off, so plan review never knows which route a task took.

Gauntlet is its own git repository, cloned by each user into `$ARCHON_HOME/workflows/gauntlet/` (by default `~/.archon/workflows/gauntlet/`), the pack root, which Archon scans for every repository on the host. Intake's script nodes run on Bun; the Python ones run on `uv`. Intake runs in any repository's checkout, on its own or inside `gauntlet-run`. Every path below is relative to the pack root unless it names `archon-workflows` (`~/dev/archon-workflows`) or the run's checkout.

What the trees already hold for the concerns intake touches:

- Task intake: no live copy. The removed `feature` workflow read a request file by a `request` input; nothing of it remains but its fixtures under archon-workflows `.archon/workflows/feature-pipeline/feature/fixtures/`, which intake does not touch.
- Gauntlet-written state: no Gauntlet workflow writes anything yet. archon-workflows ignores `.gauntlet/` through `.git/info/exclude` for the owner's job chain; that pattern does not cover `gauntlet/`.
- Task format: no home yet.
- File confinement: two copies. `fence/` in the pack: `files.py` (stdio MCP file server confined by `FENCE_*` folders under `CLAUDE_PROJECT_DIR`), `checks.py` (stdio MCP test runner), `files_helpers.py`, `test_files.py`, `test_files_write.py`; `docs/testing.md` cites `fence/test_*.py`. The older copy stays in archon-workflows `.archon/workflows/feature-pipeline/fence/` (the same five files, its `test_files_write.py` behind the pack's, plus `__pycache__`), cited by archon-workflows `docs/testing.md`. No workflow attaches either.
- This design: a second copy sits in archon-workflows `docs/superpowers/specs/gauntlet-intake-design.md`.

## Modules

### `fence/`

Gauntlet's file confinement: the stdio MCP servers that give an agent node exactly the reads, writes and checks its role allows. It holds `files.py`, `checks.py`, `files_helpers.py`, `test_files.py`, `test_files_write.py`, and replaces archon-workflows `.archon/workflows/feature-pipeline/fence/`. Intake uses only `files.py`; nothing in intake attaches `checks.py`. Its suite runs as `docs/testing.md` states, with the folder `fence`.

```python
# files.py — server "fence-files"; run as: uv run --script "${ARCHON_HOME:-$HOME/.archon}/workflows/gauntlet/fence/files.py"
# Environment (colon-separated folders, relative to the root; "." is the whole root; unset or empty allows nothing):
#   CLAUDE_PROJECT_DIR  root; must name an existing directory whose real path equals the real path of the server's
#                       working directory, else exit 2 (Claude Code sets it to the agent's working directory when no
#                       config gives a value, and a config value wins, PROBES.md P2)
#   FENCE_READ          readable folders
#   FENCE_WRITE         writable folders; .archon, .claude and .git are always refused
#   FENCE_DENY          folders refused for writes
#   FENCE_ONCE          folders whose files are written once
#   FENCE_COPY          folders whose new files come only from copy_file
def read_file(path: str, offset: int = 0, limit: int = 2000) -> str: ...
def list_directory(path: str = ".") -> str: ...
def find_files(pattern: str, path: str = ".") -> str: ...
def grep(regex: str, path: str = ".", glob: str | None = None) -> str: ...
def write_file(path: str, content: str) -> str: ...
def edit_file(path: str, old: str, new: str, replace_all: bool = False) -> str: ...
def copy_file(src: str, dst: str) -> str: ...
def delete_file(path: str) -> str: ...

# checks.py — server "fence-checks"; environment CLAUDE_PROJECT_DIR (the same check as files.py); the brief test command
#   and the timeout come from gauntlet/settings.json of the root (writing design), never from the server's environment
async def run_tests() -> str: ...
```

### `.shared/working-folder.ts`

Gauntlet's working-folder guard: the one check that the checkout keeps `gauntlet/` out of git, and the one place its failure messages live. `gauntlet-run/scripts/guard.ts`, the run's `guard` node, calls it with option `committed` once per run in the checkout, before any phase writes under `gauntlet/`, because the run's tree holds only committed files; each standalone phase's own `guard` node (`intake/scripts/guard.ts`, `plan-review/scripts/guard.ts`, `spec-review/scripts/guard.ts`) calls it without the option before the phase writes. Replaces nothing.

```typescript
// Run from the checkout (a script node's working directory).
// Passes when git reports gauntlet/ ignored in the checkout: .gitignore, .git/info/exclude
// and the global excludes file all count. A file under gauntlet/ that git tracks fails it.
// With committed, `git check-ignore -v gauntlet/` names the rule's source: a rule from .git/info/exclude or the
// global excludes file passes (a tree shares both); a rule from a .gitignore passes only when git tracks that file
// and `git diff --quiet HEAD -- <file>` holds.
// Fails by writing one line to stderr and exiting 1, <root> being `git rev-parse --show-toplevel`:
//   gauntlet/ not ignored:
//     Gauntlet failed because its working folder, <root>/gauntlet/, sits in the main repo. Add it to .gitignore and restart the run.
//   a file under gauntlet/ that git tracks, <file> being the first such path:
//     Gauntlet failed because git tracks <root>/<file> under its working folder. Run `git rm --cached <file>` (and add gauntlet/ to .gitignore if it is not ignored), commit, and restart the run.
//   with committed, the rule's .gitignore untracked or changed since HEAD, <file> being that .gitignore:
//     Gauntlet failed because the rule keeping <root>/gauntlet/ out of git sits in <root>/<file>, which is not committed, and the run's tree holds only committed files. Commit <file> and restart the run.
export function requireIgnored(options?: { committed?: boolean }): void;
```

### `.shared/task-format.md`

The one statement of what a task file holds. Clerk works to it; the file route is not checked against it.

```markdown
# <title>                      <- first line, always present; the task's name

## Outcome                     <- what is true for the owner when the task is done, in product terms
## Why                         <- the need or problem, in the owner's words where they gave them
## Done when                   <- checks the owner can observe, one per line
## Out of scope                <- what the task does not change
## Owner's standing words      <- verbatim rules the owner gave for this task

Rules:
- Every section is optional: a section is present only when it fits the task, and present sections keep this order.
- Any size and kind: a one-line bug fix and a large refactor draw on the same sections.
- Names no source file, function, module or line, and prescribes no code change: how the outcome is reached is the planner's.
- Plain present tense; no history of the conversation that produced it.
```

### `intake/commands/clerk.md`

Clerk's role: hammer a vague idea into a task file that meets `task-format.md`, in one continuing conversation with the owner. Replaces nothing.

```markdown
Inputs in the session: the owner's idea ($ARGUMENTS, may be empty), task-format.md and the slugs already taken (from node `ground`).
Opening turn (node `clerk`): read the idea; give the owner the first reply (questions, or a draft when the idea already holds enough); when the reply holds a draft, pick a kebab-case slug not among the taken ones and output the whole draft; output { slug, reply, draft }, slug and draft "" until there is a draft.
Each later turn (node `turn`):
  - reads the owner's choice and words from the previous answer, and the latest refusal, when there is one (a slug taken by another run: pick another; a slug unlike the one already written: keep that one);
  - replies to the owner: questions, or the draft's open points, kept short;
  - outputs the whole draft on the turn it first holds enough to draft, and again on every turn that changes it, with the slug (the slug of the first draft, unchanged once a draft has been written); draft "" on a turn that leaves a written draft unchanged; the draft always meets task-format.md's rules;
  - on "approve" with no draft yet: outputs the draft this turn;
  - output { slug, reply, draft }.
Reads: anything in the checkout the task needs, code included, with no cap on reads or turns.
Never: writes any file (node `put` writes the draft), copies or deletes a file, names code in the task file, decides for the owner that the task is finished.
Tools: the fence-files server only (read_file, list_directory, find_files, grep), read-only; no built-in tool.
```

### `intake/clerk.mcp.json`

Clerk's fence: the one MCP config both Clerk nodes attach. Read-only. Replaces nothing.

```json
{
  "mcpServers": {
    "fence-files": {
      "command": "sh",
      "args": ["-c", "exec uv run --script \"${ARCHON_HOME:-$HOME/.archon}/workflows/gauntlet/fence/files.py\""],
      "env": {
        "FENCE_READ": "."
      }
    }
  }
}
```

Claude Code sets the server's `CLAUDE_PROJECT_DIR` to its own working directory, the run's checkout, when the config gives none, and a value the config gives wins (PROBES.md P2). Every fence config of the pack therefore sets none, and `fence/files.py` and `fence/checks.py` exit 2 at start when the real path of `CLAUDE_PROJECT_DIR` differs from the real path of their working directory, whatever set it. `FENCE_WRITE`, `FENCE_DENY`, `FENCE_ONCE` and `FENCE_COPY` stay unset. The checkout is any repository, so the server is found in the pack wherever its user cloned it into their Archon home: `sh` resolves `$ARCHON_HOME`, else `$HOME/.archon`, on every host, and `exec` leaves `uv` as the server process.

### `intake/scripts/`: `guard.ts`, `route.ts`, `ground.ts` and `put.ts`

The scripts of intake's own nodes. Replace nothing.

```typescript
// guard.ts — node `guard`, the phase's own working-folder check: the two lines of gauntlet-tree/scripts/guard.ts
//   (requireIgnored from ../../.shared/working-folder.ts). In a run it repeats the run's guard, which has passed.

// route.ts — node `route`, the block's entry node: stdout { "file": process.env.INPUTS_FILE ?? "" }

// ground.ts — node `ground`: prints task-format.md, then the names in gauntlet/tasks/ of the checkout (none when absent)
import taskFormat from "../../.shared/task-format.md" with { type: "text" };

// put.ts — nodes `put-open` and `put`, the only writer of a Clerk draft. Env: INPUTS_SLUG, INPUTS_DRAFT; ARTIFACTS_DIR.
//   <owned> is the slug of the one marker $ARTIFACTS_DIR/owned.<owned>, when there is one; "task" is always the absolute
//     path of gauntlet/tasks/<owned>.md, or "" with no marker. First that holds:
//   draft "" or slug "": writes nothing (an empty draft after the first write means unchanged),
//     stdout { "slug": <owned> or "", "task", "refusal": "" }.
//   a marker present and slug unlike <owned>: writes nothing,
//     stdout { "slug": <owned>, "task", "refusal": "The slug <slug> differs from <owned>, the slug of this run's task file. Keep <owned>." }.
//   gauntlet/tasks/<slug>.md present and no marker: the slug is taken by another run; writes nothing,
//     stdout { "slug", "task": "", "refusal": "The slug <slug> is taken by another run. Pick another." }.
//   Else writes gauntlet/tasks/<slug>.md with the draft (whole file, overwritten), touches $ARTIFACTS_DIR/owned.<slug>,
//     stdout { "slug", "task", "refusal": "" }.
```

### `intake/intake.yaml`

The intake block: both routes, the owner's approval on the Clerk route, and the hand-off. It runs on its own and `gauntlet-run` includes it as node `intake`. Replaces nothing.

```yaml
name: intake
description: >-
  Gauntlet intake. Turns the message into a task file under gauntlet/tasks/ through a conversation with Clerk, the task specialist, ending when the owner approves the task file as written; with the `file` input, copies a task file the owner wrote, as written, into gauntlet/tasks/, failing on any name conflict for the owner to correct and resume. Runs on its own for this phase; to take a task through every phase, start gauntlet-run.
provider: claude
model: claude-opus-5-5
effort: medium
worktree:
  enabled: false                                 # a standalone run needs it; Archon drops it under include: (P7)
inputs:
  file:
    default: ""
    description: Path of a task file the owner wrote. Blank sends the run's message to Clerk.
returns: handoff

nodes:
  - id: guard                                    # the phase's own working-folder check
    runtime: bun
    script: guard

  # Entry node: the file input as a node output, so no when: reads $INPUTS.
  - id: route
    depends_on: [guard]
    runtime: bun
    script: route
    output_format: { type: object, properties: { file: { type: string } }, required: [file] }

  # File route: the owner's file, unchecked, copied verbatim to gauntlet/tasks/<slug>.md.
  - id: from-file
    depends_on: [route]
    when: "$route.output.file != ''"
    bash: <realpath -e the file $route.output.file (fails, naming the path, when it is missing); slug = its file name without extension, lowercased, each run of characters outside [a-z0-9] made one "-", "-" trimmed from both ends; the file already at gauntlet/tasks/<slug>.md: task is that path, nothing copied; else gauntlet/tasks/<slug>.md free: copy (cp -n), task is its absolute path; else gauntlet/tasks/<slug>.md holds the same bytes as the file (cmp): task is that path, nothing copied; else (target taken by different bytes, or empty slug) exit non-zero, the conflict and both paths on stderr; nothing renamed, suffixed or overwritten>
    output_format: { type: object, properties: { task: { type: string } }, required: [task] }

  # Clerk route.
  - id: ground
    depends_on: [route]
    when: "$route.output.file == ''"
    runtime: bun
    script: ground

  - id: clerk                                    # opening turn; the session's source; writes no file
    depends_on: [ground]
    command: clerk
    allowed_tools: []                            # no built-in tool; files only through the read-only fence
    mcp: clerk.mcp.json                          # found beside this YAML
    output_format: { type: object, properties: { slug: { type: string, pattern: "^([a-z0-9]+(-[a-z0-9]+)*)?$" }, reply: { type: string }, draft: { type: string } }, required: [slug, reply, draft] }

  - id: put-open                                 # writes the opening draft, when it has one
    depends_on: [clerk]
    runtime: bun
    script: put
    with:
      slug: { from: $clerk.output.slug }
      draft: { from: $clerk.output.draft }
    output_format: { type: object, properties: { slug: { type: string }, task: { type: string }, refusal: { type: string } }, required: [slug, task, refusal] }

  - id: talk
    depends_on: [put-open]
    loop_group:
      max_iterations: 1                          # each answer permits one more turn; no cap on the conversation
      until_bash: |
        decision=$answer.output.decision
        task=$latest.output.task
        [ "$decision" = "approve" ] && [ -s "$task" ]
      nodes:
        - id: turn                               # runs only once the owner has answered
          when: "$LOOP_PREV.answer.output.decision != ''"
          context: { resume: clerk }             # one continuing session for the whole conversation
          allowed_tools: []
          mcp: clerk.mcp.json
          prompt: <the owner's choice $LOOP_PREV.answer.output.decision and words $LOOP_PREV.answer.output.text; the refusal $LOOP_PREV.latest.output.refusal>
          output_format: { type: object, properties: { slug: { type: string, pattern: "^([a-z0-9]+(-[a-z0-9]+)*)?$" }, reply: { type: string }, draft: { type: string } }, required: [slug, reply, draft] }
        - id: put                                # the turn's draft written, or refused
          depends_on: [turn]
          runtime: bun
          script: put
          with:
            slug: { from: $turn.output.slug }
            draft: { from: $turn.output.draft }
          output_format: { type: object, properties: { slug: { type: string }, task: { type: string }, refusal: { type: string } }, required: [slug, task, refusal] }
        - id: latest                             # always runs: the iteration's task path and refusal
          depends_on: [put]
          trigger_rule: all_done
          runtime: bun
          script: <task "<skipped>" (put skipped): print put-open's task and refusal; else put's, the refusal even when empty; print { task, refusal }>
          with:
            task: { from: $put.output.task, if_skipped: "<skipped>" }
            refusal: { from: $put.output.refusal, if_skipped: "<skipped>" }
            opened: { from: $put-open.output.task }
            opening_refusal: { from: $put-open.output.refusal }
          output_format: { type: object, properties: { task: { type: string }, refusal: { type: string } }, required: [task, refusal] }
        - id: show
          depends_on: [turn, latest]
          trigger_rule: all_done
          runtime: bun
          script: <print reply (turn's, else the opening), the refusal when there is one, a rule, then the task file or "No task file yet.">
          with:
            reply: { from: $turn.output.reply, if_skipped: "" }
            opening: { from: $clerk.output.reply }
            task: { from: $latest.output.task }
            refusal: { from: $latest.output.refusal }
        - id: answer
          depends_on: [show]
          wait:
            form: select
            attention: "$show.output"
            options:
              - { id: approve, label: "Approve the task file as written" }
              - { id: reply, label: "Reply (your words in the text)" }

  # Hand-off: the one result both routes produce.
  - id: handoff
    depends_on: [from-file, talk]
    trigger_rule: none_failed_min_one_success
    runtime: bun
    script: <task = file || the absolute path of gauntlet/tasks/<slug>.md for the slug whose marker owned.<slug> sits in $ARTIFACTS_DIR (one at most: put refuses a second slug); print { task }>
    with:
      file: { from: $from-file.output.task, if_skipped: "" }
    output_format: { type: object, properties: { task: { type: string } }, required: [task] }
```

Intake runs on its own or as block `intake` of `gauntlet-run`, in the checkout. Run on its own, its `guard` is the working-folder check; included, `gauntlet-run`'s `guard` has already passed and the phase's repeats a passing git query. Routing reads only `route`'s output, the `file` input (`gauntlet-run` passes it in by `with:`), never the typed text. With `file` blank, `$ARGUMENTS` (the run's message: the text typed in the web UI, or the CLI message) is Clerk's starting idea, and may be empty. The `talk` group's session is Clerk's, forked once from `clerk` and continued across every pause; no turn starts a fresh agent and no conversation log is kept. Clerk writes no file: each turn outputs the slug, and the whole draft whenever it changes, and node `put` is the only writer of `gauntlet/tasks/<slug>.md`; an empty draft after the first write leaves the file unchanged. A slug already taken by a file this run did not write is refused, and so is a slug unlike the one of the run's first write, so a run owns one task file. Node `latest` always runs and prints the iteration's task path and refusal: `put`'s whenever `put` ran, else `put-open`'s. The group's completion, `show` and Clerk's next turn read it, so a refusal reaches Clerk's next turn and `show` never prints a stale one. The opening turn is Clerk's first reply to the owner; `turn` is skipped in the first iteration and runs in every later one. An answer of `approve` ends the conversation only when a task file exists; otherwise the next turn outputs the draft and asks again. A file-route conflict fails the run at `from-file`; the owner corrects it on disk and resumes the run with `archon workflow resume <run id>`, which re-runs `from-file`.

### `intake/fixtures/`

`file.stubs.yaml` (`route` stubbed with a `file`: `guard`, `route`, `from-file` and `handoff` reached, `ground` not) and `clerk.stubs.yaml` (`route` stubbed with a blank `file`, the opening reply approved: `guard`, `route`, `ground`, `clerk`, `put-open`, `talk` with its `latest`, `handoff` reached, `from-file` and `turn` not), under `docs/testing.md`. A route needing a second turn is not fixture-tested: a dry run ends a loop after one iteration. The conflict route is not fixture-tested: its deciding logic is `from-file`'s own bash, which stubs replace.

### The run's checkout

The owner keeps `gauntlet/` out of git in each repository Gauntlet runs in, by a `gauntlet/` line in its `.gitignore`, committed, or in `.git/info/exclude`; `gauntlet-run`'s `guard` refuses a `.gitignore` line that is not committed. No Gauntlet node writes that line. Intake commits nothing; a task file lives in the live checkout and the hand-off carries its absolute path.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| Gauntlet's files | the Gauntlet repository at `$ARCHON_HOME/workflows/gauntlet/` | Any Gauntlet file, fence or design in archon-workflows or in a run's checkout |
| Reaching a pack file from a run in any repository | `mcp:` named beside the workflow YAML; `.shared/` imported relative to the script's own file; the fence server under `${ARCHON_HOME:-$HOME/.archon}/workflows/gauntlet/` in `clerk.mcp.json` | A checkout-relative path to any pack file; a path naming one user's home |
| What a task file holds | `.shared/task-format.md` | Restating the sections or rules in a command, prompt or workflow; `ground` prints the file instead |
| Where intake writes | `gauntlet/` in the run's checkout, tasks at `gauntlet/tasks/<slug>.md`; `$ARTIFACTS_DIR` holds only the `owned.<slug>` marker of node `put` | Any intake node writing outside `gauntlet/` and `$ARTIFACTS_DIR`; `$ARTIFACTS_DIR` or `$STATE_DIR` holding a task |
| Keeping `gauntlet/` out of git | the owner's `.gitignore` line in each repository; `requireIgnored` in `.shared/working-folder.ts`, called with option `committed` by node `guard` of `gauntlet-run` before any phase, and without it by node `guard` of `intake` | A node writing the ignore line; a write under `gauntlet/` before the guard passes; a second statement of the check or its messages; a check that accepts only `.gitignore`; option `committed` passed by any guard but `gauntlet-run`'s |
| Choosing the route | `intake.yaml`, `when:` on `$route.output.file` | Routing on the typed text; `$INPUTS` in a `when:`; a second intake workflow |
| A handed-in file's slug and copy | `from-file` | Renaming, suffixing or overwriting a task |
| Raising a file-route conflict | `from-file` failing the run with the conflict on stderr; the owner corrects it and resumes | A conflict resolved, skipped or only logged; a wait asking for a new slug |
| The owner's approval of a Clerk task | the `answer` wait in `talk` | Any other approval before hand-off; an approval of a handed-in file |
| Clerk's memory | the `clerk` session, continued by `turn` | A fresh agent per turn; a conversation log file; `persist_session` |
| File confinement for a Gauntlet agent | `fence/files.py` | A second file server; a copy left in archon-workflows `.archon/workflows/feature-pipeline/`; a hook or prompt rule standing in for it |
| Clerk's file access | `clerk.mcp.json` (`FENCE_READ=.`, no `FENCE_WRITE`), attached by `mcp:` on `clerk` and `turn`, both with `allowed_tools: []` | Any built-in tool on either node; `FENCE_*` set anywhere but `clerk.mcp.json`; Clerk writing, copying or deleting any file |
| Writing a Clerk draft | node `put` (and `put-open` for the opening turn), the only writer of `gauntlet/tasks/<slug>.md` on the Clerk route; it refuses a slug taken by a file this run did not write, and a slug unlike the one of its first write | any other writer of a draft; a slug overwritten across runs; a second task file in one run |
| A Clerk iteration's task path and refusal | node `latest` in `talk`: `put`'s whenever `put` ran, else `put-open`'s | The completion check, `show` or `turn` reading `put` or `put-open` directly |
| The hand-off to plan review | `handoff` output `{ task }`, the block's `returns:`, read by `gauntlet-run` as `$intake.output.task` | Any other node or file telling plan review where the task is, or how it was made |

## Order

1. Clear the moved copies out of archon-workflows: `.archon/workflows/feature-pipeline/fence/` removed with its `__pycache__`, `docs/superpowers/specs/gauntlet-intake-design.md` removed, and `docs/testing.md` there citing no removed path. Agent: `builder`.
2. Task format and Clerk's role: `.shared/task-format.md`, `intake/commands/clerk.md`. Agent: `role-author`.
3. Working-folder guard and intake block: `.shared/working-folder.ts`, `intake/scripts/guard.ts`, `intake/scripts/route.ts`, `intake/scripts/ground.ts`, `intake/scripts/put.ts`, `intake/intake.yaml`, `intake/clerk.mcp.json`, `intake/fixtures/file.stubs.yaml`, `intake/fixtures/clerk.stubs.yaml`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
