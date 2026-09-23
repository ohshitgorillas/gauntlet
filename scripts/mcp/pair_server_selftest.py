"""The `--self-test` body of `pair_server.py`: one line per rule the server holds.

It lives beside the server rather than inside it, as `blind_server`'s does, and
`python3 scripts/mcp/pair_server.py --self-test` runs it. A recording runner
stands in for `pair.sh`, so nothing here touches a checkout or a branch.
"""

from __future__ import annotations

import ast
import io
import itertools
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pair_server as server
import rpc

#: what `pair.sh` prints on both streams: a CRLF and a byte that is not UTF-8
RAW_SCRIPT = "#!/bin/sh\nprintf 'a\\r\\nb\\377'\nprintf 'a\\r\\nb\\377' >&2\n"
RAW_TEXT = "a\r\nb\udcff"


def _usage() -> str:
    """The `USAGE` string `pair.sh`'s dispatch dies with, read from `cli.py` without running it."""
    cli = Path(server.__file__).resolve().parents[1] / "pair" / "cli.py"
    for node in ast.parse(cli.read_text()).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "USAGE" for target in node.targets
        ):
            return str(ast.literal_eval(node.value))
    return ""


def _verbs() -> list[str]:
    """One tool name per verb `cli.py` dispatches, in its usage order.

    `a|b` is a choice and `[x]` an optional word; `<field>` is a field, not a
    word, and the words of one verb join with `_`.
    """
    names: list[str] = []
    for form in _usage().removeprefix("usage: pair.sh ").split(" | "):
        choices = [
            ["", word[1:-1]] if word.startswith("[") else word.split("|")
            for word in form.split()
            if not word.startswith("<")
        ]
        names += ["_".join(filter(None, words)) for words in itertools.product(*choices)]
    return names


VERBS = _verbs()

#: streams a verbatim reply must carry byte for byte: a trailing space, a blank line, no newline
STDOUT = "OPEN .claude/worktrees/demo-spec \n\n"
STDERR = "pair: a progress line"


class Recorder:
    """A runner that records each argv it is handed and answers with a fixed run."""

    def __init__(self, status: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.status = status

    def __call__(
        self, words: list[str], cwd: Path, timeout: int
    ) -> subprocess.CompletedProcess[str]:
        del cwd, timeout
        self.calls.append(list(words))
        return subprocess.CompletedProcess([str(server.PAIR), *words], self.status, STDOUT, STDERR)


def _argv(name: str, arguments: dict[str, Any]) -> list[list[str]]:
    """The argvs one call hands the runner; none when it is refused."""
    recorder = Recorder()
    server.handle(name, dict(arguments), Path(), recorder)
    return recorder.calls


def _refused(name: str, arguments: dict[str, Any]) -> bool:
    """Whether the call is refused as a tool error and runs nothing."""
    recorder = Recorder()
    got = server.handle(name, dict(arguments), Path(), recorder)
    return got.error and not recorder.calls


def _answer(line: dict[str, Any]) -> dict[str, Any] | None:
    return rpc.answer(server.SERVER, json.dumps(line))


def _raising(name: str, arguments: dict[str, Any]) -> rpc.Reply:
    """A handler that faults on every call."""
    raise RuntimeError(f"boom in {name} {sorted(arguments)}")


FAULTY_CALL = {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "list"}}


