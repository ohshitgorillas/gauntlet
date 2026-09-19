#!/usr/bin/env python3
"""The self-test of `no-impl-reads.py`: its spec lines and the three cases only they use.

`python3 hooks/no-impl-reads.py --self-test` runs it, importing this module from
its own `--self-test` branch; nothing else here is wired to anything.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hook_payload  # noqa: E402
import hook_shape  # noqa: E402
import lane_config  # noqa: E402


def _hook_module() -> Any:
    """The hook these lines judge, however the run reached them.

    `no-impl-reads.py` carries a hyphen and is not importable by name. Started
    at its own entry point it is already `__main__`, and that instance is the
    one to judge, so the globals `_plugin_docs_case` moves are the ones the run
    is scoring; reached any other way the file is loaded from beside this one.
    """
    running = sys.modules.get("__main__")
    if str(getattr(running, "__file__", "")).endswith("no-impl-reads.py"):
        return running
    path = Path(__file__).resolve().parent / "no-impl-reads.py"
    spec = importlib.util.spec_from_file_location("no_impl_reads", path)
    if spec is None or spec.loader is None:  # pragma: no cover - a broken checkout
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["no_impl_reads"] = module
    spec.loader.exec_module(module)
    return module


impl = _hook_module()


def _config_parses() -> bool:
    """That the per-repo config this hook names reads, where there is one.

    `lane_config.config` answers a malformed file with an empty config, and that is the
    right answer at the gate: an empty config names no lane, so the lane is
    `tests`. It is also silent, so a typo in the file moves a repo's lane back
    to the default and says nothing about it. The runtime keeps the safe
    direction; this line is where the typo becomes visible instead of free.
    """
    path = Path(__file__).resolve().parents[1] / impl.CONFIG
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
    re-open the base, were `lane_config.dirs_from` not already refusing every
    overlapping set.
    """
    for entry in impl.DEFAULT_ALLOW:
        root = entry.rstrip("/")
        if not root:
            continue
        #: the denied base sits at or under this allowed root
        if impl._under(impl.GAUNTLET_BASE, root):
            return False
        #: the root sits inside the denied base, on a branch that is not the
        #: one re-allowed leaf, so everything it names is denied to a read
        if impl._under(root, impl.GAUNTLET_BASE) and not any(
            impl._under(root, leaf) for leaf in impl.GAUNTLET_LEAVES
        ):
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
    keep_root, keep_docs = impl.PLUGIN_ROOT, impl.PLUGIN_DOCS
    plugin_root = "/opt/plugins/gauntlet"
    impl.PLUGIN_ROOT = plugin_root
    impl.PLUGIN_DOCS = plugin_root + "/docs"
    try:

        def read(path: str) -> str | None:
            said: str | None = impl._verdict("Read", {"file_path": path}, root, root)
            return said

        return all(
            (
                hook_shape.allowed(read(f"{plugin_root}/docs/plans.md")),
                hook_shape.allowed(read(f"{plugin_root}/docs/approved-specs.md")),
                hook_shape.allowed(read(f"{plugin_root}/docs/agents.md")),
                hook_shape.allowed(read("${CLAUDE_PLUGIN_ROOT}/docs/plans.md")),
                hook_shape.allowed(read("$CLAUDE_PLUGIN_ROOT/docs/approved-specs.md")),
                hook_shape.allowed(
                    impl._verdict(
                        "Grep", {"pattern": "x", "path": f"{plugin_root}/docs"}, root, root
                    )
                ),
                #: the kit's implementation sits beside its prose and is not on
                #: the list
                hook_shape.denied(read(f"{plugin_root}/hooks/no-impl-reads.py")),
                hook_shape.denied(read(f"{plugin_root}/scripts/pair.sh")),
                hook_shape.denied(read(f"{plugin_root}/agents/scrivener.md")),
                hook_shape.denied(read("${CLAUDE_PLUGIN_ROOT}/hooks/no-impl-reads.py")),
                hook_shape.denied(
                    impl._verdict("Grep", {"pattern": "x", "path": plugin_root}, root, root)
                ),
                #: a path boundary, not a string prefix
                hook_shape.denied(read(f"{plugin_root}/docs-old/plans.md")),
                #: and the variable buys no way back out of the directory
                hook_shape.denied(read("${CLAUDE_PLUGIN_ROOT}/docs/../hooks/no-impl-reads.py")),
            )
        )
    finally:
        impl.PLUGIN_ROOT, impl.PLUGIN_DOCS = keep_root, keep_docs


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
            key: hook_shape.respell(value) if key in PATHS and isinstance(value, str) else value
            for key, value in tool_input.items()
        }
        said: str | None = impl._verdict(tool, moved, root, root)
        return said

    def read(path: str) -> str | None:
        return call("Read", {"file_path": path})

    denied, allowed = hook_shape.denied, hook_shape.allowed

    def blind(path: str, who: str | None = "scrivener") -> str | None:
        """One `Read`, through the caller gate the wire goes through.

        `who` is the payload's `agent_type`; `None` leaves the key off, which
        is the shape a call from no subagent carries.
        """
        payload: dict[str, Any] = {}
        if who is not None:
            payload["agent_type"] = who
        said: str | None = impl._caller_verdict(
            "Read", {"file_path": hook_shape.respell(path)}, payload, root, root
        )
        return said

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
                lane_config.dirs_from(
                    {"tests_dir": "spec", "gauntlet_dir": "work", "docs_dir": "prose"}
                )
                == {"tests_dir": "spec", "gauntlet_dir": "work", "docs_dir": "prose"},
                #: and every unusable one moves nothing at all, together: a name
                #: at, under or over another would put one directory's hook over
                #: the other's, and a partly honoured set is the hole itself
                lane_config.dirs_from({"tests_dir": "gauntlet"}) == dict(lane_config.DEFAULT_DIRS),
                lane_config.dirs_from({"tests_dir": "gauntlet/plans/approved"})
                == dict(lane_config.DEFAULT_DIRS),
                lane_config.dirs_from({"gauntlet_dir": "tests"}) == dict(lane_config.DEFAULT_DIRS),
                lane_config.dirs_from({"gauntlet_dir": "tests/artifacts"})
                == dict(lane_config.DEFAULT_DIRS),
                #: a key the file omits still collides: `tests_dir` at `docs` is
                #: legal read alone and sits over the default `docs_dir`
                lane_config.dirs_from({"tests_dir": "docs"}) == dict(lane_config.DEFAULT_DIRS),
                lane_config.dirs_from({"docs_dir": "spec", "tests_dir": "spec"})
                == dict(lane_config.DEFAULT_DIRS),
                #: judged by where a name lands, not by how it is spelled
                lane_config.dirs_from({"tests_dir": "spec/../gauntlet/reviews"})
                == dict(lane_config.DEFAULT_DIRS),
                lane_config.dirs_from({"tests_dir": "."}) == dict(lane_config.DEFAULT_DIRS),
                lane_config.dirs_from({"gauntlet_dir": "/repo/work"})
                == dict(lane_config.DEFAULT_DIRS),
                lane_config.dirs_from({"docs_dir": ["prose"]}) == dict(lane_config.DEFAULT_DIRS),
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
            hook_payload.survives_hostile_payloads(impl.__file__, guards=impl.GUARDS)
        ),
    }
    return hook_shape.report(lines)
