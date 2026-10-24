# Copyright 2026 oh shit, gorillas!
"""Workspace checkpoints and launch resources, m2-launcher-kinds-design Order 17."""

import os
import re
import resource
import stat
from dataclasses import replace
from itertools import combinations
from pathlib import Path

import pytest

from gauntlet.core.errors import GauntletError, RecoveryError
from gauntlet.seams.job import JobStore, LaunchResources
from tests.support.answers import state


def _job(root: Path, name: str = "job", ident: str = "j1") -> tuple[Path, Path]:
    """Create a committed job folder and its assigned tree holding a .git folder."""
    job = root / name
    job.mkdir()
    with JobStore(job) as store:
        store.create(state(job=ident))
    tree = job / "tree"
    (tree / ".git").mkdir(parents=True)
    (tree / ".git" / "HEAD").write_text("ref: refs/heads/gauntlet/j1\n", "utf-8")
    (tree / "a.txt").write_text("alpha", encoding="utf-8")
    return job, tree


def _owned(job: Path) -> set[Path]:
    """List every path under the job folder outside its assigned tree."""
    tree = job / "tree"
    return {path for path in job.rglob("*") if tree not in (path, *path.parents)}


def _listing(tree: Path) -> list[str]:
    """List every relative path under a tree without following links."""
    return sorted(str(path.relative_to(tree)) for path in tree.rglob("*"))


