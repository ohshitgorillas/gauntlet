Status: proposed.

# Gauntlet intake round

## Why

Intake turns the owner's task into one concrete, well-specced task file and hands its path to the planning round. Two routes reach it: the owner hands in a markdown file they wrote, or the owner hammers the task out with Clerk, the task specialist. Text typed into the Archon web UI ("What should Archon work on?") always takes the Clerk route. Both routes end in the same hand-off, so the planner never knows which route a task took.

Gauntlet is its own git repository, cloned by each user into `$ARCHON_HOME/workflows/gauntlet/` (by default `~/.archon/workflows/gauntlet/`), the pack root, which Archon scans for every repository on the host. Script nodes run on Bun. Intake runs in any repository's checkout. Every path below is relative to the pack root unless it names `archon-workflows` (`~/dev/archon-workflows`) or the run's checkout.

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
#   CLAUDE_PROJECT_DIR  root; must name an existing directory, else exit 2
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

# checks.py — server "fence-checks"; environment CLAUDE_PROJECT_DIR, FENCE_TEST_COMMAND, FENCE_TEST_TIMEOUT
async def run_tests() -> str: ...
```

### `.shared/working-folder.ts`

Gauntlet's working-folder guard: the one check that the checkout keeps `gauntlet/` out of git, and the one failure message when it does not. Every Gauntlet workflow calls it from its first node, before anything writes under `gauntlet/`. Replaces nothing.

```typescript
// Run from the checkout (a script node's working directory).
// Passes when git reports gauntlet/ ignored in the checkout: .gitignore, .git/info/exclude
// and the global excludes file all count. A file under gauntlet/ that git tracks fails it.
// Fails by writing one line to stderr and exiting 1, <root> being `git rev-parse --show-toplevel`:
//   Gauntlet failed because its working folder, <root>/gauntlet/, sits in the main repo. Add it to .gitignore and restart the run.
export function requireIgnored(): void;
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
Opening turn (node `clerk`): read the idea; pick a kebab-case slug not among the taken ones; give the owner the first reply (questions, or a draft written to gauntlet/tasks/<slug>.md when the idea already holds enough); output { slug, reply }.
Each later turn (node `turn`):
  - reads the owner's choice and words from the previous answer;
  - replies to the owner: questions, or the draft's open points, kept short;
  - writes or edits gauntlet/tasks/<slug>.md once it holds enough to draft, and keeps it current every turn after; the file always meets task-format.md's rules;
  - on "approve" with no task file yet: writes it this turn;
  - output { reply }.
Reads: anything in the checkout the task needs, code included, with no cap on reads or turns.
Never: writes outside gauntlet/tasks/<slug>.md, copies or deletes a file, names code in the task file, decides for the owner that the task is finished.
Tools: the fence-files server only (read_file, list_directory, find_files, grep, write_file, edit_file); no built-in tool.
```

### `intake/clerk.mcp.json`

Clerk's fence: the one MCP config both Clerk nodes attach. Replaces nothing.

```json
{
  "mcpServers": {
    "fence-files": {
      "command": "sh",
      "args": ["-c", "exec uv run --script \"${ARCHON_HOME:-$HOME/.archon}/workflows/gauntlet/fence/files.py\""],
      "env": {
        "FENCE_READ": ".",
        "FENCE_WRITE": "gauntlet/tasks"
      }
    }
  }
}
```

Claude Code sets the server's `CLAUDE_PROJECT_DIR` to its own working directory, the run's checkout, and overrides any value the config gives, so the config sets none. `FENCE_DENY`, `FENCE_ONCE` and `FENCE_COPY` stay unset. The checkout is any repository, so the server is found in the pack wherever its user cloned it into their Archon home: `sh` resolves `$ARCHON_HOME`, else `$HOME/.archon`, on every host, and `exec` leaves `uv` as the server process.

### `intake/scripts/guard.ts` and `intake/scripts/ground.ts`

The two named scripts of intake's opening nodes. Replace nothing.

```typescript
// guard.ts — node `guard`
import { requireIgnored } from "../../.shared/working-folder.ts";
requireIgnored();

