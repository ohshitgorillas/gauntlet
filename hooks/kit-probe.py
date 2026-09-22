#!/usr/bin/env python3
"""SessionStart hook: a kit missing a hook says so, instead of enforcing nothing.

    python3 hooks/kit-probe.py            # wired at SessionStart
    python3 hooks/kit-probe.py --self-test

Every lane in this kit is a hook the manifest names. A hook whose file is not
there denies nothing, and nothing in a session says so: Claude Code prints
`Hook script appears to be missing` once, into a stream nobody rereads, and the
session continues with that lane open. A session running that way looks exactly
like a session where the gate is passing.

So the kit reads itself at SessionStart and announces what is not there. The
paths come from the manifest rather than from a list kept here, because a list
kept here is the thing that goes stale.

What this cannot catch is its own absence. A kit whose whole directory is gone
takes this hook with it, and the only announcement left is the host's. The case
it does catch is the partial kit: a manifest that is live and a hook file under
it that is renamed, moved or deleted.

Silence is the whole of the good case. A SessionStart hook prints into every
session, so a kit that is whole says nothing at all, and the exit status is 0
either way -- a probe that failed a session because a hook is missing would
turn a degraded session into no session.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lane_paths import bypassed  # noqa: E402

#: the manifest, relative to the kit root
MANIFEST = ".claude-plugin/plugin.json"

#: a script path as a wired command spells one, after the variable prefix
PATH_RE = re.compile(r"(?:hooks|scripts)/[\w./-]+\.(?:py|sh)")

ANNOUNCE = (
    "gauntlet: {count} wired hook(s) absent from this kit: {names}. "
    "The lanes they hold are open for this session. Reinstall the plugin, or "
    "check {manifest} against the tree."
)


def kit_root() -> str:
    """The kit this hook is part of: what the host says, else where the file sits."""
    named = os.environ.get("CLAUDE_PLUGIN_ROOT")
    return named if named else str(Path(__file__).resolve().parents[1])


def _groups(data: dict[str, Any]) -> list[Any]:
    """Every hook group the manifest holds, whatever event each sits under."""
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return []
    return [group for listed in hooks.values() if isinstance(listed, list) for group in listed]


def wired(root: str) -> list[str]:
    """Every repository-relative script path the manifest wires, sorted, once each.

    An unreadable or malformed manifest wires nothing here. The host has its own
    complaint for that case, and a probe that guessed at a broken manifest would
    announce paths no dispatcher was ever going to run.
    """
    try:
        data = json.loads((Path(root) / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    found: set[str] = set()
    for group in _groups(data):
        for entry in group.get("hooks", []) if isinstance(group, dict) else []:
            command = entry.get("command") if isinstance(entry, dict) else None
            if isinstance(command, str):
                found.update(PATH_RE.findall(command))
    return sorted(found)


def missing(root: str) -> list[str]:
    """Every wired path the kit does not hold, in the order the manifest lists them."""
    return [path for path in wired(root) if not (Path(root) / path).is_file()]


def announce(gone: list[str]) -> str:
    """What a session is told about an incomplete kit; the empty string for a whole one."""
    if not gone:
        return ""
    return ANNOUNCE.format(count=len(gone), names=", ".join(gone), manifest=MANIFEST)


def main() -> None:
    """Announce an incomplete kit into the session, and exit 0 whatever it found."""
    if bypassed():
        return  # GAUNTLET=off: the owner's switch, read at the entry point only
    said = announce(missing(kit_root()))
    if said:
        print(said)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from kit_probe_selftest import run

        sys.exit(run())
    main()
