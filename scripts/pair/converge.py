#!/usr/bin/env python3
"""Converging a pair: rebase, combine, gate, land.

`merge` touches the target branch only at the very end, and in this order:

    1. lane check   the spec tree confined to the tests directory, the
                    implementation tree kept out of it
    2. commit       both trees
    3. rebase       both branches onto the target branch, if it moved under them
    4. combine      the implementation branch merged into the SPEC tree
    5. gate         the configured gate command in that combined tree; a red
                    gate stops here and the target branch never sees it
    6. land         the target branch fast-forwarded to it, branches and trees
                    removed

Steps 3 to 6 hold a lock, so two sessions converging at once queue instead of
racing the branch tip. Every land is `--ff-only`; nothing is ever force-pushed.

The branch and the gate are read from `.claude/blind-reads.json`, like
every directory the kit names. Neither is a literal here.
"""

from __future__ import annotations

import fcntl
import shlex
import subprocess
from pathlib import Path
from typing import TextIO

import blocks
import trees
from trees import GATE, TARGET, die, exists, git, git_ok, note, path


def report_red(slug: str, tree: str, text: str, base: str, head: str, mechanical: bool) -> None:
    """What a red gate in the combined tree leaves behind, all of it on stderr.

    Nothing landed, so nothing on stdout should read as the brief of a merged
    block. Every line here is `note`, which is why it sits in this module and
    not beside the driver's contract lines.
    """
    note("")
    note("pair: the gate is red in the combined tree. " + TARGET + " is untouched")
    note("and both trees are left exactly as they are: " + tree)
    note("A failing test here means the block and the code disagree. The code is")
    note("wrong and the fix lands in the implementation tree, or the block is wrong")
    note("and it goes back for re-approval. Tests are not edited to pass.")
    if mechanical:
        for line in blocks.strike_report(text, base, head, tree):
            note("  " + line)
    else:
        note("  merge output: " + blocks.merge_artifact(slug, base, head, tree))


class Lock:
    """`flock` on `.claude/worktrees/.pair.lock`, held for the whole converge."""

    def __init__(self) -> None:
        self.handle: TextIO | None = None

    def __enter__(self) -> Lock:
        Path(path(trees.WORKTREES)).mkdir(parents=True, exist_ok=True)
        self.handle = Path(path(trees.LOCK)).open("w", encoding="utf-8")
        note("  waiting for the pair lock...")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *_exc: object) -> None:
        if self.handle is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()


def rebase_if_moved(slug: str, has_impl: bool) -> None:
    """Replay both branches onto the target branch, where it moved under them.

    "Moved" is ancestry, not the recorded base, for the same reason
    `tree_files` measures from a merge base. A pair cut while another session
    was landing sits on a tip ahead of its own base file with nothing to
    rebase; measured against that file it reads as moved, and the guard below
    would then refuse a rebase that was never needed.
    """
    spec = trees.spec_tree(slug)
    impl = trees.impl_tree(slug)
    tip = git("rev-parse", TARGET)
    points = [git("merge-base", TARGET, "HEAD", tree=spec)]
    if has_impl:
        points.append(git("merge-base", TARGET, "HEAD", tree=impl))
    if all(point == tip for point in points):
        note("  " + TARGET + " has not moved under " + slug)
        return

    moved = git("rev-list", "--count", points[0] + ".." + tip)
    note("  " + TARGET + " moved " + moved + " commit(s) under " + slug + " -- rebasing")
    #: a re-run after a red gate reaches here with step 4's combine already on
    #: the spec branch. A plain rebase drops merge commits and replays their
    #: side, so it would flatten that combine and duplicate the implementation
    #: commits the other rebase is about to rewrite. Stop instead of corrupting.
    if git("rev-list", "--merges", points[0] + "..HEAD", tree=spec):
        die(
            "pair: " + TARGET + " moved after " + slug + " was already combined;"
            " rebasing " + trees.spec_branch(slug) + " would flatten that merge and"
            " duplicate " + trees.impl_branch(slug) + "'s commits. Rebase it by hand"
            " in " + spec + ", keeping the combine, and rerun."
        )
    if has_impl and not git_ok("rebase", "--quiet", TARGET, tree=impl):
        die(
            "pair: "
            + trees.impl_branch(slug)
            + " does not rebase onto "
            + TARGET
            + " cleanly -- resolve it in "
            + impl
            + " and rerun."
        )
    if not git_ok("rebase", "--quiet", TARGET, tree=spec):
        die(
            "pair: "
            + trees.spec_branch(slug)
            + " does not rebase onto "
            + TARGET
            + " cleanly -- resolve it in "
            + spec
            + " and rerun."
        )