# Dereferencing a saved link, dropping an execute bit or skipping
# untracked files while checkpointing breaks this.
def test_checkpoint_preserves_entries(tmp_path: Path) -> None:
    """Replay files, executable modes and link targets, never outside content."""
    job, tree = _job(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("outside", encoding="utf-8")
    run = tree / "bin" / "run.sh"
    run.parent.mkdir()
    run.write_text("#!/bin/sh\n", encoding="utf-8")
    run.chmod(0o755)
    (tree / "notes.txt").write_text("untracked", encoding="utf-8")
    (tree / "near").symlink_to("a.txt")
    (tree / "far").symlink_to(outside / "secret.txt")
    (tree / "away").symlink_to(outside)
    links = ("near", "far", "away")
    with JobStore(job) as store:
        token = store.checkpoint("e1", 0, tree)
        (outside / "secret.txt").write_text("changed", encoding="utf-8")
        (outside / "late.txt").write_text("late", encoding="utf-8")
        run.chmod(0o644)
        (tree / "a.txt").write_text("edited", encoding="utf-8")
        (tree / "notes.txt").unlink()
        for name in links:
            (tree / name).unlink()
            (tree / name).write_text("plain", encoding="utf-8")
        store.restore(token, tree)
    assert (
        (tree / "a.txt").read_text(encoding="utf-8"),
        (tree / "notes.txt").read_text(encoding="utf-8"),
        run.read_text(encoding="utf-8"),
        stat.S_IMODE(run.lstat().st_mode) & 0o111,
        [(tree / name).is_symlink() for name in links],
        [str((tree / name).readlink()) for name in links],
        sorted(path.name for path in outside.iterdir()),
        (outside / "secret.txt").read_text(encoding="utf-8"),
    ) == (
        "alpha",
        "untracked",
        "#!/bin/sh\n",
        0o111,
        [True, True, True],
        ["a.txt", str(outside / "secret.txt"), str(outside)],
        ["late.txt", "secret.txt"],
        "changed",
    )


def _tamper(paths: set[Path]) -> None:
    """Append one byte to every regular file a checkpoint published."""
    for path in paths:
        if path.is_file() and not path.is_symlink():
            path.write_bytes(path.read_bytes() + b"\0")


# Keeping post-checkpoint entries, replaying .git or writing a neighbour breaks this.
def test_restore_removes_later_entries(tmp_path: Path) -> None:
    """Remove later entries, keep .git as found and leave other trees alone."""
    job, tree = _job(tmp_path)
    neighbour = tmp_path / "main"
    neighbour.mkdir()
    with JobStore(job) as store:
        token = store.checkpoint("e1", 0, tree)
        (neighbour / "a.txt").write_text("main work", encoding="utf-8")
        (tree / "later.txt").write_text("later", encoding="utf-8")
        (tree / "later" / "deep").mkdir(parents=True)
        (tree / "later" / "deep" / "x.txt").write_text("x", encoding="utf-8")
        (tree / ".git" / "ORIG_HEAD").write_text("0" * 40, encoding="utf-8")
        store.restore(token, tree)
    assert (
        _listing(tree),
        (tree / "a.txt").read_text(encoding="utf-8"),
        (tree / ".git" / "HEAD").read_text(encoding="utf-8"),
        (tree / ".git" / "ORIG_HEAD").read_text(encoding="utf-8"),
        _listing(neighbour),
        (neighbour / "a.txt").read_text(encoding="utf-8"),
    ) == (
        [".git", ".git/HEAD", ".git/ORIG_HEAD", "a.txt"],
        "alpha",
        "ref: refs/heads/gauntlet/j1\n",
        "0" * 40,
        ["a.txt"],
        "main work",
    )


# Replaying a damaged snapshot partway, or before checking it whole, breaks this.
def test_restore_verifies_before_modifying(tmp_path: Path) -> None:
    """Reject a damaged snapshot with RecoveryError and leave the tree untouched."""
    job, tree = _job(tmp_path)
    extra = ("b.txt", "c.txt")
    names = ("a.txt", *extra)
    for name in extra:
        (tree / name).write_text("alpha", encoding="utf-8")
    before = _owned(job)
    seen: list[tuple[object, ...]] = []
    with JobStore(job) as store:
        token = store.checkpoint("e1", 0, tree)
        published = sorted(
            path
            for path in _owned(job) - before
            if path.is_file() and not path.is_symlink()
        )
        # Damaging one published file at a time puts the damage on the entry
        # replayed last in one of these rounds, whatever order restore uses.
        for damaged in published:
            for name in names:
                (tree / name).write_text("edited", encoding="utf-8")
            (tree / "later.txt").write_text("later", encoding="utf-8")
            _tamper({damaged})
            with pytest.raises(RecoveryError):
                store.restore(token, tree)
            damaged.write_bytes(damaged.read_bytes()[:-1])
            seen.append(
                (
                    _listing(tree),
                    (tree / "a.txt").read_text(encoding="utf-8"),
                    (tree / "later.txt").read_text(encoding="utf-8"),
                    [(tree / name).read_text(encoding="utf-8") for name in extra],
                )
            )
    assert (bool(published), seen) == (
        True,
        [
            (
                [".git", ".git/HEAD", "a.txt", "b.txt", "c.txt", "later.txt"],
                "edited",
                "later",
                ["edited", "edited"],
            )
        ]
        * len(published),
    )


# Consuming or rewriting the snapshot during a restore breaks the second replay.
@pytest.mark.parametrize("blocked", ["aaa", "zzz"])
def test_interrupted_restore_repeats(tmp_path: Path, blocked: str) -> None:
    """Replay the same immutable snapshot again over a half-restored tree."""
    job, tree = _job(tmp_path)
    before = _owned(job)
    with JobStore(job) as store:
        token = store.checkpoint("e1", 0, tree)
        published = (path for path in _owned(job) - before if path.is_file())
        snapshot = {path: path.read_bytes() for path in published}
        (tree / "a.txt").write_text("edited", encoding="utf-8")
        # A later folder that refuses deletion kills the first restore partway,
        # on whichever side of a.txt restore reaches it.
        (tree / blocked).mkdir()
        (tree / blocked / "later.txt").write_text("later", encoding="utf-8")
        (tree / blocked).chmod(0o500)
        try:
            with pytest.raises((GauntletError, OSError)):
                store.restore(token, tree)
        finally:
            (tree / blocked).chmod(0o700)
    (tree / "a.txt").unlink(missing_ok=True)
    (tree / "half.txt").write_text("half", encoding="utf-8")
    with JobStore(job) as store:
        store.restore(token, tree)
    assert (
        _listing(tree),
        (tree / "a.txt").read_text(encoding="utf-8"),
        {path: path.read_bytes() for path in snapshot},
    ) == ([".git", ".git/HEAD", "a.txt"], "alpha", snapshot)


# A token keyed by tree alone lets a later dispatch overwrite an earlier one.
def test_token_binds_effect_and_dispatch(tmp_path: Path) -> None:
    """Keep one distinct checkpoint per effect and dispatch."""
    job, tree = _job(tmp_path)
    keys = (("e1", 0, "alpha"), ("e1", 1, "beta"), ("e2", 0, "gamma"))
    with JobStore(job) as store:
        tokens: list[str] = []
        for effect, dispatch, text in keys:
            (tree / "a.txt").write_text(text, encoding="utf-8")
            tokens.append(store.checkpoint(effect, dispatch, tree))
        restored: list[str] = []
        for token in (tokens[2], tokens[0], tokens[1]):
            store.restore(token, tree)
            restored.append((tree / "a.txt").read_text(encoding="utf-8"))
    assert (len(set(tokens)), restored) == (3, ["gamma", "alpha", "beta"])


# Restoring into whichever tree or job the caller names breaks this.
@pytest.mark.parametrize("foreign", ["tree", "job"])
def test_contradictory_checkpoint(tmp_path: Path, foreign: str) -> None:
    """Raise RecoveryError for a token restored into another tree or job."""
    job, tree = _job(tmp_path)
    before = _owned(job)
    with JobStore(job) as store:
        token = store.checkpoint("e1", 0, tree)
    other, target = _job(tmp_path, "other", "j2")[0], tree
    if foreign == "tree":
        other = job
        target = tmp_path / "elsewhere"
        target.mkdir()
    for path in sorted(_owned(job) - before) if foreign == "job" else ():
        copy = other / path.relative_to(job)
        if path.is_dir():
            copy.mkdir(parents=True, exist_ok=True)
        else:
            copy.write_bytes(path.read_bytes())
    (target / "a.txt").write_text("edited", encoding="utf-8")
    with JobStore(other) as store, pytest.raises(RecoveryError):
        store.restore(token, target)
    assert (target / "a.txt").read_text(encoding="utf-8") == "edited"


_BIG = 1 << 22


# Publishing before flushing, or leaving a partial snapshot behind, breaks this.
@pytest.mark.parametrize("failure", ["full", "special"])
def test_incomplete_snapshot_unpublished(tmp_path: Path, failure: str) -> None:
    """Raise without a token and leave nothing published when a snapshot fails."""
    job, tree = _job(tmp_path)
    if failure == "special":
        os.mkfifo(tree / "pipe")
    # Incompressible bytes past the file-size limit fail the copy partway,
    # the way a full disk does.
    (tree / "big.bin").write_bytes(os.urandom(_BIG))
    before = _owned(job)
    soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
    limit = _BIG // 2 if failure == "full" else soft
    with JobStore(job) as store:
        resource.setrlimit(resource.RLIMIT_FSIZE, (limit, hard))
        try:
            with pytest.raises(GauntletError):
                store.checkpoint("e1", 0, tree)
        finally:
            resource.setrlimit(resource.RLIMIT_FSIZE, (soft, hard))
    assert _owned(job) == before


def _named(resources: LaunchResources) -> tuple[object, ...]:
    """Every resource identity that must differ between dispatches."""
    return (
        resources.identity,
        resources.role_container,
        resources.proxy_container,
        resources.secret,
        resources.folder,
        resources.wrapper,
        resources.staging,
    )


# Random names, or names shared across jobs, effects or dispatches, break this.
def test_resources_deterministic(tmp_path: Path) -> None:
    """Return the same resources per dispatch and distinct ones otherwise."""
    job, _ = _job(tmp_path)
    other, _ = _job(tmp_path, "other", "j2")
    with JobStore(job) as store:
        first = store.resources("e1", 0)
        again = store.resources("e1", 0)
        keys = (store.resources("e1", 1), store.resources("e2", 0))
    with JobStore(job) as store:
        reopened = store.resources("e1", 0)
    with JobStore(other) as store:
        foreign = store.resources("e1", 0)
    rows = [_named(item) for item in (first, *keys, foreign)]
    assert (
        (again, reopened),
        [len({row[index] for row in rows}) for index in range(7)],
        first.role_container == first.proxy_container,
    ) == ((first, first), [4] * 7, False)


# Allocating paths lazily, or omitting a label, name or level from the
# durable metadata, breaks this.
def test_resources_metadata_published(tmp_path: Path) -> None:
    """Allocate owned folders and publish names, labels, level and paths."""
    job, _ = _job(tmp_path)
    before = _owned(job)
    with JobStore(job) as store:
        found = store.resources("e3", 2)
    published = [
        path.read_text(encoding="utf-8")
        for path in _owned(job) - before
        if path.is_file()
        and found.folder not in path.parents
        and found.staging not in path.parents
        and path != found.wrapper
    ]
    expected = (
        found.role_container,
        found.proxy_container,
        found.secret,
        found.level,
        str(found.folder),
        str(found.wrapper),
        str(found.staging),
        *(text for pair in found.labels for text in pair),
    )
    values = {value for _, value in found.labels}
    assert (
        found.folder.is_dir(),
        found.staging.is_dir(),
        re.fullmatch(r"s0:c\d+,c\d+", found.level) is not None,
        {"e3", "2"} <= values,
        bool(values & {"j1", str(job)}),
        any(all(text in body for text in expected) for body in published),
    ) == (True, True, True, True, True, True)


def _metadata(job: Path, before: set[Path], found: LaunchResources) -> list[Path]:
    """List the files resources() published outside folder, staging and wrapper."""
    return [
        path
        for path in _owned(job) - before
        if path.is_file()
        and found.folder not in path.parents
        and found.staging not in path.parents
        and path != found.wrapper
    ]


def _unrelated(found: LaunchResources, field: str) -> tuple[str, str]:
    """Pair one saved value with an unrelated value of the same kind."""
    saved = {
        "role_container": found.role_container,
        "proxy_container": found.proxy_container,
        "secret": found.secret,
        "level": found.level,
    }[field]
    if field == "level":
        return saved, "s0:c1,c2" if saved != "s0:c1,c2" else "s0:c3,c4"
    return saved, f"unrelated-{field}"


# Recomputing names on reopen and ignoring, or silently rewriting, the
# saved metadata breaks this.
@pytest.mark.parametrize(
    "field", ["role_container", "proxy_container", "secret", "level"]
)
def test_reopen_verifies_metadata(tmp_path: Path, field: str) -> None:
    """Refuse to reopen a dispatch whose saved metadata names something else."""
    job, _ = _job(tmp_path)
    before = _owned(job)
    with JobStore(job) as store:
        found = store.resources("e1", 0)
    saved, unrelated = _unrelated(found, field)
    for path in _metadata(job, before, found):
        body = path.read_text(encoding="utf-8")
        path.write_text(body.replace(saved, unrelated), encoding="utf-8")
    with JobStore(job) as store, pytest.raises(GauntletError):
        store.resources("e1", 0)


def _nested(first: Path, second: Path) -> bool:
    """Tell whether one path is, or lies within, the other."""
    return first == second or first in second.parents or second in first.parents


# Allocating the wrapper, metadata, staging or a checkpoint inside the
# socket folder, another dispatch's paths or the assigned tree breaks this.
def test_folder_holds_only_socket(tmp_path: Path) -> None:
    """Keep wrapper, staging, metadata and checkpoints apart from every bind."""
    job, tree = _job(tmp_path)
    before = _owned(job)
    with JobStore(job) as store:
        found = store.resources("e1", 0)
        later = store.resources("e1", 1)
        store.checkpoint("e1", 0, tree)
        store.checkpoint("e1", 1, tree)
    made = _owned(job) - before
    roots = (found.folder, found.wrapper, found.staging)
    assert (
        sorted(found.folder.iterdir()),
        sorted(found.staging.iterdir()),
        [_nested(first, second) for first, second in combinations(roots, 2)],
        [_nested(root, tree) for root in (*roots, *(later.folder, later.staging))],
        sorted(
            path
            for path in made
            if found.folder in path.parents or found.staging in path.parents
        ),
        _listing(tree),
    ) == ([], [], [False] * 3, [False] * 5, [], [".git", ".git/HEAD", "a.txt"])


# Leaving the socket folder, staging or wrapper behind, or deleting another
# dispatch's paths, a checkpoint or the job state, breaks this.
def test_release_removes_owned_paths(tmp_path: Path) -> None:
    """Remove one dispatch's files and keep checkpoints, state and neighbours."""
    job, tree = _job(tmp_path)
    with JobStore(job) as store:
        found = store.resources("e1", 0)
        kept = store.resources("e1", 1)
        token = store.checkpoint("e2", 0, tree)
        (found.folder / "proxy.sock").write_text("socket", encoding="utf-8")
        (found.staging / "docs").mkdir()
        (found.staging / "docs" / "spec.md").write_text("spec", encoding="utf-8")
        found.wrapper.parent.mkdir(parents=True, exist_ok=True)
        found.wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
        (tree / "a.txt").write_text("edited", encoding="utf-8")
        store.release_resources(found)
        released = [os.path.lexists(path) for path in (found.folder, found.staging)]
        released.append(os.path.lexists(found.wrapper))
        survivors = [kept.folder.is_dir(), kept.staging.is_dir()]
        store.restore(token, tree)
        loaded = store.load()
    assert (
        released,
        survivors,
        (tree / "a.txt").read_text(encoding="utf-8"),
        loaded,
    ) == ([False, False, False], [True, True], "alpha", state())


# Deleting whatever paths the caller's resources name, unchecked against
# the saved metadata, breaks this.
@pytest.mark.parametrize("field", ["folder", "staging", "wrapper"])
def test_release_refuses_foreign_paths(tmp_path: Path, field: str) -> None:
    """Refuse resources naming paths the store never allocated and keep them."""
    job, _ = _job(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    with JobStore(job) as store:
        found = store.resources("e1", 0)
        forged = {
            "folder": replace(found, folder=outside),
            "staging": replace(found, staging=outside),
            "wrapper": replace(found, wrapper=outside / "keep.txt"),
        }[field]
        with pytest.raises(GauntletError):
            store.release_resources(forged)
    assert (
        sorted(path.name for path in outside.iterdir()),
        (outside / "keep.txt").read_text(encoding="utf-8"),
    ) == (["keep.txt"], "keep")
