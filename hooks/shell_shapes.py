#!/usr/bin/env python3
"""The `--config` reader a shell script calls.

    python3 hooks/shell_shapes.py --config <key>

`scripts/blind.sh` and `scripts/pair.sh` read every directory, scalar and
runner the project declares through this one command, so one reader serves the
hooks and the scripts alike. The table it answers from is
`lane_config.CONFIG_READERS`; nothing is imported from here. A hook or script
that needs a shape imports the module that defines it: `lane_config.py`,
`lane_paths.py`, `hook_payload.py` or `hook_shape.py`.

A fault is the exit status and a line on stderr, never a value on stdout: the
shell reading this substitutes what it is given, and a default printed here is
the wrong branch or the wrong lane, silently.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lane_config  # noqa: E402
import lane_declaration  # noqa: E402


def main(argv: list[str]) -> int:
    """Write the declared lines for the key on argv, or a fault on stderr."""
    if len(argv) != 3 or argv[1] != "--config":
        sys.stderr.write("usage: shell_shapes.py --config <key>\n")
        return 2
    fault = lane_declaration.config_fault()
    if fault is not None:
        sys.stderr.write(f"shell_shapes.py: {fault}\n")
        return 2
    sys.stdout.write("".join(line + "\n" for line in lane_config.config_lines(argv[2])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