def combine(slug: str) -> None:
    """Merge the implementation branch into the spec tree.

    An implementation branch already an ancestor of the spec branch is a combine
    that has run: the spec tree already holds every commit the merge would
    bring, so the step is skipped and the converge carries on to the gate. A
    second `--no-ff` merge commit over one that already landed would flatten
    nothing and prove nothing, which is why it is skipped rather than repeated.
    A re-run after a red gate arrives in exactly this state, and the way out of
    a red gate that re-approves the block leaves the branch an ancestor, so
    stopping here would strand the pair with no verb that lands it.
    """
    spec = trees.spec_tree(slug)
    branch = trees.impl_branch(slug)
    if git("rev-list", "--count", TARGET + ".." + branch) == "0":
        note("  " + branch + " carries no commit of its own; nothing to combine")
        return
    if git_ok("merge-base", "--is-ancestor", branch, "HEAD", tree=spec):
        note(
            "  "
            + branch
            + " is already combined into "
            + trees.spec_branch(slug)
            + "; going straight to the gate"
        )
        return
    if not git_ok("merge", "--no-ff", "--no-edit", branch, tree=spec):
        die(
            "pair: merging "
            + branch
            + " into "
            + trees.spec_branch(slug)
            + " conflicted -- the lanes should have prevented this; resolve in "
            + spec
            + "."
        )
    note("  " + spec + " now holds the tests and the implementation")


def gate(slug: str) -> bool:
    """Run the configured gate command in the combined tree.

    `shlex.split`, not a shell: the command is configuration, and a shell would
    make a second command smuggled into that value run here.
    """
    argv = shlex.split(GATE)
    if not argv:
        die("pair: gate_command in .claude/blind-reads.json is empty")
    note("  gate: " + GATE)
    return trees.in_tree(trees.spec_tree(slug), argv) == 0


def shadowing(branch: str) -> list[str]:
    """Untracked files in the primary checkout the land would write, byte for byte identical.

    The approved block is such a file. It reaches the lane as a file the
    reviewer wrote in the primary checkout, untracked there, and `pair.sh open`
    commits it on the spec branch; the land then brings that commit back. git
    refuses to fast-forward over an untracked working tree file even where the
    blob landing on it is that file byte for byte, so the pair died on a copy of
    the commit it was landing.

    Identical is the whole of the test. A tracked file is an ordinary local
    change and not this function's business, and an untracked file whose content
    differs is the owner's work, which the land must keep refusing rather than
    quietly delete.
    """
    named = []
    for name in git("diff", "--name-only", "HEAD", branch).splitlines():
        if not name or git_ok("ls-files", "--error-unmatch", "--", name):
            continue
        local = Path(path(name))
        if local.is_symlink() or not local.is_file():
            continue
        landing = git("rev-parse", branch + ":" + name, check=False)
        if landing and landing == git("hash-object", "--", name, check=False):
            named.append(name)
    return named


def land(slug: str) -> str:
    """Fast-forward the target branch onto the spec branch. Returns the commit."""
    branch = trees.spec_branch(slug)
    on = git("rev-parse", "--abbrev-ref", "HEAD")
    if on != TARGET:
        die(
            "pair: the primary checkout is on "
            + on
            + ", and a pair lands on "
            + TARGET
            + " -- check out "
            + TARGET
            + " and rerun."
        )
    gave_way = shadowing(branch)
    for name in gave_way:
        Path(path(name)).unlink()
        note("  " + name + ": the untracked copy gives way to the commit landing on it")
    if not git_ok("merge", "--ff-only", branch):
        #: the land refused for some other file, so nothing came back to take
        #: the place of the copies taken out of the way: write them back rather
        #: than leave the checkout short a file the refusal did not name
        for name in gave_way:
            #: bytes, and `cat-file blob` rather than `show`: a restored copy
            #: has to be the file that was there, newlines and all
            blob = subprocess.run(
                ("git", "-C", path(), "cat-file", "blob", branch + ":" + name),
                capture_output=True,
                check=False,
                timeout=60,
            ).stdout
            Path(path(name)).write_bytes(blob)
        die(
            "pair: "
            + TARGET
            + " will not fast-forward to "
            + branch
            + " -- the primary checkout may carry local changes over the same files."
        )
    return git("rev-parse", "HEAD")


def cleanup(slug: str, has_impl: bool) -> None:
    """Remove both trees, both branches and the recorded base."""
    for tree in [trees.spec_tree(slug)] + ([trees.impl_tree(slug)] if has_impl else []):
        trees.unlink_tooling(tree)
        git("worktree", "remove", tree)
    branches = [trees.spec_branch(slug)] + ([trees.impl_branch(slug)] if has_impl else [])
    for branch in branches:
        git("branch", "-d", branch, check=False)
    trees.forget_base(slug)
    note("  both worktrees removed")


def abort(slug: str) -> None:
    """Take the pair back out: trees, branches and recorded base alike."""
    for tree in (trees.spec_tree(slug), trees.impl_tree(slug)):
        if Path(path(tree)).is_dir():
            trees.unlink_tooling(tree)
            git("worktree", "remove", "--force", tree, check=False)
    git("worktree", "prune", check=False)
    for branch in (trees.spec_branch(slug), trees.impl_branch(slug)):
        if exists(branch):
            git("branch", "-D", branch, check=False)
    trees.forget_base(slug)


def behind(base: str) -> str:
    """How many commits the target branch has moved since a pair was cut."""
    done = subprocess.run(
        ("git", "-C", trees.ROOT, "rev-list", "--count", base + ".." + TARGET),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    return done.stdout.strip() if done.returncode == 0 else "?"
