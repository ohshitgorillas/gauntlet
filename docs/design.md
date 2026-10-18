# Gauntlet design (v0.11.0)

This document describes what Gauntlet is and how it enforces what it claims. The purpose and scope are in [`charter.md`](charter.md). Repository configuration is in [`config.md`](config.md). Usage is in [`../README.md`](../README.md).

Each section states a mechanism, then lists the approaches it replaces under **Not instead**, with the reason each one failed. Read those lines before changing the mechanism above them.

## 1. Principles

**A program runs the pipeline.** Gauntlet is a standalone harness: plain code that sequences the stages, runs git, runs the gates, commits and lands. LLM agents only do role work: they receive an input and return an answer.

- Not instead: a main LLM agent that drives the workflow. Any agent that holds the pipeline and a shell can tamper with the tests that judge it, and instructions do not stop it.
- Not instead: a Claude Code plugin. A plugin runs inside the session it is meant to govern, and the installed copy drifted from the source.

**Answers go back to the harness.** Every verdict, plan, spec and ruling is a structured answer that the harness receives and writes to the job record. No agent writes a file of record.

- Not instead: verdict files in folders only one agent may write. A gate that reads a file an agent can edit is a gate the agent can forge.

**No shell command is ever parsed.** Enforcement comes from what an agent's container contains and which tools exist in its launch. Nothing inspects, matches or interprets the text of a command. The one exception is a gate that detects such parsing in Gauntlet's own code in order to block it.

- Not instead: regex on command heads, allowlists of commands, carve-outs by command shape. Every parser gets bypassed, and every carve-out invites the next.

**A check that did not run never passes.** Every check writes a row to the job record on every run, including runs that find nothing. Every verdict set includes `COULD NOT JUDGE`, which blocks like a failure.

**Loops are capped by a counter.** Every review loop has a round cap (default 2). Each round is a fresh agent that reads the current files from the job record; no agent is resumed. At the cap the job stops and shows you both sides.

- Not instead: review until convergence. The arbiter loops never converged, and they burned tokens agreeing with themselves.

**Decisions are pure functions.** Every decision the harness makes, such as the next stage, whether a job may land, or which jobs may start, is a pure function of the job state and the latest answer, with a unit test for every branch. The code that touches disk, git, containers and the API is a thin layer around them.

## 2. Workflow

A job runs these stages in order. "You approve" means the job waits at a screen until you act.

| # | Stage | Who | Input | Returns | Gate |
|---|---|---|---|---|---|
| 1 | Brief | brief-writer (reader) | conversation with you | `brief.md` | you approve |
| 2 | Discovery | detective (reader) | the planner's questions, all at once | file:line table | — |
| 3 | Outline | planner (reader) | brief, discovery table | steps, the implementer for each, the areas each touches | you approve or redirect |
| 4 | Plan | planner and prosecutor (readers), in rounds | brief, outline, discovery, objections | plan; per-check `PASS` / `FAIL` / `COULD NOT JUDGE` | prosecutor passes every check, then you approve |
| 5 | Spec | planner, examiner (scratch), arbiter (judge), in rounds | brief, plan | behavior lines `S1…` with `bite:` values, collateral rows; per-line rulings | arbiter accepts every line, then you approve |
| 6 | Stubs | implementer | the plan's stub step | signatures whose bodies only raise | — |
| 7 | Tests | scriveners (tester) | spec lines routed to them, interface view | tests, with test ids per spec line | — |
| 8 | Red run | harness, then juror (judge) | every configured test runner; spec, tests, red output | `RED` / `ERROR` / `GREEN` / `INVALID` / `COULD NOT JUDGE` per line | every line `RED` |
| 9 | Lock | harness | — | commit of the tests on the job branch | — |
| 10 | Build | implementers, one plan step each | the step, the locked tests | `complete` / `partial` / `blocked`, with a reason | step's tests and gates green |
| 11 | Review | repo reviewers (reader) | the diff, supplied by the harness | findings with file:line, failure scenario, `blocking` flag | no blocking findings |
| 12 | Bailiff | bailiff (judge) | final spec, final tests, collateral rows, test policy | `PIN` / `UNPINNED` / `COULD NOT JUDGE` per line; `HELD` / `ALTERED` per collateral row | every line `PIN`, every row as the spec says |
| 13 | Land | harness | — | land screen | you approve |

