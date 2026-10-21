"""A project tree a gate test runs in: its files, its pyproject.toml, unreadable paths, and a git repository.

Design: the gates-core design spec under docs/superpowers/specs/, section 3, "project.py", and its decision 25. The
config is the repository's own pyproject.toml unless the test gives one, so a gate test runs under `make check`'s
settings. The files are written after it, so a `files` entry named pyproject.toml replaces it. With `git=True` the root
becomes a repository holding one commit of everything. The `unreadable` paths lose every permission last.
"""

from collections.abc import Mapping
from pathlib import Path

from gates.core.checker import Completed
from gates.core.project import CONFIG, Project

# The repository's own pyproject.toml, found from this module's path: tests/support/project.py.
OWN_CONFIG = Path(__file__).resolve().parents[2] / CONFIG

# Settings that keep the user's git config from changing the commit: a fixed author, no signing and no hooks.
GIT_SETTINGS = (
    "-c",
    "user.name=scaffold",
    "-c",
    "user.email=scaffold@example.invalid",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "core.hooksPath=/dev/null",
)


class ScaffoldError(Exception):
    """A git step of the scaffold failed; `completed` is what git gave back."""

    completed: Completed

    def __init__(self, completed: Completed) -> None:
        super().__init__(f"scaffold: git exited {completed.status}: {completed.output()}")
        self.completed = completed


def scaffold(
    root: Path,
    files: Mapping[str, str | bytes],
    *,
    pyproject: str | None = None,
    unreadable: tuple[str, ...] = (),
    git: bool = False,
) -> Project:
    """Write the project tree in the root and return its Project.

    Raises ScaffoldError when a git step fails.
    """
    root.mkdir(parents=True, exist_ok=True)
    project = Project(root)
    project.config.write_text(OWN_CONFIG.read_text(encoding="utf-8") if pyproject is None else pyproject, encoding="utf-8")
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    if git:
        for arguments in (("init", "--quiet"), ("add", "--all"), ("commit", "--quiet", "--allow-empty", "-m", "scaffold")):
            completed = project.git(*GIT_SETTINGS, *arguments)
            if completed.status != 0:
                raise ScaffoldError(completed)
    for name in unreadable:
        (root / name).chmod(0)
    return project
