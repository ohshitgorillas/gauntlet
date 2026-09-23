#!/usr/bin/env python3
"""Gate: no hook reads a `Bash` command.

    scripts/gates/no-command-reads.py [--check]
    scripts/gates/no-command-reads.py --self-test

A reading of a command string is undecidable, and a list of spellings leaves the
next spelling open, so `bwrap-wrap.py` carries the text into the wrap byte for
byte and reads nothing in it. This gate holds that from two sides.

**Static**, over every module under `hooks/` and `scripts/mcp/` with `ast`.
Outside `hooks/bwrap-wrap.py`, a subscript or `.get` of `"command"` on a value
taken from `tool_input` fails; a sample payload is a literal, not a subscript.
Inside it the command is read once, into a name, which may be tested with
`isinstance` and handed to `_heredoc` once; handing it to another function of
the module carries the rule into that parameter, and every other use -- `in`,
`split`, `startswith`, `==`, `re.*`, an f-string, a slice -- fails. A shlex call
on a value taken from `tool_input` fails; shlex on a config value passes.

**Behavioral.** Every hook the manifest wires on `PreToolUse` for `Bash` runs for
each caller in `CALLERS` over every text in `CORPUS`. With the text and the
here-document carrying it taken out, a hook that reads no command answers every
text alike; two texts answered differently for one caller fail.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

#: the directories whose modules the static leg reads
SCANNED = ("hooks", "scripts/mcp")

#: the one hook that holds the command, and the one function it may hand it to
WRAP = "hooks/bwrap-wrap.py"
SINK = "_heredoc"

#: the shell tokenizer, which may split a config value but never a call's input
SHLEX = "shlex"

#: the payload field a call's input sits in, and the key the command sits at
INPUT = "tool_input"
FIELD = "command"

#: the manifest whose `PreToolUse` groups the behavioral leg drives
MANIFEST = ".claude-plugin/plugin.json"

#: the tool a hook must not read, as the manifest's matchers name it
TOOL = "Bash"

#: every caller a hook can be asked for: the main agent, then each subagent
CALLERS = ("", "scrivener", "arbiter", "juror", "bailiff", "auditor", "prosecutor")

#: the texts every caller's hook sees. A hook that reads none of them answers
#: all of them alike.
CORPUS: dict[str, str] = {
    "a bare command": "pwd",
    "a delete of the approved lane": "rm -rf gauntlet/specs/approved",
    "sudo": "sudo ls",
    "the off switch": "GAUNTLET=off claude",
    "a pair merge": "scripts/pair.sh merge x",
    "a here-document": "cat <<'EOF'\nGAUNTLET_COMMAND_EOF\nEOF",
    "a read of a test": "cat tests/x.py",
    "nothing": "",
    "a megabyte": "echo " + "x" * 1024 * 1024,
}

#: where a here-document opens in a rewritten command; the rest is the text
HEREDOC = " <<'"

#: what the text itself becomes in a normalized answer
PLACEHOLDER = "<command>"


def _load(name: str) -> ModuleType:
    """Import a sibling gate by path, since its name is hyphenated."""
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _keyed(node: ast.AST, key: str) -> ast.expr | None:
    """What `node` takes `key` out of, by subscript or `.get`, or None."""
    if isinstance(node, ast.Subscript):
        hit = isinstance(node.slice, ast.Constant) and node.slice.value == key
        return node.value if hit else None
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        first = node.args[0] if node.args else None
        hit = node.func.attr == "get" and isinstance(first, ast.Constant) and first.value == key
        return node.func.value if hit else None
    return None


def _from_input(expr: ast.AST, tainted: set[str]) -> bool:
    """Whether an expression's value is, or comes out of, a call's `tool_input`."""
    return any(
        _keyed(node, INPUT) is not None or (isinstance(node, ast.Name) and node.id in tainted)
        for node in ast.walk(expr)
    )


def _tainted(scope: ast.AST) -> set[str]:
    """The names in one scope bound from `tool_input`, followed to a fixpoint."""
    names: set[str] = set()
    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        names |= {arg.arg for arg in scope.args.args if arg.arg.lstrip("_") == INPUT}
    while True:
        grown = set(names)
        for node in ast.walk(scope):
            if isinstance(node, ast.Assign) and _from_input(node.value, names):
                grown |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        if grown == names:
            return names
        names = grown


def _reads_command(node: ast.AST, tainted: set[str]) -> bool:
    """Whether one node is a subscript or `.get` of `"command"` on the call's input."""
    base = _keyed(node, FIELD)
    return base is not None and _from_input(base, tainted)


