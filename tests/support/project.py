"""A project tree a gate test runs in: its files, its pyproject.toml, unreadable paths, and a git repository."""

from collections.abc import Mapping
from pathlib import Path

from gates.core.checker import Completed
from gates.core.project import Project


class ScaffoldError(Exception):
    """A git step of the scaffold failed; `completed` is what git gave back."""

    completed: Completed

    def __init__(self, completed: Completed) -> None:
        raise NotImplementedError


def scaffold(
    root: Path,
    files: Mapping[str, str | bytes],
    *,
    pyproject: str | None = None,
    unreadable: tuple[str, ...] = (),
    git: bool = False,
) -> Project:
    raise NotImplementedError