// ground.ts — node `ground`: prints task-format.md, then the names in gauntlet/tasks/ of the checkout (none when absent)
import taskFormat from "../../.shared/task-format.md" with { type: "text" };
```

### `intake/intake.yaml`

The intake workflow: both routes, the owner's approval on the Clerk route, and the hand-off. Replaces nothing.

```yaml
name: intake
description: >-
  Gauntlet intake. Turns what the owner describes into a task file under gauntlet/tasks/ through a conversation with Clerk, the task specialist, ending when the owner approves the task file as written; with the `file` input, copies a task file the owner wrote, as written, into gauntlet/tasks/, failing on any name conflict for the owner to correct and resume. Use for any new piece of work the owner types or hands in; not for planning or building.
provider: claude
model: claude-opus-5-5
effort: medium
worktree:
  enabled: false            # task files land in the live checkout
inputs:
  file:
    default: ""
    description: Path of a task file the owner wrote. Blank sends the run to Clerk.
returns: handoff

nodes:
  # Both routes: the checkout must keep gauntlet/ out of git.
  - id: guard
    runtime: bun
    script: guard

  # File route: the owner's file, unchecked, copied verbatim to gauntlet/tasks/<slug>.md.
  - id: from-file
    depends_on: [guard]
    when: "$INPUTS.file != ''"
    bash: <realpath -e the file (fails, naming the path, when it is missing); slug = its file name without extension, lowercased, each run of characters outside [a-z0-9] made one "-", "-" trimmed from both ends; the file already at gauntlet/tasks/<slug>.md: task is that path, nothing copied; else gauntlet/tasks/<slug>.md free: copy (cp -n), task is its absolute path; else (target taken, or empty slug) exit non-zero, the conflict and both paths on stderr; nothing renamed, suffixed or overwritten>
    output_format: { type: object, properties: { task: { type: string } }, required: [task] }

  # Clerk route.
  - id: ground
    depends_on: [guard]
    when: "$INPUTS.file == ''"
    runtime: bun
    script: ground

  - id: clerk                                    # opening turn; the session's source
    depends_on: [ground]
    command: clerk
    allowed_tools: []                            # no built-in tool; files only through the fence
    mcp: clerk.mcp.json                          # found beside this YAML
    output_format: { type: object, properties: { slug: { type: string, pattern: "^[a-z0-9]+(-[a-z0-9]+)*$" }, reply: { type: string } }, required: [slug, reply] }

  - id: talk
    depends_on: [clerk]
    loop_group:
      max_iterations: 1                          # each answer permits one more turn; no cap on the conversation
      until_bash: |
        decision=$answer.output.decision
        slug=$clerk.output.slug
        [ "$decision" = "approve" ] && [ -s "gauntlet/tasks/$slug.md" ]
      nodes:
        - id: turn                               # runs only once the owner has answered
          when: "$LOOP_PREV.answer.output.decision != ''"
          context: { resume: clerk }             # one continuing session for the whole conversation
          allowed_tools: []
          mcp: clerk.mcp.json
          prompt: <the owner's choice $LOOP_PREV.answer.output.decision and words $LOOP_PREV.answer.output.text; the task path>
          output_format: { type: object, properties: { reply: { type: string } }, required: [reply] }
        - id: show
          depends_on: [turn]
          trigger_rule: all_done
          runtime: bun
          script: <print reply (turn's, else the opening), a rule, then gauntlet/tasks/<slug>.md or "No task file yet.">
          with:
            reply: { from: $turn.output.reply, if_skipped: "" }
            opening: { from: $clerk.output.reply }
            slug: { from: $clerk.output.slug }
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
    script: <task = file || absolute path of gauntlet/tasks/<slug>.md; print { task }>
    with:
      file: { from: $from-file.output.task, if_skipped: "" }
      slug: { from: $clerk.output.slug, if_skipped: "" }
    output_format: { type: object, properties: { task: { type: string } }, required: [task] }
```

Intake is launched as `intake` from any repository's checkout and writes only in that checkout. `guard` runs first on both routes; when it fails, nothing is written and the run ends with its message. Routing reads only the `file` input, never the typed text. With `file` blank, `$ARGUMENTS` (the text typed in the web UI, or the CLI message) is Clerk's starting idea, and may be empty. The `talk` group's session is Clerk's, forked once from `clerk` and continued across every pause; no turn starts a fresh agent and no conversation log is kept. The opening turn is Clerk's first reply to the owner; `turn` is skipped in the first iteration and runs in every later one. An answer of `approve` ends the conversation only when the task file exists; otherwise the next turn writes it and asks again. A file-route conflict fails the run at `from-file`; the owner corrects it on disk and resumes the run, which re-runs `from-file`.

### `intake/fixtures/`

`file.stubs.yaml` (the `file` input set: `guard`, `from-file` and `handoff` reached, `ground` not) and `clerk.stubs.yaml` (blank `file`, the opening reply approved: `guard`, `ground`, `clerk`, `talk`, `handoff` reached, `from-file` and `turn` not), under `docs/testing.md`. A route needing a second turn is not fixture-tested: a dry run ends a loop after one iteration. The conflict route and the guard's failure are not fixture-tested: their deciding logic is `from-file`'s own bash and `requireIgnored`, which stubs replace.

### The run's checkout

The owner keeps `gauntlet/` out of git in each repository Gauntlet runs in, by a `gauntlet/` line in its `.gitignore`. No Gauntlet node writes that line. Intake commits nothing; a task file lives in the live checkout and the hand-off carries its absolute path.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| Gauntlet's files | the Gauntlet repository at `$ARCHON_HOME/workflows/gauntlet/` | Any Gauntlet file, fence or design in archon-workflows or in a run's checkout |
| Reaching a pack file from a run in any repository | `mcp:` named beside the workflow YAML; `.shared/` imported relative to the script's own file; the fence server under `${ARCHON_HOME:-$HOME/.archon}/workflows/gauntlet/` in `clerk.mcp.json` | A checkout-relative path to any pack file; a path naming one user's home |
| What a task file holds | `.shared/task-format.md` | Restating the sections or rules in a command, prompt or workflow; `ground` prints the file instead |
| Where Gauntlet writes | `gauntlet/` in the run's checkout, tasks at `gauntlet/tasks/<slug>.md` | Any Gauntlet node writing outside `gauntlet/`; `$ARTIFACTS_DIR` or `$STATE_DIR` holding a task |
| Keeping `gauntlet/` out of git | the owner's `.gitignore` line in each repository; `requireIgnored` in `.shared/working-folder.ts`, called by the first node of every Gauntlet workflow (intake: `guard`) | A node writing the ignore line; a write under `gauntlet/` before the guard passes; a second statement of the check or its message; a check that accepts only `.gitignore` |
| Choosing the route | `intake.yaml`, `when:` on `$INPUTS.file` | Routing on the typed text; a second intake workflow |
| A handed-in file's slug and copy | `from-file` | Renaming, suffixing or overwriting a task |
| Raising a file-route conflict | `from-file` failing the run with the conflict on stderr; the owner corrects it and resumes | A conflict resolved, skipped or only logged; a wait asking for a new slug |
| The owner's approval of a Clerk task | the `answer` wait in `talk` | Any other approval before hand-off; an approval of a handed-in file |
| Clerk's memory | the `clerk` session, continued by `turn` | A fresh agent per turn; a conversation log file; `persist_session` |
| File confinement for a Gauntlet agent | `fence/files.py` | A second file server; a copy left in archon-workflows `.archon/workflows/feature-pipeline/`; a hook or prompt rule standing in for it |
| Clerk's file access | `clerk.mcp.json` (`FENCE_READ=.`, `FENCE_WRITE=gauntlet/tasks`), attached by `mcp:` on `clerk` and `turn`, both with `allowed_tools: []` | Any built-in tool on either node; `FENCE_*` set anywhere but `clerk.mcp.json`; a non-agent node writing the task file for Clerk |
| The hand-off to planning | `handoff` output `{ task }`, the workflow's `returns:` | Any other node or file telling planning where the task is, or how it was made |

## Order

1. Clear the moved copies out of archon-workflows: `.archon/workflows/feature-pipeline/fence/` removed with its `__pycache__`, `docs/superpowers/specs/gauntlet-intake-design.md` removed, and `docs/testing.md` there citing no removed path. Agent: `builder`.
2. Task format and Clerk's role: `.shared/task-format.md`, `intake/commands/clerk.md`. Agent: `role-author`.
3. Working-folder guard and intake workflow: `.shared/working-folder.ts`, `intake/scripts/guard.ts`, `intake/scripts/ground.ts`, `intake/intake.yaml`, `intake/clerk.mcp.json`, `intake/fixtures/file.stubs.yaml`, `intake/fixtures/clerk.stubs.yaml`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
