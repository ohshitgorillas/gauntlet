#!/usr/bin/env python3
"""Gate: a lane's answer to a real call changes only when somebody rewrites it.

    scripts/gates/verdict-corpus.py [--check]
    scripts/gates/verdict-corpus.py --harvest [TRANSCRIPT...]
    scripts/gates/verdict-corpus.py --self-test

The self-tests of the lane hooks are written from the same head that writes the
hook, so they agree with it by construction. What they cannot say is whether a
call the owner actually made still gets the answer it got. A matcher widened by
one character, a message reworded, a table row reordered: every one of those
leaves every self-test green and changes what a session feels like.

So the corpus is harvested rather than invented. `--harvest` reads session
transcripts, lifts the tool calls out of them, replays each one through the
deciding hooks, and writes what came back to `CORPUS`. `--check` replays the
same calls and compares. A difference is not a failure to be argued with: it is
a report that the kit now answers a real call differently, and the fix is to
look at the new answer and, where it is the intended one, harvest again. The
corpus is a tracked file, so that rewrite lands in a diff a reader can see.

Both the payload and the verdict are stored with the checkout root replaced by
`ROOT_TOKEN`, so a corpus harvested in one checkout replays in another.

The deciding hooks are the three that answer deny or silence. `bwrap-wrap.py`
emits a mount table rather than a verdict, and its bars are `wrap-scale.py`,
`wrap-runtime.py` and `wrap-concurrency.py`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

#: the harvested calls and the answers they drew, tracked beside the gate
CORPUS = ROOT / "scripts" / "gates" / "verdict-corpus.json"

#: the hooks that answer a call with a verdict rather than with a rewrite
DECIDING = ("lanes.py", "no-impl-reads.py")

#: who the call is replayed as. The main agent is the empty name, and the two
#: blind agents are the ones with a lane and without one: a corpus replayed as
#: the main agent alone is a corpus of silences, since these hooks answer the
#: main agent by letting it through.
CALLERS = ("", "scrivener", "juror")

#: what stands in for the checkout root inside a stored payload or verdict
ROOT_TOKEN = "<root>"

#: where the host keeps session transcripts, when none are named
TRANSCRIPTS = Path.home() / ".claude" / "projects"

#: a hook that has not decided one call by now is stuck
TIMEOUT = 30

#: the most calls one harvest keeps, newest first, after duplicates are dropped
LIMIT = 40


def _portable(value: Any, root: Path) -> Any:
    """One payload or verdict with the checkout root replaced by its token."""
    if isinstance(value, str):
        return value.replace(str(root), ROOT_TOKEN)
    if isinstance(value, dict):
        return {key: _portable(inner, root) for key, inner in value.items()}
    if isinstance(value, list):
        return [_portable(inner, root) for inner in value]
    return value


def _local(value: Any, root: Path) -> Any:
    """One stored payload or verdict with the token replaced by this checkout."""
    if isinstance(value, str):
        return value.replace(ROOT_TOKEN, str(root))
    if isinstance(value, dict):
        return {key: _local(inner, root) for key, inner in value.items()}
    if isinstance(value, list):
        return [_local(inner, root) for inner in value]
    return value


def calls(lines: list[str]) -> list[dict[str, Any]]:
    """Every tool call one transcript carries, as `(tool_name, tool_input)` pairs."""
    found = []
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message") if isinstance(event, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if isinstance(block.get("name"), str) and isinstance(block.get("input"), dict):
                found.append({"tool_name": block["name"], "tool_input": block["input"]})
    return found


def transcripts(named: list[str], root: Path = ROOT) -> list[Path]:
    """The transcript files to harvest: the ones named, or this checkout's own.

    This checkout's own, and not every session on the host: a corpus is a
    tracked file, and a harvest that reached into another project's sessions
    would commit that project's commands and paths into this repository.
    """
    if named:
        return [Path(one) for one in named]
    try:
        return sorted((TRANSCRIPTS / str(root).replace("/", "-")).glob("*.jsonl"))
    except OSError:
        return []


def distinct(found: list[dict[str, Any]], limit: int = LIMIT) -> list[dict[str, Any]]:
    """The newest `limit` calls, one per distinct call, in a stable order."""
    seen: dict[str, dict[str, Any]] = {}
    for call in reversed(found):
        seen.setdefault(json.dumps(call, sort_keys=True), call)
        if len(seen) >= limit:
            break
    return [seen[key] for key in sorted(seen)]


def answer(hook: str, call: dict[str, Any], agent: str, root: Path = ROOT) -> dict[str, Any]:
    """What one deciding hook says about one call from one caller."""
    payload = {**call, "cwd": str(root), "session_id": "verdict-corpus"}
    if agent:
        payload["agent_type"] = agent
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    environment["CLAUDE_PLUGIN_ROOT"] = str(root)
    try:
        done = subprocess.run(
            [sys.executable, str(root / "hooks" / hook)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return {"decision": "stuck", "reason": f"no answer in {TIMEOUT}s"}
    try:
        said = json.loads(done.stdout)
    except ValueError:
        return {"decision": "silent", "reason": done.stdout.strip()}
    specific = said.get("hookSpecificOutput") if isinstance(said, dict) else None
    if not isinstance(specific, dict):
        return {"decision": "silent", "reason": done.stdout.strip()}
    return {
        "decision": str(specific.get("permissionDecision", "silent")),
        "reason": str(specific.get("permissionDecisionReason", "")),
    }


def harvest(named: list[str], root: Path = ROOT) -> list[dict[str, Any]]:
    """Every distinct harvested call, with the verdict each deciding hook gives."""
    found: list[dict[str, Any]] = []
    for path in transcripts(named):
        try:
            found += calls(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            continue
    entries = []
    for call in distinct(_portable(found, root)):
        live = _local(call, root)
        entries.append(
            {
                "call": call,
                "verdicts": {
                    key(hook, agent): _portable(answer(hook, live, agent, root), root)
                    for hook in DECIDING
                    for agent in CALLERS
                },
            }
        )
    return entries


def key(hook: str, agent: str) -> str:
    """How one hook's answer to one caller is named in the corpus."""
    return f"{hook} as {agent or 'the main agent'}"


