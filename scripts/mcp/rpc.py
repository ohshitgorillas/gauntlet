"""The JSON-RPC loop an MCP server of this kit runs on, standard library only.

A server here is a table of tools and one function that answers a call. This
module owns everything else: reading one JSON message per line from stdin,
answering `initialize`, `ping`, `tools/list` and `tools/call`, and writing one
JSON message per line to stdout. A notification carries no `id` and gets no
answer. Nothing is imported beyond the standard library, because the kit ships
as a directory and a consumer installs no package for it.

A tool that refuses its arguments answers with a result whose `isError` is set,
which the model reads; a request the loop cannot parse, a method it does not
know and a tool name the table does not hold are JSON-RPC errors, which the
host reads.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import IO, Any

#: the revision this loop answers with when the client names none
PROTOCOL_VERSION = "2025-06-18"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


@dataclass(frozen=True)
class Tool:
    """One tool as `tools/list` describes it."""

    name: str
    description: str
    schema: dict[str, Any]


@dataclass(frozen=True)
class Reply:
    """What a tool call returns: its text, and whether it is a refusal or a fault."""

    text: str
    error: bool = False


#: the function a server hands the loop: a tool name and its arguments in, a reply out
Handler = Callable[[str, dict[str, Any]], Reply]


@dataclass(frozen=True)
class Server:
    """A named server: its tools and the function that answers them."""

    name: str
    version: str
    tools: tuple[Tool, ...]
    handler: Handler


class RpcError(Exception):
    """A request the loop answers with a JSON-RPC error rather than a result."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _call(server: Server, params: dict[str, Any]) -> dict[str, Any]:
    """Answer `tools/call`: an unknown tool is an error, anything else a result."""
    name = params.get("name")
    arguments = params.get("arguments", {})
    if name not in {tool.name for tool in server.tools}:
        raise RpcError(INVALID_PARAMS, f"no tool named {name!r}")
    if not isinstance(arguments, dict):
        raise RpcError(INVALID_PARAMS, "arguments must be an object")
    reply = server.handler(str(name), arguments)
    return {"content": [{"type": "text", "text": reply.text}], "isError": reply.error}


def _initialize(server: Server, params: dict[str, Any]) -> dict[str, Any]:
    """Answer `initialize` in the revision the client asked for."""
    return {
        "protocolVersion": str(params.get("protocolVersion") or PROTOCOL_VERSION),
        "capabilities": {"tools": {}},
        "serverInfo": {"name": server.name, "version": server.version},
    }


def _list(server: Server) -> dict[str, Any]:
    """Answer `tools/list` from the server's table."""
    return {
        "tools": [
            {"name": tool.name, "description": tool.description, "inputSchema": tool.schema}
            for tool in server.tools
        ]
    }


def dispatch(server: Server, method: str, params: dict[str, Any]) -> dict[str, Any]:
    """The result for one request, or an `RpcError` naming why there is none."""
    if method == "initialize":
        return _initialize(server, params)
    if method == "ping":
        return {}
    if method == "tools/list":
        return _list(server)
    if method == "tools/call":
        return _call(server, params)
    raise RpcError(METHOD_NOT_FOUND, f"no method {method!r}")


def _error(ident: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": message}}


def answer(server: Server, line: str) -> dict[str, Any] | None:
    """The message to write for one line read, or None for a notification."""
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return _error(None, PARSE_ERROR, "not JSON")
    if not isinstance(message, dict) or not isinstance(message.get("method"), str):
        return _error(None, INVALID_REQUEST, "not a request")
    if "id" not in message:
        return None
    ident = message["id"]
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _error(ident, INVALID_PARAMS, "params must be an object")
    try:
        result = dispatch(server, message["method"], params)
    except RpcError as fault:
        return _error(ident, fault.code, fault.message)
    return {"jsonrpc": "2.0", "id": ident, "result": result}


def serve(server: Server, stdin: IO[str] = sys.stdin, stdout: IO[str] = sys.stdout) -> int:
    """Answer every line on `stdin` until it closes."""
    for line in stdin:
        if not line.strip():
            continue
        reply = answer(server, line)
        if reply is not None:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()
    return 0