def _line(node: ast.AST) -> int:
    return int(getattr(node, "lineno", 0))


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}


def _scope(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST:
    """The function a node sits in, or the module."""
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return node
    return node


def command_reads(tree: ast.AST) -> list[ast.AST]:
    """Every read of a call's command in one module, in source order."""
    parents = _parents(tree)
    scopes: dict[ast.AST, set[str]] = {}
    found = []
    for node in ast.walk(tree):
        scope = _scope(node, parents)
        if scope not in scopes:
            scopes[scope] = _tainted(scope)
        if _reads_command(node, scopes[scope]):
            found.append(node)
    return sorted(found, key=_line)


class _Flow:
    """The one command value in the wrap hook, followed through the module."""

    def __init__(self, path: str, tree: ast.Module) -> None:
        self.path = path
        self.parents = _parents(tree)
        self.functions = {
            node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        self.seen: set[tuple[str, str]] = set()
        self.sinks = 0
        self.problems: list[str] = []

    def follow(self, scope: ast.AST, name: str) -> None:
        """Judge every use of `name` in `scope`, carrying it into local calls."""
        key = (getattr(scope, "name", "<module>"), name)
        if key in self.seen:
            return
        self.seen.add(key)
        for node in ast.walk(scope):
            if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Load):
                self._judge(node, name)

    def _judge(self, node: ast.Name, name: str) -> None:
        parent = self.parents.get(node)
        call = parent if isinstance(parent, ast.Call) else None
        callee = call.func.id if call is not None and isinstance(call.func, ast.Name) else ""
        if callee == "isinstance" and call is not None and call.args[:1] == [node]:
            return
        if callee == SINK:
            self.sinks += 1
            if self.sinks > 1:
                self.problems.append(f"{self.path}:{_line(node)}: the command reaches {SINK} twice")
            return
        target = self.functions.get(callee)
        if target is not None and isinstance(parent, ast.Call) and node in parent.args:
            params = target.args.args
            index = parent.args.index(node)
            if index < len(params):
                self.follow(target, params[index].arg)
                return
        shape = ast.unparse(parent) if parent is not None else name
        self.problems.append(f"{self.path}:{_line(node)}: the command is read by {shape[:60]!r}")


def _wrap_problems(path: str, tree: ast.Module) -> list[str]:
    """Why the wrap hook's handling of the command cannot stand, if it cannot."""
    flow = _Flow(path, tree)
    for read in command_reads(tree):
        parent = flow.parents.get(read)
        targets = parent.targets if isinstance(parent, ast.Assign) else []
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            flow.problems.append(f"{path}:{_line(read)}: the command is read without a name")
            continue
        flow.follow(_scope(read, flow.parents), targets[0].id)
    return flow.problems


def _shlex_calls(tree: ast.AST) -> list[ast.Call]:
    """Every call into shlex whose argument is a value taken from `tool_input`."""
    parents = _parents(tree)
    names = {
        a.asname or a.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == SHLEX
        for a in node.names
    }
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    return [
        call
        for call in calls
        if ast.unparse(call.func) in names or ast.unparse(call.func).startswith(f"{SHLEX}.")
        if any(
            _from_input(arg, _tainted(_scope(call, parents)))
            for arg in [*call.args, *(k.value for k in call.keywords)]
        )
    ]


def judge(path: str, source: str) -> list[str]:
    """Why one module cannot stand beside the rule that no hook reads a command."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{path}: cannot be parsed ({exc.msg})"]
    problems: list[str] = []
    problems += [
        f"{path}:{_line(node)}: hands a call's input to shlex" for node in _shlex_calls(tree)
    ]
    if path == WRAP:
        return problems + _wrap_problems(path, tree)
    return problems + [
        f"{path}:{_line(node)}: reads a call's command" for node in command_reads(tree)
    ]


def modules(root: Path = ROOT) -> list[str]:
    """Every module the static leg reads, relative to the root, sorted."""
    return sorted(
        path.relative_to(root).as_posix()
        for directory in SCANNED
        for path in (root / directory).glob("*.py")
    )


def static(root: Path = ROOT) -> list[str]:
    """The static leg over the whole tree."""
    problems: list[str] = []
    for name in modules(root):
        try:
            source = (root / name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            problems.append(f"{name}: cannot be read ({exc})")
            continue
        problems += judge(name, source)
    return problems


def covers(matcher: Any) -> bool:
    """Whether a `PreToolUse` matcher fires on a `Bash` call."""
    if matcher in (None, "", "*"):
        return True
    if not isinstance(matcher, str):
        return False
    try:
        return re.fullmatch(matcher, TOOL) is not None
    except re.error:
        return False


def bash_hooks(root: Path = ROOT) -> list[str]:
    """Every command the manifest wires on `PreToolUse` for `Bash`, once each."""
    wired = _load("hooks-wired")
    try:
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    found = [
        entry["command"]
        for event, group in wired.groups(data)
        if event == "PreToolUse" and isinstance(group, dict) and covers(group.get("matcher"))
        for entry in group.get("hooks", [])
        if isinstance(entry, dict) and isinstance(entry.get("command"), str)
    ]
    return list(dict.fromkeys(found))


def payload(text: str, caller: str, root: Path = ROOT) -> str:
    """One `Bash` call carrying `text`, as `caller` would send it."""
    call: dict[str, Any] = {"tool_name": TOOL, "tool_input": {FIELD: text}, "cwd": str(root)}
    if caller:
        call["agent_type"] = caller
    return json.dumps(call)


def _scrub(value: Any, text: str) -> Any:
    """One piece of an answer with the text and any here-document taken out."""
    if isinstance(value, dict):
        return {key: _scrub(inner, text) for key, inner in value.items()}
    if isinstance(value, list):
        return [_scrub(inner, text) for inner in value]
    if not isinstance(value, str):
        return value
    if HEREDOC in value:
        return value[: value.index(HEREDOC)] + HEREDOC + PLACEHOLDER
    return value.replace(text, PLACEHOLDER) if text else value


def normalize(text: str, said: tuple[str, str]) -> tuple[Any, str]:
    """What an answer says once the text it was about is taken out of it."""
    out, err = said
    try:
        body: Any = _scrub(json.loads(out), text)
    except ValueError:
        body = _scrub(out, text)
    return body, _scrub(err, text)


def _shown(name: str) -> str:
    return f"{name} ({CORPUS.get(name, name)[:40]!r})"


def judge_answers(hook: str, caller: str, answers: dict[str, tuple[Any, str]]) -> list[str]:
    """Why one hook's normalized answers for one caller show it reading the text."""
    items = list(answers.items())
    differing = [name for name, said in items if said != items[0][1]]
    if not differing:
        return []
    return [
        f"{hook.rsplit('/', 1)[-1]} for {caller or 'the main agent'}: {_shown(items[0][0])} "
        f"and {_shown(differing[0])} are answered differently"
    ]


def behavioral(root: Path = ROOT) -> list[str]:
    """The behavioral leg: every Bash hook, every caller, the whole corpus."""
    answer = _load("hook-degenerate").answer
    problems: list[str] = []
    for hook in bash_hooks(root):
        for caller in CALLERS:
            answers = {
                name: normalize(text, answer(hook, payload(text, caller, root), root))
                for name, text in CORPUS.items()
            }
            problems += judge_answers(hook, caller, answers)
    return problems


def check(root: Path = ROOT) -> int:
    """Refuse a tree where a hook reads a command, by its source or by its answers."""
    problems = static(root) + behavioral(root)
    for problem in problems:
        print(problem)
    print(f"{len(modules(root))} module(s); {len(CALLERS)} caller(s) x {len(CORPUS)} text(s)")
    if problems:
        print(f"\n{len(problems)} problem(s). No hook reads a shell command.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from no_command_reads_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
