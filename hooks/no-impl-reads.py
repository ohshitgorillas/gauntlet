#!/usr/bin/env python3
"""PreToolUse hook: keep a blind agent out of the implementation.

Wired session-wide from `.claude/settings.json`, and gated on the caller. A
plugin-shipped agent definition runs no `hooks:` frontmatter of its own, so
frontmatter wiring reaches nothing once the kit ships as a plugin; session
wiring is the only wiring a packaged hook has.

Session-wide is not session-blind. `agent_type` is present in the payload only
for subagent calls, so an absent key is the main agent, which passes untouched
-- it has to read the code to adjudicate a failing test. A caller not in
`BLIND` passes the same way, unjudged, so nothing outside the four blind agents
is read-blocked by this hook.

The fail direction is the price of that guard, and it is the opposite of the
lane hook's. `lanes.py` answers an absent `agent_type` by over-denying,
which leaks nothing. Here an absent key must pass, because the main agent is
itself the caller that carries none, so a build that stopped supplying the key
for subagents would hand the blind agents the implementation rather than deny
them their spec. Guarding by caller identity buys packaging and cannot fail
closed; guarding by wiring scope failed closed and does not survive packaging.

The rule the four work under is that a spec is judged, and a test written,
from the behavior contract and never from the code under test. A test shaped
against the implementation mirrors it, and goes green on an implementation
that is wrong in exactly the way the main agent was wrong. A prompt alone does not
enforce that: the agent that must not peek is the same agent deciding whether
it peeked.

**This hook is an allowlist, not a blocklist.** A blind agent may read the
spec's own sources and nothing else. That is the portable direction — a
blocklist has to know what this repo calls its source directory, and gets it
wrong the first time someone adds one — and it fails closed: an unlisted path
is denied, and the denial names the file to widen.

Allowed by default: the blind writer's own lane, `docs/testing.md`, the three
re-allowed leaves under the gauntlet base, the declaration itself, and
documentation files at the repo root (`*.md`, `*.txt`, `*.pdf`). Every entry is
either a directory only a protected writer fills or the one policy file these
agents are held to. The prose directory as a whole is not one: a project keeps
design notes there, and a design note quotes the code it describes. Neither is
`state/`, which holds gate output, and gate output is the implementation's own
tracebacks under another name.

The kit's own `docs/` is on the list too, at `${CLAUDE_PLUGIN_ROOT}/docs/`, and
it is the one allowed path that sits outside the checkout. The kit cites its own
prose there — the plan shape, the spec-gate rules, the roster — so a consumer
installs the plugin and holds only `docs/testing.md`, which is genuinely its own
policy, rather than a copy of the kit's prose kept in step by hand. A citation a
blind agent cannot follow is a rule it does not hold, so the allowlist reaches
that directory and nothing else beside it: `${CLAUDE_PLUGIN_ROOT}/hooks/` and
`${CLAUDE_PLUGIN_ROOT}/scripts/` are the kit's implementation and stay denied.
The variable is expanded where it appears in a path, because the citation is
written that way and an agent following it literally reads a path that resolves
nowhere.

`gauntlet/` is a base of its own at the repo root, and it is a denial, not a
widening. Everything the gauntlet's agents write lives there, and three of the
four kinds quote implementation citations: an approved plan resolves
`file:line` into the source, a draft does so unreviewed, and a reviewer round
quotes the plan back. So the base is denied entire, with three leaves re-allowed
inside it: `gauntlet/specs/approved/`, the approved spec block a blind agent
works from; `gauntlet/red/`, the red run a blind writer must certify; and
`gauntlet/merge/`, the evidence the bailiff is spawned to read. Denying those
two moved the certification to the main agent, which is the inversion this hook
exists to prevent. No denied subtree nests inside an allowed one: `docs/`,
`tests/` and `state/` are allowed the whole way down, and the three re-allowed
leaves sit inside the denied base, which is the harmless direction. Both tests
run before the allow list below, so a fifth artifact
directory added later is blind-safe until someone deliberately opens it, and no
`blind-reads.json` entry can re-open the plans, the drafts or the rounds.

The list is not configurable. What `blind-reads.json` moves is
where the entries point, never which entries there are: `tests_dir` is the
blind writer's lane, `docs_dir` the prose, and `gauntlet_dir` the base whose
`specs/approved` subtree is the one artifact a blind agent works from. All
three are read through `shell_shapes`, which refuses any set of names that
overlap, so no value here can put the lane over the prose or the base under
either. The file itself is on the list too, because a blind agent's definition
names those directories only as `<tests dir>` and `<docs dir>` and this is
where the names resolve. A spec source that lives elsewhere belongs under the
docs directory or beside the block in the approved-specs lane, not on a list
that could grow to reach the implementation.

No shell command is judged here. This hook read one once -- stages, `cd`
targets, runner invocations, git forms -- and that reading is gone with every
other command parse in the kit. A blind agent's shell is `blind-bash.py`'s one
entry point, `scripts/blind.sh`, which admits three invocations by name; every
other caller's shell runs inside the wrap `bwrap-wrap.py` builds. What is left
here is the three tools that reach a file without a shell.

Blocked for those agents:

  * `Read` of any path outside the allowlist
  * `Grep`/`Glob` rooted outside it, and `Grep`/`Glob` with no path at all
    (an unrooted search sweeps the tree and prints matching source lines)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shell_shapes as sh  # noqa: E402

#: the agents this hook answers for. Every other caller, the main agent
#: included, passes unjudged -- see the fail direction in the module docstring
BLIND = (
    "arbiter",
    "scrivener",
    "juror",
    "bailiff",
)

#: the blind writer's lane, `tests` unless `blind-reads.json` names another
TESTS = sh.tests_dir()
#: the prose a blind agent may read, `docs` unless the file names another
DOCS = sh.docs_dir()
#: the one file that says where those are, readable by a blind agent whose
#: definition names them as `<tests dir>` and `<docs dir>` and nothing more concrete
CONFIG = ".claude/blind-reads.json"
#: the variable the kit's citations are written with, expanded before a path is
#: scored so a citation followed literally reaches the file it names
PLUGIN_VAR = "CLAUDE_PLUGIN_ROOT"


def _plugin_root() -> str:
    """Where the kit is installed.

    The harness sets `CLAUDE_PLUGIN_ROOT` for a hook it launches from a plugin
    manifest. The hook's own location is the fallback, for a run that carries no
    environment -- a self-test, or a checkout wired by hand -- and both name the
    same directory, so neither spelling is the privileged one.
    """
    return os.path.abspath(os.environ.get(PLUGIN_VAR) or str(Path(__file__).resolve().parents[1]))  # noqa: PTH100


#: the kit's own prose, the one allowed path outside the checkout. Its siblings
#: -- `hooks/`, `scripts/`, `agents/` -- are the kit's implementation and are not
#: on the list, so the entry is the `docs` directory and never the plugin root
PLUGIN_ROOT = _plugin_root()
PLUGIN_DOCS = os.path.join(PLUGIN_ROOT, "docs")  # noqa: PTH118
#: the gauntlet's own artifact base at the repo root, denied entire
GAUNTLET_BASE = sh.gauntlet_dir()
#: the one subtree of it a blind agent works from: the approved spec block
GAUNTLET_SPECS = sh.specs_lane()
#: the chain's own run artifacts under that base: the red run a blind writer
#: certifies, and the merge evidence the bailiff reads
GAUNTLET_RED = GAUNTLET_BASE + "/red"
GAUNTLET_MERGE = GAUNTLET_BASE + "/merge"
#: every leaf re-allowed inside the denied base, and the whole of what is
#: readable under it
GAUNTLET_LEAVES = (GAUNTLET_SPECS, GAUNTLET_RED, GAUNTLET_MERGE)
#: repo-relative paths a blind agent may read; a trailing `/` means the subtree.
#: Each one is a directory only a protected writer fills, or a named file: the
#: test lane the blind writer owns, the test policy it is held to, the two run
#: artifacts it certifies, the approved block it works from, and the declaration
#: that says where those are. A directory anyone may write is not on it, which
#: is why the prose directory is here as one file rather than as a subtree.
DEFAULT_ALLOW = (
    DOCS + "/testing.md",
    TESTS + "/",
    GAUNTLET_SPECS + "/",
    GAUNTLET_RED + "/",
    GAUNTLET_MERGE + "/",
    CONFIG,
)
#: repo-root files a blind agent may read, by extension
DEFAULT_ROOT_FILES = (".md", ".txt", ".pdf")

_WHY = (
    "Blind agent: the implementation is out of bounds. Work from the approved spec "
    f"block at {GAUNTLET_SPECS}/, {DOCS}/testing.md, {TESTS}/, and the kit's own prose "
    f"at ${{{PLUGIN_VAR}}}/docs/. If the spec does "
    "not say what the behavior is, report that gap instead of reading the code to "
    f"find out. If this path is genuinely a spec source, it belongs in "
    f"{GAUNTLET_SPECS}/, which is the only part of {GAUNTLET_BASE}/ that is yours: the "
    "plans, the drafts and the reviewer rounds quote implementation citations, and "
    "no list reaches them. (hooks/no-impl-reads.py)"
)
_UNROOTED = (
    f"Give Grep/Glob an explicit path ({TESTS}/, {DOCS}/, {GAUNTLET_SPECS}/): an "
    "unrooted search sweeps the whole tree and prints its source. " + _WHY
)


def repo_root(start: str) -> str | None:
    #: lexical, not `Path.resolve()`: resolving follows symlinks, and a checkout
    #: reached through a symlinked path would answer with a root the session
    #: never named
    path = os.path.abspath(start or ".")  # noqa: PTH100
    while True:
        if Path(path, ".git").exists():
            return path
        parent = str(Path(path).parent)
        if parent == path:
            return None
        path = parent


def _under(rel: str, name: str) -> bool:
    """Is this repo-relative path that directory, or something inside it?

    The bare directory counts. A test that only asks whether the path starts
    with the directory plus a separator misses `Grep` rooted at the directory
    itself, which is the one search that returns everything in it.
    """
    prefix = name.replace("/", os.sep)
    return rel == prefix or rel.startswith(prefix + os.sep)


def readable(target: str, root: str | None, cwd: str) -> bool:
    """Is this path one of the spec's own sources?

    An allowlist entry is anchored: `docs/` is the repository's own `docs`,
    not any directory called `docs` at any depth. Matching at depth reads
    `src/docs/impl.py` as documentation, which hands the blind agent the
    implementation under a directory name it does not control.

    Outside a checkout there is no repo-relative path to test, so the path is
    anchored at the filesystem root instead and almost nothing is readable.
    Failing closed there is the point: a blind agent in an unknown tree stays
    blind.
    """
    if not target:
        return True
    #: the kit writes its citations with the variable in them, so expand it
    #: before anything is scored. Only this one name, and only to the directory
    #: the manifest already points every hook command at
    target = target.replace("${" + PLUGIN_VAR + "}", PLUGIN_ROOT).replace(
        "$" + PLUGIN_VAR, PLUGIN_ROOT
    )
    #: lexical again: the `..` collapse is the whole job here, and
    #: `Path.resolve()` would follow a symlink out of the lane the allowlist
    #: anchors on
    resolved = os.path.abspath(os.path.join(cwd or (root or "."), target))  # noqa: PTH100, PTH118
    #: the kit's own prose, judged absolute and ahead of the repo-relative work
    #: below. It has to be: the plugin is installed outside the checkout, so
    #: `os.path.relpath` against the repo root answers with a `..` path and the
    #: allowlist never sees it. The test is anchored at `docs` and not at the
    #: plugin root, so the kit's hooks, scripts and agent definitions stay denied
    if resolved == PLUGIN_DOCS or resolved.startswith(PLUGIN_DOCS + os.sep):
        return True
    #: a path inside `.claude/worktrees/<slug>` is anchored at that worktree, not
    #: at the checkout the session was started in. A blind agent is handed the
    #: absolute paths of files in its own worktree, and against the session root
    #: every one of them reads as `.claude/worktrees/<slug>/tests/...` — outside
    #: the allowlist — so its own spec block and its own tests were denied to it.
    #: `shell_shapes.root_by_name` is the rule the three lane hooks already use;
    #: this hook carried a private `repo_root` that did not know a worktree.
    base = sh.root_by_name(resolved) or root
    if base:
        rel = os.path.relpath(resolved, base)
        if rel.startswith(".."):
            return False
    else:
        rel = resolved.lstrip(os.sep)
    #: the gauntlet's own base, in the one order that works. The re-allowed
    #: leaves are tested first and are readable; the base is tested second and is
    #: denied; the
    #: allow list runs last. Reversing the first two refuses the blind writer the
    #: block it is spawned against, and putting either behind the allow list lets
    #: a `blind-reads.json` entry hand over the plans, the drafts and the rounds,
    #: every one of which carries implementation citations. The matching
    #: `DEFAULT_ALLOW` entry is therefore unreachable here, and is kept because
    #: the invariant self-test computes over that list: it is what makes the
    #: deliberate leaf visible to the case, which catches a later hand that
    #: rebases one of the two without the other.
    if any(_under(rel, leaf) for leaf in GAUNTLET_LEAVES):
        return True
    if _under(rel, GAUNTLET_BASE):
        return False
    #: the allowlist runs next: `tests` is the allowed directory itself, not a
    #: root file that happens to carry no extension
    for entry in DEFAULT_ALLOW:
        name = entry.rstrip("/").replace("/", os.sep)
        if entry.endswith("/"):
            if rel == name or rel.startswith(name + os.sep):
                return True
        elif rel == name:
            return True
    #: a documentation file sitting at the repo root, by extension
    return (
        base is not None and os.sep not in rel and (Path(rel).suffix.lower() in DEFAULT_ROOT_FILES)
    )


def _verdict(name: str, tool_input: dict[str, Any], root: str | None, cwd: str) -> str | None:
    """Why this call is refused, or None to let it through."""
    if name == "Read":
        return None if readable(tool_input.get("file_path", ""), root, cwd) else _WHY
    if name in ("Grep", "Glob"):
        target = tool_input.get("path")
        if target is None:
            return _UNROOTED
        return None if readable(target, root, cwd) else _WHY
    return None


#: the tools this hook decides. A call of anything else is not its subject,
#: and a malformed one is not its refusal to give -- see `sh.payload_fault`.
GUARDS = ("Read", "Grep", "Glob")


def _caller_verdict(
    name: str,
    tool_input: dict[str, Any],
    payload: dict[str, Any],
    root: str | None,
    cwd: str,
) -> str | None:
    """Why this call is refused, or None to let it through, judged by caller.

    Session wiring puts every agent's reads in front of this hook, so the
    allowlist below runs for the four blind agents and for nobody else. An
    absent `agent_type` is the main agent and passes; a name not in `BLIND`
    passes too, unjudged rather than allowlisted.
    """
    if sh.agent_of(payload) not in BLIND:
        return None
    return _verdict(name, tool_input, root, cwd)


def main() -> None:
    def verdict(name: str, tool_input: dict[str, Any], payload: dict[str, Any]) -> str | None:
        #: inside the closure, so that a root that will not resolve is a
        #: refusal like any other rather than a crash read as one
        cwd = sh.cwd_of(payload)
        return _caller_verdict(name, tool_input, payload, repo_root(cwd), cwd)

    sh.hook_main(verdict, guards=GUARDS)


def _config_parses() -> bool:
    """That the per-repo config this hook names reads, where there is one.

    `sh.config` answers a malformed file with an empty config, and that is the
    right answer at the gate: an empty config names no lane, so the lane is
    `tests`. It is also silent, so a typo in the file moves a repo's lane back
    to the default and says nothing about it. The runtime keeps the safe
    direction; this line is where the typo becomes visible instead of free.
    """
    path = Path(__file__).resolve().parents[1] / CONFIG
    if not path.exists():
        return True  # no per-repo value here; nothing to parse
    try:
        with path.open(encoding="utf-8") as fh:
            return isinstance(json.load(fh), dict)
    except (OSError, ValueError):
        return False


def _no_denied_nesting() -> bool:
    """Is every allowed root free of a denied subtree beneath it?

    The invariant the layout exists to hold, computed rather than asserted by
    hand: a denied tree inside an allowed one is readable by a sweep rooted at
    the ancestor while its contents are denied one by one, which is the hole
    the `docs/gauntlet/` nesting opened. The other direction — the re-allowed
    leaf inside the denied base — is harmless and is excluded here.

    `DEFAULT_ALLOW` carries the directories the real `blind-reads.json`
    names, so a repo whose `tests_dir` or `docs_dir` resolved to the
    artifact base or an ancestor of it would fail this case rather than silently
    re-open the base, were `shell_shapes.dirs_from` not already refusing every
    overlapping set.
    """
    for entry in DEFAULT_ALLOW:
        root = entry.rstrip("/")
        if not root:
            continue
        #: the denied base sits at or under this allowed root
        if _under(GAUNTLET_BASE, root):
            return False
        #: the root sits inside the denied base, on a branch that is not the
        #: one re-allowed leaf, so everything it names is denied to a read
        if _under(root, GAUNTLET_BASE) and not any(_under(root, leaf) for leaf in GAUNTLET_LEAVES):
            return False
    return True


def _plugin_docs_case(root: str) -> bool:
    """That a blind agent can follow a citation into the installed kit, and no further.

    Run against a plugin root of its own rather than this checkout's, because the
    two coincide here and a test that cannot tell them apart pins nothing: in a
    consumer's tree the kit sits somewhere else entirely, and that is the layout
    the entry exists for.

    Both directions are the case. The citation resolves, spelled absolute or with
    the variable the kit writes it with, and the plugin's siblings do not -- the
    hooks and the scripts beside that `docs/` are the implementation, and reading
    them is the thing this hook is for. `respell` is left off deliberately: the
    kit's own directory is named by the kit, and no `blind-reads.json` value
    moves it.
    """
    global PLUGIN_ROOT, PLUGIN_DOCS  # noqa: PLW0603
    keep_root, keep_docs = PLUGIN_ROOT, PLUGIN_DOCS
    PLUGIN_ROOT = "/opt/plugins/gauntlet"
    PLUGIN_DOCS = PLUGIN_ROOT + "/docs"
    try:

        def read(path: str) -> str | None:
            return _verdict("Read", {"file_path": path}, root, root)

        return all(
            (
                sh.allowed(read(f"{PLUGIN_ROOT}/docs/plans.md")),
                sh.allowed(read(f"{PLUGIN_ROOT}/docs/approved-specs.md")),
                sh.allowed(read(f"{PLUGIN_ROOT}/docs/agents.md")),
                sh.allowed(read("${CLAUDE_PLUGIN_ROOT}/docs/plans.md")),
                sh.allowed(read("$CLAUDE_PLUGIN_ROOT/docs/approved-specs.md")),
                sh.allowed(
                    _verdict("Grep", {"pattern": "x", "path": f"{PLUGIN_ROOT}/docs"}, root, root)
                ),
                #: the kit's implementation sits beside its prose and is not on
                #: the list
                sh.denied(read(f"{PLUGIN_ROOT}/hooks/no-impl-reads.py")),
                sh.denied(read(f"{PLUGIN_ROOT}/scripts/pair.sh")),
                sh.denied(read(f"{PLUGIN_ROOT}/agents/scrivener.md")),
                sh.denied(read("${CLAUDE_PLUGIN_ROOT}/hooks/no-impl-reads.py")),
                sh.denied(_verdict("Grep", {"pattern": "x", "path": PLUGIN_ROOT}, root, root)),
                #: a path boundary, not a string prefix
                sh.denied(read(f"{PLUGIN_ROOT}/docs-old/plans.md")),
                #: and the variable buys no way back out of the directory
                sh.denied(read("${CLAUDE_PLUGIN_ROOT}/docs/../hooks/no-impl-reads.py")),
            )
        )
    finally:
        PLUGIN_ROOT, PLUGIN_DOCS = keep_root, keep_docs


def self_test() -> int:
    """Pin the spec lines of the blind-read allowlist."""
    root = "/repo"
    tree = f"{root}/.claude/worktrees/demo-spec"

    #: the lines below spell the kit's defaults; under a project that moved one
    #: of the three directories, the same lines run at that project's own. The
    #: respelling sits here rather than on `read` and `bash`, so the payloads
    #: built by hand below carry it too, and no string gets two passes
    PATHS = ("file_path", "path", "command")

    def call(tool: str, tool_input: dict[str, Any]) -> str | None:
        moved = {
            key: sh.respell(value) if key in PATHS and isinstance(value, str) else value
            for key, value in tool_input.items()
        }
        return _verdict(tool, moved, root, root)

    def read(path: str) -> str | None:
        return call("Read", {"file_path": path})

    denied, allowed = sh.denied, sh.allowed

    def blind(path: str, who: str | None = "scrivener") -> str | None:
        """One `Read`, through the caller gate the wire goes through.

        `who` is the payload's `agent_type`; `None` leaves the key off, which
        is the shape a call from no subagent carries.
        """
        payload: dict[str, Any] = {}
        if who is not None:
            payload["agent_type"] = who
        return _caller_verdict("Read", {"file_path": sh.respell(path)}, payload, root, root)
    lines = {
        "1 the spec's own sources are readable, the rest is not": all(
            (
                allowed(read(f"{root}/docs/testing.md")),
                allowed(read(f"{root}/tests/test_lane.py")),
                allowed(read(f"{root}/gauntlet/specs/approved/slug.txt")),
                allowed(read(f"{root}/README.md")),
                denied(read(f"{root}/src/core/manager.py")),
                denied(read(f"{root}/app/main.py")),
                denied(read("/etc/passwd")),
            )
        ),
        "2 an unrooted search is denied, a rooted one follows the allowlist": all(
            (
                denied(call("Grep", {"pattern": "def resolve"})),
                denied(call("Glob", {"pattern": "**/*.py"})),
                allowed(call("Grep", {"pattern": "def test_", "path": f"{root}/tests"})),
                denied(call("Grep", {"pattern": "def resolve", "path": f"{root}/src"})),
            )
        ),
        "6 an allowlisted directory name counts at the root and nowhere else": all(
            (
                denied(read(f"{root}/src/docs/impl.py")),
                denied(read(f"{root}/src/tests/impl.py")),
                denied(call("Grep", {"pattern": "x", "path": f"{root}/src/specs"})),
                allowed(read(f"{root}/docs/testing.md")),
                allowed(read(f"{root}/tests/test_lane.py")),
            )
        ),
        "7 a blind agent's own worktree is anchored at that worktree": all(
            (
                allowed(read(f"{tree}/gauntlet/specs/approved/demo.txt")),
                allowed(read(f"{tree}/tests/test_demo.py")),
                allowed(call("Grep", {"pattern": "x", "path": f"{tree}/tests"})),
                #: the worktree carries its own copy of these, and neither is a
                #: spec source in either tree
                denied(read(f"{tree}/src/core/manager.py")),
                denied(read(f"{tree}/hooks/no-impl-reads.py")),
            )
        ),
        "8 the chain's own run artifacts are readable, so the writer certifies its run": all(
            (
                allowed(read(f"{root}/gauntlet/red/demo.txt")),
                allowed(read(f"{root}/gauntlet/merge/demo.txt")),
                denied(read(f"{root}/src/state/manager.py")),
            )
        ),
        "9 the gauntlet's base is denied, three leaves re-allowed": all(
            (
                allowed(read(f"{root}/gauntlet/specs/approved/demo.txt")),
                allowed(read(f"{root}/gauntlet/red/demo.txt")),
                allowed(read(f"{root}/gauntlet/merge/demo.txt")),
                allowed(call("Grep", {"pattern": "x", "path": f"{root}/gauntlet/red"})),
                allowed(call("Grep", {"pattern": "x", "path": f"{root}/gauntlet/merge"})),
                denied(read(f"{root}/gauntlet/plans/approved/demo.txt")),
                denied(read(f"{root}/gauntlet/reviews/demo.plan.4.txt")),
                denied(read(f"{root}/gauntlet/plans/drafts/demo.txt")),
                denied(read(f"{root}/gauntlet/specs/drafts/demo.txt")),
                #: the bare directory is the one search that returns everything
                #: in it, and it is not `<dir>/` + something
                denied(call("Grep", {"pattern": "x", "path": f"{root}/gauntlet"})),
                denied(call("Grep", {"pattern": "x", "path": f"{root}/gauntlet/plans/approved"})),
                allowed(call("Grep", {"pattern": "x", "path": f"{root}/gauntlet/specs/approved"})),
                #: the leaf is the approved directory, not the stage above it:
                #: the drafts sit beside it under the same parent
                denied(call("Grep", {"pattern": "x", "path": f"{root}/gauntlet/specs"})),
                denied(call("Grep", {"pattern": "x", "path": f"{root}/gauntlet/specs/drafts"})),
                #: a path boundary, not a string prefix
                allowed(read(f"{root}/gauntlet/specs/approved/sub/x.txt")),
                denied(read(f"{root}/gauntlet/specs/approved-old/x.txt")),
                #: the test policy is untouched, and so is the same name nested
                #: under the source tree
                allowed(read(f"{root}/docs/testing.md")),
                denied(read(f"{root}/src/gauntlet/specs/approved/demo.txt")),
            )
        ),
        "10 no blind-reads.json value re-opens the base or overlaps another": all(
            (
                #: a usable set moves all three, which is the point of the file
                sh.dirs_from({"tests_dir": "spec", "gauntlet_dir": "work", "docs_dir": "prose"})
                == {"tests_dir": "spec", "gauntlet_dir": "work", "docs_dir": "prose"},
                #: and every unusable one moves nothing at all, together: a name
                #: at, under or over another would put one directory's hook over
                #: the other's, and a partly honoured set is the hole itself
                sh.dirs_from({"tests_dir": "gauntlet"}) == dict(sh.DEFAULT_DIRS),
                sh.dirs_from({"tests_dir": "gauntlet/plans/approved"}) == dict(sh.DEFAULT_DIRS),
                sh.dirs_from({"gauntlet_dir": "tests"}) == dict(sh.DEFAULT_DIRS),
                sh.dirs_from({"gauntlet_dir": "tests/artifacts"}) == dict(sh.DEFAULT_DIRS),
                #: a key the file omits still collides: `tests_dir` at `docs` is
                #: legal read alone and sits over the default `docs_dir`
                sh.dirs_from({"tests_dir": "docs"}) == dict(sh.DEFAULT_DIRS),
                sh.dirs_from({"docs_dir": "spec", "tests_dir": "spec"}) == dict(sh.DEFAULT_DIRS),
                #: judged by where a name lands, not by how it is spelled
                sh.dirs_from({"tests_dir": "spec/../gauntlet/reviews"}) == dict(sh.DEFAULT_DIRS),
                sh.dirs_from({"tests_dir": "."}) == dict(sh.DEFAULT_DIRS),
                sh.dirs_from({"gauntlet_dir": "/repo/work"}) == dict(sh.DEFAULT_DIRS),
                sh.dirs_from({"docs_dir": ["prose"]}) == dict(sh.DEFAULT_DIRS),
                #: there is no allow key: a path off the table stays off it
                denied(read(f"{root}/reference/protocol.md")),
            )
        ),
        "11 the four blind agents are judged, and no other caller is": all(
            (
                #: the allowlist runs for a caller in BLIND, in both directions
                denied(blind(f"{root}/src/core/manager.py")),
                allowed(blind(f"{root}/docs/testing.md")),
                denied(blind(f"{root}/src/core/manager.py", "juror")),
                denied(blind(f"{root}/src/core/manager.py", "arbiter")),
                denied(blind(f"{root}/src/core/manager.py", "bailiff")),
                #: the main agent carries no `agent_type` at all, and session
                #: wiring puts its every read here: it passes unjudged
                allowed(blind(f"{root}/src/core/manager.py", None)),
                #: and so does a caller this hook does not answer for, rather
                #: than being read-blocked by a list that is not about it
                allowed(blind(f"{root}/src/core/manager.py", "prosecutor")),
                allowed(blind(f"{root}/src/core/manager.py", "examiner")),
                allowed(blind(f"{root}/src/core/manager.py", "general-purpose")),
                #: an empty string is no name, and reads as the main agent
                allowed(blind(f"{root}/src/core/manager.py", "")),
                #: installed as a plugin the harness spells the name with its
                #: plugin in front of it, and that is the same agent
                denied(blind(f"{root}/src/core/manager.py", "gauntlet:scrivener")),
                allowed(blind(f"{root}/docs/testing.md", "gauntlet:scrivener")),
                denied(blind(f"{root}/src/core/manager.py", "gauntlet:juror")),
                denied(blind(f"{root}/src/core/manager.py", "gauntlet:arbiter")),
                denied(blind(f"{root}/src/core/manager.py", "gauntlet:bailiff")),
                allowed(blind(f"{root}/src/core/manager.py", "gauntlet:prosecutor")),
            )
        ),
        "12 the kit's own docs/ is readable, the rest of the plugin is not": _plugin_docs_case(
            root
        ),
        "13 no denied subtree nests inside an allowed one": _no_denied_nesting(),
        "14 this repo's own blind-reads.json parses, if it is there": _config_parses(),
        "15 the prose directory is one file, and gate output is not readable": all(
            (
                #: the one policy file these agents are held to, and not the
                #: directory around it: a design note there quotes the code it
                #: describes
                allowed(read(f"{root}/docs/testing.md")),
                denied(read(f"{root}/docs/plans.md")),
                denied(call("Grep", {"pattern": "x", "path": f"{root}/docs"})),
                #: the entry is that file, not a prefix of its name
                denied(read(f"{root}/docs/testing.md.bak")),
                #: gate output is the implementation's own tracebacks under
                #: another name
                denied(read(f"{root}/state/gates/pytest.txt")),
                denied(call("Grep", {"pattern": "x", "path": f"{root}/state"})),
                #: what stays on the list beside that file: the lane the blind
                #: writer owns and the two run artifacts it certifies
                allowed(read(f"{root}/tests/test_lane.py")),
                allowed(read(f"{root}/gauntlet/red/demo.txt")),
                allowed(read(f"{root}/gauntlet/merge/demo.txt")),
            )
        ),
        #: a hook decides a tool call, so its own crash is a denial -- and a
        #: payload it cannot read is a call it cannot decide, which is a refusal
        "every payload shape is answered, and an unreadable one is refused": (
            sh.survives_hostile_payloads(__file__, guards=GUARDS)
        ),
    }
    return sh.report(lines)


if __name__ == "__main__":
    sh.entry(self_test, main)
