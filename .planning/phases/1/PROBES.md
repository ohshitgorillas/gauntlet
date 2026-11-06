# Phase 1 probes

Date: 2026-11-05. Run by the `spiker` agent per D-03, on Archon CLI v0.13.2 and Claude Code 2.1.318. Each probe used a throwaway `git init` repo under `/tmp/spike-20261105T213414/repo`, `archon workflow run <name> --no-worktree` and `model: haiku`. Output below is quoted verbatim from the spiker's report.

Side finding (all probes): `archon validate` warns `Tool 'Task' was renamed to 'Agent' in the claude SDK — the old name is silently ignored at runtime`.

## P1 (A10): `sandbox:` write confinement

Verdict (a): no pure allow-list. `filesystem.allowWrite` is accepted, but it only adds writable paths. The checkout stays writable by default.
Verdict (b): yes. Whatever confinement the sandbox applies also holds for the Bash of an `Agent` sub-agent spawned from the node.

Run 1: `allowWrite: ['gauntlet/scratch']` only, `allowed_tools: [Agent, Bash]`, `allowUnsandboxedCommands: false`, an inline `agents: sub` with `tools: [Bash]`. `echo b > outside1.txt` (direct) and `outside2.txt` (sub-agent) both succeeded: listing `.: gauntlet outside1.txt outside2.txt README`.

Run 2: `denyWrite: [<repo>]` plus `allowWrite: [<repo>/gauntlet/scratch]`. Deny beats allow:
`1. echo a > gauntlet/scratch/ok1.txt: (eval):1: read-only file system: gauntlet/scratch/ok1.txt (exit 1)`

Run 3 (working form; `$R` = absolute checkout path):

```yaml
    sandbox:
      enabled: true
      allowUnsandboxedCommands: false
      filesystem:
        allowWrite: ['$R/gauntlet/scratch']
        denyWrite: ['$R/README', '$R/gauntlet/other']
```

Sub-agent output:

```
4. `echo c > gauntlet/scratch/ok2.txt`: succeeded, no output (exit 0).
5. `echo d > gauntlet/other/o2.txt`: failed, exit 1: `(eval):1: read-only file system: gauntlet/other/o2.txt`
6. `echo e >> README`: failed, exit 1: `(eval):1: read-only file system: README`
```

The parent node's direct Bash behaved the same. A "writes only under scratch" rule therefore needs `denyWrite` to list every other path. A new top-level file not on that list stays writable (Run 1). Globs in `denyWrite` were not tested.

## P2 (A5): `CLAUDE_PROJECT_DIR` in an MCP server's environment

Verdict: Claude Code sets it to the agent's cwd when the MCP config gives no value. A value in the config's `env` is NOT overridden; the config value wins.

Node `mcp: .archon/<a|b>.mcp.json`, `allowed_tools: []`. A stdio server writes `CLAUDE_PROJECT_DIR=%r cwd=%s` on start; `b.mcp.json` adds `"env":{"CLAUDE_PROJECT_DIR":"/bogus"}`.

```
bogus.txt: CLAUDE_PROJECT_DIR='/bogus' cwd=/tmp/spike-20261105T213414/repo
noenv.txt: CLAUDE_PROJECT_DIR='/tmp/spike-20261105T213414/repo' cwd=/tmp/spike-20261105T213414/repo
```

## P3 (finding 1.06): `Bash(<pattern>)` in `allowed_tools`

Verdict: no. `archon validate` accepts the specifier, warning only about `Task`, and reports `Results: 1 valid, 0 with errors, 1 with warnings`. At runtime Bash is removed entirely: it is not limited to matching commands.

```yaml
      allowed_tools: [Task, "Bash(uv run --script *cite.py *)"]
```

Run output: `No such tool available: Bash. Bash is disabled for this session, in subagents as well as here.` Neither `echo hi > x` nor `uv run --script cite.py arg1` ran (`ls: cannot access 'x'`; `CITE-RAN` absent). Control: plain `allowed_tools: [Agent, Bash]` ran Bash (P1). Not tested: a `Bash(...)` rule set through `settings`/permissions.

## P4 (D-13, D-24): `sandbox:` path forms

Run by the `spiker` agent on 2026-11-05 in `/tmp/spike-20261105T221740/repo`, using the same node shape as P1: `allowed_tools: [Agent, Bash]`, an inline `agents: sub` with `tools: [Bash]`, and `allowUnsandboxedCommands: false`. The vendored docs show only absolute paths in `sandbox:`.

