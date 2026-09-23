#!/usr/bin/env python3
"""Move a block between the reviewer, the writer and the tree.

    pair.sh open <slug>      cut the spec worktree and commit the reviewed block
    pair.sh respec <slug>    land a re-approved block on the open spec branch
    pair.sh red <slug>       run the suite there, and remove whole-file targets
    pair.sh check <slug>     converge the pair and gate it, landing nothing
    pair.sh merge <slug>     land a pair a check passed on the target branch
    pair.sh abort <slug>     take the pair back out, trees and branches alike
    pair.sh close <slug>     remove the pair's worktrees, keeping every commit
    pair.sh list             the pairs with a recorded base
    pair.sh review <slug>    the path the next spec round is written to
    pair.sh review plan <slug>     the same, for the next plan round
    pair.sh restore <slug> <rev>   put the approved block back as it was at <rev>
    pair.sh impl checkout <slug>   cut the implementation tree, or name the cut one
    pair.sh impl merge <slug>      merge the implementation tree back

The stdout of each is contract, and `${CLAUDE_PLUGIN_ROOT}/docs/agents.md` carries
the table. A blind writer reads these literals there, never here. This file owns
every line of that stdout: the four modules beside it print to stderr only, so a
progress line can never be read as a contract line.

`open` refuses on a mismatch because the approved spec is editable after the
reviewer passed it and the round file is not. Comparing the two is what makes
the block that reaches the writer the block that was reviewed, rather than the
latest one someone typed. `respec` makes the same comparison and one more: the
round has to be newer than the one the spec branch already committed.

`check` and `merge` are two verbs because gating and landing are two decisions.
`check` runs the gate over the combined tree and records the verdict beside the
three tips it ran over; it lands nothing, so a reading costs the owner nothing
and a red one survives the run that fixes it. `merge` reads that record and
refuses anything else: no record, a red one, or one taken over a revision that
has since moved is `UNCHECKED`, because a land on a gate reading of some other
tree is a land on a gate that never ran.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blocks  # noqa: E402
import converge  # noqa: E402

#: `lane_declaration` and `lane_paths` are imported here rather than taken from
#: `trees`, which does not re-export them. The import above put the hooks
#: directory on `sys.path`, so they follow it, and `steps` sorts in among them.
import lane_declaration  # noqa: E402
import lane_paths  # noqa: E402
import steps  # noqa: E402
import trees  # noqa: E402
from trees import REVIEWS, TARGET, die, git, git_ok, note, path  # noqa: E402

USAGE = (
    "usage: pair.sh open|respec|red|check|merge|abort|close <slug> | list"
    " | review [plan] <slug> | restore <slug> <rev> | impl checkout|merge <slug>"
)


def out(line: str) -> None:
    """One contract line. Every `print` in this repository's pair driver is here."""
    sys.stdout.write(line + "\n")


def check_slug(slug: str) -> str:
    """A slug names two branches and two directories. Keep it boring."""
    if not slug or not re.fullmatch(lane_paths.SLUG, slug):
        die("pair: slug '" + slug + "' -- letters, digits, dot, dash and underscore only.")
    return slug


# --- the pair -----------------------------------------------------------------


def cmd_open(slug: str) -> int:
    relative, text = steps.approved(slug)
    newest, matched = steps.round_match(slug, text)
    if not matched:
        out("MISMATCH " + newest)
        return 1

    tree = trees.spec_tree(slug)
    if Path(path(tree)).exists():
        die("pair: " + tree + " already exists -- abort that pair, or pick another slug.")
    if trees.exists(trees.spec_branch(slug)):
        die("pair: branch " + trees.spec_branch(slug) + " already exists.")

    base = git("rev-parse", "HEAD")
    git("worktree", "add", "--quiet", "-b", trees.spec_branch(slug), tree)
    trees.record_base(slug, base)
    trees.link_tooling(tree)
    steps.commit_block(slug, tree, relative, text)
    note("  base " + base + ", block at " + relative)
    out("OPEN " + tree)
    return 0


def cmd_respec(slug: str) -> int:
    relative, text = steps.approved(slug)
    tree = trees.spec_tree(slug)
    if not Path(path(tree)).is_dir():
        die("pair: no spec worktree at " + tree + " -- was this pair opened?")
    newest, matched = steps.round_match(slug, text)
    if not matched:
        out("MISMATCH " + newest)
        return 1
    if blocks.committed_section(tree, slug) == blocks.reviewer_section(text):
        die(
            "pair: "
            + newest
            + " is the round already committed on "
            + trees.spec_branch(slug)
            + " -- a re-approved block carries a new round,"
            " not the last one pasted under a changed block."
        )

    #: read before the write, against the block the branch holds rather than the
    #: file the write is about to replace. A respec that touches rows alone
    #: changed no contract line, so it owes no second owner word, and this is
    #: the whole evidence for that: the shortcut skips the owner, never the
    #: `arbiter`, whose round the comparison above has already matched.
    shortcut = blocks.collateral_only(blocks.committed_block(tree, slug), text)

    Path(path(tree, relative)).write_text(text, encoding="utf-8")
    if git_ok("diff", "--quiet", "HEAD", "--", relative, tree=tree):
        die("pair: " + relative + " matches the block at HEAD -- nothing for the delta to read.")
    #: the block alone. The writer may hold uncommitted tests in this tree, and a
    #: spec commit that swept them in would hide them from the next red run.
    git("add", "--", relative, tree=tree)
    if trees.in_tree(tree, ["git", "commit", "-q", "-m", "spec: " + slug]) != 0:
        die("pair: the spec commit in " + tree + " failed")
    token = "RESPEC COLLATERAL " if shortcut else "RESPEC "
    out(token + relative + " " + git("rev-parse", "HEAD", tree=tree))
    return 0


