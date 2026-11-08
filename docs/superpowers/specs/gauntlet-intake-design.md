Status: proposed.

# Gauntlet intake round

## Why

Intake turns what the owner wants done into the item file: few issue-shaped items, each with fields the owner stated or confirmed, and hands its path to plan review. It runs on its own (`archon workflow run intake`) and is the first phase of `gauntlet-run`, the workflow for a whole run, which includes it as block `intake`; `gauntlet-design.md` gives the run, its `guard` node and how phases join. Two routes reach intake: the run's `file` input names an item file the owner wrote, or the owner states everything at once and settles the items with Clerk, the intake specialist. A run started from the Archon web UI ("What should Archon work on?") has a blank `file` and takes the Clerk route. Both routes end in the same hand-off, so plan review never knows which route an item file took. The design this implements is `2026-11-07-owner-control-design.md`, section 1.

Gauntlet is its own git repository, cloned by each user into `$ARCHON_HOME/workflows/gauntlet/` (by default `~/.archon/workflows/gauntlet/`), the pack root, which Archon scans for every repository on the host. Intake's script nodes run on Bun; the Python ones run on `uv`. Intake runs in any repository's checkout, on its own or inside `gauntlet-run`. Every path below is relative to the pack root unless it names `archon-workflows` (`~/dev/archon-workflows`) or the run's checkout.

What the trees already hold for the concerns intake touches:

- Intake of work: no live copy. The removed `feature` workflow read a request file by a `request` input; nothing of it remains but its fixtures under archon-workflows `.archon/workflows/feature-pipeline/feature/fixtures/`, which intake does not touch.
- Gauntlet-written state: no Gauntlet workflow writes anything yet. archon-workflows ignores `.gauntlet/` through `.git/info/exclude` for the owner's job chain; that pattern does not cover `gauntlet/`.
- The item file's format: no home yet. Its home is `intake/scripts/items.py` below.
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
// With committed, the rule is read from what the tree will hold, whatever the working copy's .gitignore files hold:
// it passes when .git/info/exclude or the global excludes file ignores gauntlet/ (a tree shares both), or when the
// .gitignore files as HEAD commits them (`git show HEAD:<file>`) do.
// Fails by writing one line to stderr and exiting 1, <root> being `git rev-parse --show-toplevel`:
//   gauntlet/ not ignored:
//     Gauntlet failed because its working folder, <root>/gauntlet/, sits in the main repo. Add it to .gitignore and restart the run.
//   a file under gauntlet/ that git tracks, <file> being the first such path:
//     Gauntlet failed because git tracks <root>/<file> under its working folder. Run `git rm --cached <file>` (and add gauntlet/ to .gitignore if it is not ignored), commit, and restart the run.
//   with committed, gauntlet/ ignored only by a .gitignore rule HEAD does not hold, <file> being that .gitignore:
//     Gauntlet failed because the rule keeping <root>/gauntlet/ out of git sits in <root>/<file>, which is not committed, and the run's tree holds only committed files. Commit <file> and restart the run.
export function requireIgnored(options?: { committed?: boolean }): void;
```

### `intake/scripts/items.py` (the item file: schema and checks)

The one statement of the item file and the one judge of it: its name, format, location and hand-off to plan review (D-83), and every mechanical check of intake. Standard library only; `intake/scripts/put` runs it and `intake/scripts/from-file.py` imports it. Clerk works to the schema `ground` prints from mode `schema`; the file route is checked against the same schema. Replaces nothing.

```markdown
Name, location: gauntlet/items/<slug>.md in the run's checkout; the slug is .shared/pin.py's slug (worktree cut design) of the
  file name. Items deferred by the owner: gauntlet/deferred/<slug>-later.md, the same format, taken later as `--input file=<path>`.
