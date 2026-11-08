# /// script
# requires-python = ">=3.12"
# dependencies = ["mcp>=1.2,<2"]
# ///
"""Stdio MCP file server confined to folders named in the environment."""

import fnmatch
import glob as globmod
import os
import re
import shutil
import sys

from mcp.server.fastmcp import FastMCP

import files_commit  # the sibling of this script, on sys.path when it runs

ALWAYS_DENY_WRITE = (".archon", ".claude", ".git")
CAP = 500

Parts = tuple[str, ...]


def _folders(name: str) -> list[Parts]:
    out: list[Parts] = []
    for item in os.environ.get(name, "").split(":"):
        if not item.strip():
            continue
        norm = os.path.normpath(item.strip())
        out.append(() if norm == "." else tuple(norm.split(os.sep)))
    return out


def _root() -> str:
    raw = os.environ.get("CLAUDE_PROJECT_DIR")
    if not raw or not os.path.isdir(raw):
        print(
            "fence-files: CLAUDE_PROJECT_DIR must name an existing directory",
            file=sys.stderr,
        )
        sys.exit(2)
    return os.path.realpath(raw)


ROOT = _root()
READ = _folders("FENCE_READ")
WRITE = _folders("FENCE_WRITE")
DENY = _folders("FENCE_DENY") + [(d,) for d in ALWAYS_DENY_WRITE]
ONCE = _folders("FENCE_ONCE")
COPY = _folders("FENCE_COPY")
HIDE = _folders("FENCE_HIDE")
RECORDED: set[str] = set()  # paths this process wrote, edited, copied to or deleted

mcp = FastMCP("fence-files")


def _is_pattern(entry: Parts) -> bool:
    return any(c in seg for seg in entry for c in "*?[")


def _segments(parts: Parts, entry: Parts) -> bool:
    return all(fnmatch.fnmatchcase(p, e) for p, e in zip(parts, entry))


def _matches(parts: Parts, entry: Parts) -> bool:
    """A folder entry covers its subtree; a pattern entry covers the paths with
    its segment count whose segments each match."""
    if _is_pattern(entry):
        return len(parts) == len(entry) and _segments(parts, entry)
    return parts[: len(entry)] == entry


def _covered(parts: Parts, entries: list[Parts]) -> bool:
    return any(_matches(parts, e) for e in entries)


def _name(folder: Parts) -> str:
    return "/".join(folder) or "."


def _resolve(path: str) -> tuple[str, Parts]:
    """Return (real absolute path, parts relative to root); reject escapes and
    hidden paths. Every tool resolves first, so a hidden path is refused before
    any other effect, and listings that skip a refused path skip a hidden one."""
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    head, tail = full, []
    while not os.path.lexists(head):
        head, last = os.path.split(head)
        tail.insert(0, last)
    real = os.path.normpath(os.path.join(os.path.realpath(head), *tail))
    rel = os.path.relpath(real, ROOT)
    if rel == ".." or rel.startswith(".." + os.sep):
        raise PermissionError(f"{path}: resolves outside the project root")
    parts: Parts = () if rel == "." else tuple(rel.split(os.sep))
    if _covered(parts, HIDE):
        raise PermissionError(f"{path}: hidden (FENCE_HIDE)")
    return real, parts


def _check_read(path: str, parts: Parts) -> None:
    if not _covered(parts, READ):
        rules = ", ".join(_name(f) for f in READ) or "none"
        raise PermissionError(
            f"{path}: not inside any FENCE_READ folder (allowed: {rules})"
        )


def _check_write(path: str, parts: Parts) -> None:
    for f in DENY:
        if _matches(parts, f):
            raise PermissionError(f"{path}: inside denied folder {_name(f)}")
    if not _covered(parts, WRITE):
        rules = ", ".join(_name(f) for f in WRITE) or "none"
        raise PermissionError(
            f"{path}: not inside any FENCE_WRITE folder (allowed: {rules})"
        )


def _check_copy(path: str, parts: Parts) -> None:
    if _covered(parts, COPY):
        raise PermissionError(f"{path}: created only by copy_file (FENCE_COPY)")


