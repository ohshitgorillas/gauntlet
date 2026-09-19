#!/usr/bin/env python3
"""The two carve-outs from the sandbox: `scripts/pair.sh`, and what a project declares.

`pair.sh` writes lane files by design -- it is the route by which a lane file
changes on disk -- so it must run unwrapped, and something has to decide that.
This module is that decision and nothing else. `bwrap-wrap.py` imports it and
returns no `updatedInput` where it answers yes.

It is a module rather than a second hook entry ahead of the wrapper. Hook
entries under one matcher run in parallel and do not chain: every entry receives
the original `tool_input`, no entry sees another's `updatedInput`, and two
entries both returning one would race. An ordered carve-out therefore has no
mechanism to mark a call for a hook that has already answered.

Its own file rather than a branch inside the wrapper, because a wrapper that
decided for itself which commands to skip would be a classifier again under a
new name. What lives here is the opposite of a classifier: a closed set of
anchored whole-string patterns, one per subcommand, with nothing to extend as
new commands appear. It never walks a command apart and never judges its pieces.

The match is end to end, and that is the whole of its safety. A predicate that
searched for `scripts/pair.sh` anywhere in the command would answer yes for
`scripts/pair.sh red demo; rm -rf state`, and that second command would then run
outside the sandbox -- the one place in this design where a command does. A
command in front, a command behind, an environment assignment, a redirection, a
`cd` first: none of them match, so all of them get wrapped.

The argument grammar is the other half, and it names no verb. Every argument is
one bare token drawn from `[A-Za-z0-9_./@-]`, so a token can carry no `;`, `|`,
`&`, `$`, quote, space or glob, and nothing rides out beside the script. Which
verbs exist and what each takes is `scripts/pair/cli.py`'s to know: it holds
the slug to one path segment and dies on a verb it lacks, so a table of verbs
here would be a second copy of that grammar, one that every new verb had to be
added to and that `close`, `restore`, `impl`, `review` and `respec` were not.

The second predicate is over `unwrapped_commands`, which is the project's own
word rather than this kit's. A hook holding that set as its own constant would
unwrap a command no project asked for and ignore every command a project did
ask for, so nothing here names a command: the declaration does. The match is by
equality on the whole command text as the project wrote it -- not a prefix, not
a regex, not a word split, nothing parsed -- so no argument can be appended to a
declared command and no shape of it is read.

A declared command names the paths it reads, and they are the other half of the
guarantee: `bwrap-wrap.py` binds each of them read-only inside every wrapped
profile, so the shell that runs inside the sandbox cannot rewrite the input of
the one command that runs outside it. A `reads` entry that does not resolve in
this checkout voids its declaration, and the command is wrapped like any other:
binding what resolves and skipping the rest would leave the project holding a
guarantee the mount table does not make, exactly where a typo put it.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shell_shapes as sh  # noqa: E402

ENTRY = "scripts/pair.sh"

#: one argument: a bare token, nothing the shell reads as structure
ARG = r"[A-Za-z0-9_./@-]+"

#: the head, in the three spellings admitted, the same three `blind-bash.py`
#: admits for its own entry. `scripts/pair.sh` bare is the one an agent types;
#: the absolute path and the `${CLAUDE_PLUGIN_ROOT}` the runtime expands into
#: one are admitted because a brief or a doc may still carry them. A *relative*
#: prefix is deliberately not admitted, so no path inside the checkout is a
#: route by which a tree authors the one command that runs outside the sandbox.
_HEAD = r"(?:/[A-Za-z0-9_.@+:/-]*/|\$\{CLAUDE_PLUGIN_ROOT\}/)?" + re.escape(ENTRY)

#: blanks are space and tab only: `\s` would take a newline, and a newline is
#: a second command in front of bare tokens
ALLOWED = re.compile(rf"\A[ \t]*{_HEAD}(?:[ \t]+{ARG})*[ \t]*\Z")


def is_pair_command(command: str) -> bool:
    """Whether the whole command text is `pair.sh` followed by bare tokens only.

    False for everything else, which is the direction that costs a wrap rather
    than an escape: a command this answers no about still runs, inside `bwrap`.
    """
    return ALLOWED.match(command) is not None


def kit_entry() -> str:
    """This kit's own `scripts/pair.sh`, absolute.

    `hooks/` and `scripts/` are siblings in the plugin, so the entry is found
    from this file rather than from the checkout the command runs in, which for
    an installed plugin holds no copy of the script at all.
    """
    return str(Path(__file__).resolve().parent.parent / ENTRY)


def resolved_pair_command(command: str) -> str | None:
    """The same command with a bare head spelled at this kit's own entry.

    None where the head is already absolute or `${CLAUDE_PLUGIN_ROOT}`: those
    name a script themselves and are left exactly as typed. The command has
    matched an admitted shape before this runs, so the head is the first word
    and a leading occurrence of the entry is that word.
    """
    head = command.lstrip()
    if not head.startswith(ENTRY):
        return None
    lead = command[: len(command) - len(head)]
    return lead + kit_entry() + head[len(ENTRY) :]


def _resolved(root: str, path: str) -> str | None:
    """One declared `reads` path as it is on disk now, or `None` where it is not.

    Relative to the checkout, because that is what a project writes down; an
    absolute path is taken as it is spelled. `Path.exists` answers False for
    every reason a bind would fail on the source, which is the whole of what a
    read-only bind of it needs to know.
    """
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path(root) / candidate
    return str(candidate) if candidate.exists() else None


def declared_reads(root: str) -> dict[str, list[str]]:
    """The declared commands whose `reads` all resolve in `root`, and those paths.

    An entry naming a path that is not there is left out altogether, so it is
    wrapped and its paths are bound nowhere.
    """
    live: dict[str, list[str]] = {}
    for command, reads in sh.unwrapped_commands().items():
        paths = [_resolved(root, one) for one in reads]
        if any(path is None for path in paths):
            continue
        live[command] = [path for path in paths if path is not None]
    return live


def is_declared_command(command: str, root: str) -> bool:
    """Whether this whole command text is one the project declared unwrapped."""
    return command in declared_reads(root)


def read_only_paths(root: str) -> list[str]:
    """Every path a live declaration reads, sorted, each named once."""
    paths: set[str] = set()
    for reads in declared_reads(root).values():
        paths.update(reads)
    return sorted(paths)


def _with_declaration(declared: dict[str, Any], body):
    """Run `body` with `declared` standing in for the project's own word."""
    original = sh.unwrapped_commands
    sh.unwrapped_commands = lambda: declared  # type: ignore[assignment]
    try:
        return body()
    finally:
        sh.unwrapped_commands = original  # type: ignore[assignment]