Hand-off to plan review: the absolute path of gauntlet/items/<slug>.md, block output `items`.
Format: one section per item, in order of Id; the first line of the file is "# <slug>".
  ## <Id>                     <- the Id field: "I" and a number, unique in the file; plan steps cite it
  ### Goal                    <- the core goal, in the owner's words or Clerk's reading the owner confirmed
  ### Current behavior        <- filled from the code; "does not exist" for a new feature
  ### Desired behavior        <- what it does once done
  ### Constraints             <- limits on how it may be done
  ### Out of scope            <- what the item does not ask for
  ### Notes                   <- anything else, per-item escalation rules included (plan review design)
Rules:
- The seven fields are all present, in that order. An empty field holds the word "none", never an empty string.
- A field Clerk writes is capped at CAP = 400 characters (about three sentences), so every confirmation is short enough to judge.
  The cap binds Clerk's fields only; a field the owner typed or an owner's file is not capped.
- Names no source file, function or line in Goal, Desired behavior or Constraints: how it is reached is the planner's.
```

```python
# Modes, INPUTS_MODE; stdout JSON; state in gauntlet/intake/<slug>.json (the draft, never read by plan review):
# schema   prints the text above; node `ground` shows it to Clerk.
# put      INPUTS_SLUG, INPUTS_PROPOSAL (Clerk's whole proposal, a JSON array of { id, points, goal, current, desired,
#          constraints, out_of_scope, notes }), INPUTS_POINTS (the turn that settles the statement only: the owner's points,
#          each a verbatim quote of the statement), INPUTS_STATEMENT (the run's $ARGUMENTS; when that is empty, the owner's
#          first reply is the statement, and INPUTS_REPLY carries it on that turn). Refuses, recording only the refusal, which
#          mode state reads, with the refusal for Clerk:
#          a point that does not occur in the statement; a point assigned to no item or to two items; a sentence of the
#          statement quoted by no point; a field over CAP; an empty field (write "none"); a Goal Clerk changes after the
#          owner typed it; a changed field of an approved item; a slug taken by another run's
#          item file or unlike this run's first. Else writes the draft state. stdout { slug, refusal, current }, current
#          the Id of the first item not yet approved ("" when all are).
# goal     INPUTS_GOAL, INPUTS_ID: records the owner's typed text, exactly as typed, as that item's Goal and marks it typed;
#          no agent writes it. A script reads the text from $LOOP_PREV.<wait>.output.text through `with:` (contracts A31).
# approve  INPUTS_ID: marks that one item approved. Never several items in one call.
# defer    INPUTS_IDS (the owner's text, ids named): moves those items to gauntlet/deferred/<slug>-later.md; refuses when none would
#          stay in this run or an id is unknown.
# finish   writes gauntlet/items/<slug>.md from the approved items when every item is approved; stdout { items }.
# check    INPUTS_FILE: the file route. Checks the owner's file against the format and rules above, the cap and the no-code rule excepted; stdout
#          { items }, the file's absolute path once it is in place at gauntlet/items/<slug>.md.
```

### `intake/commands/clerk.md`

Clerk's role: turn the owner's opening statement into the fewest items and settle their fields one item at a time, in one continuing conversation with the owner. Replaces nothing.

```markdown
Inputs in the session: the owner's opening statement ($ARGUMENTS, may be empty; then the owner's first reply is the statement), the item schema and the slugs already taken (from node `ground`).
The rule for how many items: one item per goal the owner would accept or reject on its own ("would you ever want one of these done without the other?" No: one item).
  Points sharing a goal, a root cause or the same code join into one item. An overarching goal stays one item however large.
  Split only when the owner answers yes to the test. Never split on your own; ask the test only where two points could plausibly stand alone.
Opening turn (node `clerk`): list the owner's points, each a verbatim quote of the statement; propose the fewest items, each with its Id, the points it absorbs and a draft of every field; pick a kebab-case slug not among the taken ones;
  reply to the owner in a few lines; output { slug, reply, points, items }.
