#!/usr/bin/env python3
"""The `--self-test` body of `cite.py`: one line per rule the resolver holds.

It lives beside the script rather than inside it so `cite.py` stays readable as
a grammar, a resolver and three modes, and
`python3 scripts/cite.py --self-test` runs it.

Every rule is pinned on a throwaway tree written for the case, so the rules stay
fixed while the checkout they would otherwise have been written against moves.
The resolver is imported by path and its module globals are set on that module,
so the tree a rule resolves against is the one the case just wrote.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

SCRIPT_PATH = Path(__file__).resolve().parent / "cite.py"


def _load_script() -> ModuleType:
    """Import the resolver by path, so a self-test run reaches the file beside it."""
    spec = importlib.util.spec_from_file_location("cite_under_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CITE = _load_script()


def _git(repo: Path, *args: str) -> None:
    """Run one git command in `repo`, failing loudly."""
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def self_test() -> int:
    """Pin the rules of the grammar and the three modes, on a throwaway tree."""
    keep, keep_plugin = CITE.ROOT, CITE.PLUGIN_ROOT
    rules = {}
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as away:
        tree, elsewhere = Path(tmp), Path(away)
        CITE.ROOT = tree
        (tree / "docs").mkdir()
        (tree / "other").mkdir()
        (tree / "docs" / "a.md").write_text("one\ntwo\nthree\n", encoding="utf-8")
        (tree / "docs" / "b.md").write_text("alpha\nbeta\n", encoding="utf-8")
        (tree / "docs" / "twin.md").write_text("x\n", encoding="utf-8")
        (tree / "other" / "twin.md").write_text("x\n", encoding="utf-8")
        (tree / "docs" / "pair.md").write_text("first half\nsecond half\n", encoding="utf-8")
        (tree / "docs" / "twice.md").write_text("same\nsame\n", encoding="utf-8")
        outside = elsewhere / "OUT.md"
        outside.write_text("out one\nout two\n", encoding="utf-8")

        def codes(doc: str) -> list[str]:
            return [row.split()[0] for row in CITE.report(doc)]

        rules["1 a path absent from the checkout is MISSING, one present is not"] = (
            codes("`docs/nope.md:1`") == ["MISSING"] and codes("`docs/a.md:1`") == []
        )
        rules["2 a span past the file's last line is RANGE, one ending on it is not"] = (
            codes("`docs/a.md:2-9`") == ["RANGE"] and codes("`docs/a.md:2-3`") == []
        )
        rules["3 a basename two paths carry is AMBIGUOUS, one path carries resolves"] = (
            codes("`twin.md:1`") == ["AMBIGUOUS"] and codes("`pair.md:1`") == []
        )
        rules["4 a bare number with no full citation before it is ORPHAN"] = codes("`:2`") == [
            "INHERITED-FROM",
            "ORPHAN",
        ] and codes("`docs/a.md:1` and `:2`") == ["INHERITED-FROM"]
        rules["5 INHERITED-FROM prints on a passing continuation and a failing one"] = codes(
            "`docs/a.md:1` `:2`"
        ) == ["INHERITED-FROM"] and codes("`docs/a.md:1` `:9`") == ["INHERITED-FROM", "RANGE"]
        rules["6 a bare number inherits the nearest preceding path, not the first"] = CITE.report(
            "`docs/a.md:1` `docs/b.md:1` `:2`"
        )[-1].endswith("docs/b.md") and CITE.report(
            "`docs/b.md:1` `docs/a.md:1` `:2`"
        )[-1].endswith("docs/a.md")
        rules["7 an anchor is read on the cited line only, never elsewhere in the file"] = codes(
            '`docs/a.md:2` "two"'
        ) == [] and codes('`docs/a.md:1` "two"') == ["QUOTE"]
        rules["8 an anchor on a span's second line passes, one on neither fails"] = codes(
            '`docs/pair.md:1-2` "second half"'
        ) == [] and codes('`docs/pair.md:1-2` "nowhere"') == ["QUOTE"]
        rules["9 a citation with no anchor is checked for existence only"] = codes(
            "the sentence says something else entirely `docs/a.md:2`"
        ) == [] and codes("the sentence says something else entirely `docs/a.md:9`") == ["RANGE"]
        rules["10 a path outside the checkout resolves, and prints CROSS-REPO"] = codes(
            f"`{outside}:1`"
        ) == ["CROSS-REPO"] and codes(f"`{elsewhere / 'gone.md'}:1`") == ["MISSING"]
        rules["11 only a backticked path:line is a citation"] = codes(
            "`docs/a.md:1` and docs/a.md:99 in prose"
        ) == [] and codes("`docs/a.md:1` and `docs/a.md:99`") == ["RANGE"]
        unique, _ = CITE.apply_fixes('`docs/a.md:1` "three"')
        several, _ = CITE.apply_fixes('`docs/twice.md:9` "same"')
        rules["12 --fix fills from a unique anchor and refuses on several"] = (
            unique == '`docs/a.md:3` "three"' and several == '`docs/twice.md:9` "same"'
        )
        both = '`docs/a.md:3` "three" and `docs/a.md:1` "two"'
        rules["13 --fix moves the citation that missed its anchor and no other"] = (
            CITE.apply_fixes(both)[0] == '`docs/a.md:3` "three" and `docs/a.md:2` "two"'
        )
        (elsewhere / ".git").mkdir()
        (elsewhere / "sub").mkdir()
        homeless = tree / "docs" / "plan.md"
        rules["14 the root is the document's own checkout, the script's only where it has none"] = (
            CITE.checkout_of(elsewhere / "sub" / "plan.md", tree) == elsewhere
            and CITE.checkout_of(homeless, tree) == tree
        )
        (elsewhere / "wt").mkdir()
        (elsewhere / "wt" / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        rules["15 a worktree's .git file marks its root ahead of the checkout above it"] = (
            CITE.checkout_of(elsewhere / "wt" / "plan.md", tree) == elsewhere / "wt"
        )

        (elsewhere / "target.md").write_text("one\ntwo\nthree\n", encoding="utf-8")
        good = elsewhere / "good.md"
        bad = elsewhere / "bad.md"
        good.write_text("`target.md:1`\n", encoding="utf-8")
        bad.write_text("`target.md:9`\n", encoding="utf-8")

        def call_all(paths: list[Path]) -> tuple[int, str]:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = CITE.check_all([str(p) for p in paths])
            return code, buf.getvalue()

        clean_code, clean_out = call_all([good])
        rules["16 --check-all exits 0 and prints nothing where every document passes"] = (
            clean_code == 0 and clean_out == ""
        )
        mixed_code, mixed_out = call_all([good, bad])
        rules["17 --check-all exits 1 and prefixes a failing row with its document"] = (
            mixed_code == 1 and f"{bad}: RANGE" in mixed_out and f"{good}:" not in mixed_out
        )

        (elsewhere2 := tree / "elsewhere2").mkdir()
        (elsewhere2 / ".git").mkdir()
        (elsewhere2 / "target.md").write_text("just one line\n", encoding="utf-8")
        own_root = elsewhere2 / "doc.md"
        own_root.write_text("`target.md:1`\n", encoding="utf-8")
        own_code, own_out = call_all([good, own_root])
        rules["18 --check-all resolves each document against its own checkout"] = (
            own_code == 0 and own_out == ""
        )

        CITE.ROOT = elsewhere2  # a checkout carrying no docs/a.md
        CITE.PLUGIN_ROOT = tree  # the kit's own checkout, where docs/a.md does live
        rules["19 ${CLAUDE_PLUGIN_ROOT}/ resolves against the kit's checkout, not the document's"] = (
            codes("`${CLAUDE_PLUGIN_ROOT}/docs/a.md:1`") == []
            and codes("`${CLAUDE_PLUGIN_ROOT}/docs/nope.md:1`") == ["MISSING"]
        )

        rules["20 --check-all with no document checks every tracked .md, and no untracked one"] = (
            _tracked_default_rule()
        )
    CITE.ROOT, CITE.PLUGIN_ROOT = keep, keep_plugin

    for label, ok in rules.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(rules.values()) else 1


def _tracked_default_rule() -> bool:
    """Rule 20, on its own throwaway git repo.

    A tracked document with a failing citation and an untracked one beside it:
    the default set is what `git ls-files` lists, so the run fails on the first
    and never reads the second.
    """
    with tempfile.TemporaryDirectory() as repo_dir:
        repo = Path(repo_dir)
        _git(repo, "init", "-q")
        (repo / "target.md").write_text("one\ntwo\n", encoding="utf-8")
        (repo / "tracked.md").write_text("`target.md:9`\n", encoding="utf-8")
        _git(repo, "add", "target.md", "tracked.md")
        (repo / "untracked.md").write_text("`target.md:8`\n", encoding="utf-8")

        here = Path.cwd()
        buf = io.StringIO()
        try:
            os.chdir(repo)
            with contextlib.redirect_stdout(buf):
                code = CITE.check_all([])
        finally:
            os.chdir(here)
        out = buf.getvalue()
    return code == 1 and "tracked.md: RANGE" in out and "untracked.md" not in out


if __name__ == "__main__":
    sys.exit(self_test())
