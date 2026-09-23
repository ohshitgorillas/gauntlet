#!/usr/bin/env python3
"""Soft-wrap enforcement for Markdown.

Project rule: documentation is soft-wrapped. One paragraph, list item, or
blockquote is one logical line; wrapping is the viewer's job, not the author's.
Hard-wrapped prose makes every later edit a reflow and every diff unreadable.

Three modes:

  --check FILE...   exit 1 if any file carries hard-wrapped prose (prints paths)
                    with no FILE, checks every `*.md` from `git ls-files
                    --cached --others --exclude-standard`, tracked or untracked
  --fix   FILE...   rewrite the files in place, joining continuation lines
  --self-test       one PASS or FAIL line per rule this gate holds

With no flag, reads a PostToolUse hook payload on stdin and blocks (exit 2) when
the file just written is hard-wrapped.

Preserved verbatim: leading YAML frontmatter, fenced code, headings, tables,
thematic breaks, HTML blocks, blank lines, indentation, blockquote prefixes, and
explicit hard breaks (a line ending in two spaces or a backslash).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^\s*#{1,6}\s")
TABLE_RE = re.compile(r"^\s*\|")
RULE_RE = re.compile(r"^\s*([-*_])\s*(?:\1\s*){2,}$")
HTML_RE = re.compile(r"^\s*<")
LIST_RE = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+")
QUOTE_RE = re.compile(r"^(\s*>+\s?)(.*)$")
SETEXT_RE = re.compile(r"^\s*(=+|-+)\s*$")
HARD_BREAK_RE = re.compile(r"(?:  +|\\)$")


def _is_block_start(text: str) -> bool:
    """A line that opens its own block and never joins the previous one."""
    return bool(
        not text.strip()
        or HEADING_RE.match(text)
        or TABLE_RE.match(text)
        or RULE_RE.match(text)
        or SETEXT_RE.match(text)
        or HTML_RE.match(text)
        or LIST_RE.match(text)
    )


def _frontmatter_end(lines: list[str]) -> int:
    """Index just past a leading YAML frontmatter block, or 0 if there is none.

    The fences are `---`, which also reads as a thematic break: a block start
    that opens a block rather than closing one. Left to the reflow loop the
    opening fence would glue itself to the first key (`--- description: ...`),
    so the whole block is handed through verbatim instead.
    """
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i + 1
    return 0  # unterminated — not frontmatter, reflow it like any other prose


class _Blocks:
    """The output lines, and the one logical line being gathered into them.

    A paragraph, list item or blockquote arrives as several source lines and
    leaves as one, so the gathering needs somewhere to sit between them. It
    sits here rather than in a closure over `reflow`, which is what lets the
    fence bookkeeping and the prose gathering be two readable functions
    instead of one long loop.
    """

    def __init__(self, out: list[str]) -> None:
        self.out = out
        self.block: list[str] = []
        self.prefix = ""

    def add(self, entry: str) -> None:
        """Continue the block being gathered."""
        self.block.append(entry)

    def open(self, text: str, prefix: str) -> None:
        """End the block being gathered and start a new one at this line."""
        self.flush()
        self.prefix, entry = _opening(text, prefix)
        self.block.append(entry)

    def flush(self) -> None:
        """Emit the gathered block, if there is one."""
        if self.block:
            self.out.append(self.prefix + " ".join(self.block))
            self.block, self.prefix = [], ""

    def hard_break(self) -> None:
        """Emit the gathered block with the two spaces that ended it."""
        self.out.append(self.prefix + " ".join(self.block) + "  ")
        self.block, self.prefix = [], ""


def _opening(text: str, prefix: str) -> tuple[str, str]:
    """The prefix a block starting at this line carries, and its first entry."""
    if LIST_RE.match(text) is None and not prefix:
        indent = re.match(r"^\s*", text)
        return (indent.group(0) if indent else ""), text.strip()
    return prefix, text.rstrip()


def _fence_line(line: str, in_fence: bool, marker: str, blocks: _Blocks) -> tuple[bool, str, bool]:
    """Fence bookkeeping for one line.

    Returns the fence state after it and whether the line was already emitted.
    Everything inside a fence is copied through untouched; a fence closes only
    on its own marker, so a ``~~~`` inside a ``````` block does not end it.
    """
    fence = FENCE_RE.match(line)
    if fence:
        if not in_fence:
            blocks.flush()
            blocks.out.append(line)
            return True, fence.group(1), True
        blocks.out.append(line)
        if line.strip().startswith(marker):
            return False, "", True
        return True, marker, True
    if in_fence:
        blocks.out.append(line)
        return True, marker, True
    return in_fence, marker, False


def _prose_line(line: str, blocks: _Blocks) -> None:
    """Gather one line of prose into the block being built."""
    quote = QUOTE_RE.match(line)
    prefix, text = (quote.group(1), quote.group(2)) if quote else ("", line)

    if not text.strip():
        blocks.flush()
        blocks.out.append(line)
        return

    if _is_block_start(text) or prefix != blocks.prefix or not blocks.block:
        blocks.open(text, prefix)
    else:
        blocks.add(text.strip())

    if HARD_BREAK_RE.search(line):
        # explicit hard break: the author meant this line to end here
        blocks.hard_break()


def reflow(source: str) -> str:
    lines = source.split("\n")
    fm = _frontmatter_end(lines)
    out: list[str] = lines[:fm]
    blocks = _Blocks(out)
    in_fence = False
    fence_marker = ""

    for line in lines[fm:]:
        in_fence, fence_marker, handled = _fence_line(line, in_fence, fence_marker, blocks)
        if not handled:
            _prose_line(line, blocks)

    blocks.flush()
    return "\n".join(out)


def tracked_md() -> list[str]:
    """Return the Markdown files of the tree the gate is run in, tracked or untracked.

    The no-argument default for `--check`. A gate that has to be handed its
    paths checks whatever the caller remembered; asking git instead means a new
    document is covered the moment it is written, and an ignored one never is.
    """
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "*.md"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return [name for name in listed.stdout.split("\0") if name and Path(name).is_file()]


def _offenders(paths: list[str]) -> list[Path]:
    bad = []
    for raw in paths:
        path = Path(raw)
        if path.suffix.lower() != ".md" or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if reflow(text) != text:
            bad.append(path)
    return bad


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] in ("--check", "--fix"):
        mode, paths = argv[0], argv[1:]
        if mode == "--fix":
            for raw in paths:
                path = Path(raw)
                if path.suffix.lower() != ".md" or not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8")
                new = reflow(text)
                if new != text:
                    path.write_text(new, encoding="utf-8")
                    print(f"reflowed {path}")
            return 0
        bad = _offenders(paths or tracked_md())
        for path in bad:
            print(f"hard-wrapped: {path}")
        return 1 if bad else 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    target = (payload.get("tool_input") or {}).get("file_path")
    if not target or not _offenders([target]):
        return 0
    print(
        f"{target} is hard-wrapped. Project rule: Markdown is soft-wrapped — one logical "
        "line per paragraph, list item, or blockquote, no wrapping at any column. "
        f"Fix with: python3 scripts/gates/md-softwrap.py --fix {target}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from md_softwrap_selftest import self_test

        sys.exit(self_test())
    sys.exit(main())