Notes on the stages:

- **Plan (4).**
  - The prosecutor resolves every citation in the plan against the tree.
  - It cuts any change you would see that no sentence of the brief asked for. If the planner argues the change is needed, the prosecutor returns `ESCALATE: LEAVE` and you decide.
  - A question the planner dodges counts as a fail. A question no agent can answer goes to you.
  - The prosecutor may return `REFUSE` when the plan text itself tries to steer its ruling.
  - Each plan step lists the spec lines it serves (filled in at stage 5), the stubs it needs, and the files it expects to touch.
- **Spec (5).**
  - A `bite:` value is the measured behavior a test pins. The examiner measures any `bite:` value that needs a script or a rendered state space. It runs on a throwaway copy of the tree.
  - Collateral rows name existing tests that the change alters or retires, and quote the assertion that must survive.
  - The planner routes each line to a tester by the testers' one-line descriptions.
- **Stubs (6).** Stubs let the red run fail on assertions (`RED`) instead of on missing imports (`ERROR`). A `GREEN` verdict at stage 8 sends the line to the arbiter, which rules whether the spec or the stub is at fault.
- **Tests (7).**
  - A line the scrivener cannot test goes back to the arbiter instead of getting a weak test.
  - For a collateral row, the scrivener repairs the code around the quoted assertion. The harness checks that the assertion is byte-identical.
- **Red run (8).** The harness runs every runner in `gauntlet.yaml`, not just one. A test that passes before any implementation exists reopens its spec line.
  - Not instead: a pytest-only red run. It once ignored the JS tests entirely.
- **Juror (8).** Its verdict stops the pipeline. The juror cannot be overruled by any agent; only you can, through `accept`.
  - Not instead: a juror whose verdict advises. A juror without teeth was ignored.
- **Build (10).**
  - When a test fails, the implementer either fixes the code or returns `spec_defect`.
  - A `partial` step goes to a fresh implementer, starting from that step's diff. A step is never re-run on top of its own partial work.
  - The harness commits each finished step.
- **Review (11).** A finding without a file:line and a failure scenario is dropped. Blocking findings go back to the implementer of the step they cite.
- **Bailiff (12).** It holds none of the reasons the spec was accepted, so a softened assertion cannot reach it as permission.

### Reopening the spec

Any role's answer may carry `spec_defect: {line, claim, evidence}`. You can raise one with `gauntlet reopen <id> S4`.

1. The harness pauses the stage that raised it.
2. The arbiter rules on the defect. Your own reopen skips this step, since you own the spec.
3. If it is upheld, the planner amends only the affected lines. Arbiter rounds run on the change alone, and you approve it.
4. For the amended lines, stages 7 to 9 run again. Then stages 10 to 12 run again for the plan steps that serve those lines.
5. If the arbiter rules that the plan is affected too, the planner revises those steps and the prosecutor gets one round on them before step 4.

Spec lines have stable ids, plan steps list the lines they serve, and testers return test ids per line, so the harness computes what an amendment touches. Reopens are capped by `caps.reopen` (default 2). Every amendment appears on the land screen.

- Not instead: separate procedures for plan amendments and spec revisions. One mechanism covers both.

### Audit jobs

`gauntlet audit <scope>` runs the auditor (judge) over existing tests, one test file per call, against the test policy. Each test gets `VALID`, `STRIKE`, `AMEND` or `NOTE`. The rows you select become a job that starts at stage 5 with those rows as its spec, and skips stages 6, 10 and 11.

- Not instead: separate lanes with their own pipelines. Job shapes are stages skipped within the one pipeline; rigid lanes did not fit real work.

## 3. Kinds