def _check_once(path: str, parts: Parts) -> None:
    if _covered(parts, ONCE):
        raise PermissionError(f"{path}: files here are written once (FENCE_ONCE)")


def _holds_file(real: str) -> bool:
    for dirpath, _dirs, names in os.walk(real):
        for n in names:
            try:
                fparts = _resolve(os.path.join(dirpath, n))[1]
            except PermissionError:
                continue
            if _covered(fparts, READ):
                return True
    return False


def _emptied(real: str, parts: Parts) -> bool:
    """A folder with a hidden path below it that holds no other readable file."""
    return (
        os.path.isdir(real)
        and any(len(parts) < len(h) and _segments(parts, h) for h in HIDE)
        and not _holds_file(real)
    )


def _visible(real: str, parts: Parts) -> bool:
    """Readable, or a parent of a readable folder. Where a pattern entry is
    what makes a folder visible, the folder must hold a readable file."""
    return _reads(real, parts) and not _emptied(real, parts)


def _reads(real: str, parts: Parts) -> bool:
    for f in READ:
        if not _is_pattern(f):
            if parts[: len(f)] == f or f[: len(parts)] == parts:
                return True
        elif len(parts) <= len(f) and _segments(parts, f):
            if not os.path.isdir(real):
                if len(parts) == len(f):
                    return True
            elif _holds_file(real):
                return True
    return False


def _shown(real: str, parts: Parts) -> bool:
    """Readable and listable: a folder covered by a pattern entry only when it
    holds a readable file."""
    return not _emptied(real, parts) and any(
        _matches(parts, f)
        and (not _is_pattern(f) or not os.path.isdir(real) or _holds_file(real))
        for f in READ
    )


def _walkable(dirpath: str, dirs: list[str]) -> list[str]:
    """The subfolders grep descends into: visible, never `.git`."""
    keep = []
    for name in sorted(dirs):
        if name == ".git":
            continue
        try:
            shown = _visible(*_resolve(os.path.join(dirpath, name)))
        except PermissionError:
            continue
        if shown:
            keep.append(name)
    return keep


def _rel(real: str) -> str:
    return os.path.relpath(real, ROOT)