def _served(server_: rpc.Server, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every reply `rpc.serve` writes for `messages`, one per line."""
    out = io.StringIO()
    rpc.serve(server_, io.StringIO("".join(json.dumps(m) + "\n" for m in messages)), out)
    return [json.loads(line) for line in out.getvalue().splitlines()]


def _raw_run() -> subprocess.CompletedProcess[str]:
    """`server.run` over a stand-in `pair.sh` that prints a CRLF and a non-UTF-8 byte."""
    saved = server.PAIR
    with tempfile.TemporaryDirectory() as name:
        script = Path(name) / "pair.sh"
        script.write_text(RAW_SCRIPT)
        script.chmod(0o755)
        server.PAIR = script
        try:
            return server.run(["list"], Path(name), 60)
        finally:
            server.PAIR = saved


def _robust_rules() -> dict[str, bool]:
    faulty = rpc.Server(server.NAME, server.VERSION, server.SERVER.tools, _raising)
    faulted = rpc.answer(faulty, json.dumps(FAULTY_CALL)) or {}
    served = _served(faulty, [FAULTY_CALL, {"jsonrpc": "2.0", "id": 5, "method": "ping"}])
    raw = _raw_run()
    return {
        "a raising handler answers isError with its class and message": faulted.get(
            "result", {}
        ).get("isError")
        is True
        and faulted["result"]["content"][0]["text"].startswith("RuntimeError: boom"),
        "rpc.serve answers a raising call and then a ping": [r.get("id") for r in served] == [4, 5]
        and served[1].get("result") == {},
        "pair.sh's streams come back byte-faithful, CRLF and bad byte kept": raw.stdout == RAW_TEXT
        and raw.stderr == RAW_TEXT,
        "review refuses the slug plan and runs nothing": _refused("review", {"slug": "plan"}),
        "a slug pair.sh admits is admitted": _argv("close", {"slug": "Demo_1.x"})
        == [["close", "Demo_1.x"]],
    }


def _rules() -> dict[str, bool]:
    listed = _answer({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) or {}
    unknown = _answer({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "x"}})
    failed = server.handle("check", {"slug": "demo"}, Path(), Recorder(1))
    passed = server.handle("list", {}, Path(), Recorder(0))
    return {
        "tools/list names one tool per pair.sh verb": [
            tool["name"] for tool in listed.get("result", {}).get("tools", [])
        ]
        == VERBS,
        "a slug verb runs pair.sh <verb> <slug>": _argv("open", {"slug": "demo"})
        == [["open", "demo"]],
        "review_plan runs pair.sh review plan <slug>": _argv("review_plan", {"slug": "demo"})
        == [["review", "plan", "demo"]],
        "impl_checkout and impl_merge run pair.sh impl <step> <slug>": _argv(
            "impl_checkout", {"slug": "demo"}
        )
        + _argv("impl_merge", {"slug": "demo"})
        == [["impl", "checkout", "demo"], ["impl", "merge", "demo"]],
        "restore runs pair.sh restore <slug> <rev>": _argv(
            "restore", {"slug": "demo", "rev": "HEAD~2"}
        )
        == [["restore", "demo", "HEAD~2"]],
        "list runs pair.sh list with no field": _argv("list", {}) == [["list"]],
        "a slug carrying a path is refused and runs nothing": _refused("open", {"slug": "../demo"}),
        "a slug that reads as an option is refused": _refused("close", {"slug": "-rf"}),
        "a rev that is not a hash or HEAD is refused": _refused(
            "restore", {"slug": "demo", "rev": "HEAD:hooks/lanes.py"}
        ),
        "a field that is not a string is refused": _refused("merge", {"slug": ["demo"]}),
        "a missing field is refused": _refused("restore", {"slug": "demo"}),
        "an argument the tool does not declare is refused": _refused("list", {"slug": "demo"}),
        "stdout and stderr come back verbatim with the exit status": json.loads(failed.text)
        == {"exit": 1, "stdout": STDOUT, "stderr": STDERR},
        "a non-zero exit is an error and a zero exit is not": failed.error and not passed.error,
        "a tool the table does not hold is a JSON-RPC error": bool(unknown)
        and "error" in (unknown or {}),
        "a notification gets no answer": _answer(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        is None,
    }


def self_test() -> int:
    """Print one PASS or FAIL per rule; exit 1 if any failed."""
    rules = _rules() | _robust_rules()
    for name, held in rules.items():
        print(f"{'PASS' if held else 'FAIL'}  {name}")
    return 0 if all(rules.values()) else 1