def cmd_red(slug: str) -> int:
    _, text = steps.approved(slug)
    tree = trees.spec_tree(slug)
    if not Path(path(tree)).is_dir():
        die("pair: no spec worktree at " + tree)
    blocks.strike_whole_files(tree, text)
    out(blocks.red_run(slug, tree, steps.pytest_argv()))
    return 0


def _brief(slug: str, tree: str, saved: str) -> list[str]:
    """The five lines a `bailiff` is briefed with, and the file they name."""
    return [
        "TEST CHECK " + slug,
        "spec commit: " + blocks.spec_commit(tree, slug),
        "red commit: " + (blocks.red_commit(slug) or "unknown"),
        "merge output: " + saved,
        "END TEST CHECK",
    ]


def _gate_it(slug: str, tree: str, text: str, has_impl: bool) -> int:
    """Rebase, combine and gate, recording the reading, with the lock held."""
    note("  [3/5] rebase onto " + TARGET)
    converge.rebase_if_moved(slug, has_impl)
    if has_impl:
        note("  [4/5] combine in the spec tree")
        converge.combine(slug)

    base = git("merge-base", TARGET, trees.spec_branch(slug))
    head = git("rev-parse", "HEAD", tree=tree)

    note("  [5/5] gate")
    passed = converge.gate(slug)
    #: the tips are read after the combine, so the reading names the revision
    #: the gate ran in rather than the one the verb was handed
    saved = blocks.merge_artifact(slug, base, head, tree, steps.tips(slug, tree, has_impl), passed)
    if passed:
        out("CHECK " + saved + " PASS")
        return 0
    mechanical = blocks.block_kind(text) in ("strike", "amend", "rehome")
    converge.report_red(tree, text, base, head, mechanical, saved)
    out("CHECK " + saved + " FAIL")
    return 1


def cmd_check(slug: str) -> int:
    text, tree, _, has_impl = steps.prepare(slug, "5")
    with converge.Lock():
        return _gate_it(slug, tree, text, has_impl)


def _converge_and_land(slug: str, tree: str, text: str, has_impl: bool) -> int:
    """Rebase, combine, read the gate reading and land, with the lock held."""
    note("  [3/6] rebase onto " + TARGET)
    converge.rebase_if_moved(slug, has_impl)
    if has_impl:
        note("  [4/6] combine in the spec tree")
        converge.combine(slug)

    base = git("merge-base", TARGET, trees.spec_branch(slug))
    head = git("rev-parse", "HEAD", tree=tree)
    mechanical = blocks.block_kind(text) in ("strike", "amend", "rehome")

    note("  [5/6] the gate reading")
    saved = steps.checked(slug, tree, has_impl)
    if saved is None:
        out("UNCHECKED " + slug)
        return 1

    if mechanical:
        #: no implementation phase, so no window for a test to soften in:
        #: the mechanical check takes the bailiff's round
        verdicts = blocks.strike_report(text, base, head, tree)
        for line in verdicts:
            out(line)
        if not all(line.startswith("OK ") for line in verdicts):
            die("pair: the landed tests do not match the block that approved them.")
    else:
        #: a block's `collateral:` rows, where it carries any. The reviewer round
        #: below rules on the behavior lines; these name tests no line pins, so
        #: the mechanical check is what holds them, and it runs before the land.
        rows = blocks.collateral_report(text, base, head, tree)
        for line in rows:
            out(line)
        if not all(line.startswith("OK ") for line in rows):
            die("pair: a collateral row's assertion did not survive the change.")

    note("  [6/6] land on " + TARGET)
    converge.land(slug)
    if not mechanical:  # a brief is of a block that landed; the tree stands until cleanup
        for line in _brief(slug, tree, saved):
            out(line)
    converge.cleanup(slug, has_impl)
    return 0


def cmd_merge(slug: str) -> int:
    text, tree, _, has_impl = steps.prepare(slug, "6")
    with converge.Lock():
        return _converge_and_land(slug, tree, text, has_impl)


def cmd_abort(slug: str) -> int:
    converge.abort(slug)
    out("ABORTED " + slug)
    return 0