@mcp.tool()
def read_file(path: str, offset: int = 0, limit: int = 2000) -> str:
    """Read a text file; returns numbered lines like `cat -n`. offset is the
    number of lines to skip, limit the maximum lines returned."""
    real, parts = _resolve(path)
    _check_read(path, parts)
    with open(real, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    chosen = lines[offset : offset + limit]
    return "\n".join(f"{offset + i + 1:6}\t{line}" for i, line in enumerate(chosen))


@mcp.tool()
def list_directory(path: str = ".") -> str:
    """List a directory; subdirectories end with `/`. Shows only readable
    entries and entries leading to readable folders."""
    real, parts = _resolve(path)
    if not _visible(real, parts):
        _check_read(path, parts)
    names = []
    for entry in sorted(os.listdir(real)):
        try:
            ereal, eparts = _resolve(os.path.join(real, entry))
        except PermissionError:
            continue
        if not _visible(ereal, eparts):
            continue
        is_dir = os.path.isdir(os.path.join(real, entry))
        names.append(entry + "/" if is_dir else entry)
    return "\n".join(names)


@mcp.tool()
def find_files(pattern: str, path: str = ".") -> str:
    """Glob for files under path (supports `**`); readable paths only, max 500."""
    real, parts = _resolve(path)
    if not _visible(real, parts):
        _check_read(path, parts)
    found = []
    for match in sorted(globmod.glob(pattern, root_dir=real, recursive=True)):
        try:
            mreal, mparts = _resolve(os.path.join(real, match))
        except PermissionError:
            continue
        if _shown(mreal, mparts):
            found.append(_rel(mreal))
        if len(found) >= CAP:
            break
    return "\n".join(found)


@mcp.tool()
def grep(regex: str, path: str = ".", glob: str | None = None) -> str:
    """Search files under path for a regex; returns `path:line:text`.
    Readable text files only, skips `.git`, max 500 hits. glob filters names."""
    real, parts = _resolve(path)
    if not _visible(real, parts):
        _check_read(path, parts)
    pat = re.compile(regex)
    if os.path.isfile(real):
        files = [real]
    else:
        files = []
        for dirpath, dirs, names in os.walk(real):
            dirs[:] = _walkable(dirpath, dirs)
            files += [os.path.join(dirpath, n) for n in sorted(names)]
    hits: list[str] = []
    for f in files:
        try:
            freal, fparts = _resolve(f)
        except PermissionError:
            continue
        if not _covered(fparts, READ) or not os.path.isfile(freal):
            continue
        if glob and not (
            fnmatch.fnmatch(os.path.basename(f), glob)
            or fnmatch.fnmatch(os.path.relpath(f, real), glob)
        ):
            continue
        with open(freal, "rb") as fh:
            data = fh.read()
        if b"\0" in data[:8192]:
            continue
        text = data.decode("utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if pat.search(line):
                hits.append(f"{_rel(freal)}:{n}:{line}")
                if len(hits) >= CAP:
                    return "\n".join(hits)
    return "\n".join(hits)


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write a file, creating parent folders. Needs a writable path."""
    real, parts = _resolve(path)
    _check_write(path, parts)
    _check_copy(path, parts)
    if os.path.lexists(real):
        _check_once(path, parts)
    RECORDED.add(_rel(real))
    os.makedirs(os.path.dirname(real), exist_ok=True)
    with open(real, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)
    return f"wrote {_rel(real)}"


@mcp.tool()
def edit_file(path: str, old: str, new: str, replace_all: bool = False) -> str:
    """Replace exact text in a file. Errors if `old` is missing, or not unique
    while replace_all is false. Needs a readable and writable path."""
    real, parts = _resolve(path)
    _check_read(path, parts)
    _check_write(path, parts)
    _check_copy(path, parts)
    _check_once(path, parts)
    with open(real, encoding="utf-8", newline="") as fh:
        text = fh.read()
    count = text.count(old)
    if count == 0:
        raise ValueError(f"{path}: old text not found")
    if count > 1 and not replace_all:
        raise ValueError(f"{path}: old text occurs {count} times; not unique")
    RECORDED.add(_rel(real))
    with open(real, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace(old, new))
    return f"edited {_rel(real)} ({count} replacement{'s' if count > 1 else ''})"


@mcp.tool()
def copy_file(src: str, dst: str) -> str:
    """Copy a file, creating parent folders. Needs a readable `src` and a
    writable `dst`; an existing `dst` is refused."""
    src_real, src_parts = _resolve(src)
    _check_read(src, src_parts)
    dst_real, dst_parts = _resolve(dst)
    _check_write(dst, dst_parts)
    if os.path.lexists(dst_real):
        raise FileExistsError(f"{dst}: destination already exists")
    if not os.path.isfile(src_real):
        raise ValueError(f"{src}: not a file")
    RECORDED.add(_rel(dst_real))
    os.makedirs(os.path.dirname(dst_real), exist_ok=True)
    shutil.copyfile(src_real, dst_real)
    return f"copied {_rel(src_real)} to {_rel(dst_real)}"


@mcp.tool()
def delete_file(path: str) -> str:
    """Delete a file (not a directory). Needs a writable path."""
    real, parts = _resolve(path)
    _check_write(path, parts)
    _check_once(path, parts)
    if not os.path.isfile(real):
        raise ValueError(f"{path}: not a file")
    RECORDED.add(_rel(real))
    os.remove(real)
    return f"deleted {_rel(real)}"


def _writable(path: str) -> str:
    """Fence-check a path the commit tool may stage; return it relative to root."""
    real, parts = _resolve(path)
    _check_write(path, parts)
    return _rel(real)


if os.environ.get("FENCE_COMMIT") == "1":

    @mcp.tool()
    def commit(message: str, paths: list[str]) -> str:
        """Commit the listed paths that changed, and only those. Refuses a
        changed path this server wrote, edited, copied to or deleted that is
        missing from `paths`. Returns `exit=<n>`, then the commit hash, or the
        hook names when git failed, or `nothing`."""
        return files_commit.commit(
            ROOT, message, [_writable(p) for p in paths], RECORDED, _writable
        )


if __name__ == "__main__":
    mcp.run()
