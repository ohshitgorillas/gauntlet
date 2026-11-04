Status: proposed.

# Gauntlet intake round

## Why

Intake turns the owner's task into one concrete, well-specced task file and hands its path to the planning round. Two routes reach it: the owner hands in a markdown file they wrote, or the owner hammers the task out with Clerk, the task specialist. Text typed into the Archon web UI ("What should Archon work on?") always takes the Clerk route. Both routes end in the same hand-off, so the planner never knows which route a task took.

What the tree already holds for the concerns intake touches:

- Task intake: no live copy. The removed `feature` workflow read a request file by a `request` input; nothing of it remains but its fixtures under `.archon/workflows/feature-pipeline/feature/fixtures/`, which intake does not touch.
- Gauntlet-written state: one folder outside `gauntlet/` already carries the name, `.gauntlet/jobs/` (excluded through `.git/info/exclude`), written by the owner's job chain, not by any workflow in the tree. Intake writes only under `gauntlet/`.
- Task format: no home yet.
- File confinement: one copy, `.archon/workflows/feature-pipeline/fence/`, in the pack being dismantled: `files.py` (stdio MCP file server confined by `FENCE_*` folders under `CLAUDE_PROJECT_DIR`), `checks.py` (stdio MCP test runner), `files_helpers.py`, `test_files.py`, `test_files_write.py`. No workflow in the tree attaches it. `docs/testing.md` cites its path as its Python-suite example.

## Modules

### `.archon/workflows/gauntlet/fence/`

Gauntlet's file confinement: the stdio MCP servers that give an agent node exactly the reads, writes and checks its role allows. Moved unchanged from `.archon/workflows/feature-pipeline/fence/`, which it replaces: `files.py`, `checks.py`, `files_helpers.py`, `test_files.py`, `test_files_write.py`. Intake uses only `files.py`; `checks.py` moves with it and nothing in intake attaches it. Its suite runs as `docs/testing.md` states, with the folder `.archon/workflows/gauntlet/fence`.