Each later turn (node `turn`):
  - reads the owner's choice and words from the previous answer, and the latest refusal, when there is one;
  - merges or splits as the owner says, fills Current behavior from the code, and settles one item at a time; each item is approved on its own, never as a batch;
  - the owner states each Goal in their own words, or confirms your reading of it; a Goal the owner typed is recorded by a script and is not yours to write;
  - every field you write is plain and short (CAP in items.py), and holds "none" when it has nothing;
  - at the end asks how the run takes the items: everything in this run, or defer some;
  - output { slug, reply, points, items }, points "[]" except on the turn that settles the statement (the opening turn, or, when $ARGUMENTS is empty, the turn answering the owner's first reply).
Reads: anything in the checkout the work needs, code included, with no cap on reads or turns.
Never: writes any file (node `put` writes the draft), copies or deletes a file, names code in a field the schema keeps code out of, decides for the owner that an item is approved.
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

### `intake/scripts/`: `guard.ts`, `route.ts`, `items.py` and `from-file.py`

The scripts of intake's own nodes. `items.py` is the module above; its modes run as the nodes `ground`, `put-open`, `put`, `step`, `latest`, `show` and `finish`. Replace nothing.

```typescript
// guard.ts — node `guard`, the phase's own working-folder check: the two lines of gauntlet-tree/scripts/guard.ts
//   (requireIgnored from ../../.shared/working-folder.ts). In a run it repeats the run's guard, which has passed.

// route.ts — node `route`, the block's entry node: stdout { "file": process.env.INPUTS_FILE ?? "" }
```

```python
# items.py modes (the item file's module above), beyond put, goal, approve, defer, finish and check:
# ground   prints the item schema (mode schema), then the slugs taken in gauntlet/items/ and gauntlet/deferred/ of the checkout (none when absent).
# step     INPUTS_DECISION, INPUTS_TEXT: the owner's last answer, applied by the script and by no agent.
#          go: phase propose -> fields. approve: the current item approved (mode approve). goal: the text, exactly as typed
#          (no trim, no rewrite), becomes the current item's Goal (mode goal). all: phase defer -> done. defer: mode defer, then done.
#          An answer that does not fit the phase: stdout refusal, nothing changed.
# state    stdout { phase: "propose" | "fields" | "defer" | "done", current, refusal, options }: the draft state, the latest
#          refusal of put or step ("" when the last action took), and the options the phase offers (propose: go, reply;
#          fields: approve, goal, reply; defer: all, defer). The one channel a refusal reaches Clerk by.
# show     prints what the owner reads: propose: every item's Id and Goal with the points it absorbs; fields: the current item whole
#          and how many remain; defer: the approved items' Ids and Goals and the question "Do everything in this run, or defer some?".
```

### `intake/intake.yaml`

The intake block: both routes, the owner's approval item by item on the Clerk route, and the hand-off. It runs on its own and `gauntlet-run` includes it as node `intake`. Replaces nothing.

```yaml
name: intake
description: >-
  Gauntlet intake. Turns what the owner wants done into the item file, gauntlet/items/<slug>.md, a few issue-shaped items whose goals and fields the owner stated or confirmed, one item at a time, through a conversation with Clerk, the intake specialist; with the `file` input, checks an item file the owner wrote against the same format and copies it, as written, into gauntlet/items/, failing on any name conflict for the owner to correct and resume. Runs on its own for this phase; to take the work through every phase, start gauntlet-run.
provider: claude
model: claude-opus-5-5
effort: medium
worktree:
  enabled: false                                 # a standalone run needs it; Archon drops it under include: (P7)
inputs:
  file:
    default: ""
    description: Path of an item file the owner wrote. Blank sends the run's message to Clerk.
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

  # File route: the owner's file, checked against the item format, then at gauntlet/items/<slug>.md.
  - id: from-file
    depends_on: [route]
    when: "$route.output.file != ''"
    runtime: uv
    script: from-file                  # intake/scripts/from-file.py, importing slug from ../../.shared/pin.py and the checks of items.py (mode check)
    with: { file: $route.output.file }
    # <the real path of INPUTS_FILE (fails, naming the path, when it is missing); items.py mode check fails, naming the field and the item, on any departure from the format (the length cap and the no-code rule excepted); slug = .shared/pin.py's slug of it; the file already at gauntlet/items/<slug>.md: items is that path, nothing copied; else gauntlet/items/<slug>.md free: copy (cp -n), items is its absolute path; else gauntlet/items/<slug>.md holds the same bytes as the file (cmp): items is that path, nothing copied; else (target taken by different bytes, or empty slug) exit non-zero, the conflict and both paths on stderr; nothing renamed, suffixed or overwritten>
    output_format: { type: object, properties: { items: { type: string } }, required: [items] }

  # Clerk route.
  - id: ground
    depends_on: [route]
    when: "$route.output.file == ''"
    runtime: uv
    script: items                      # mode ground
    with: { mode: ground }

  - id: clerk                                    # opening turn; the session's source; writes no file
    depends_on: [ground]
    command: clerk
    allowed_tools: []                            # no built-in tool; files only through the read-only fence
    mcp: clerk.mcp.json                          # found beside this YAML
    output_format: { type: object, properties: { slug: { type: string, pattern: "^([a-z0-9]+(-[a-z0-9]+)*)?$" }, reply: { type: string }, points: { type: string }, items: { type: array } }, required: [slug, reply, points, items] }

  - id: put-open                                 # the opening proposal and points, checked and written as the draft state
    depends_on: [clerk]
    runtime: uv
    script: items
    with: { mode: put, slug: $clerk.output.slug, proposal: $clerk.output.items, points: $clerk.output.points, statement: $ARGUMENTS }

  - id: talk
    depends_on: [put-open]
    loop_group:
      max_iterations: 1                          # each answer permits one more turn; no cap on the conversation
      until_bash: |
        phase=$latest.output.phase
        [ "$phase" = "done" ]
      nodes:
        - id: step                               # the owner's go, approve, typed goal, all or defer, applied by the script
          when: "$LOOP_PREV.answer.output.decision != '' && $LOOP_PREV.answer.output.decision != 'reply'"
          runtime: uv
          script: items
          with: { mode: step, decision: $LOOP_PREV.answer.output.decision, text: $LOOP_PREV.answer.output.text }   # the typed text reaches the script raw (contracts A31)
        - id: turn                               # Clerk answers the owner's words; no turn after go, approve, goal, all or defer
          when: "$LOOP_PREV.answer.output.decision == 'reply'"
          context: { resume: clerk }             # one continuing session for the whole conversation
          allowed_tools: []
          mcp: clerk.mcp.json
          prompt: <the owner's words $LOOP_PREV.answer.output.text; the latest refusal $LOOP_PREV.latest.output.refusal>
          output_format: <as node clerk's>
        - id: put                                # the turn's proposal checked and written, or refused
          depends_on: [turn]
          runtime: uv
          script: items
          with: { mode: put, slug: $turn.output.slug, proposal: $turn.output.items, points: $turn.output.points, statement: $ARGUMENTS, reply: $LOOP_PREV.answer.output.text }
        - id: latest                             # always runs: the phase, the current item, the latest refusal and the options
          depends_on: [step, put]
          trigger_rule: all_done
          runtime: uv
          script: items                          # mode state
          with: { mode: state }
          output_format: { type: object, properties: { phase: { type: string }, current: { type: string }, refusal: { type: string }, options: { type: array } }, required: [phase, current, refusal, options] }
        - id: show
          depends_on: [latest]
          runtime: uv
          script: items                          # mode show: the reply of the turn that ran, else the opening reply, then the refusal when there is one, then the phase's text
          with: { mode: show, reply: { from: $turn.output.reply, if_skipped: "" }, opening: { from: $clerk.output.reply } }
        - id: answer
          depends_on: [show]
          when: "$latest.output.phase != 'done'"   # the owner's last answer is applied by the next iteration's step; no wait on a state with no options
          wait:
            form: select
            attention: "$show.output"
            options: "$latest.output.options"

  - id: finish                                   # the item file, written when every item is approved
    depends_on: [talk]
    runtime: uv
    script: items                      # mode finish
    with: { mode: finish }
    output_format: { type: object, properties: { items: { type: string } }, required: [items] }

  # Hand-off: the one result both routes produce.
  - id: handoff
    depends_on: [from-file, finish]
    trigger_rule: none_failed_min_one_success
    runtime: bun
    script: <items = the file route's items || finish's items; print { items }>
    with:
      file: { from: $from-file.output.items, if_skipped: "" }
      finished: { from: $finish.output.items, if_skipped: "" }
    output_format: { type: object, properties: { items: { type: string } }, required: [items] }
```

Intake runs on its own or as block `intake` of `gauntlet-run`, in the checkout. Run on its own, its `guard` is the working-folder check; included, `gauntlet-run`'s `guard` has already passed and the phase's repeats a passing git query. Routing reads only `route`'s output, the `file` input (`gauntlet-run` passes it in by `with:`), never the typed text. With `file` blank, `$ARGUMENTS` (the run's message: the text typed in the web UI, or the CLI message) is the owner's opening statement, and may be empty; then the owner's first reply becomes the statement. The `talk` group's session is Clerk's, forked once from `clerk` and continued across every pause; no turn starts a fresh agent and no conversation log is kept. Clerk writes no file: it outputs the slug, the points and the whole proposal, and `items.py` is the only writer of the draft state and of `gauntlet/items/<slug>.md`. A turn runs only when the owner replies in words; the owner's `go`, `approve`, typed goal, `all` and `defer` are applied by `step` and cost no agent turn. The owner approves each item on its own (`approve` marks one item), never the set as a batch, and Clerk cannot write a Goal the owner typed. Intake closes with the question "do everything in this run, or defer some", and deferred items go to `gauntlet/deferred/<slug>-later.md`. A slug already taken by an item file this run did not write is refused, and so is a slug unlike the one of the run's first proposal, so a run owns one item file. `latest` always runs and prints the refusal of the latest `put` or `step`; Clerk's next turn and `show` read it, so a refusal reaches Clerk and `show` never prints a stale one. A file-route conflict or a departure from the format fails the run at `from-file`; the owner corrects it on disk and resumes the run with `archon workflow resume <run id>`, which re-runs `from-file`.

