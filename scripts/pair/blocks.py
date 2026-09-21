#!/usr/bin/env python3
"""The approved block, the rounds beside it, and the evidence a run leaves.

An approved block is one file in the reviewer's lane. Everything above the
`--- reviewer ---` divider is the contract; everything below it is the
reviewer's own output, and `open` refuses a pair whose section differs from the
round file on disk, because the block is editable after the reviewer passed it
and the round is not.

Like `trees.py`, nothing here prints to stdout.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path
from types import ModuleType

import trees
from trees import GAUNTLET, REVIEWS, SPECS, TESTS, git, git_out, note, path

DIVIDER = "--- reviewer ---"

#: `N. strike <target>` of a committed block, targets only
_STRIKE = re.compile(r"^\s*\d+\.\s*strike\s+(?P<target>.*?)\s*$")
#: the structure line: `kind:` for a block that writes tests, `motion:` for one
#: that removes or moves them
_KIND = re.compile(r"^(?:kind|motion):\s*(?P<kind>.*?)\s*$")
#: the header of the `collateral:` section, where a `kind:` block carries one
_COLLATERAL = re.compile(r"^\s*collateral:\s*$")

#: the three headings `<gauntlet dir>/merge/<slug>.txt` carries, in this order
HEADINGS = ("test files:", "diff:", "red output:")


def _load_strike_diff() -> ModuleType:
    """`scripts/strike-diff.py`, imported rather than run.

    Its name is not an identifier, so it is loaded by path. A subprocess would
    be a second interpreter start and a second copy of the config, for a
    function this process can simply call.
    """
    source = str(Path(__file__).resolve().parents[1] / "strike-diff.py")
    spec = importlib.util.spec_from_file_location("strike_diff", source)
    if spec is None or spec.loader is None:  # pragma: no cover - a broken checkout
        sys.exit("pair: no scripts/strike-diff.py beside scripts/pair/")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def spec_path(slug: str) -> str:
    return SPECS + "/" + slug + ".txt"


def red_path(slug: str) -> str:
    return GAUNTLET + "/red/" + slug + ".txt"


def merge_path(slug: str) -> str:
    return GAUNTLET + "/merge/" + slug + ".txt"


def read(relative: str) -> str | None:
    try:
        return Path(path(relative)).read_text(encoding="utf-8")
    except OSError:
        return None


def reviewer_section(text: str) -> str:
    """Everything below the divider, verbatim, or the empty string for none."""
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.rstrip("\n") == DIVIDER:
            return "".join(lines[index + 1 :])
    return ""


def highest_round(slug: str, infix: str) -> int:
    """The highest `<N>` on disk for a slug in one round series, or 0 for none.

    The series is named by its infix: empty for the spec rounds
    `<slug>.<N>.txt`, `plan.` for the plan rounds `<slug>.plan.<N>.txt`. A name
    that is not a numbered round of the series asked for is not counted, so the
    two series never read as each other.
    """
    shape = re.compile(re.escape(slug + "." + infix) + r"(\d+)\.txt\Z")
    best = 0
    try:
        names = [entry.name for entry in Path(path(REVIEWS)).iterdir()]
    except OSError:
        return 0
    for name in names:
        found = shape.match(name)
        if found:
            best = max(best, int(found.group(1)))
    return best


def newest_round(slug: str) -> str | None:
    """The newest spec round the reviewer has written for this slug, or None."""
    highest = highest_round(slug, "")
    if highest == 0:
        return None
    return REVIEWS + "/" + slug + "." + str(highest) + ".txt"


def block_kind(text: str) -> str:
    for line in text.splitlines():
        found = _KIND.match(line)
        if found:
            return found.group("kind")
    return ""


def strike_targets(text: str) -> list[str]:
    targets = []
    for line in text.splitlines():
        found = _STRIKE.match(line)
        if found and found.group("target"):
            targets.append(found.group("target"))
    return targets


def whole_file_targets(text: str) -> list[str]:
    """The targets no writer can remove.

    A single test is an `Edit` and the writer's; a whole file cannot be, because
    the lane hook denies every agent the shell it would take.
    """
    return [target for target in strike_targets(text) if "::" not in target]


def red_run(slug: str, tree: str, runner: list[str]) -> str:
    """Run the suite in the spec tree and save the output. Returns its path.

    `runner` is the configured invocation, whole: the caller resolves it, and
    the only word this function adds to it is its own.
    """
    saved = red_path(slug)
    where = Path(path(saved))
    where.parent.mkdir(parents=True, exist_ok=True)
    #: verbose, so a passing test is named rather than summarized as a dot: the
    #: juror rules on the names this file carries and on nothing else
    output = trees.capture_in_tree(tree, list(runner) + ["-v"])
    where.write_text(output, encoding="utf-8")
    return saved


def merge_artifact(slug: str, base: str, head: str, tree: str) -> str:
    """Write `<gauntlet dir>/merge/<slug>.txt` and return its path.

    Evidence by path, not by paste: the main agent only carries the brief, and
    the `bailiff` reads this file itself.
    """
    saved = merge_path(slug)
    where = Path(path(saved))
    where.parent.mkdir(parents=True, exist_ok=True)
    names = git_out("diff", "--name-only", base, head, "--", TESTS + "/", tree=tree)
    diff = git_out("diff", base, head, "--", TESTS + "/", tree=tree)
    #: no red log on disk is a complete brief with an empty section, not an
    #: abort that leaves the block unterminated
    red = read(red_path(slug)) or ""
    with where.open("w", encoding="utf-8") as handle:
        handle.write(HEADINGS[0] + "\n" + names)
        handle.write(HEADINGS[1] + "\n" + diff)
        handle.write(HEADINGS[2] + "\n" + red)
    return saved


def strike_report(block: str, base: str, head: str, tree: str) -> list[str]:
    """The `scripts/strike-diff.py` verdicts for a landed tests-only change.

    That module runs git in the process's own directory, so the call is made
    from the tree being checked and the directory is put back afterwards.
    """
    module = _load_strike_diff()
    here = Path.cwd()
    os.chdir(path(tree))
    try:
        verdicts: list[str] = module.report(block, base, head)
        return verdicts
    finally:
        os.chdir(here)


def collateral_targets(block: str) -> list[str]:
    """The targets of the block's `collateral:` rows, in block order.

    Parsed by the same module that rules on them at merge, so the grammar this
    driver reads and the grammar the check reads cannot drift apart.
    """
    module = _load_strike_diff()
    targets: list[str] = [row.target for row in module.parse_collateral(block)]
    return targets


def collateral_report(block: str, base: str, head: str, tree: str) -> list[str]:
    """The `scripts/strike-diff.py` verdicts for a `kind:` block's rows.

    Same `chdir` discipline as `strike_report`, for the same reason: that
    module runs git in the process's own directory.
    """
    module = _load_strike_diff()
    here = Path.cwd()
    os.chdir(path(tree))
    try:
        verdicts: list[str] = module.collateral_report(block, base, head)
        return verdicts
    finally:
        os.chdir(here)


def committed_block(tree: str, slug: str) -> str:
    """The approved block as the spec branch last committed it, whole."""
    return git_out("show", "HEAD:" + spec_path(slug), tree=tree)


def committed_section(tree: str, slug: str) -> str:
    """The block's reviewer section as the spec branch last committed it.

    Matching the block against the newest round proves the round was pasted
    verbatim; it cannot tell that round from the one already committed. A
    re-approved block carries a new round, so comparing the two is what keeps
    the last `READY` from being pasted under a changed block.
    """
    return reviewer_section(committed_block(tree, slug))


def _parted(text: str) -> tuple[str, str] | None:
    """A block's contract above its `collateral:` header, and the rows beneath.

    `None` where the text carries no structure line or no `brief:` section:
    those are the two pieces the shortcut below has to hold constant, and a
    text they cannot be read out of is one this comparison does not rule on.
    """
    contract, _, _ = text.partition(DIVIDER)
    rows = contract.splitlines(keepends=True)
    if not any(_KIND.match(row) for row in rows):
        return None
    if not any(row.startswith("brief:") for row in rows):
        return None
    for index, row in enumerate(rows):
        if _COLLATERAL.match(row):
            return "".join(rows[:index]), "".join(rows[index:])
    return "".join(rows), ""


def collateral_only(before: str, after: str) -> bool:
    """Whether the two blocks differ in `collateral:` rows and nothing else.

    This is the whole guard on the respec shortcut, so it is a comparison by
    section and never by how many lines differ: a respec that rewrites one
    behavior line and one row changes the contract, and the owner reads a
    changed contract line. Either text this cannot be parted into its pieces
    answers no, and the respec pays the full price.
    """
    two = _parted(before), _parted(after)
    if two[0] is None or two[1] is None:
        return False
    return two[0][0] == two[1][0] and two[0][1] != two[1][1]


def strike_whole_files(tree: str, block: str) -> None:
    """Remove the whole-file targets of a block from a tree.

    Two passes on purpose: every target is validated before any file goes, so a
    block whose third line names source leaves the first two files standing.
    """
    targets = whole_file_targets(block)
    prefix = TESTS + "/"
    for target in targets:
        if not target.startswith(prefix):
            trees.die(
                "pair: strike target '"
                + target
                + "' is not under "
                + prefix
                + " -- a strike motion removes tests, never source."
            )
        if ".." in target:
            trees.die(
                "pair: strike target '" + target + "' contains '..' -- name the path"
                " as it sits under " + prefix + "."
            )
    for target in targets:
        try:
            Path(path(tree, target)).unlink()
        except OSError:
            continue
        note("  struck " + target)


def spec_commit(tree: str, slug: str) -> str:
    """The commit that last wrote the block, as that tree's HEAD reaches it.

    A commit rather than the block's object name, because the one shell the
    `bailiff` has is `scripts/blind.sh show <spec-commit> <slug>`, which spells
    `git show <rev>:<path>`. An object name there resolves to no tree and the
    reviewer is left reading the block off the working copy instead of the
    landed one.
    """
    found = git("log", "-1", "--format=%H", "HEAD", "--", spec_path(slug), tree=tree, check=False)
    return found or "unknown"