Every role runs in exactly one kind. The kind alone decides what the role can see, write and run. Repositories choose a kind for each of their roles and can never add one.

| Kind | Sees | Writes | Tools | Roles |
|---|---|---|---|---|
| judge | only what the harness puts in its prompt | nothing | none | arbiter, juror, bailiff, auditor |
| reader | the job checkout | nothing | Read, Grep, Glob | brief-writer, planner, detective, prosecutor, reviewers |
| coordinator | the main checkout | nothing | Read, Grep, Glob, `open_job`, `job_status`, `job_record` | coordinator |
| scratch | a throwaway copy of the job checkout | the copy, discarded after | shell, Read, Write, Edit, Grep, Glob | examiner |
| tester | spec, `tests/`, test helpers, test policy, interface view, lint and type configs | `tests/` | shell, Read, Write, Edit, Grep, Glob, `run_tests` | scriveners |
| implementer | the job checkout | everything except `tests/` and the protected set | shell, Read, Write, Edit, Grep, Glob | implementers |

The Tools column is the SDK `tools` list each kind is given. A launch whose answer is constrained by a schema also has `StructuredOutput`, which `output_format` adds and through which the answer comes back (§4, "Judge launches").

No kind has git, the `gauntlet` CLI, the job record, or the ability to start subagents.

- Not instead: per-repo permission sets. Permissions that grow per repo become the mount-table problem of §4 again.

## 4. Enforcement

### The launcher

Every role, judges included, starts through one launcher. The harness calls the Claude Agent SDK with `cli_path` set to a wrapper that runs the Claude Code CLI inside a fresh rootless podman container. The CLI is installed in the pinned image at a pinned version and is never bound in from the host. The host's binary is labelled `data_home_t`, which a container process cannot execute without `label=disable` (measured, below). Relabelling it with `:z` would relabel the host's live CLI.

The repository's `Containerfile` builds its toolchain image. The harness builds the pinned image on top of it, adding three things the repository never supplies: the CLI at a version the harness pins, `socat` as the proxy relay, and the entrypoint `gauntlet-launch`. The wrapper runs `podman run ... <pinned image> gauntlet-launch "$@"`. `gauntlet-launch` starts `socat TCP-LISTEN:<port>,bind=127.0.0.1,fork UNIX-CONNECT:/run/gauntlet/proxy.sock`, waits until `127.0.0.1:<port>` accepts a connection, and then execs `/usr/local/bin/claude "$@"`. The harness's gate and test containers use the same image with their own command and never start `gauntlet-launch`.

Every container that runs the CLI binds one path, the proxy socket folder, at `/run/gauntlet` with `:z`. That covers every role launch, judges included. The harness's gate and test containers run no CLI and bind no socket. The kind decides two things:

1. **Mounts.** Which paths exist in the container, and whether each is read-only or writable. Everything else does not exist.
2. **Tools.** The SDK `tools` list. A tool left off the list is not present at all, which is a hard restriction rather than a permission prompt. Leaving out `Agent` is what stops a role from starting subagents.

Harness tools (`run_tests`, `open_job`, `job_status`, `job_record`) are in-process SDK MCP tools. They run in the harness on the host, and the CLI reaches them over stdio.

Launches load no host settings, hooks or instruction files (`setting_sources=[]`, `strict_mcp_config=True`, `permission_mode="dontAsk"`, a tmpfs home). Every container but a judge's sees the job tree at `/work`; every container runs as a non-root user with all capabilities dropped and `no-new-privileges`, and is removed when the launch ends. Job folders are mounted with `:z` so SELinux labels allow access.

Mounts that are bound into a container are locked. Measured on Fedora 44 with podman 5.8.9: unmounting, remounting and new namespaces from inside all fail to make a read-only path writable.

### Measured

