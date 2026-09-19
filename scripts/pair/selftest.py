"""Pins the parsing and the stdout literals of `cli.py`, without touching a checkout.

`cli.py --self-test` imports this module lazily and runs `self_test()`.
"""

from __future__ import annotations

import re
from pathlib import Path

import blocks  # noqa: E402

#: imported here rather than taken from `trees`, which does not re-export them.
import hook_shape  # noqa: E402
import lane_config  # noqa: E402
import lane_paths  # noqa: E402
import trees  # noqa: E402


def self_test() -> int:
    """Pin the parsing and the stdout literals, without touching a checkout."""
    block = (
        "slug: demo\nmotion: strike\n\n"
        "1. strike tests/test_a.py::test_x\n"
        "   assertion: assert 2 + 2 == 4\n"
        "2. strike tests/test_b.py\n"
        "\n--- reviewer ---\nREADY\n1  KEEP  the counter\n"
    )
    source = (Path(__file__).resolve().parent / "cli.py").read_text(encoding="utf-8")
    lines = {
        "the reviewer section is everything below the divider, verbatim": (
            blocks.reviewer_section(block) == "READY\n1  KEEP  the counter\n"
            and blocks.reviewer_section("no divider here\n") == ""
        ),
        "a block's kind is its first kind: or motion: line": (
            blocks.block_kind(block) == "strike"
            and blocks.block_kind("slug: x\nkind: new\n") == "new"
            and blocks.block_kind("slug: x\n") == ""
        ),
        "every strike target parses, and only the whole-file ones are the script's": (
            blocks.strike_targets(block) == ["tests/test_a.py::test_x", "tests/test_b.py"]
            and blocks.whole_file_targets(block) == ["tests/test_b.py"]
        ),
        "the merge artifact names its three headings in one order": (
            blocks.HEADINGS == ("test files:", "diff:", "red output:")
        ),
        "the branch and the gate are what the configuration says they are": (
            lane_config.target_branch() == trees.TARGET and lane_config.gate_command() == trees.GATE
        ),
        "every contract literal this driver prints is in this file": (
            all(
                token in source
                for token in (
                    "OPEN ",
                    "MISMATCH ",
                    "RESPEC ",
                    "REVIEW ",
                    "RESTORED ",
                    "IMPL ",
                    "MERGED ",
                    "ABORTED ",
                    "CLOSED ",
                    "REFUSED ",
                    "PAIR ",
                    "NO PAIRS",
                    "TEST CHECK ",
                    "END TEST CHECK",
                )
            )
        ),
        "the libraries beside this file write no contract line": (
            all(
                "sys.stdout.write" not in _sibling(name)
                for name in ("trees.py", "blocks.py", "converge.py")
            )
        ),
        "a slug is one boring name, and a path is not one": (
            _accepts("demo") and not _accepts("../etc") and not _accepts("a/b") and not _accepts("")
        ),
    }
    return hook_shape.report(lines)


def _sibling(name: str) -> str:
    return (Path(__file__).resolve().parent / name).read_text(encoding="utf-8")


def _accepts(slug: str) -> bool:
    """Whether `check_slug` takes a name, without ending the process on a no."""
    return bool(slug) and bool(re.fullmatch(lane_paths.SLUG, slug))
