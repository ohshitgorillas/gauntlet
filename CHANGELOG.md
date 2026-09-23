# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versioning: [SemVer](https://semver.org/), 0.x during pre-release.

## [Unreleased]

### Changed
- **A plan has a seventh section, `## Rules touched`.** It lists each rule in force on the changed surface as `kept` or `overturned`, and the `prosecutor`'s check (e) reads it. `docs/plans.md` also requires a relation's reading at its edges, which check (f) reads, and states that neither is escape prose that check (l) deletes. It also states what each `prosecutor` brief carries.
- **A plan header reading `grounding:` is read as `discovery:`.** An approved plan written under the header's former name no longer reads as a missing line.

### Fixed
- **A spec block's `brief:` copies the approved plan's `brief:` verbatim.** The `arbiter` cannot read the approved plan, so a `brief:` holding a path, pointer or summary left its brief-fulfilment check (m) nothing to check. Check (m) now answers such a `brief:` with a block-level `ANOTHER PASS`, and `docs/approved-specs.md` and `docs/agents.md` state the copy.
- **An `examiner` measurement can be rerun.** A throwaway script runs from a stdin heredoc and its full text is the returned command, where it used to be deleted in the same command. The `arbiter`'s check (k) treats a `bite:` whose command is prose, or names a script absent from the checkout, as unfilled.
- **The blind agent definitions carry no placeholder the plugin cannot fill.** `<source dir>` and the external-docs placeholder are gone from the `arbiter`, `auditor`, `bailiff` and `scrivener`, whose read lists now match `no-impl-reads.py`, and the `arbiter` no longer cites a section of the chain that does not exist.
- **A blind agent may read the whole prose directory.** `no-impl-reads.py` allows `docs/` entire, not one policy file in it, so the `arbiter` and `scrivener` reach the protocol and vendor docs their definitions cite, and a Grep rooted at `docs/` is no longer suggested and then denied. `state/` and the gauntlet base outside its three leaves stay denied. The hook's docstring and denial message match the code.
- **`cite.py` counts only the files git shows when it resolves a basename.** An ignored tool cache carrying its own `.gitignore`, such as `.mypy_cache/`, no longer makes a `.gitignore:<N>` citation `AMBIGUOUS`.
- **`red` commits what it runs, and the brief names that commit.** `pair.sh red` commits the spec tree's lane directory before the run, keeping HEAD where nothing is staged, and the saved log opens with `red commit: <sha>`. The bailiff's brief reads its `red commit:` from that line, or says `unknown`, rather than naming the spec branch tip, which is the combine by then.
- **A refused land prints no brief and names what blocks it.** `pair.sh merge` prints the bailiff's brief only once the target branch has fast-forwarded, and a refused fast-forward quotes git's own lines, the blocking files among them.

## [0.9.0] - 2026-09-23

### Added
- **A blind agent's tools line carries no shell and no `pair` tool.** `scripts/gates/blind-no-shell.py` holds every agent in the `BLIND` tuple to that, and the gate run fails where one does.
- **No hook reads a `Bash` call's command.** `scripts/gates/no-command-reads.py` fails the gate run where any hook or server inspects the command text, or where a wired `Bash` hook answers two command texts differently for one caller.
- **The shipped-kit gates cover the MCP servers.** An untracked or uncompilable server, one that answers no self-check, or one whose `tools/list` omits a tool an agent definition grants fails the gate run. `kit-probe.py` names a missing server dependency at SessionStart.

### Changed
- **The `arbiter` holds no shell.** Its `tools:` line is `Read, Grep, Glob, Write`, so every blind agent reaches the tree through its typed tools alone.
- **`GAUNTLET=off` names every hook it silences.** `lanes.py`, `no-impl-reads.py`, `bwrap-wrap.py`, `blind-write.py`, `lane-audit.py`, `kit-probe.py` and the `Stop` gate, from one constant in `gauntlet-off.py`, in `README.md` and in `docs/agents.md`.

### Fixed
- **The sandbox root is the checkout the cwd sits in.** A wrapped shell binds the main checkout writable and every lane inside it read-only whatever directory the session stands in, a worktree included, and starts in the cwd. A cwd in no checkout is denied.
- **A failing MCP call answers with an error and the server stays up.** Every handler failure, unreadable line or runner that cannot start comes back as an error reply, and the next call is answered.
- **`pair` and `blind` tool output is byte-faithful.** `\r\n` and a non-UTF-8 byte reach the caller as they were, and `CLAUDE_PROJECT_DIR` is forwarded only where the host set it.
- **The `pair` server admits every slug `pair.sh` admits.** `review` refuses the slug `plan`, and `blind`'s node report keeps two entries sharing a name as two lines.

## [0.8.0] - 2026-09-23

### Added
- **A kit missing an MCP server announces it at SessionStart.** `kit-probe.py` reads the manifest's `mcpServers` beside its `hooks` and names every server whose script under `${CLAUDE_PLUGIN_ROOT}` the installed kit does not hold, with the path the manifest gives, so a tool the host dropped is visible in the session. A malformed server entry is named by its key. A whole kit says nothing.

## [0.7.0] - 2026-09-22