Taken on 2026-10-17 with `podman version 5.8.9`, Claude Code `2.1.302`, `claude-agent-sdk 0.2.168`, image `docker.io/library/python:3.13-slim`, every container run with `--rm --userns=keep-id --cap-drop=all --security-opt no-new-privileges`. Scripts: `exp.sh`, `exp_sdk.py` and `claude-in-podman.sh` under `~/.claude/jobs/efee45eb/tmp/research/`; transcript `~/.claude/projects/-home-atom-dev-gauntlet/efee45eb-06bf-4dbd-9983-7364f029120f/subagents/agent-aa9801e5327a67927.jsonl`, line 80. These are not measured again (roadmap rule 4).

| Claim | Command | Decisive output |
|---|---|---|
| The SDK with `cli_path` set to a wrapper runs `claude` inside `podman run -i` over stdio, and in-process SDK MCP tools reach it | `venv/bin/python -I exp_sdk.py` with `ClaudeAgentOptions(cli_path="claude-in-podman.sh", mcp_servers={"h": create_sdk_mcp_server(...)}, strict_mcp_config=True, setting_sources=[], permission_mode="dontAsk")`; the wrapper runs `podman run --rm -i ... /usr/local/bin/claude "$@"` | `init tools: ['Edit', 'Glob', 'Grep', 'Read', 'StructuredOutput', 'Write', 'mcp__h__run_tests']` then `tool_use: mcp__h__run_tests {"ids": "tests/test_new.py"}` and `harness tool calls: [{'ids': 'tests/test_new.py'}]` |
| `output_format` constrains the answer to a JSON schema | same launch, `output_format={"type": "json_schema", "schema": SCHEMA}` | `structured: {"tools_i_have": [...], "files_seen": [...], "src_readable": false, "spawned_subagent": false, ...}`, every required key present |
| A `tools` list without `Bash` or `Agent` leaves the agent without them | same launch, `tools=["Read", "Glob", "Grep"]` | init tool list carries no `Bash` and no `Agent`; the agent's own notes: "I do not have an Agent/Task tool" |
| `:O` overlays discard writes | `podman run ... -v "$R/job:/work:O" -w /work python:3.13-slim bash -c 'echo junk > src/calc.py; rm -rf tests; touch scratch_file; ls'` | `scratch_file` listed inside; on the host `ls job` gives `spec src tests` and `cat job/src/calc.py` gives `def add(a, b): return a + b  # SECRET_IMPL` |
| A read-only bind mount cannot be made writable from inside, non-root | `-v "$R/job:/work" -v "$R/job/tests:/work/tests:ro"`, then `umount /work/tests`, `mount -o remount,rw /work/tests`, `unshare -Urm sh -c "umount /work/tests \|\| mount -o remount,rw,bind /work/tests; touch /work/tests/y"`; repeated with `--cap-add SYS_ADMIN` | `umount: /work/tests: must be superuser to unmount.` then `touch: cannot touch '/work/tests/y': Read-only file system`; same with `SYS_ADMIN` added |
| A labelled bind mount fails without `:z` on SELinux | the same launch without `--security-opt label=disable` | ``exec container process `/usr/local/bin/claude`: Permission denied`` and `touch: cannot touch 'src/new.py': Permission denied` |
| A job folder bound with `:z`, and `tests/` with `:ro,z`, is readable and writable by the non-root user under SELinux without `label=disable` | `podman run --rm --userns=keep-id --cap-drop=all --security-opt no-new-privileges -v job:/work:z -v job/tests:/work/tests:ro,z -w /work python:3.13-slim bash -c 'cat /proc/self/attr/current; ls -Zd /work; touch src/new.py && echo "src write: ok"; touch tests/x'` (2026-10-18, image pulled that day, no CLI binary mounted) | `system_u:system_r:container_t:s0:c789,c931`, `system_u:object_r:container_file_t:s0 /work`, `src write: ok`, `touch: cannot touch 'tests/x': Read-only file system` |
| An empty `tools` list leaves a launch one tool, `StructuredOutput`, which `output_format` adds | the `exp_sdk.py` launch above with `tools=[]` and no harness MCP tools, so the SDK passes `--tools ""` to the CLI | `init tools: ['StructuredOutput']`; the agent's notes: "I do not have Read, Bash, or Agent/Task tools" |
| A CLI with no credential in the container refuses before it sends anything, so `ANTHROPIC_BASE_URL` alone does not reach the API | `podman run --userns=keep-id --cap-drop=all --security-opt no-new-privileges --tmpfs /home/agent:rw,mode=1777 -e HOME=/home/agent -v claude:/usr/local/bin/claude:ro,z -e ANTHROPIC_BASE_URL=http://host.containers.internal:18765 -w /home/agent python:3.13-slim /usr/local/bin/claude -p 'Reply with exactly the word PROXY_OK and nothing else.'`, `claude` a copy of the CLI in a scratch folder, a host proxy listening on `127.0.0.1:18765` | `Not logged in · Please run /login`; the proxy log holds only `listening 127.0.0.1:18765` |
| The host's CLI binary, bound `:ro` without `:z`, cannot be executed under SELinux without `label=disable` | the `:z` run's flags plus `-v ~/.local/share/claude/versions/2.1.302:/usr/local/bin/claude:ro`, running `cat /proc/self/attr/current; ls -Z /usr/local/bin/claude; /usr/local/bin/claude --version` | host label `unconfined_u:object_r:data_home_t:s0`; inside, `system_u:system_r:container_t:s0:c404,c617`, then `bash: line 1: /usr/local/bin/claude: Permission denied` |
| A fresh container, image already local, takes 59 to 88 ms from `podman run` to its first command, and 66 to 95 ms to return | three runs of the `:z` run's flags with `-v job:/work:z -w /work python:3.13-slim date +%s%N`, timed against host `date +%s%N` around each run | `run 1 start_to_exec_ms=88 run_total_ms=95 exec_to_return_ms=7`; runs 2 and 3 give 59/66 and 80/86 ms |
| Under podman's default rootless network (pasta), `host.containers.internal` resolves to `169.254.1.2`, and a listener bound to host `127.0.0.1` cannot be reached from the container | `podman run --userns=keep-id --cap-drop=all --security-opt no-new-privileges python:3.13-slim python3 -c "$PROBE"`, a TCP probe of `host.containers.internal:18765` and `:18766`, with two host listeners bound to `127.0.0.1` on those ports | `proxy 18765 FAILED ConnectionRefusedError(111, 'Connection refused')`, the same for `18766`, and neither listener logs a connection |
| With `ANTHROPIC_API_KEY` set to a placeholder and the proxy unreachable, the CLI prints no refusal and no output in 60 s and sends the proxy nothing; this does not show that the CLI accepts the placeholder | the credential row's command plus `-e ANTHROPIC_API_KEY=gauntlet-placeholder`, under `--timeout 60` | no CLI output and no `Not logged in` line; the proxy log holds only `listening 127.0.0.1:18765`; podman ends the run at 60 s with exit 255 |
| A container under `--network none` has only `lo` and reaches nothing off the box, but a relay inside it cannot connect to a host process's unix socket bound in with `:z` (mode 666, same uid, `container_file_t`), so the CLI's request never reaches the proxy | `podman run --network none --userns=keep-id --cap-drop=all --security-opt no-new-privileges --tmpfs /home/agent:rw,mode=1777 -e HOME=/home/agent -v claude:/usr/local/bin/claude:ro,z -v sock:/run/gauntlet:z -e ANTHROPIC_API_KEY=gauntlet-placeholder -e ANTHROPIC_BASE_URL=http://127.0.0.1:18080 python:3.13-slim`, a `python3` relay on container `127.0.0.1:18080` to `/run/gauntlet/proxy.sock` (the image has no `socat`), a host proxy holding the socket, probes of host addresses, `host.containers.internal`, internet addresses and DNS | `relay: unix connect failed PermissionError(13, 'Permission denied')`; every probe `OSError(101, 'Network is unreachable')`; `api.anthropic.com` does not resolve; the proxy log holds only its listening line |