def self_test() -> int:
    """Pin the whole-string match, the slug grammar, and the declared set."""
    declared_text = "sudo systemctl restart hqplayerd"
    with tempfile.TemporaryDirectory() as root:
        (Path(root) / "present.txt").write_text("", encoding="utf-8")

        def declared_answers(declaration: dict[str, Any], command: str) -> bool:
            return _with_declaration(
                declaration, lambda: is_declared_command(command, root)
            )

        declaration_rules = {
            "the declared text exactly is the project's command": declared_answers(
                {declared_text: []}, declared_text
            ),
            "nothing less than the whole declared string matches": not any(
                declared_answers({declared_text: []}, spelling)
                for spelling in (
                    declared_text + " ",
                    declared_text + " --now",
                    declared_text + "; rm -rf state",
                    "cd /tmp && " + declared_text,
                    "echo " + declared_text,
                )
            ),
            "a command the project did not declare is not declared": not declared_answers(
                {"sudo systemctl restart other": []}, declared_text
            ),
            "a declaration carrying nothing declares nothing": not declared_answers(
                {}, declared_text
            ),
            "a reads path that resolves keeps its declaration": declared_answers(
                {declared_text: ["present.txt"]}, declared_text
            ),
            "a reads path that does not resolve voids its declaration": not declared_answers(
                {declared_text: ["absent.txt"]}, declared_text
            ),
            "a voided declaration binds none of its paths": _with_declaration(
                {declared_text: ["present.txt", "absent.txt"]},
                lambda: read_only_paths(root),
            )
            == [],
            "a live declaration's paths are bound, each named once": _with_declaration(
                {declared_text: ["present.txt"], "other": ["present.txt"]},
                lambda: read_only_paths(root),
            )
            == [str(Path(root) / "present.txt")],
        }

    shape_rules = {
        "an unusable entry voids the whole mapping": all(
            sh.unwrapped_from({"unwrapped_commands": bad}) == {}
            for bad in (
                [declared_text],
                {declared_text: ["present.txt"]},
                {declared_text: {"reads": "present.txt"}},
                {declared_text: {"reads": [1]}},
                {"": {"reads": []}},
            )
        ),
        "a key the file omits declares nothing": sh.unwrapped_from({}) == {},
        "a declaration the file carries is read as written": sh.unwrapped_from(
            {"unwrapped_commands": {declared_text: {"reads": ["a", "b"]}}}
        )
        == {declared_text: ["a", "b"]},
    }

    lines = {
        **declaration_rules,
        **shape_rules,
        "the script with any count of bare tokens matches": all(
            is_pair_command(c)
            for c in (
                ENTRY,
                f"{ENTRY} list",
                f"{ENTRY} red demo",
                f"{ENTRY} review plan demo",
                f"{ENTRY} restore demo abc123",
                f"{ENTRY} restore demo feature/x",
                f"{ENTRY} impl checkout demo",
                f"  {ENTRY}  close   demo  ",
            )
        ),
        "a second command appended does not match": not any(
            is_pair_command(f"{ENTRY} red demo{tail}")
            for tail in (
                "; rm -rf state", " && rm -rf state", " | tee x", " > out.txt",
                "\nrm -rf state", "\rrm -rf state",
            )
        ),
        "a command or an assignment in front does not match": not any(
            is_pair_command(head + f"{ENTRY} red demo")
            for head in ("cd /tmp && ", "GAUNTLET=off ", "echo hi; ", "time ")
        ),
        "a token the shell reads as structure does not match": not any(
            is_pair_command(f"{ENTRY} red {arg}")
            for arg in (
                "$HOME", "`id`", "$(id)", "'demo'", '"demo"', "demo\\", "a*",
                "a?", "{a,b}", "~", "HEAD^", "x=y", "d#",
            )
        ),
        "an entry path that only contains ours does not match": not any(
            is_pair_command(c)
            for c in (f"x{ENTRY} red demo", f"./{ENTRY} red demo", f"tests/{ENTRY} red demo")
        ),
        "the absolute and expanded spellings match too": all(
            is_pair_command(f"{head}{ENTRY} red demo")
            for head in ("/opt/", "${CLAUDE_PLUGIN_ROOT}/", kit_entry()[: -len(ENTRY)])
        ),
        "a bare head resolves to this kit's own entry": resolved_pair_command(
            f"{ENTRY} open demo"
        )
        == f"{kit_entry()} open demo",
        "a head that names a script itself is left as typed": all(
            resolved_pair_command(f"{head}{ENTRY} open demo") is None
            for head in ("/opt/", "${CLAUDE_PLUGIN_ROOT}/")
        ),
    }
    return sh.report(lines)


if __name__ == "__main__":
    sys.exit(self_test())