### Added
- **The blind agents reach `scripts/blind.sh` through the `blind` MCP server.** `scripts/mcp/blind_server.py` serves three tools, one per `blind.sh` verb, checks each argument against its type and runs the script as an argv list with no shell between them. A run returns one `PASSED`, `FAILED` or `ERROR` line per id, a parametrized id cut to its bracket index and a node name to its run position. No source line, exception message or lint output reaches the caller. The `scrivener` and the `bailiff` admit `mcp__plugin_gauntlet_blind__*`.
- **The `scrivener` formats the file it writes through the `blind-write` MCP server.** `scripts/mcp/blind_write_server.py` serves one tool, `format`, which runs `blind.sh format` over one path and returns `clean` or `not clean`, never the fix tools' output. `hooks/blind-write.py`, wired at `PreToolUse` on `mcp__plugin_gauntlet_blind-write__.*`, denies every caller but the `scrivener`, the main agent included.
- **The main agent runs `scripts/pair.sh` through the `pair` MCP server.** `scripts/mcp/pair_server.py` serves one tool per verb — `open`, `respec`, `red`, `check`, `merge`, `abort`, `close`, `list`, `review`, `review_plan`, `restore`, `impl_checkout` and `impl_merge` — checks a slug and a rev before anything runs, and returns the script's exit, stdout and stderr verbatim. The agent definitions and `docs/agents.md` name `mcp__plugin_gauntlet_pair__<verb>` wherever they named a `pair.sh` command.

### Changed
- **Every `Bash` call runs inside `bwrap`, with no carve-out.** `bwrap-wrap.py` carries the command into the wrap byte for byte and reads nothing in it, so `pair.sh` and a project-declared command are wrapped like any other. No hook decides a `Bash` call by its text.
- **The `scrivener` and the `bailiff` hold no `Bash`.** A blind agent's shell would need a reading of its command to hold, so each reaches `blind.sh` through the `blind` tools instead.

### Removed
- **`hooks/blind-bash.py` and `hooks/pair-passthrough.py`.** The one-command lock on the blind agents' shell and the two carve-outs from the wrap are gone with the shell they judged.
- **`gauntlet-off.py --bash`.** A `GAUNTLET=` assignment or a nested `claude` invocation inside a session is no longer denied by a hook; the rule that an agent may not throw the switch holds without one. `GAUNTLET=off claude` silences `lanes.py`, `no-impl-reads.py` and the `Stop` gate.
- **The `unwrapped_commands` key of `.claude/blind-reads.json`.** No command leaves the sandbox, so the file carries eight keys and `shell_shapes.py --config` answers no ninth. A project that set it has its declared commands wrapped like any other.

## [0.6.0] - 2026-09-21

### Added
- **A kit missing a wired hook announces it at SessionStart.** `kit-probe.py` reads the manifest and names every wired hook file the installed kit does not hold, so a lane nothing is enforcing is visible in the session. A whole kit says nothing.

### Fixed
- **A wrapped shell's `/tmp` is one scratch directory per checkout, shared by every wrap of it.** A nested wrap resolves the same directory at the same path, so a tree one wrapped command builds there is still there for the wrapped command that runs against it.
- **A wrapped `Bash` call works in a checkout of any size.** Every lane is bound whole, one mount rather than one per file inside it, so the mount table is the same size in every checkout and stays well inside the kernel's limit on a single argument.

## [0.5.0] - 2026-09-21

### Added
- **A plan carries the changes the brief asked for and no others.** `prosecutor` cuts an owner-visible delta — a config key, flag, hook entry, tracked artifact, changed default or gate token — that no brief sentence reaches, and the cut has a line under **What it costs**. An element the main agent says the briefed change cannot work without reaches the owner as `ESCALATE: LEAVE`, quoted with its cost and why it is not its own slug.
- **The `Stop` gate names a file the runner collects that no commit carries.** The mount table cannot stop a shell from creating one, so the turn is held open until that file goes through the chain or off disk. A path under a dot-prefixed directory is scratch and is never named.

### Changed
- **Every reviewer refuses in the same two tokens.** `CONTEMPT: LEADING` for a brief that leads the reviewer, `OBJECTION: EVASION` for a return that evades its findings, from `prosecutor`, `arbiter` and `bailiff` alike.

### Fixed
- **A wrapped shell writes scratch inside the lane its runner owns.** The files a runner collects stay read-only in every wrapped profile; the directory around them does not, so a run that has to build a tree inside the checkout no longer takes `EROFS` on its first `mkdir`.

## [0.4.2] - 2026-09-21

### Fixed
- **A wrapped shell writes `scripts/`, `hooks/` and `agents/` again.** `bwrap-wrap.py` bound those three bare directory names read-only in whatever checkout it wrapped, so a consumer project whose own source sits under one of them got `EROFS` from every wrapped shell, and `pre-commit`'s `git checkout -- .` could not restore the worktree, failing any commit that touched it. The lane directories, `<gauntlet dir>/red`, `<gauntlet dir>/merge`, `.claude/`, `.git/hooks` and `.git/config` stay read-only in every wrapped shell.

## [0.4.1] - 2026-09-20

### Changed
- **A `prosecutor` round and an `arbiter` block reach the owner shorter.** A passing check is one clause. Check (b) names the citations that did not resolve and gives the rest as a count, `resolved: <N>`, on the check's own line. An `ADMITTED` line is the token alone: its input, outcome, `kills:` and `bite:` sit in the approved block the same reviewer lands.