The last seven rows used image `ce3ff9524414`. The socket refusal is attributed to SELinux denying `container_t` a connect to a socket held by an unconfined host process; the audit log was not read, so that cause is inferred. The `:ro` result holds for the non-root user `--userns=keep-id` gives; a root process with `CAP_SYS_ADMIN` is outside it and is not how any kind runs. A copy of the CLI bound `:ro,z` from a scratch folder, labelled `container_file_t`, executes where the host's `data_home_t` original does not. The start time excludes `--rm` teardown and CLI start-up, and its share of a job's wall clock waits for the first job wall clock at M3.

- Not instead: exempting any caller from the launcher. Every exemption in the old system became a hole.
- Not instead: widening the mounts when a tool breaks under them. The tool's own configuration is fixed instead. Widening the mount table one gap at a time is how the old system drifted.
- Not instead: separate OS users or a gatekeeper process; the Claude Code sandbox setting; shell-less agents with an MCP tool per allowed action, which turns into a list of every command spelled out.
- Not instead: checking at land time what an agent wrote. Writes are prevented, never audited after the fact.

**Why podman.** Rootless podman has no root daemon, locks its mounts, provides overlay volumes for scratch copies, and runs a pinned image, so the gate always sees the same environment. A pinned image is what shuts out the plugin and `sitecustomize` routes in "The protected set" below. The cost is that each repository maintains a `Containerfile` with its whole toolchain, and a dependency change means a rebuild. Bubblewrap would avoid the image, but it runs on the host's environment and pins nothing. Docker runs a root daemon by default.