def corpus(path: Path = CORPUS) -> list[dict[str, Any]]:
    """The corpus as it stands on disk, or an empty one."""
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    return held if isinstance(held, list) else []


def judge(entries: list[dict[str, Any]], root: Path = ROOT) -> list[str]:
    """Every corpus entry the kit now answers differently, replayed one by one."""
    problems = []
    for index, entry in enumerate(entries):
        call = entry.get("call", {})
        for named, pinned in entry.get("verdicts", {}).items():
            hook, _, agent = named.partition(" as ")
            caller = "" if agent == "the main agent" else agent
            now = _portable(answer(hook, _local(call, root), caller, root), root)
            if now == pinned:
                continue
            problems.append(
                f"entry {index} ({call.get('tool_name')}): {named} answered "
                f"{pinned.get('decision')!r} and now answers {now.get('decision')!r}"
                + (f", {now.get('reason')!r}" if now.get("reason") != pinned.get("reason") else "")
            )
    return problems


def check(path: Path = CORPUS, root: Path = ROOT) -> int:
    """Replay the whole corpus against the live hooks."""
    entries = corpus(path)
    if not entries:
        print(
            f"{path.name} holds no call. Harvest one with --harvest before this gate says anything"
        )
        return 1
    problems = judge(entries, root)
    for problem in problems:
        print(problem)
    print(f"{len(entries)} call(s) x {len(DECIDING)} hook(s) x {len(CALLERS)} caller(s)")
    if problems:
        print(
            f"\n{len(problems)} problem(s). Where the new answer is the intended one, "
            "re-harvest, and the rewrite lands in the diff."
        )
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the corpus, or harvest a new one from the transcripts named."""
    if "--harvest" in argv:
        named = [one for one in argv[argv.index("--harvest") + 1 :] if not one.startswith("-")]
        entries = harvest(named)
        CORPUS.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"{len(entries)} call(s) harvested into {CORPUS.name}")
        return 0
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from verdict_corpus_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
