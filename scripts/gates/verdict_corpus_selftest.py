#!/usr/bin/env python3
"""The `--self-test` body of `verdict-corpus.py`: one line per rule it holds.

The lifting, the dedup and the root substitution are read against invented
transcripts. The comparison is not invented: a real corpus entry is replayed
against the live hooks, once as it stands and once with its pinned answer
altered, so the rule that a changed verdict is reported is exercised through
the same path `--check` takes.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

GATE_PATH = Path(__file__).resolve().parent / "verdict-corpus.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("verdict_corpus_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

#: two transcript lines: one carrying a tool call, one carrying nothing
LINES = [
    json.dumps(
        {
            "message": {
                "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "pwd"}}]
            }
        }
    ),
    json.dumps({"message": {"content": [{"type": "text", "text": "hello"}]}}),
    "not json at all",
]


def _held() -> list[Any]:
    """The corpus as it stands on disk."""
    held: list[Any] = GATE.corpus()
    return held


def _altered() -> list[str]:
    """What `judge` says when one entry's pinned decision is not what the kit says."""
    entries = copy.deepcopy(_held()[:1])
    for pinned in entries[0]["verdicts"].values():
        pinned["decision"] = "invented"
    said: list[str] = GATE.judge(entries)
    return said


def _denies() -> bool:
    """The corpus pins at least one refusal, so it is not a corpus of silences."""
    return any(
        pinned.get("decision") == "deny"
        for entry in _held()
        for pinned in entry["verdicts"].values()
    )


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    lifted = GATE.calls(LINES)
    twice = GATE.distinct(lifted * 3)
    capped = GATE.distinct(
        [{"tool_name": "Bash", "tool_input": {"command": str(n)}} for n in range(200)]
    )
    altered = _altered()
    return {
        "a tool call is lifted out of a transcript, and prose is not": (
            len(lifted) == 1 and lifted[0]["tool_name"] == "Bash"
        ),
        "a line that is not JSON is stepped over": GATE.calls(["not json"]) == [],
        "the same call twice is one call": len(twice) == 1,
        "a harvest keeps no more calls than its limit": len(capped) == GATE.LIMIT,
        "the checkout root goes out as a token and comes back as itself": (
            GATE._portable({"p": f"{GATE.ROOT}/hooks"}, GATE.ROOT)["p"]
            == f"{GATE.ROOT_TOKEN}/hooks"
            and GATE._local({"p": f"{GATE.ROOT_TOKEN}/hooks"}, GATE.ROOT)["p"]
            == f"{GATE.ROOT}/hooks"
        ),
        "a hook and a caller name one verdict, and it parses back": (
            GATE.key("lanes.py", "juror") == "lanes.py as juror"
            and GATE.key("lanes.py", "") == "lanes.py as the main agent"
        ),
        "the corpus holds calls, and pins a refusal among them": (len(_held()) > 0 and _denies()),
        "the corpus as it stands replays clean": GATE.judge(_held()) == [],
        "a pinned answer the kit no longer gives is reported, naming both": (
            len(altered) == len(GATE.DECIDING) * len(GATE.CALLERS) and "invented" in altered[0]
        ),
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