### One path for every checkout

The job checkout is a git worktree at `.gauntlet/jobs/<id>/tree`. Containers see it only as `/work`. The harness alone knows the host path, and it runs every git command on the host with an explicit `--git-dir` and `--work-tree`. Agents never run git; inside a container, `.git` points at a host path that is not mounted.

- Not instead: each tool resolving which checkout it is in. The old resolvers (worktree, symlink, `CLAUDE_PROJECT_DIR`) disagreed with each other.
- The old read-only mounts broke git, pre-commit, worktrees and fixtures with EROFS. Agents no longer run any of them. What still breaks under a read-only `tests/` is a test that writes into `tests/` (snapshot updates, fixtures written in place). Those tests are fixed to write elsewhere.

### Implementer containers

- The job tree is mounted writable, with `tests/` and the protected set mounted read-only on top.
- `.git` is mounted read-only. A writable `.git` file could be pointed at a directory the implementer controls, with settings such as `core.fsmonitor`, and the harness's next git command on the host would run the implementer's code.
- No credentials are inside. The harness runs a forwarding proxy that adds the API key to each request, and the container reaches it through `ANTHROPIC_BASE_URL`. The container has no other network access unless `gauntlet.yaml` allows it.
- A CLI with no credential refuses before it sends anything (measured, §4), so `ANTHROPIC_BASE_URL` alone is not enough. The launcher gives the container a placeholder credential that the CLI accepts and that is worth nothing outside the proxy. The proxy drops it and adds the real key to each request. The placeholder is `ANTHROPIC_API_KEY` set to a fixed dummy value. With it set and the proxy unreachable, the CLI prints no refusal (measured, §4). That the CLI accepts it is shown only when a request carrying it arrives at the proxy, which is unmeasured.
- Default rootless networking cannot reach a proxy bound to host loopback (measured, §4). The proxy opens no TCP port on the host. It listens on a unix socket in a harness-owned folder, bound into the container with `:z`. A process on the host cannot hold that socket: a `container_t` process connecting to a socket held by a host process gets `Permission denied`, even with mode 666, the same uid and a `container_file_t` label (measured, §4). So the proxy runs in its own sidecar container, one per launch. The sidecar does not run the pinned image: that image carries the repository's toolchain, and no repository code runs next to the key. It runs the proxy image, which the harness builds from `docker.io/library/python:3.13-slim` pinned by digest plus the harness's own `gauntlet` wheel, built from the installed Gauntlet. Its command is `python -m gauntlet.seams.proxy /run/gauntlet/proxy.sock`. The sidecar runs with podman's default rootless network and the API key as a podman secret that only it mounts. Both containers bind the socket folder and run under the same SELinux level, which the harness picks per launch and passes to both as `--security-opt label=level:s0:<cA>,<cB>`. Inside the role's container, a relay from the pinned image listens on container `127.0.0.1:<port>` and forwards to that socket, and `ANTHROPIC_BASE_URL` is `http://127.0.0.1:<port>`. Every role container, judges included, and the harness's gate and test containers run with `--network none`, so they have loopback and, for role containers, the socket, and nothing else. The proxy sidecar is the only container on a network, apart from implementer containers under `implementer_network: true` below. That is how the tester's "No network", a judge's launch and `implementer_network: false` are enforced: there is no interface to reach anything through. `implementer_network: true` swaps `--network none` for podman's default rootless network for implementer containers only, and the proxy still comes through the socket. pasta with `-T` was rejected: it adds a forwarded port on top of ordinary outbound access, and with every capability dropped the container cannot filter that access itself. `--network none` leaves a container only `lo` and nothing off the box (measured, §4). The sidecar route is unmeasured.
- An implementer may run tests while it works. Those runs are only advisory. The harness's own gate run is the one that counts.