Verdict (a): no. A relative `denyWrite: ['.']` denies nothing. Direct Bash and sub-agent Bash both wrote in the checkout root and in a subdirectory. An absolute `allowWrite` outside the checkout does allow writes there. Files on disk after the run: `d_root.txt s_root.txt` in the root, `sub: d_sub.txt keep.txt s_sub.txt`, `sx: d_out.txt s_out.txt`.
Control (absolute `denyWrite: ['<repo>/sub']`, `allowWrite: []`): the write to `sub` was denied, and so was the write outside the checkout.

```
1.2: exit 1 / `(eval):1: read-only file system: sub/d_sub.txt`
1.3: exit 1 / `(eval):1: read-only file system: /tmp/spike-20261105T221740/sx/d_out.txt`
```

Verdict (b): no. A relative `denyRead: ['gauntlet/failed']` blocks nothing. Both direct and sub-agent `cat gauntlet/failed/x.txt` printed the file's text, `secret`. An absolute `denyRead: ['<repo>/gauntlet/failed']` hides the path from both, and `README` stays readable:

```
1.4: exit 1 / `cat: gauntlet/failed/x.txt: No such file or directory`
1.5: exit 0 / `readme`
```

Verdict (c): no. Archon substitutes no variable inside `sandbox:` values. With `allowWrite: ['$ARTIFACTS_DIR/sx', '$WORKFLOW_ID']`, a write under the real artifacts directory was refused, so the sandbox used the literal string:
`mkdir: cannot create directory ‘/home/atom/.archon/workspaces/_local/repo-4/artifacts/runs/0f614561-78e0-4653-97ed-3b87973b60c0/sx’: Read-only file system`
The prompt text did substitute `$ARTIFACTS_DIR`. The probe did not dump the sandbox config, so the literal path is inferred from the refused write.

Consequence: every `sandbox:` path must be absolute and literal, and Archon cannot supply a path that is known only at run time.

Noise: under the sandbox, every Bash command also prints `read-only file system: /tmp/claude-1000/cwd-<id>` (the shell's cwd-state file) and exits 1, even when the write succeeded. Results were judged by the files on disk.

## P5 (D-13, D-24): `with:` in a loop body from an outer node

Verdict: yes. `archon validate` accepts the body node, and the body receives the value as `INPUTS_START`. `loop-nodes.md:617` seals the body's `depends_on`, but `with:` refs to outer nodes are not affected. Only the whole `$outer.output` was bound. The `$outer.output.start` field form (which needs an `output_format` on `outer`) was not tested.

```yaml
name: q5
worktree: {enabled: false}
nodes:
  - id: outer
    bash: 'echo hello5'
  - id: lp
    depends_on: [outer]
    loop_group:
      max_iterations: 1
      until_bash: 'true'
      nodes:
        - id: body
          script: |
            import os
            print("INPUTS_START=" + repr(os.environ.get("INPUTS_START")))
          runtime: uv
          with:
            start: $outer.output
```

```
  q5                                       ok
Results: 1 valid, 0 with errors
INPUTS_START='hello5'
```

Side finding: `archon workflow run --model haiku` is rejected with `Invalid --model 'haiku'. Expected <small|medium|large|@alias>=<model>`. A node-level `model: haiku` works.

## P7 (D-21): a run-owned key dropped under `include:`

Run by the main session on 2026-11-05 in `/tmp/spike-d21-1793917353`. Block `blk` declares `worktree: {enabled: false}`, and `top` includes it as node `b`.

Verdict: the drop raises no validation warning. `archon validate workflows blk` and `archon validate workflows top` both print `ok` and `Results: 1 valid, 0 with errors`, and `archon workflow list --json` gives `"parseWarnings":null` for both. Every command that loads the workflows, including `archon workflow run blk`, writes one structured log line to stderr:

```
{"level":40,...,"module":"workflow.include-expander","include":"b","target":"blk","droppedFields":["worktree"],"msg":"include.workflow_level_fields_dropped"}
```

## P6 (D-13): `./` and glob forms in `sandbox:`

Run by the `spiker` agent on 2026-11-05 in `/tmp/spike-20261105T221740/repo`. The runs used direct Bash only, `model: haiku`, `sandbox: enabled: true` and `allowUnsandboxedCommands: false`.

Verdict: no. None of `denyWrite: ['./']`, `denyWrite: ['./sub']`, `denyRead: ['./gauntlet/failed']`, `denyWrite: ['**/sub']` or `denyRead: ['**/gauntlet/failed']` confines anything. Writes to the root and to `sub/` landed on disk in every run, and `cat gauntlet/failed/x.txt` printed `secret`. `archon validate workflows` printed `ok` for each form, with no warning. In the `./` run the sandbox was engaged: it printed `zsh:1: read-only file system: /tmp/claude-1000/cwd-605d`.

Together with P4, this means `sandbox:` confines only absolute literal paths. A workflow that runs in any checkout cannot name that checkout in its sandbox.
