# Copyright 2026 oh shit, gorillas!
"""Decide which work may run beside which, by declared files."""

from collections.abc import Collection, Sequence


def _overlap(files: frozenset[str], other: frozenset[str]) -> bool:
    """Whether two pieces' file sets overlap; an empty set overlaps every piece."""
    return not files or not other or not files.isdisjoint(other)


def _held(files: frozenset[str], held: Collection[str]) -> bool:
    """Whether a piece holds a held path; an empty set holds every held path."""
    return bool(held) and (not files or not files.isdisjoint(held))


def startable(
    order: Sequence[tuple[str, frozenset[str]]],
    done: Collection[str],
    running: Collection[str],
    held: Collection[str],
) -> tuple[str, ...]:
    """Give, in order, each piece free to start beside the running ones.

    A piece is free when it is not done and not running, and its files overlap
    no running piece, no earlier piece not done and no held path.
    """
    running_files = tuple(files for name, files in order if name in running)
    earlier: list[frozenset[str]] = []
    given: list[str] = []
    for name, files in order:
        if name in done:
            continue
        blockers = (*running_files, *earlier)
        if (
            name not in running
            and not any(_overlap(files, other) for other in blockers)
            and not _held(files, held)
        ):
            given.append(name)
        earlier.append(files)
    return tuple(given)