### The protected set

A read-only `tests/` protects the test files, not the test outcome. These can change what runs without touching `tests/`:
- root `conftest.py`;
- pytest settings in `pytest.ini`, `setup.cfg` or `pyproject.toml` (`addopts`, `testpaths`);
- `package.json`;
- the gate script;
- `sitecustomize.py` and `.pth` files;
- installed pytest plugins.

Two defences cover them:

1. The repository lists these paths as `protected` in `gauntlet.yaml`. They are mounted read-only for implementers, with single files bound individually.
2. The harness runs the gates and every test run in its own container from the pinned image. It uses its own pytest configuration: `-c <harness ini>`, `--confcutdir=tests`, and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.

Code that special-cases the tests is beyond any file rule. It is caught by review and the bailiff, not by enforcement.

### Tester containers

- Mounted: spec and helpers read-only, `tests/` writable, the test policy, the interface view, and the lint and type configs. The source is not mounted, so it does not exist inside.
- No network.
- A shell is safe here, because nothing in the container contains the source. The tester lints, formats and typechecks its tests, and runs them against the interface view to catch import errors, collection errors and broken fixtures.

**Interface view.** Before stage 7 the harness generates, with the repository's `interface` commands, a signatures-only view of the public names the plan touches, stubs included: `.pyi` from `stubgen`, `.d.ts` from `tsc --allowJs --declaration --emitDeclarationOnly`. Default values and private helpers can hint at how the code works, so the view is trimmed to the names the plan touches.

- Not instead: a blind tester with no way to check its work. Blind agents blocked from files they needed stalled.

**`run_tests`.** This is the tester's only path to the real source. The harness copies `tests/` into its own container as an overlay, runs the requested test ids with no network, and returns only an outcome per id (`pass`, `fail` or `error`) plus the exception type. It returns no tracebacks and no output. A test can still leak about one bit per id per call through its outcome; that residual is accepted.

- Not instead: returning raw test output. Huge outputs swamped agents' context, and tracebacks print implementation source.

### Scratch containers

The job tree is mounted as a podman overlay volume (`:O`), so writes land in a throwaway layer and the host tree is untouched. The same `.git` and credential rules as implementers apply.

### Judge launches

A judge's container binds only the proxy socket folder, which every CLI launch carries, and no job path. Its launch has an empty tool list. Its whole input is in its prompt, and its answer is constrained by a JSON schema (`output_format`). Setting `output_format` adds one tool, `StructuredOutput`, which is how the answer comes back, so an empty list leaves a judge that one tool and nothing that reads, writes, runs or starts a subagent (measured, §4).

## 5. Epics

`gauntlet epic` runs an effort too large for one job.

