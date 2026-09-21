"""The steps `check` and `merge` share, and the reading one leaves for the other.

`pair.sh check` gates a pair and `pair.sh merge` lands one, and the first half
of each is the same half: the approved block, the two trees, the lane check and
the commit of both. It lives here so the two verbs cannot drift apart, and so
`cli.py` stays what it is -- dispatch and the contract lines.

Like `trees.py`, `blocks.py` and `converge.py`, nothing here prints to stdout.
The driver owns every contract line; a progress line from this module is
`note`, on stderr, and can never be read as one.
"""

from __future__ import annotations

import os
from pathlib import Path

import blocks
import lane_config
import trees
from trees import TARGET, die, git, git_ok, note, path


def approved(slug: str) -> tuple[str, str]:
    """The approved block's path and text, or an exit where there is none."""
    relative = blocks.spec_path(slug)
    text = blocks.read(relative)
    if text is None:
        die("pair: no approved spec at " + relative)
    return relative, text


def round_match(slug: str, text: str) -> tuple[str, bool]:
    """The newest round file, and whether the block's reviewer section is it.

    The path comes back either way, because the caller names it on the
    `MISMATCH` line. `MISMATCH` is a contract line and so is not printed here.
    """
    newest = blocks.newest_round(slug)
    if newest is None:
        die("pair: no reviewer round on disk for " + slug)
    return newest, blocks.reviewer_section(text) == (blocks.read(newest) or "")


def commit_block(slug: str, tree: str, relative: str, text: str) -> None:
    """Put the approved block on the spec branch, where the writer's brief reads it.

    The block reaches the lane as a file the reviewer wrote, tracked by the
    primary checkout or not. Every agent downstream reads it out of a commit
    rather than off disk: the `scrivener` refuses a spec no tree HEAD holds,
    `blocks.spec_commit` names the commit the `bailiff` is briefed with, and a
    delta names a `spec:` commit newer than this one. Staging before the
    comparison is what makes it answer for an untracked block too, which
    `git diff HEAD` on its own does not see. A branch already holding the block
    byte for byte takes no second commit.
    """
    Path(path(tree, relative)).write_text(text, encoding="utf-8")
    git("add", "--", relative, tree=tree)
    if git_ok("diff", "--cached", "--quiet", "HEAD", "--", relative, tree=tree):
        return
    if trees.in_tree(tree, ["git", "commit", "-q", "-m", "spec: " + slug]) != 0:
        die("pair: the spec commit in " + tree + " failed")


def pytest_argv() -> list[str]:
    """The configured python runner, as this checkout runs it.

    `pytest_command` from `blind-reads.json`, so a project that deselects a
    marker names it once there instead of editing this file and
    `scripts/blind.sh` both. A word carrying a slash is a path in the checkout
    and is made absolute, because the run happens with a worktree as its working
    directory; a bare word is on `PATH` and is left alone. `PYTEST` in the
    environment replaces the head word and keeps the configured arguments.
    """
    words = lane_config.pytest_command()
    head = os.environ.get("PYTEST") or words[0]
    if not Path(head).is_absolute() and "/" in head:
        head = path(head)
    return [head] + words[1:]


def check_lanes(tree: str, impl: str, has_impl: bool) -> None:
    """The disjoint-path rule over both trees, or an exit naming the files."""
    lanes = trees.lane_check(tree, "spec")
    if has_impl and not trees.lane_check(impl, "impl"):
        lanes = False
    if not lanes:
        die("pair: the lanes are what make this combine conflict-free; move those files.")


def prepare(slug: str, total: str) -> tuple[str, str, str, bool]:
    """The half `check` and `merge` share: the block, both trees, lanes, commits.

    `total` is the denominator of the step banners, because `check` ends at the
    gate in five steps and `merge` lands in six. The steps themselves are the
    same two, so they are counted here once rather than written out twice.
    """
    _, text = approved(slug)
    tree = trees.spec_tree(slug)
    impl = trees.impl_tree(slug)
    if not Path(path(tree)).is_dir():
        die("pair: no spec worktree at " + tree + " -- was this pair opened?")
    #: an implementation tree that was never cut is a tests-only pair, which is
    #: the ordinary shape of the three tests-only kinds: skipped, never fatal
    has_impl = Path(path(impl)).is_dir() and trees.exists(trees.impl_branch(slug))
    if not has_impl:
        note("  no implementation tree for " + slug + "; the spec tree lands alone")

    note("  [1/" + total + "] lane check")
    check_lanes(tree, impl, has_impl)

    note("  [2/" + total + "] commit both trees")
    trees.commit_tree(tree, "test: " + slug)
    if has_impl:
        trees.commit_tree(impl, "feat: " + slug)
    return text, tree, impl, has_impl


def tips(slug: str, tree: str, has_impl: bool) -> tuple[str, str, str]:
    """The three revisions a gate reading is taken over, in header order.

    The spec tip is read from the spec tree rather than from the branch name so
    that it is the same revision the gate ran in. A pair with no implementation
    tree carries `-`, which is a tip no rebase can produce and so never
    compares equal to one.
    """
    impl = git("rev-parse", trees.impl_branch(slug)) if has_impl else "-"
    return git("rev-parse", "HEAD", tree=tree), impl, git("rev-parse", TARGET)


def checked(slug: str, tree: str, has_impl: bool) -> str | None:
    """The newest merge artifact that passed the gate over these tips, or None.

    This is the whole of what `merge` trusts. A pair with no artifact, with a
    red one, or with one taken over a revision that is no longer the tip, has a
    gate reading that says nothing about what is about to land, and `merge`
    refuses it rather than landing on a measurement of some other tree.
    """
    newest = blocks.newest_merge(slug)
    if newest is None:
        return None
    header = blocks.check_header(blocks.read(newest) or "")
    if header is None or header[3] != "PASS":
        return None
    return newest if header[:3] == tips(slug, tree, has_impl) else None
