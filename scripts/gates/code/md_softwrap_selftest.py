#!/usr/bin/env python3
"""The `--self-test` body of `md-softwrap.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays a reflow and
two modes, and `python3 scripts/gates/code/md-softwrap.py --self-test` runs it.

Three shapes are covered, which are the three a caller meets. A hard-wrapped
file is refused by `--check` and named on stdout. A soft-wrapped file passes
`--check` silently and survives a reflow byte for byte, so the fixer is not a
rewriter. `--fix` joins the continuation lines on disk and leaves everything the
reflow preserves — fences, headings, tables, frontmatter, hard breaks — where it
found them.
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "md-softwrap.py"

HARD = "A paragraph that the author\nwrapped by hand at some column\nnobody agreed on.\n"
SOFT = "A paragraph that the author left on one logical line, however long it runs.\n"

FENCED = "Prose.\n\n```python\nx = 1\ny = 2\n```\n"
TABLE = "| a | b |\n| - | - |\n| 1 | 2 |\n"
FRONTMATTER = "---\ndescription: a thing\n---\n\nProse on one line.\n"
HARD_BREAK = "First line ending in a break  \nSecond line.\n"
QUOTED = "> a quote wrapped\n> by hand.\n"
LIST = "- one item\n- another item\n"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location("md_softwrap_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _run(mode: str, files: dict[str, str]) -> tuple[int, str, dict[str, str]]:
    """Write `files` to a throwaway tree, run the gate's mode over them, and report.

    Returns the exit status, what landed on stdout, and the files as they are
    left on disk, so a `--fix` case can read back what it rewrote.
    """
    argv = sys.argv
    with tempfile.TemporaryDirectory() as tmp:
        paths = {}
        for name, text in files.items():
            path = Path(tmp) / name
            path.write_text(text, encoding="utf-8")
            paths[name] = path
        out = io.StringIO()
        sys.argv = ["md-softwrap.py", mode, *(str(path) for path in paths.values())]
        try:
            with redirect_stdout(out):
                status = GATE.main()
        finally:
            sys.argv = argv
        left = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    return status, out.getvalue(), left


def _run_tracked(files: dict[str, str], tracked: list[str]) -> tuple[int, str]:
    """Run bare `--check` in a throwaway git tree, with `tracked` added to its index.

    The no-argument default asks git for the tracked and the untracked files, so
    the only honest test of it is a real checkout: an untracked offender is read
    beside a tracked one, and an ignored one is left out, which proves the gate
    is reading `git ls-files` rather than the directory.
    """
    argv, cwd = sys.argv, Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "init", "-q", tmp], check=True, timeout=60)
        for name, text in files.items():
            (Path(tmp) / name).write_text(text, encoding="utf-8")
        if tracked:
            subprocess.run(["git", "-C", tmp, "add", "-N", *tracked], check=True, timeout=60)
        out = io.StringIO()
        sys.argv = ["md-softwrap.py", "--check"]
        try:
            os.chdir(tmp)
            with redirect_stdout(out):
                status = GATE.main()
        finally:
            os.chdir(cwd)
            sys.argv = argv
    return status, out.getvalue()


def self_test() -> int:
    """One PASS or FAIL per rule this gate exists to hold."""
    failed = 0

    def check(rule: str, got: object, want: object) -> None:
        nonlocal failed
        if got == want:
            print(f"PASS {rule}")
        else:
            failed += 1
            print(f"FAIL {rule}: {got!r} != {want!r}")

    status, out, _ = _run("--check", {"doc.md": HARD})
    check("--check refuses a hard-wrapped file", status, 1)
    check("--check names the hard-wrapped file on stdout", "doc.md" in out, True)

    status, out, _ = _run("--check", {"doc.md": SOFT})
    check("--check passes a soft-wrapped file silently", (status, out), (0, ""))

    status, _, _ = _run("--check", {"good.md": SOFT, "bad.md": HARD})
    check("one hard-wrapped file among soft ones refuses the run", status, 1)

    _, out, _ = _run("--check", {"good.md": SOFT, "bad.md": HARD})
    check("the soft-wrapped file beside it is not named", "good.md" in out, False)

    status, out, _ = _run("--check", {"notes.txt": HARD})
    check("--check ignores a file that is not markdown", (status, out), (0, ""))

    check(
        "a hard-wrapped paragraph reflows onto one line",
        GATE.reflow(HARD),
        "A paragraph that the author wrapped by hand at some column nobody agreed on.\n",
    )

    for name, text in (
        ("fenced code", FENCED),
        ("a table", TABLE),
        ("frontmatter", FRONTMATTER),
        ("a hard break", HARD_BREAK),
        ("a list", LIST),
    ):
        check(f"{name} survives a reflow unchanged", GATE.reflow(text), text)

    check(
        "a hand-wrapped blockquote reflows onto one line",
        GATE.reflow(QUOTED),
        "> a quote wrapped by hand.\n",
    )

    status, out, left = _run("--fix", {"doc.md": HARD})
    check("--fix exits zero", status, 0)
    check("--fix joins the continuation lines on disk", left["doc.md"], GATE.reflow(HARD))
    check("--fix says which file it reflowed", "doc.md" in out, True)

    _, _, left = _run("--fix", {"doc.md": HARD})
    check(
        "a file --fix rewrote then passes --check",
        _run("--check", {"doc.md": left["doc.md"]})[0],
        0,
    )

    status, out, left = _run("--fix", {"doc.md": SOFT})
    check("--fix leaves a soft-wrapped file byte for byte", left["doc.md"], SOFT)
    check("--fix says nothing about a file it did not rewrite", out, "")

    _, _, left = _run("--fix", {"notes.txt": HARD})
    check("--fix ignores a file that is not markdown", left["notes.txt"], HARD)

    status, out = _run_tracked({"doc.md": HARD, "ok.md": SOFT}, ["doc.md", "ok.md"])
    check(
        "--check with no paths refuses a tracked hard-wrapped file",
        (status, "doc.md" in out),
        (1, True),
    )

    status, out = _run_tracked({"loose.md": HARD, "ok.md": SOFT}, ["ok.md"])
    check(
        "--check with no paths refuses an untracked hard-wrapped file",
        (status, "loose.md" in out),
        (1, True),
    )

    status, out = _run_tracked({".gitignore": "loose.md\n", "loose.md": HARD, "ok.md": SOFT}, [])
    check("--check with no paths ignores a gitignored hard-wrapped file", (status, out), (0, ""))

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
