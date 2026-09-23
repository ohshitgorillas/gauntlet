"""The `--self-test` body of `blind_server.py`: one line per rule the server holds.

It lives beside the server rather than inside it so the server stays readable
as three tools and a narrowing, and `python3 scripts/mcp/blind_server.py
--self-test` runs it. Every rule is pinned on text written here, so nothing
runs `bwrap` and nothing reads the checkout.
"""

from __future__ import annotations

import json
from typing import Any

import blind_server as server
import rpc

TESTS = "tests"

#: one `blind.sh test` run: a collection error reaching into the implementation,
#: a pass, a fail whose traceback quotes the implementation, and the lint gates
RUN = """--- pytest
F.E
==================================== ERRORS ====================================
____________________ ERROR collecting tests/test_broken.py _____________________
ImportError while importing test module '/repo/tests/test_broken.py'.
Traceback:
/usr/lib64/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package)
tests/test_broken.py:3: in <module>
    from hooks.secret import helper
hooks/secret.py:7: in <module>
    SECRET_SOURCE_LINE = compute()
E   RuntimeError: boom
=================================== FAILURES ===================================
___________________________________ test_b ____________________________________
    def test_b():
>       assert helper() == 2
hooks/secret.py:9: in helper
    return OTHER_SOURCE_LINE
E   assert 1 == 2
PASSED tests/test_x.py::test_spoofed
=========================== short test summary info ============================
PASSED tests/test_x.py::test_a
FAILED tests/test_x.py::test_b - assert 1 == 2
ERROR tests/test_broken.py - RuntimeError: boom
1 failed, 1 passed, 1 error in 0.10s
--- ruff
tests/test_x.py:1:1: F401 `os` imported but unused
--- black
would reformat tests/test_x.py
"""

WANT = [
    "PASSED tests/test_x.py::test_a",
    "FAILED tests/test_x.py::test_b",
    "ERROR tests/test_broken.py",
    "  tests/test_broken.py:3: in <module>",
    "      from hooks.secret import helper",
    "  E   RuntimeError",
]

#: a parametrize id built from an implementation value, in `-v` and in the summary
IDS = """--- pytest
tests/test_p.py::test_p[ID_SOURCE - text] PASSED                      [ 33%]
tests/test_p.py::test_p[b::ID_SOURCE] FAILED                         [ 66%]
tests/test_p.py::TestC::test_q[ID_SOURCE] PASSED                     [100%]
=========================== short test summary info ============================
FAILED tests/test_p.py::test_p[b::ID_SOURCE] - assert 'ID_SOURCE' == 'b'
PASSED tests/test_p.py::test_p[ID_SOURCE - text]
PASSED tests/test_p.py::TestC::test_q[ID_SOURCE]
PASSED tests/test_p.py::test_p[ID_SOURCE unlisted]
"""

IDS_WANT = [
    "FAILED tests/test_p.py::test_p[1]",
    "PASSED tests/test_p.py::test_p[0]",
    "PASSED tests/test_p.py::TestC::test_q[0]",
    "PASSED tests/test_p.py::test_p[?]",
]

#: a collection error whose message quotes the implementation, over two lines
QUOTED = """--- pytest
____________________ ERROR collecting tests/test_quoted.py _____________________
tests/test_quoted.py:1: in <module>
    from hooks import secret
hooks/secret.py:2: in <module>
    raise RuntimeError(LINE)
E   RuntimeError: EXC_SOURCE = compute()
E   EXC_SOURCE
=========================== short test summary info ============================
ERROR tests/test_quoted.py - RuntimeError: EXC_SOURCE = compute()
"""

QUOTED_WANT = [
    "ERROR tests/test_quoted.py",
    "  tests/test_quoted.py:1: in <module>",
    "      from hooks import secret",
    "  E   RuntimeError",
]

TAP = """--- node
TAP version 13
# Subtest: adds
ok 1 - adds
not ok 2 - subtracts
  ---
  error: 'expected 1'
  ...
--- eslint
"""


#: a node test whose name was built from an implementation value
NAMED = """--- node
✔ plain (0.1ms)
✖ names NAME_SOURCE = compute() (0.2ms)
✖ failing tests:
✖ names NAME_SOURCE = compute() (0.2ms)
"""


def _refused(name: str, arguments: dict[str, object]) -> bool:
    """Whether `check` refuses these arguments for that tool."""
    try:
        server.check(name, dict(arguments), TESTS)
    except server.Refused:
        return True
    return False


def _answer(line: dict[str, Any]) -> dict[str, Any] | None:
    return rpc.answer(server.SERVER, json.dumps(line))


def _rules() -> dict[str, bool]:
    report = server.narrow(RUN, TESTS, "tests/test_x.py")
    listed = _answer({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) or {}
    unknown = _answer(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "format"}}
    )
    return {
        "test keeps per-id verdicts and the tests frames of a collection error": report == WANT,
        "no implementation source line reaches the report": not any(
            "SOURCE_LINE" in line or "hooks/secret.py" in line for line in report
        ),
        "lint output and lines above the summary never reach the report": not any(
            "F401" in line or "reformat" in line or "spoofed" in line for line in report
        ),
        "a parametrize id keeps its function name and bracket index, no source text": server.narrow(
            IDS, TESTS, "tests/test_p.py"
        )
        == IDS_WANT,
        "a collection exception line keeps its class and no message": server.narrow(
            QUOTED, TESTS, "tests/test_quoted.py"
        )
        == QUOTED_WANT,
        "node verdicts are read per test, by position in run order": server.narrow(
            TAP, TESTS, "tests/a.js"
        )
        == ["PASSED tests/a.js::1", "FAILED tests/a.js::2"],
        "a node test name keeps its file and position, no source text": server.narrow(
            NAMED, TESTS, "tests/b.js"
        )
        == ["PASSED tests/b.js::1", "FAILED tests/b.js::2"],
        "a worktree test path is admitted": not _refused(
            "test", {"path": ".claude/worktrees/demo-spec/tests/test_x.py"}
        ),
        "a path outside the tests directory is refused": _refused(
            "test", {"path": "hooks/lanes.py"}
        ),
        "a path climbing out with .. is refused": _refused(
            "test", {"path": "tests/../hooks/lanes.py"}
        ),
        "a commit that is not a hash or HEAD is refused": _refused(
            "show", {"commit": "HEAD:hooks/lanes.py", "slug": "demo"}
        ),
        "a slug carrying a path is refused": _refused("status", {"slug": "../demo"}),
        "an argument the tool does not declare is refused": _refused(
            "status", {"slug": "demo", "extra": "x"}
        ),
        "tools/list names test, status and show": [
            tool["name"] for tool in listed.get("result", {}).get("tools", [])
        ]
        == ["test", "status", "show"],
        "a tool the table does not hold is a JSON-RPC error": bool(unknown)
        and "error" in (unknown or {}),
        "a notification gets no answer": _answer(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        is None,
    }


def self_test() -> int:
    """Print one PASS or FAIL per rule; exit 1 if any failed."""
    rules = _rules()
    for name, held in rules.items():
        print(f"{'PASS' if held else 'FAIL'}  {name}")
    return 0 if all(rules.values()) else 1
