#!/usr/bin/env python3
"""PreToolUse hook: keep a blind agent out of the implementation.

Wired from the `hooks:` frontmatter of `.claude/agents/gauntlet-arbiter.md` and
`.claude/agents/gauntlet-testsmith.md`, so it binds those subagents only. The
main agent and every other agent are untouched, deliberately: a session-wide
`permissions.deny` would blind the one agent that has to read the code to
adjudicate a failing test.

The rule those two work under is that a spec is judged, and a test written,
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

Allowed by default: `docs/`, `tests/`, `specs/`, `state/`, and documentation
files at the repo root (`*.md`, `*.txt`, `*.pdf`). `state/` is the workflow's
own output, never the repository's source: it holds the red run a blind writer
must certify and the reviewer rounds a blind reviewer writes. Denying it moved
the certification to the main agent, which is the inversion this hook exists
to prevent. Extend the list per repo with `blind-reads.json` beside this file:

    {"allow": ["reference/", "vendor/protocol.h"], "runners": ["pytest", "make"]}

`allow` entries are repo-relative paths anchored at the repo root, a trailing
`/` meaning the directory and everything under it. A name matches there and
nowhere else: `docs/` is this repository's `docs`, never `src/docs`.

`runners` are the names of this repo's own suite commands, accepted with any
arguments — a traceback through the code is the cost of running the suite at
all, and running the suite is the point. The common runners need no entry:
`shell_shapes.is_runner` recognizes them by their whole invocation, which is
the only way to tell `node --test` from `node -e`. An inline-script flag
(`-e`, `-c`, `-p`, `--eval`, `--print`) disqualifies any command, configured
name included.

Blocked for those agents:

  * `Read` of any path outside the allowlist
  * `Grep`/`Glob` rooted outside it, and `Grep`/`Glob` with no path at all
    (an unrooted search sweeps the tree and prints matching source lines)
  * a `Bash` command naming a path outside it, by any reader the tool reaches
  * a `Bash` command that reads recursively with nothing to root it — `grep
    -rn x .`, `grep -rn x`, `rg x` — which sweeps the tree the same way an
    unrooted `Grep` does
  * a `Bash` fetch of a served source file from localhost (`.js`, `.css`,
    `.map`, `.ts`, `.py`) — the same source by another road
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shell_shapes as sh  # noqa: E402

#: repo-relative paths a blind agent may read; a trailing `/` means the subtree
DEFAULT_ALLOW = ("docs/", "tests/", "specs/", "state/")
#: repo-root files a blind agent may read, by extension
DEFAULT_ROOT_FILES = (".md", ".txt", ".pdf")

#: commands that read a whole tree; unrooted, they sweep the implementation
RECURSIVE_ALWAYS = frozenset({"find", "rg", "tree"})
#: commands that read a whole tree only when told to
RECURSIVE_ON_FLAG = {"grep": "rR", "egrep": "rR", "fgrep": "rR", "ls": "R"}
#: path candidates that root a search at the whole tree, which is no root
UNROOTED = frozenset({".", ".."})

#: a served source file fetched from a local dev server
SERVED = re.compile(
    r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?/[^\s\"']*\.(?:js|css|map|ts|py)\b"
)

_WHY = (
    "Blind agent: the implementation is out of bounds. Work from the approved spec "
    "block, docs/ and tests/. If the spec does not say what the behavior is, report "
    "that gap instead of reading the code to find out. If this path is genuinely a "
    "spec source, add it to the allow list in hooks/blind-reads.json. "
    "(hooks/no-impl-reads.py)"
)
_UNROOTED = (
    "Give Grep/Glob an explicit path (tests/, docs/, specs/): an unrooted search "
    "sweeps the whole tree and prints its source. " + _WHY
)


def repo_root(start: str) -> str | None:
    path = os.path.abspath(start or ".")
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def config() -> dict:
    """Per-repo widening, from `blind-reads.json` beside this file."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blind-reads.json")
    try:
        with open(path, encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _rules(conf: dict) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The allowlist and the repo's own extra runner names.

    There is no default runner list any more. A head word cannot tell a suite
    run from an interpreter printing a source file — `node -e` and `node
    --test` share it — so the runner question goes to `shell_shapes.is_runner`,
    which reads the whole invocation. What stays configurable is the name a
    repo gives its own suite command, and an inline-script flag disqualifies
    those too.
    """
    allow = tuple(DEFAULT_ALLOW) + tuple(conf.get("allow") or ())
    return allow, tuple(conf.get("runners") or ())


def readable(target: str, root: str | None, cwd: str, allow: tuple[str, ...]) -> bool:
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
    resolved = os.path.abspath(os.path.join(cwd or (root or "."), target))
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
    #: the allowlist runs first: `tests` is the allowed directory itself, not a
    #: root file that happens to carry no extension
    for entry in allow:
        name = entry.rstrip("/").replace("/", os.sep)
        if entry.endswith("/"):
            if rel == name or rel.startswith(name + os.sep):
                return True
        elif rel == name:
            return True
    #: a documentation file sitting at the repo root, by extension
    return base is not None and os.sep not in rel and (
        os.path.splitext(rel)[1].lower() in DEFAULT_ROOT_FILES
    )


def _candidates(words: list[str]) -> list[str]:
    """The words of a command that look like paths."""
    return [
        w
        for w in words[1:]
        #: a URL is not a path: `SERVED` above rules on the ones that carry source,
        #: and an API call over HTTP reaches no file this hook is guarding
        if "://" not in w
        and ("/" in w or os.path.splitext(w)[1])
        and not w.startswith("-")
    ]


def _reads_recursively(words: list[str]) -> bool:
    """Does this command walk a whole tree?

    `find`, `tree` and `rg` always do — `rg` needs no flag for it. The grep
    family and `ls` do when told to, and they are told in three spellings: a
    standalone `-r`, a clustered short option carrying it (`-rn`), or the long
    `--recursive`.
    """
    head = os.path.basename(words[0]) if words else ""
    if head in RECURSIVE_ALWAYS:
        return True
    letters = RECURSIVE_ON_FLAG.get(head)
    if letters is None:
        return False
    return any(
        w == "--recursive"
        or (w.startswith("-") and not w.startswith("--") and any(c in w[1:] for c in letters))
        for w in words[1:]
    )


def _unrooted_sweep(words: list[str]) -> bool:
    """A recursive reader with nothing to root it is a read of the whole tree."""
    if not _reads_recursively(words):
        return False
    return all(w.rstrip(os.sep) in UNROOTED for w in _candidates(words))


def _git_subcommand(words: list[str]) -> str | None:
    """The subcommand of a git invocation, past any global option.

    `git -C <dir> show` and `git --no-pager show` put the option in `words[1]`,
    so reading `words[1]` as the subcommand misses both. A bare `git` has no
    subcommand at all.
    """
    i = 1
    while i < len(words):
        word = words[i]
        if word in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2
            continue
        if word.startswith("-"):
            i += 1
            continue
        return word
    return None


def _git_prints_content(words: list[str]) -> bool:
    """Does this git command print file content?

    Metadata subcommands print commits, refs and names. Everything else prints
    some of the tree, and an unrecognized subcommand is treated as content --
    the same direction the rest of this hook takes, where unlisted is denied.
    """
    sub = _git_subcommand(words)
    if sub is None:
        return True
    if sub == "log":
        return any(w in sh.GIT_PATCH_FLAGS for w in words[1:])
    return sub not in sh.GIT_METADATA


def _git_candidates(words: list[str]) -> list[str]:
    """The path-shaped words of a git command, with any `<rev>:` prefix removed.

    `git show HEAD:specs/approved/<slug>.txt` is the supported way for a blind agent to
    read an allowlisted spec out of history. Scored literally, the revision
    prefix makes that path a filename that exists nowhere, so the read the
    escape hatch exists for was refused.
    """
    out = []
    for word in _candidates(words):
        head, sep, tail = word.partition(":")
        out.append(tail if sep and "/" not in head else word)
    return out


def _strip_env(words: list[str]) -> list[str]:
    """Drop a leading `VAR=value` prefix, so the head word is the command.

    The suite run a blind writer is told to make is `PYTHONPATH=$(pwd) pytest
    ...`. Without this the head word is the assignment, no runner is recognized,
    and the run falls through to the path test.
    """
    i = 0
    while i < len(words) and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*=.*", words[i]):
        i += 1
    return words[i:]


def _bash_verdict(
    command: str, root: str | None, cwd: str, allow: tuple[str, ...], runners: tuple[str, ...]
) -> str | None:
    """Why this shell command is refused, or None to let it through.

    The stages are walked in order carrying the directory a `cd` moved them to,
    because a blind agent works by `cd <its worktree> && <run>`: the tree is
    named once, as a `cd` target, and every path after it is relative to that
    tree. Scoring that target as a path to allowlist denied the whole idiom, and
    with it every run of the tests the agent had just written.
    """
    here = cwd
    for stage in sh.segments(command):
        words = _strip_env(sh.words_of(stage))
        if not words:
            continue
        target = sh.cd_target(words)
        if target is not None:
            #: `cd`, `cd -` and `cd ~...` move where this walk cannot follow
            if target in ("", "-") or target.startswith("~"):
                here = cwd
            else:
                here = os.path.abspath(os.path.join(here, target))
            continue
        head = os.path.basename(words[0])
        inline = sh.has_inline_script(words)
        if sh.is_runner(words) or (head in runners and not inline):
            continue
        if _unrooted_sweep(words):
            return _UNROOTED
        if head == "git":
            #: a git command that prints content carries no path of its own when
            #: it is spelled `git show <rev>`, so the candidate test has nothing
            #: to fail on and the implementation goes out whole
            if _git_prints_content(words):
                paths = _git_candidates(words)
                if not paths or any(not readable(w, root, here, allow) for w in paths):
                    return _WHY
            continue
        if any(not readable(w, root, here, allow) for w in _candidates(words)):
            return _WHY
    return None


def _verdict(name: str, tool_input: dict, root: str | None, cwd: str, conf: dict) -> str | None:
    """Why this call is refused, or None to let it through."""
    allow, runners = _rules(conf)
    if name == "Read":
        return None if readable(tool_input.get("file_path", ""), root, cwd, allow) else _WHY
    if name in ("Grep", "Glob"):
        target = tool_input.get("path")
        if target is None:
            return _UNROOTED
        return None if readable(target, root, cwd, allow) else _WHY
    if name == "Bash":
        command = tool_input.get("command", "")
        if SERVED.search(command):
            return _WHY
        return _bash_verdict(command, root, cwd, allow, runners)
    return None


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        return  # never block on our own failure
    cwd = data.get("cwd") or os.getcwd()
    try:
        reason = _verdict(
            data.get("tool_name", ""), data.get("tool_input") or {}, repo_root(cwd), cwd, config()
        )
    except (ValueError, IndexError):
        reason = None  # never block on our own failure
    if reason is None:
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def self_test() -> int:
    """Pin the spec lines of the blind-read allowlist."""
    root = "/repo"
    tree = f"{root}/.claude/worktrees/demo-spec"
    conf: dict = {}

    def call(tool: str, tool_input: dict) -> str | None:
        return _verdict(tool, tool_input, root, root, conf)

    def read(path: str) -> str | None:
        return call("Read", {"file_path": path})

    def bash(cmd: str) -> str | None:
        return call("Bash", {"command": cmd})

    denied, allowed = (lambda v: isinstance(v, str)), (lambda v: v is None)
    lines = {
        "1 the spec's own sources are readable, the rest is not": all(
            (
                allowed(read(f"{root}/docs/testing.md")),
                allowed(read(f"{root}/tests/test_lane.py")),
                allowed(read(f"{root}/specs/approved/slug.txt")),
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
        "3 shell readers follow the same list, runners and API calls pass": all(
            (
                allowed(bash(f"cat {root}/docs/testing.md")),
                denied(bash(f"cat {root}/src/core/manager.py")),
                denied(bash("sed -n '1,40p' src/core/manager.py")),
                allowed(bash("pytest tests/test_lane.py -q")),
                allowed(bash("curl -s http://127.0.0.1:8090/api/state")),
                denied(bash("curl -s http://127.0.0.1:8090/components/copy.js")),
            )
        ),
        "4 an interpreter reading source is denied, a suite run is not": all(
            (
                #: the runner question is the whole invocation, never the head
                #: word: `node -e` and `node --test` share one
                denied(bash("node -e \"console.log(require('fs').readFileSync('src/core.py','utf8'))\"")),
                denied(bash("python -c \"print(open('src/core.py').read())\"")),
                allowed(bash("pytest tests/test_lane.py -q")),
                allowed(bash("npx vitest run")),
                allowed(bash("node --test tests/t.test.js")),
            )
        ),
        "5 a recursive search with no root is denied, a rooted one is not": all(
            (
                denied(bash("grep -rn secret .")),
                denied(bash("grep -rn secret")),
                denied(bash("grep --recursive secret .")),
                denied(bash("rg secret")),
                allowed(bash("grep -rn secret docs/")),
                allowed(bash("grep -n secret README.md")),
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
                allowed(read(f"{tree}/specs/approved/demo.txt")),
                allowed(read(f"{tree}/tests/test_demo.py")),
                allowed(call("Grep", {"pattern": "x", "path": f"{tree}/tests"})),
                #: the worktree carries its own copy of these, and neither is a
                #: spec source in either tree
                denied(read(f"{tree}/src/core/manager.py")),
                denied(read(f"{tree}/.claude/hooks/no-impl-reads.py")),
                #: the run the agent is told to make, from inside its own tree
                allowed(bash(f"cd {tree} && PYTHONPATH=$(pwd) .venv/bin/pytest tests/t.py -q")),
                #: a `cd` does not launder a read: the path is resolved from there
                denied(bash(f"cd {tree}/src && cat core.py")),
            )
        ),
        "8 the workflow's own state is readable, so the writer certifies its run": all(
            (
                allowed(read(f"{root}/state/red/demo.txt")),
                allowed(read(f"{root}/state/reviews/demo.1.txt")),
                denied(read(f"{root}/src/state/manager.py")),
            )
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test()) if "--self-test" in sys.argv else main()