```python
# files.py — server "fence-files"; run as: uv run --script .archon/workflows/gauntlet/fence/files.py
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

### `.archon/workflows/gauntlet/.shared/task-format.md`

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

### `.archon/workflows/gauntlet/intake/commands/clerk.md`

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

### `.archon/workflows/gauntlet/intake/clerk.mcp.json`

Clerk's fence: the one MCP config both Clerk nodes attach. Replaces nothing.

```json
{
  "mcpServers": {
    "fence-files": {
      "command": "uv",
      "args": ["run", "--script", ".archon/workflows/gauntlet/fence/files.py"],
      "env": {
        "FENCE_READ": ".",
        "FENCE_WRITE": "gauntlet/tasks"
      }
    }
  }
}
```

Claude Code sets the server's `CLAUDE_PROJECT_DIR` to its own working directory, the run's checkout, and overrides any value the config gives, so the config sets none. `FENCE_DENY`, `FENCE_ONCE` and `FENCE_COPY` stay unset.

### `.archon/workflows/gauntlet/intake/intake.yaml`

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
  # File route: the owner's file, unchecked, copied verbatim to gauntlet/tasks/<slug>.md.
  - id: from-file
    when: "$INPUTS.file != ''"
    bash: <realpath -e the file (fails, naming the path, when it is missing); slug = its file name without extension, lowercased, each run of characters outside [a-z0-9] made one "-", "-" trimmed from both ends; the file already at gauntlet/tasks/<slug>.md: task is that path, nothing copied; else gauntlet/tasks/<slug>.md free: copy (cp -n), task is its absolute path; else (target taken, or empty slug) exit non-zero, the conflict and both paths on stderr; nothing renamed, suffixed or overwritten>
    output_format: { type: object, properties: { task: { type: string } }, required: [task] }

  # Clerk route.
  - id: ground
    when: "$INPUTS.file == ''"
    bash: <print .shared/task-format.md, then the names in gauntlet/tasks/ (none when absent)>

  - id: clerk                                    # opening turn; the session's source
    depends_on: [ground]
    command: clerk
    allowed_tools: []                            # no built-in tool; files only through the fence
    mcp: .archon/workflows/gauntlet/intake/clerk.mcp.json
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
          mcp: .archon/workflows/gauntlet/intake/clerk.mcp.json
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

Routing reads only the `file` input, never the typed text. With `file` blank, `$ARGUMENTS` (the text typed in the web UI, or the CLI message) is Clerk's starting idea, and may be empty. The `talk` group's session is Clerk's, forked once from `clerk` and continued across every pause; no turn starts a fresh agent and no conversation log is kept. The opening turn is Clerk's first reply to the owner; `turn` is skipped in the first iteration and runs in every later one. An answer of `approve` ends the conversation only when the task file exists; otherwise the next turn writes it and asks again. A file-route conflict fails the run at `from-file`; the owner corrects it on disk and resumes the run, which re-runs `from-file`.

### `.archon/workflows/gauntlet/intake/fixtures/`

`file.stubs.yaml` (the `file` input set: `from-file` and `handoff` reached, `ground` not) and `clerk.stubs.yaml` (blank `file`, the opening reply approved: `ground`, `clerk`, `talk`, `handoff` reached, `from-file` and `turn` not), under `docs/testing.md`. A route needing a second turn is not fixture-tested: a dry run ends a loop after one iteration. The conflict route is not fixture-tested: its deciding logic is `from-file`'s own bash, which a stub replaces.

### `.gitignore`

Adds `gauntlet/`. Intake commits nothing; a task file lives in the live checkout and the hand-off carries its absolute path.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| What a task file holds | `.archon/workflows/gauntlet/.shared/task-format.md` | Restating the sections or rules in a command, prompt or workflow; `ground` prints the file instead |
| Where Gauntlet writes | `gauntlet/`, tasks at `gauntlet/tasks/<slug>.md` | Any Gauntlet node writing outside `gauntlet/`; `$ARTIFACTS_DIR` or `$STATE_DIR` holding a task |
| Choosing the route | `intake.yaml`, `when:` on `$INPUTS.file` | Routing on the typed text; a second intake workflow |
| A handed-in file's slug and copy | `from-file` | Renaming, suffixing or overwriting a task |
| Raising a file-route conflict | `from-file` failing the run with the conflict on stderr; the owner corrects it and resumes | A conflict resolved, skipped or only logged; a wait asking for a new slug |
| The owner's approval of a Clerk task | the `answer` wait in `talk` | Any other approval before hand-off; an approval of a handed-in file |
| Clerk's memory | the `clerk` session, continued by `turn` | A fresh agent per turn; a conversation log file; `persist_session` |
| File confinement for a Gauntlet agent | `.archon/workflows/gauntlet/fence/files.py` | A second file server; a copy left under `.archon/workflows/feature-pipeline/`; a hook or prompt rule standing in for it |
| Clerk's file access | `clerk.mcp.json` (`FENCE_READ=.`, `FENCE_WRITE=gauntlet/tasks`), attached by `mcp:` on `clerk` and `turn`, both with `allowed_tools: []` | Any built-in tool on either node; `FENCE_*` set anywhere but `clerk.mcp.json`; a non-agent node writing the task file for Clerk |
| The hand-off to planning | `handoff` output `{ task }`, the workflow's `returns:` | Any other node or file telling planning where the task is, or how it was made |

## Order

1. Relocate the fence: `.archon/workflows/feature-pipeline/fence/` moved by `git mv` to `.archon/workflows/gauntlet/fence/` (`files.py`, `checks.py`, `files_helpers.py`, `test_files.py`, `test_files_write.py`, contents unchanged), the old folder gone with its `__pycache__`; `docs/testing.md` cites the new path. The moved suite passes as `docs/testing.md` runs it. Agent: `builder`.
2. Task format and Clerk's role: `.archon/workflows/gauntlet/.shared/task-format.md`, `.archon/workflows/gauntlet/intake/commands/clerk.md`. Agent: `role-author`.
3. Intake workflow: `.archon/workflows/gauntlet/intake/intake.yaml`, `.archon/workflows/gauntlet/intake/clerk.mcp.json`, `.archon/workflows/gauntlet/intake/fixtures/file.stubs.yaml`, `.archon/workflows/gauntlet/intake/fixtures/clerk.stubs.yaml`. Agent: `workflow-builder`.
4. Ignore Gauntlet's folder: `.gitignore`. Agent: `builder`.