1. **Brief.** Same as stage 1, for the whole effort. You approve `epic.md`.
2. **Split.** The coordinator returns jobs, each with a sub-brief, the jobs it depends on, and the areas it expects to touch. One prosecutor round checks the split for gaps, overlap and wrong order. You approve or edit it.
3. **Run.** The harness starts every job whose dependencies have landed. A dependent job starts from `main` after its dependency lands, so branches never stack. Jobs run in parallel only when their approved plans declare files that do not overlap. A job with no file declaration runs alone.
4. **Revise.** After each job lands or stops, a fresh coordinator reads the epic record. It may change upcoming sub-briefs, add a job, or stop the epic. Changes and additions come back to you for approval.

Each job lands through its own land screen. The coordinator runs jobs through `open_job`; it cannot start agents, approve, land, or use any owner control.

- Not instead: a coordinator that starts subagents itself. It could run a scrivener or implementer outside the pipeline.

## 6. Owner controls and landing

Every stop shows one screen: what stopped, both sides of any disagreement, and your choices. You reach a stop through a cap, a block, `gauntlet stop <id>`, or a failure in the harness itself.

| Command | Effect |
|---|---|
| `gauntlet retry <id> [--note "…"]` | Run the failed stage again with a fresh cap |
| `gauntlet accept <id>` | Rule the stage passed |
| `gauntlet edit <id>` | Edit the stage's file or the tree, then `resume`. The harness commits your edit as an owner commit. |
| `gauntlet skip <id> <stage>` | Drop a stage |
| `gauntlet eject <id>` | The harness steps out and leaves branch `gauntlet/<id>` and the job folder for you |
| `gauntlet resume <id>` | Continue from `state.json` |

These commands exist only on the host CLI, which no container contains. Every use is recorded and shown on the land screen. A bypassed job can land, but the screen says exactly what did not go through.

**Landing.** The land screen shows:
- the diff, split into tests and code;
- red and green lines;
- open findings;
- amendments and bypasses;
- cost per role.

On your approval the harness merges `gauntlet/<id>` into `main` in your checkout. It does this only when your uncommitted changes touch none of the landed files. Otherwise it stops and touches nothing.

- Not instead: `--ff-only` in your live checkout, which was refused whenever your tree held work.

## 7. Records

All records live in `.gauntlet/`, which the harness adds to `.git/info/exclude`.

```
.gauntlet/jobs/<id>/
  state.json       stage, a row for every check run (passes included), bypasses, amendments
  trace.jsonl      one line per launch: role, model, effort, tokens, cost, outcome
  chat.md brief.md outline.md
  plan.N.md plan.N.objections.md plan.md
  spec.N.md spec.N.rulings.md spec.md
  red.txt juror.md steps/NN.log review.N.md bailiff.md land.md
  tree/            job checkout on branch gauntlet/<id>
.gauntlet/epics/<id>/
  epic.md split.N.md split.N.objections.md split.md
  state.json       jobs, dependencies, status, check rows
  trace.jsonl      coordinator launches, plus a total of each job's cost
```

Every file is plain text, so a job survives a harness crash. `resume` restarts from `state.json`, and `eject` hands you everything as is.

## 8. Harness layout

```
gauntlet/
  core/              pure, no I/O, one unit test per branch
    decide.py        decide(state, answer) -> next action
    verdicts.py      answer schemas, COULD NOT JUDGE handling
    reopen.py        spec line -> affected tests and steps
    schedule.py      which epic jobs may start
    land.py          land or refuse
  seams/             thin I/O around the core
    cli.py           every command in §6, plus new, run, epic, audit, status, reopen
    git.py           worktrees, commits, land; the only place git runs
    launch.py        the container launcher and per-kind mounts and tools
    proxy.py         the credential proxy
    tools.py         run_tests, open_job, job_status, job_record
    runner.py        harness-owned test and gate runs
    job.py           job and epic records
    screens.py       everything you see
roles/               fixed role prompts with their answer schemas, plus
                     the general implementer and general tester
```

Each role's rules live in its prompt file and nowhere else.