## [0.4.0] - 2026-09-20

### Added
- **`scripts/blind.sh format <path>` is the blind shell's fourth subcommand, and the first that writes.** It runs `ruff check --fix` then `black` over the one path it is given, `eslint --fix` for a JS file, inside the sandbox with the caller's own lane bound writable, and exits with whatever the fix tools still find. `blind-bash.py` admits it for the `scrivener` alone, whose lane it writes into, and denies it every other caller.
- **`scripts/pair.sh check <slug>` gates a pair without landing it, and `merge` lands only what a check passed.** `check` converges the pair and runs the gate, writing a numbered `<gauntlet dir>/merge/<slug>.<N>.txt` that opens with the tips of `spec/<slug>`, `impl/<slug>` and the target branch and a `gate:` line, and prints `CHECK <path> PASS` or `FAIL`. `merge` reads the newest reading and prints `UNCHECKED <slug>` where it is absent, red or stale.
- **A `kind:` block carries `collateral:` rows for what a change breaks and no behavior line pins.** Each row names a target in the blind writer's lane as `<file>::<name>`, the `breaks:` fact outside that lane that forced the repair, and the `assertion:` that survives byte-identical. The `arbiter` rules on them with check (u), the `scrivener` admits a delta naming a row's target, `scripts/strike-diff.py --collateral` prints `OK`, `ALTERED` or `MISSING` per row at `scripts/pair.sh merge`, and the `bailiff` returns `HELD` or `ALTERED` per row after it.
- **`scripts/pair.sh respec` prints `RESPEC COLLATERAL` for a re-approved block that differs in `collateral:` rows alone.** The comparison is by section and not by how many lines differ, so a behavior line that changed in the same round prints `RESPEC` and owes the owner's word; a block it cannot part into its structure line, `brief:` and behavior lines prints `RESPEC` too.
- **An `auditor` agent sweeps the suite against the policy file.** Blind: `Read`, `Grep`, `Glob`, and a row in the `BLIND` tuple of `no-impl-reads.py` denies it the source. It resolves the owner's scope wording to a target list, prints the list, then returns one row per target — `VALID` by default, `STRIKE` or `AMEND` with a rule number and a quoted assertion, `NOTE` for a fact it cannot read.

### Fixed
- **`scripts/blind.sh` runs a file in the tree its path names.** `.claude/worktrees/<slug>-spec/<lane>/<file>` is that worktree and a bare `<lane>/<file>` is the caller's own tree, from any working directory; the runner and `.venv/` come from the main checkout either way. The `scrivener` definition names the worktree form, since its shell stands in the main checkout.
- **`ruff` caches under the sandbox's private `/tmp`.** A spec worktree is read-only inside the sandbox and carries no `.ruff_cache`, so the gate passes there.
- **An `arbiter` round reaches `<gauntlet dir>/reviews/` on disk.** The definition names the `Write` tool for the round file and the approved block; a shell redirect from a reviewer lands nowhere.

## [0.3.0] - 2026-09-19

### Added
- **`scripts/cite.py --check-all` resolves several documents in one run.** Each row is prefixed with its document, and with no document named it reads every tracked `*.md` from `git ls-files`. A citation whose path begins with `${CLAUDE_PLUGIN_ROOT}/` resolves against the kit's own checkout rather than the document's.
- **A project declares extra writable paths under `extra_binds`.** A ninth key in `.claude/blind-reads.json`, a list of absolute paths, empty by default: each live entry is bound writable inside the author's wrapped profile, so a package cache or scratch tree outside the checkout is reachable. The key adds write access only, to the author's profile. An entry over a protected mount, the checkout or a worktree is dropped; a malformed list voids the key.

### Fixed
- **`scripts/pair.sh merge` lands a pair whose implementation branch is already combined into its spec branch.** The combine is skipped and the gate runs.

## [0.2.3] - 2026-09-19

### Fixed
- **Every `scripts/pair.sh` verb runs outside the sandbox.** The carve-out admits the script followed by bare tokens, whatever the verb, rather than `open`, `red` and `merge` by name. A `restore` revision is one such token, so `HEAD~1` and `HEAD^` are not admitted; name a commit, branch or tag.

## [0.2.2] - 2026-09-19

### Fixed
- **`scripts/cite.py --check` resolves against the document's own checkout.** The root was taken from the script's own path, so a plan in a project that installs the kit as a plugin had every repo-relative citation resolved against the plugin checkout and reported `MISSING`. The root is now the nearest ancestor of the document carrying `.git`, a worktree's file included; a document under no checkout falls back to the script's own.
- **`scripts/pair.sh` reaches the kit's own copy.** The passthrough admitted one spelling of the head, the bare `scripts/pair.sh`, and ran it as typed; a project holding no local copy of the script therefore had no spelling that both escaped the sandbox and resolved on disk, so `open`, `red` and `merge` all failed under a read-only `.claude/worktrees`. The bare head now resolves to the plugin's own entry, and the absolute and `${CLAUDE_PLUGIN_ROOT}` spellings are admitted beside it, as they already were for `scripts/blind.sh`.

## [0.2.1] - 2026-09-16