### `intake/fixtures/`

`file.stubs.yaml` (`route` stubbed with a `file`: `guard`, `route`, `from-file` and `handoff` reached, `ground` not) and `clerk.stubs.yaml` (`route` stubbed with a blank `file`, the opening proposal settled: `guard`, `route`, `ground`, `clerk`, `put-open`, `talk` with its `latest`, `finish`, `handoff` reached, `from-file` and `turn` not), under `docs/testing.md`. A route needing a second turn is not fixture-tested: a dry run ends a loop after one iteration. The conflict route and the format check are not fixture-tested: their deciding logic is the scripts' own, which stubs replace; `intake/tests/test_items.py` pins the checks (the cap, the "none" rule, the point assignment, the typed goal recorded as typed, per-item approval, the defer move) as `docs/testing.md` states.

### The run's checkout

The owner keeps `gauntlet/` out of git in each repository Gauntlet runs in, by a `gauntlet/` line in its `.gitignore`, committed, or in `.git/info/exclude`; `gauntlet-run`'s `guard` refuses a `.gitignore` line that is not committed. No Gauntlet node writes that line. Intake commits nothing; the item file lives in the live checkout and the hand-off carries its absolute path.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| Gauntlet's files | the Gauntlet repository at `$ARCHON_HOME/workflows/gauntlet/` | Any Gauntlet file, fence or design in archon-workflows or in a run's checkout |
| Reaching a pack file from a run in any repository | `mcp:` named beside the workflow YAML; `.shared/` imported relative to the script's own file; the fence server under `${ARCHON_HOME:-$HOME/.archon}/workflows/gauntlet/` in `clerk.mcp.json` | A checkout-relative path to any pack file; a path naming one user's home |
| What an item file holds, its name, location and hand-off | `intake/scripts/items.py` (the item file module above): `gauntlet/items/<slug>.md`, deferred items in `gauntlet/deferred/<slug>-later.md`, the hand-off `items` | Restating the fields or rules in a command, prompt or workflow; `ground` prints the schema instead; another design restating the format |
| Where intake writes | `gauntlet/` in the run's checkout, items at `gauntlet/items/<slug>.md`, the draft state at `gauntlet/intake/<slug>.json`; `$ARTIFACTS_DIR` holds only the `owned.<slug>` marker of the first `put` | Any intake node writing outside `gauntlet/` and `$ARTIFACTS_DIR`; `$ARTIFACTS_DIR` or `$STATE_DIR` holding an item; plan review reading `gauntlet/intake/` |
| Keeping `gauntlet/` out of git | the owner's `.gitignore` line in each repository; `requireIgnored` in `.shared/working-folder.ts`, called with option `committed` by node `guard` of `gauntlet-run` before any phase, and without it by node `guard` of `intake` | A node writing the ignore line; a write under `gauntlet/` before the guard passes; a second statement of the check or its messages; a check that accepts only `.gitignore`; option `committed` passed by any guard but `gauntlet-run`'s |
| Choosing the route | `intake.yaml`, `when:` on `$route.output.file` | Routing on the typed text; `$INPUTS` in a `when:`; a second intake workflow |
| A handed-in file's check, slug and copy | `from-file`, its slug from `.shared/pin.py`'s `slug` (worktree cut design), its checks `items.py` mode `check` | Renaming, suffixing or overwriting an item file; a file passed unchecked |
| Raising a file-route conflict | `from-file` failing the run with the conflict on stderr; the owner corrects it and resumes | A conflict resolved, skipped or only logged; a wait asking for a new slug |
| The owner's approval of the items | the `answer` wait in `talk`, one item per approval, applied by node `step` | Any other approval before hand-off; an approval of a handed-in file; several items approved in one answer |
| Clerk's memory | the `clerk` session, continued by `turn` | A fresh agent per turn; a conversation log file; `persist_session` |
| File confinement for a Gauntlet agent | `fence/files.py` | A second file server; a copy left in archon-workflows `.archon/workflows/feature-pipeline/`; a hook or prompt rule standing in for it |
| Clerk's file access | `clerk.mcp.json` (`FENCE_READ=.`, no `FENCE_WRITE`), attached by `mcp:` on `clerk` and `turn`, both with `allowed_tools: []` | Any built-in tool on either node; `FENCE_*` set anywhere but `clerk.mcp.json`; Clerk writing, copying or deleting any file |
| Writing the draft and the item file | `items.py`, through nodes `put-open`, `put`, `step` and `finish`, the only writer of `gauntlet/intake/<slug>.json` and `gauntlet/items/<slug>.md` on the Clerk route; it refuses a slug taken by a file this run did not write, and a slug unlike the one of its first write | any other writer of a draft; a slug overwritten across runs; a second item file in one run; Clerk writing a Goal the owner typed |
| The owner's typed goal | `items.py` mode `step`, the text read from `$LOOP_PREV.answer.output.text` through `with:` (contracts A31) | Clerk or any agent writing, trimming or rewording it |
| The hand-off to plan review | `handoff` output `{ items }`, the block's `returns:`, read by `gauntlet-run` as `$intake.output.items` | Any other node or file telling plan review where the item file is, or how it was made |

## Order

1. Clear the moved copies out of archon-workflows: `.archon/workflows/feature-pipeline/fence/` removed with its `__pycache__`, `docs/superpowers/specs/gauntlet-intake-design.md` removed, and `docs/testing.md` there citing no removed path. Agent: `builder`.
2. The item module and Clerk's role: `intake/scripts/items.py`, `intake/tests/test_items.py`, `intake/commands/clerk.md`. Agent: `builder` for the module, `role-author` for the role.
3. Working-folder guard and intake block: `.shared/working-folder.ts`, `intake/scripts/guard.ts`, `intake/scripts/route.ts`, `intake/scripts/from-file.py`, `intake/intake.yaml`, `intake/clerk.mcp.json`, `intake/fixtures/file.stubs.yaml`, `intake/fixtures/clerk.stubs.yaml`. Needs step 2 and the worktree cut design's `.shared/pin.py` (its step 1). `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
