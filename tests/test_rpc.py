"""Tests for the JSON-RPC loop every MCP server of the kit runs on, scripts/mcp/rpc.py.

The loop is driven in process: a table of one tool, a handler written here, and
lines handed to `answer` or `serve` as the host would write them.
"""

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

MCP = Path(__file__).resolve().parent.parent / "scripts" / "mcp"


def _rpc():
    """The loop's module, loaded from its file, as the servers load it."""
    spec = importlib.util.spec_from_file_location("mcp_rpc", MCP / "rpc.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rpc = _rpc()

TOOL = rpc.Tool("echo", "Echo the arguments.", {"type": "object"})


#: the message the handler raises with
FAULT = "bad echo"


def _echo(_name, arguments):
    if arguments.get("raise"):
        raise ValueError(FAULT)
    return rpc.Reply(json.dumps(arguments))


SERVER = rpc.Server("demo", "1", (TOOL,), _echo)


def _call(arguments, ident=1):
    params = {"name": "echo"}
    if arguments is not ...:
        params["arguments"] = arguments
    return {"jsonrpc": "2.0", "id": ident, "method": "tools/call", "params": params}


def _answer(message):
    return rpc.answer(SERVER, json.dumps(message))


def _served(raw):
    """Every reply `serve` writes for the bytes `raw`, read as the host's stdin is."""
    stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8")
    stdout = io.StringIO()
    rpc.serve(SERVER, stdin, stdout)
    return [json.loads(line) for line in stdout.getvalue().splitlines()]


def test_a_raising_handler_answers_is_error():
    assert _answer(_call({"raise": True}))["result"]["isError"] is True


def test_a_raising_handler_answers_its_class_and_message():
    text = _answer(_call({"raise": True}))["result"]["content"][0]["text"]
    assert text == ValueError.__name__ + ": " + FAULT


def test_serve_answers_the_request_after_a_raising_call():
    lines = [_call({"raise": True}, 1), {"jsonrpc": "2.0", "id": 2, "method": "ping"}]
    raw = "".join(json.dumps(line) + "\n" for line in lines).encode()
    assert [reply["id"] for reply in _served(raw)] == [1, 2]


def test_a_line_that_is_not_utf8_is_a_parse_error():
    assert _served(b"\xff\n")[0]["error"]["code"] == rpc.PARSE_ERROR


def test_serve_answers_the_request_after_a_line_that_is_not_utf8():
    raw = b"\xff\n" + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}).encode() + b"\n"
    assert _served(raw)[1] == {"jsonrpc": "2.0", "id": 2, "result": {}}


def test_a_fault_outside_the_handler_is_an_internal_error(monkeypatch):
    def broken(_server, method, _params):
        raise KeyError(method)

    monkeypatch.setattr(rpc, "dispatch", broken)
    assert _answer({"jsonrpc": "2.0", "id": 1, "method": "ping"})["error"]["code"] == (
        rpc.INTERNAL_ERROR
    )


def test_initialize_answers_the_revision_the_loop_speaks():
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "1999-01-01"},
    }
    assert _answer(message)["result"]["protocolVersion"] == rpc.PROTOCOL_VERSION


def test_a_response_from_the_client_gets_no_answer():
    assert _answer({"jsonrpc": "2.0", "id": 7, "result": {}}) is None


@pytest.mark.parametrize("arguments", [None, ...], ids=["null", "absent"])
def test_null_or_absent_arguments_read_as_an_empty_object(arguments):
    assert _answer(_call(arguments))["result"]["content"][0]["text"] == "{}"


def test_text_keeps_crlf_and_an_undecodable_byte():
    assert rpc.text(b"a\r\nb\xff") == "a\r\nb\udcff"