### Changed
- **A shell on the default profile cannot write `<tests dir>`.** It is bound read-only there now, with the other four lanes. A command that regenerates a file under it — a snapshot update, a fixture a test writes — fails with `EROFS` where it used to pass; run it outside the session, or through the writer. The blind agents are unaffected: they run under `scripts/blind.sh`, which builds its own sandbox with their lane writable.

## [0.2.0] - 2026-09-16

### Added
- **A third tests-only motion, `motion: rehome`.** For a test whose assertion stands and whose file, or whose body around that assertion, has to move. Its fields are `strike <tests dir>/<file>::<test>`, `moved:`, `assertion:` quoting the assertion verbatim, and `as:` naming where it lands, which may name the target itself. No red run and no reviewer round. `scripts/strike-diff.py` checks the landing at merge and reports `OK`, `ALTERED` or `UNSATISFIED`.
- **`juror`, a blind agent spawned once per red run.** Returns `RED`, `ERROR`, `GREEN` or `INVALID` per behavior line.
- **`bailiff`, a blind agent spawned once per merged block.** Returns `PIN`, `SOFT`, `MISSING` or `EXTRA` per behavior line, plus a row per test-policy violation.
- **The verdicts lane and its `Stop` gate.** Only the `juror` writes `<gauntlet dir>/verdicts/<slug>.txt`, and a turn ending with an uncertified or stale red run is blocked. A project that never runs `scripts/pair.sh red` never sees the gate.
- **`hooks/blind-bash.py` and `scripts/blind.sh`.** A blind agent's shell is one command: `blind.sh test <path>`, `blind.sh status <slug>`, `blind.sh show <commit> <slug>`, each under `bwrap` with the filesystem read-only apart from the agent's own lane. Gated on the caller, so the two agents in its `BLIND` tuple hold to that one command and every other caller passes unjudged. Needs `bwrap` on the host.
- **`hooks/bwrap-wrap.py`, which runs every `Bash` call inside `bwrap`.** The command is carried on stdin through a here-document, and `agent_type` picks one of three profiles: passthrough for the two blind agents, reviewer with a read-only filesystem and a tmpfs over the reviewers' lane, and default, which keeps the repository, `~/.cache` and `/tmp` writable and the lanes, `.claude/`, `hooks/`, `agents/`, `scripts/` and the git configuration read-only. Fails closed without `bwrap`.
- **`hooks/pair-passthrough.py`, the two carve-outs from that wrap.** `scripts/pair.sh` runs unwrapped, and so does any command the project itself declares.
- **`unwrapped_commands`, the project's word on which commands leave the sandbox.** It maps exact command text to the paths that command reads, and is empty by default. A command escapes only where the declaration carries its whole text as typed, so nothing rides out appended to it. Every `reads` path binds read-only inside every wrapped profile; one that resolves to nothing voids its declaration and the command is wrapped like any other.
- **`hooks/gauntlet-off.py` and the `GAUNTLET` switch.** `GAUNTLET=off claude` runs one session with the lane hooks, `no-impl-reads.py`, `blind-bash.py` and the `Stop` gate silent, read from `os.environ` and never from a payload. A `GAUNTLET=` assignment or a nested `claude` invocation is denied inside such a session. With the gauntlet off, the standing notice speaks on the first turn and every tenth after, counted per session under the system temporary directory.
- **Three flat keys in `.claude/blind-reads.json` name every directory the kit uses.** `tests_dir` is the blind writer's lane and what `<tests dir>` means in the prose, `gauntlet_dir` is the base the four artifact lanes sit under, and `docs_dir` is the prose a blind agent may read. Each key defaults to the name the kit ships. One reader answers them, `shell_shapes.py --config <key>`, along with the four derived lanes `specs_lane`, `plans_lane`, `reviews_lane` and `verdicts_lane`.
- **The three directory names must be usable and pairwise disjoint.** Repo-relative and normalized, none the root, absolute or walking out, and none equal to, under, or over another. A set that fails moves nothing: every key falls back to its default together, rather than half a layout being applied.
- **`scripts/pair.sh restore <slug> <rev>`**, printing `RESTORED <path> <rev>`.
- **`scripts/pair.sh impl checkout <slug>` and `impl merge <slug>`**, printing `IMPL .claude/worktrees/<slug>-impl` and `MERGED <slug> <commit>`.
- **`scripts/pair.sh close <slug>`, which removes a pair's worktrees and keeps its commits.** The branches and the recorded base stay, so what a pair committed is still there to merge or read. One line per tree: `CLOSED <path>`, or `REFUSED <path> uncommitted` for a tree holding work no commit holds, which is left standing. It exits 1 where any tree was refused. `abort` remains the verb that throws a pair away.
- **`scripts/pair.sh review <slug>` and `review plan <slug>`**, printing the one path the next round is written to, with `<N>` one more than the highest on disk.
- **`scripts/pair.sh respec <slug>`, `abort <slug>` and `list`**, printing `RESPEC <gauntlet dir>/specs/approved/<slug>.txt <commit>`, `ABORTED <slug>`, and one `PAIR <slug> <base> <n>` line per open pair or `NO PAIRS`. `respec` refuses a block whose reviewer section is the round the spec branch already committed, so a re-approved block carries a new round rather than the last `READY` pasted under changed lines.
- **`target_branch` and `gate_command` in `.claude/blind-reads.json`.** The branch a finished pair lands on and the command that has to pass before it does, `main` and `make check` by default. Being scalars they collide with no lane and with each other, so each falls back on its own and a directory set that moves nothing leaves both standing.
- **`pytest_command` and `node_command` in `.claude/blind-reads.json`.** The invocations `scripts/blind.sh test` and `scripts/pair.sh red` run, `.venv/bin/pytest` and `node --test` by default, so a project that deselects a marker or imports a loader names the whole invocation there rather than editing the two scripts. The test path and each script's own flags follow the configured words, and a configured word carrying a slash reads as a path in the checkout.
- **`scripts/init.py`, the one deliberate step of an install.** It writes `<project>/.claude/blind-reads.json` with all eight keys at the kit's defaults, read out of `shell_shapes.py` rather than retyped, and creates the skeleton under `gauntlet_dir`, each directory carrying a `.gitkeep` so a clone keeps the lane. An existing declaration stands and the exit status says so; `--force` overwrites, `--print` prints the file, `--project DIR` names the checkout. Hook wiring is the manifest's business.
- **`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, which make the kit installable rather than copyable.** `/plugin marketplace add ohshitgorillas/gauntlet` and `/plugin install gauntlet@gauntlet` put `hooks/`, `agents/` and `scripts/` in front of a project without putting a file in it. `agents/` is found by convention; `plugin.json` carries every hook invocation inline, each naming `${CLAUDE_PLUGIN_ROOT}/hooks/`, which is the plugin's own root rather than the project's.
- **`scripts/cite.py`.** `--check` resolves every backticked `path:line` against the tree and exits 1 on one that does not; `--fix` fills a number from its quoted anchor.
- **"The approval word" in `README.md`.** Plan, spec block and start of implementation each wait for a message whose first line is exactly `approved`, or `approved with revision` with the amendments below it. No hook enforces it.
- **`docs/workflow.mermaid`, a diagram of the chain.** The plan gate from brief through discovery, citation check and the `prosecutor`'s rounds to the approved plan; the spec gate from the drafted block and the `examiner`'s measurement through the `arbiter`'s rounds to the approved block; the blind write, the red run and the `juror`'s verdict; the implementation phase and its two routes out of a failing test; and the six-step merge, with the owner's three approval words on it.

**Breaking for existing installs:** install the plugin instead of copying `.claude/`, and delete the kit's hook entries from `.claude/settings.json` in the same step. A project that installs the plugin while its `settings.json` still declares the same hooks wires every lane twice: each lane judges each call a second time, and a denied call is denied twice. Then run `python3 scripts/init.py` and re-run the `--self-test` commands.

### Changed
- **The five lane hooks are one table-driven hook, `hooks/lanes.py`.** Each lane is a row carrying its directory, the agents whose write into it passes, and the refusal every other hand gets; the three exceptions the old files held as branches are fields on the row. The `Stop` gate moves with the verdicts row and is `lanes.py --stop`. A consumer gets one `PreToolUse` entry on `Write|Edit|NotebookEdit|Read|Grep`, and one gate, `python3 hooks/lanes.py --self-test`.
- **A lane owns the write tools, and the sandbox holds the shell.** No lane hook is wired on `Bash` or reads command text. What keeps a shell out of a lane is the mount table `bwrap-wrap.py` builds, which binds every lane directory read-only inside every wrapped profile, so a `rm`, a redirection or an inline script aimed at a lane fails in the kernel rather than being read for a path. The `Bash` matcher wires `gauntlet-off.py --bash` and `bwrap-wrap.py`.
- **`no-impl-reads.py` judges `Read`, `Grep` and `Glob`, over a narrower allowlist.** A blind agent reads `docs/testing.md` as one file, its own test lane, the approved spec block, the red run, the merge evidence, `.claude/blind-reads.json`, documentation at the repo root, and the installed kit's own `docs/`. `state/` comes off, since gate output is the implementation's own tracebacks under another name, and so does the rest of `docs/`, where a design note quotes the code it describes.
- **`scripts/pair.sh merge` writes its evidence to `<gauntlet dir>/merge/<slug>.txt`** rather than to stdout. An absent or empty file is a `NO EVIDENCE` verdict.
- **`scripts/pair.sh merge` lands a pair whose approved block is untracked in the primary checkout.** The block reaches the lane as the reviewer's file, `open` commits it on the spec branch, and git refuses to fast-forward over a working tree file even where the landing blob is identical. Every identical untracked file gives way first, named on stderr. One whose content differs is the owner's work: the land refuses and restores each copy it moved aside.
- **The seven agents drop the `gauntlet-` prefix.** They are `prosecutor`, `detective`, `arbiter`, `examiner`, `scrivener`, `juror` and `bailiff`, each in `agents/<name>.md`; installed as a plugin the harness spells them `gauntlet:prosecutor`. Anything spawning one by its old name has to be retyped. One consequence is deliberate: a host project agent named `arbiter`, `juror` or `scrivener` is held to the kit's lane and blindness rules, as a foreign plugin's same-named agent already was.
- **`bwrap-wrap.py` wraps every caller, with no roster and no exempt agent.** `agent_type` picks a profile and never admits a caller, and an absent one is the main agent taking the default profile. So `sudo` stops working in a shell — `bwrap` sets `NO_NEW_PRIVS`, and every script calling `sudo` internally dies with it — and no sudoers file changes. A project needing a privileged command declares its exact text under `unwrapped_commands`; a project that declares nothing has no privileged shell.
- **The `prosecutor` runs a check (l), restatement.** A plan sentence adding no fact beyond its citation or beyond an earlier section is a `FAIL`, and the repair is deletion. `docs/plans.md` carries the three rules it holds: a citation stands for its content, so a plan quotes at most the decisive fragment of a cited line; each `brief:` sentence takes one line, `delivered:` naming the element or `dropped:` naming why; escape prose is owed after a `FAIL`.
- **A plan body takes the compressed register the agent definitions use.** Each fact lands in exactly one section, cited rather than restated where another section needs it, and `docs/plans.md` carries both rules beneath the section list. Plans were full English by default and repeated a design's rationale under its price, which cost the `prosecutor`, the implementation stage and the owner the same words three times over.
- **The kit's hook wiring is the plugin manifest's.** Every invocation moved verbatim — same events, same matchers, same order — with `${CLAUDE_PROJECT_DIR}/hooks/` becoming `${CLAUDE_PLUGIN_ROOT}/hooks/`, because an installed plugin sits outside the checkout it judges. `.claude/settings.json` is a consumer's own file and the kit stops writing to it.
- **`.claude/blind-reads.json` is the project's declaration, and it is required.** It lives beside the project's own settings rather than beside `shell_shapes.py`, and `{}` asks for the defaults and gets them. Absent, unreadable, not JSON and not a JSON object are four faults, each reaching the operator by the path: a denial out of every hook, a non-zero exit out of `shell_shapes.py --config`, a refusal out of `scripts/pair.sh`. The fault is held rather than raised at import.
- **`scripts/pair.sh` and `scripts/blind.sh` resolve the checkout once at entry** and export `CLAUDE_PROJECT_DIR` for everything they invoke, and the fallback walk in `shell_shapes.py` follows a worktree's `.git` pointer file to the main checkout. Run from `.claude/worktrees/<slug>-spec`, the walk stopped at the worktree, which holds no declaration, and every lane moved back to its kit default in silence. A variable the caller already set is taken at its word.
- **The kit ships as a plugin, so `hooks/` and `agents/` sit at the root of it.** `.claude/` keeps what belongs to a project: `settings.json`, `settings.local.json` and `worktrees/`, which anchors the spec and implementation trees. `scripts/pair.sh`, `scripts/strike-diff.py` and `scripts/blind.sh` find `shell_shapes.py` beside their own directory rather than under the checkout they run against, because `scripts/` and `hooks/` travel together and an installed checkout holds neither.
- **The agent definitions and the docs write the kit's scripts under `${CLAUDE_PLUGIN_ROOT}/scripts/`**: `pair.sh`, `strike-diff.py`, `blind.sh` and `cite.py`. An installed plugin is outside the checkout, so a repo-relative spelling names nothing.
- **`blind-bash.py` admits an absolute head or a `${CLAUDE_PLUGIN_ROOT}` head** on the blind agents' one command, matching the `endswith` rule `shell_shapes.is_blind_run` already carried. A relative prefix is still denied: the blind writer can write under its own lane, so `<tests dir>/scripts/blind.sh` would be a shell of its own authoring.
- **The default `bwrap` profile binds `hooks/` and `agents/` read-only inside every checkout.** They were covered by `.claude/` before they left it, and without the two entries one of the kit's own agents could rewrite the hooks that judge it.
- **Hook wiring lives in one file rather than in seven agent definitions.** The `hooks:` block is gone from every agent, and `no-impl-reads.py` and `blind-bash.py` join the lane hooks in `.claude/settings.json`. A plugin-shipped agent definition runs no frontmatter hooks, so a block left in place reads as enforcement the runtime never executes. Copying `.claude/` still wires everything, and now wires it in one place.
- **`no-impl-reads.py` and `blind-bash.py` are gated on `agent_type`** rather than on where they are wired. Each carries a `BLIND` tuple — four agents for the read block, two for the command lock — and every caller outside it, the main agent included, passes unjudged. The fail direction inverts with it: an absent `agent_type` is the main agent and must pass, so a build that stopped supplying the key would hand a blind agent the implementation and an unrestricted shell. `docs/approved-specs.md` states that cost.
- **The tests-only removal lane reads as a motion to strike.** Its structure line is `motion: strike` rather than `kind: excision`, its per-line verb is `strike <target>`, its shape comes from `docs/testing.md` "Strike motions", and its merge check is `scripts/strike-diff.py`. `scripts/pair.sh` reads `kind:` and `motion:` as the same structure line, so it routes on either.
- **The tests-only replacement lane is a motion to amend.** Its structure line is `motion: amend` rather than `kind: repair`, its shape comes from `docs/testing.md` "Amend motions", and `scripts/pair.sh merge` routes `strike` and `amend` alike to `scripts/strike-diff.py`. The line shape holds: `strike <target>`, `rule:`, `assertion:`, `replace:`, `as:`, `kills:`. A block written `motion: amend` previously missed the mechanical route and merged with no check at all.
- **The plan gate's locator round is the discovery round.** A plan's second metadata line is `discovery: detective | inline` rather than `grounding:`, and the `prosecutor` check that reads it is `(b) Discovery`.
- **`scripts/pair.sh` is an `exec` shim over `scripts/pair/`**, whose `cli.py` owns every contract line and whose three libraries print to stderr only. The name holds: it is a literal in the agent definitions, in the lane table and in the `bwrap` carve-out `pair-passthrough.py` matches end to end.
- **`scripts/pair.sh merge` converges the pair** rather than merging the spec branch alone: the lane check, a commit in each tree, a rebase of both branches onto the target branch where it moved, the combine of `impl/<slug>` into the spec tree, the gate in that combined tree, and an `--ff-only` land followed by the removal of both trees and both branches. Steps three to six hold `flock`. A red gate lands nothing and leaves both trees standing.
- **The gauntlet's artifacts leave `docs/` for `<gauntlet dir>`, `gauntlet/` by default.** Its lanes are `plans/approved/`, `plans/drafts/`, `specs/approved/`, `specs/drafts/`, `reviews/` and `verdicts/`, and the base itself is `gauntlet_dir` in `.claude/blind-reads.json`. The agent definitions, `README.md` and the docs write them as `<gauntlet dir>/…`, the convention `<tests dir>` already follows, so a project that moves the base reads its own layout. The lane hooks, `scripts/` and `.gitignore` move with them.
- **The `arbiter` returns `ADMITTED`, `AMENDED` or `STRICKEN` per behavior line**, defaulting to `STRICKEN`.
- **The post-merge test check belongs to the `bailiff`** rather than to the `arbiter`, on the same brief and the same output format.
- **The `detective`, `juror` and `examiner` are pinned to Sonnet.**
- **The `prosecutor` takes an amendment round on an approved plan.** Checks run on the amended lines alone and every other check prints `carried`. On `READY` it rewrites `<gauntlet dir>/plans/approved/<slug>.txt`, keeping every reviewer block oldest first, and the rewritten plan takes a new approval word. A spec amendment stays a full re-review.
- **The `arbiter` and `prosecutor` count a host conduct block in the framing count**, with no exemption for it.
- **A blind agent's allowlist is `docs/`, `tests/`, `state/`, `gauntlet/specs/approved/`, `gauntlet/red/` and `gauntlet/merge/`**, with the `gauntlet/` base denied entire. No denied subtree nests inside an allowed root.
- **The chain's two run artifact directories sit under the gauntlet base**: `<gauntlet dir>/red/<slug>.txt` for the saved red run and `<gauntlet dir>/merge/<slug>.txt` for the merge evidence. Both are gitignored, both are re-allowed leaves inside the denied base so the `juror` and `bailiff` read their own evidence, and both are read-only inside every checkout under `bwrap-wrap.py`. `state/` keeps gate scratch alone.
- **Every hook fails closed on a payload it cannot decide**, the one that most needs deciding. Not JSON, not an object, a `tool_name` that is not a string, or a field the hook must read carrying the wrong type: each is denied, naming the hook and the field, and so is a call whose verdict raises. Each hook refuses only for the tools it decides, so a malformed call of another tool still passes.
- **`bwrap-wrap.py` denies a `Bash` call it cannot build a sandbox for**, rather than letting the command run unwrapped.
- **`bwrap-wrap.py` runs `bwrap` once on a trivial profile before it rewrites anything.** A `bwrap` that is on `PATH` but cannot run here — user namespaces off, a seccomp or LSM policy refusing the setup — becomes a named denial quoting what `bwrap` said, instead of every `Bash` call in the session dying at exec.
- **`bwrap-wrap.py` binds each writable worktree with `--bind-try`.** A tree cut between the worktree listing and the exec costs its own writability rather than killing the whole command.
- **The `Stop` gate reports a red run whose file cannot be read as a complaint.** A run this gate cannot open is one nobody can be shown a verdict for, so it is a complaint rather than a file to step over.
- **The kit cites its own prose at `${CLAUDE_PLUGIN_ROOT}/docs/`.** The agent definitions, the lane hooks and the `scripts/` drivers pointed at `docs/plans.md`, `docs/approved-specs.md` and `docs/agents.md` as if every installing project kept a copy of them; it does not, and the citations resolved to nothing. A project now holds `docs/testing.md`, which is its own test policy, and reads the rest out of the installed plugin.
- **`no-impl-reads.py` lets a blind agent read `${CLAUDE_PLUGIN_ROOT}/docs/`**, so it can follow those citations. The entry is anchored at that `docs` directory: the plugin's `hooks/`, `scripts/` and `agents/` beside it stay denied. `${CLAUDE_PLUGIN_ROOT}` and `$CLAUDE_PLUGIN_ROOT` are expanded where they appear in a path, since that is the spelling the citations carry.

### Removed
- **The `allow` and `runners` keys of `.claude/blind-reads.json`.** A repo that set either gets the default read allowance and the built-in runner table instead, and `shell_shapes.py --config` answers neither name. `allow` could re-open the artifact base to a blind agent, which is the whole of what that base is denied for, and the runner table is code because whether an invocation only reads is not a repo's to declare. A project whose suite runs some other way edits `scripts/blind.sh`.

### Fixed
- **Every hook that reads `agent_type` matched a bare agent name**, so none matched under an installed plugin, where the harness spells the same agent `gauntlet:prosecutor`. The reviews lane denied each reviewer its own round file and the other lanes denied their own writer; `no-impl-reads.py` and `blind-bash.py` found no subject and let a blind agent read the implementation and run any command; `bwrap-wrap.py` left the kit's agents unsandboxed. The name is normalized once, in `shell_shapes.agent_of`.
- **Read-only `git` was refused when a global option came before the subcommand.** `git -C <dir> ls-files <lane>`, `git --no-pager grep -- <lane>`, `git -c core.pager=cat …`, `git --git-dir=<dir> …` and `git -P diff -- <lane>` all read as writes to every path they named, so an agent investigating a lane it may read got denied and had no spelling that worked.
- **The `spec commit:` line of the `TEST CHECK` brief carried the block's object name** rather than a commit, so the one shell the `bailiff` has — `scripts/blind.sh show <spec-commit> <slug>`, which spells `git show <rev>:<path>` — failed with `fatal: path ... exists on disk, but not in '<object>'`. Every reviewer hit it and fell back to reading the block off the working copy. The line names the commit that last wrote the block.
- **`scripts/pair.sh merge <slug>` refused every pair its own `open` cut.** `open` commits the approved block on the spec branch, and the lane check read that commit as the spec tree writing outside its lane, so the merge stopped at step one and nothing could land. The spec lane is the tests directory and the approved block together.
- **`scripts/pair.sh open <slug>` left the approved block uncommitted on the spec worktree.** Every agent downstream reads the block out of a commit, so the pair opened into a state the writer could not be briefed from, and the only hand that could commit it was the one the lane hook denies. `open` now commits it as `spec: <slug>`, staging first so an untracked block is seen, and taking no second commit where the branch already holds it.
- **A turn held open by the `Stop` gate could not end.** The gate answered 2 to every `Stop`, including the one ending the turn it had just started, so a session with an unruled red run and no juror to spawn looped. It reads `stop_hook_active` from the payload: the complaints still print, and the second `Stop` exits 0 so the turn ends and the user sees the state.
- **`agents/scrivener.md` named four commands `hooks/blind-bash.py` denies** and never the one shell the hook admits: a bare `git status --porcelain` for the spec check, `PYTHONPATH=$(pwd) .venv/bin/pytest` and `node --test` for the suite, and three lint commands for the gates. The writer's first command came back denied at each of the three sites. All three name `scripts/blind.sh` now: `status <slug>` for the spec check, `test <tests dir>/<file>` for the suite and the gates.
- **A blind agent had to type `${CLAUDE_PLUGIN_ROOT}/` in front of every `scripts/blind.sh` call.** The bare head the hook admitted named nothing in a consumer's checkout, so the call passed the hook and died at exec. The hook resolves a bare head to its own sibling copy and answers with `updatedInput` — only a bare head, only for a caller in `BLIND`, and only after the admitted-shape match has decided the call. `scripts/pair.sh` calls are the main agent's and keep their prefix.
- **`agents/bailiff.md` named a `git show` command `hooks/blind-bash.py` denies**, so the reviewer's first command came back refused on every round. It names `scripts/blind.sh show <spec-commit> <slug>`, which runs that same `git show` in the tree the brief names, and `scripts/blind.sh show HEAD <slug>` for the post-merge read, where the spec worktree is gone and the script falls back to the checkout.

## [0.1.0] - 2026-09-10

### Added
- `gauntlet/` as the base for every agent write: `plans/`, `specs/`, `reviews/`, `drafts/{plans,specs}/`. Plans and specs tracked, the other two gitignored.
- `plans-lane.py`. Only the `gauntlet-prosecutor` writes `gauntlet/plans/approved/<slug>.txt`.
- `docs/plans.md`, the stage-1 plan shape.
- A tests-only lane: `motion: strike` and `motion: amend` blocks skip the plan gate, the red run and the post-merge round.
- `scripts/pair.sh` — `open`, `red`, `merge` — and `scripts/strike-diff.py`, the mechanical merge check for the two tests-only shapes.

### Changed
- Approved specs moved to `gauntlet/specs/approved/`, reviewer rounds to `gauntlet/reviews/`. `state/` holds the red run alone. `reviews-lane.py` carves out one folder per reviewer.
- `no-impl-reads.py` denies `gauntlet/` and re-allows `gauntlet/specs/approved/`, so plans, drafts and rounds stay closed to the blind agents.
- `EVASION` no longer burns the reviewer; only `STEERING` does.
- The five agents are prefixed `gauntlet-`, since the lane hooks key on `agent_type`.

**Breaking for existing installs:** re-copy `.claude/` and re-run the `--self-test` commands.

### Fixed
- `scripts/blind.sh test` resolving a spec worktree against a `tests_dir` that carries a glob character. The configured name is the needle in both of the parameter expansions that split the path, so it is quoted: an unquoted `*` or `?` there matched a directory the key does not name, and the run landed in the wrong tree.
- Lane writes slipping through behind a harmless head word.
- Blind reads through an interpreter's `-e`/`-c`, an unrooted `grep -rn x .`, or a source file under a directory named `docs`, `tests` or `specs`.
- Lanes now hold outside a git checkout, including the write that creates the lane directory.

## [0.0.1] - 2026-09-09

### Added
- Blind adversarial review workflow: plans and test specs get checked by reviewers that cannot read the implementation.
- Enforced lanes: only the approving reviewer can write approved specs or tests.