def cmd_close(slug: str) -> int:
    """Remove the pair's worktrees, and leave every commit where it is.

    `abort` throws the pair away -- trees, branches and the recorded base. This
    is the other half: the trees go, the branches and the base stay, so what a
    pair committed is still on its branch to merge or read afterwards, and
    `list` still names the pair.

    A tree holding uncommitted work is refused, not removed. A red run the
    writer has not committed exists in no git object, so removing the tree that
    holds it is the one loss this script cannot undo. One line per tree, so a
    pair whose spec tree is clean and whose implementation tree is not gets
    both readings rather than one.
    """
    named = [
        tree for tree in (trees.spec_tree(slug), trees.impl_tree(slug)) if Path(path(tree)).is_dir()
    ]
    if not named:
        die("pair: no worktree for " + slug)
    status = 0
    for tree in named:
        if trees.dirty_files(tree):
            out("REFUSED " + tree + " uncommitted")
            status = 1
            continue
        trees.unlink_tooling(tree)
        git("worktree", "remove", tree)
        out("CLOSED " + tree)
    git("worktree", "prune", check=False)
    return status


def cmd_list() -> int:
    slugs = trees.open_pairs()
    if not slugs:
        out("NO PAIRS")
        return 0
    for slug in slugs:
        base = trees.read_base(slug) or "unknown"
        out("PAIR " + slug + " " + base + " " + converge.behind(base))
    return 0


# --- the paths a reviewer and the owner are handed -----------------------------


def cmd_review(first: str, second: str | None) -> int:
    """The path a reviewer writes its round to, counted here and handed to it.

    A reviewer cannot count the directory itself: `lanes.py` denies it
    every read of the reviewers' lane, so a reviewer left to pick its own `<N>`
    is guessing, and a guess that lands on a number already taken overwrites a
    round that exists in no git object and is gone.
    """
    infix = ""
    slug = first
    if first == "plan":
        infix = "plan."
        slug = second or ""
    check_slug(slug)
    #: the reviewer's Write is its own; the directory it writes into is not
    Path(path(REVIEWS)).mkdir(parents=True, exist_ok=True)
    number = blocks.highest_round(slug, infix) + 1
    out("REVIEW " + REVIEWS + "/" + slug + "." + infix + str(number) + ".txt")
    return 0


def cmd_restore(slug: str, rev: str | None) -> int:
    """The `git restore --source` step of `${CLAUDE_PLUGIN_ROOT}/docs/approved-specs.md`.

    The classifier carves out that one shell shape, and a subcommand keeps the
    carve-out in one place rather than in every transcript.
    """
    if not rev:
        die("usage: pair.sh restore <slug> <rev>")
    relative = blocks.spec_path(slug)
    git("restore", "--source", rev, "--", relative)
    out("RESTORED " + relative + " " + rev)
    return 0


def cmd_impl(verb: str, slug: str | None) -> int:
    """The implementation tree, cut beside the spec tree and merged back from it."""
    if not slug:
        die("usage: pair.sh impl checkout|merge <slug>")
    check_slug(slug)
    tree = trees.impl_tree(slug)
    if verb == "checkout":
        #: a second checkout of a slug already cut is the same tree, not a fresh
        #: one: re-cutting would discard the implementation in progress in it
        if not Path(path(tree)).is_dir():
            git("worktree", "add", "--quiet", "-b", trees.impl_branch(slug), tree)
            trees.link_tooling(tree)
        out("IMPL " + tree)
        return 0
    if verb == "merge":
        if not Path(path(tree)).is_dir():
            die("pair: no implementation worktree at " + tree)
        git("merge", "--no-edit", "-q", trees.impl_branch(slug))
        out("MERGED " + slug + " " + git("rev-parse", "HEAD"))
        return 0
    die("usage: pair.sh impl checkout|merge <slug>")
    return 2


# --- dispatch ------------------------------------------------------------------


def main(argv: list[str]) -> int:
    #: the driver converges onto `target_branch` and runs `gate_command`, both
    #: of them configured, so a declaration that will not load is a merge onto
    #: whatever the kit defaults to. It is a fault here, not a default.
    fault = lane_declaration.config_fault()
    if fault is not None:
        die("pair: " + fault)
    if not argv:
        die(USAGE)
    verb, rest = argv[0], argv[1:]

    if verb == "list":
        if rest:
            die(USAGE)
        return cmd_list()
    if not rest:
        die(USAGE)

    if verb == "review":
        return cmd_review(rest[0], rest[1] if len(rest) > 1 else None)
    if verb == "impl":
        return cmd_impl(rest[0], rest[1] if len(rest) > 1 else None)
    if verb == "restore":
        return cmd_restore(check_slug(rest[0]), rest[1] if len(rest) > 1 else None)

    one = {
        "open": cmd_open,
        "respec": cmd_respec,
        "red": cmd_red,
        "check": cmd_check,
        "merge": cmd_merge,
        "abort": cmd_abort,
        "close": cmd_close,
    }.get(verb)
    if one is None or len(rest) != 1:
        die(USAGE)
    return one(check_slug(rest[0]))


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        import selftest

        sys.exit(selftest.self_test())
    sys.exit(main(sys.argv[1:]))
