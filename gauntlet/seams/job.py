# Copyright 2026 oh shit, gorillas!
"""Publish durable job snapshots and their derived launch ledger."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Self

from gauntlet.core import codec
from gauntlet.core.decide import state_problems
from gauntlet.core.errors import (
    RecordError,
    RecoveryError,
    StateError,
    StorageError,
)

if TYPE_CHECKING:
    from types import TracebackType

    from gauntlet.core.records import Json, State


@dataclass(frozen=True)
class LaunchResources:
    """Name the host resources one launch holds until they are released."""

    identity: str
    role_container: str
    proxy_container: str
    secret: str
    level: str
    folder: Path
    wrapper: Path
    staging: Path
    labels: tuple[tuple[str, str], ...]


_TOKEN = re.compile(r"[0-9a-f]{64}")
_IDENTITY = re.compile(r"[0-9a-f]{32}")
_CATEGORIES = 1023


def _digest(*parts: object) -> str:
    """Derive a stable hexadecimal name from the supplied parts."""
    return hashlib.sha256(json.dumps(parts).encode("utf-8")).hexdigest()


def _allocate(job: Path, effect: str, dispatch: int) -> LaunchResources:
    """Name every resource of one job, effect and dispatch deterministically."""
    digest = _digest(str(job), effect, dispatch)
    identity = digest[:32]
    home = job / "launch" / identity
    low = int(digest[32:36], 16) % _CATEGORIES
    high = low + 1 + int(digest[36:40], 16) % (_CATEGORIES - low)
    return LaunchResources(
        identity=identity,
        role_container=f"gauntlet-{identity}-role",
        proxy_container=f"gauntlet-{identity}-proxy",
        secret=f"gauntlet-{identity}-secret",
        level=f"s0:c{low},c{high}",
        folder=home / "folder",
        wrapper=home / "wrapper" / "run.sh",
        staging=home / "staging",
        labels=(
            ("gauntlet.job", str(job)),
            ("gauntlet.effect", effect),
            ("gauntlet.dispatch", str(dispatch)),
        ),
    )


def _record(resources: LaunchResources) -> dict[str, object]:
    """Describe resources as the durable metadata publishes them."""
    return {
        "identity": resources.identity,
        "role_container": resources.role_container,
        "proxy_container": resources.proxy_container,
        "secret": resources.secret,
        "level": resources.level,
        "folder": str(resources.folder),
        "wrapper": str(resources.wrapper),
        "staging": str(resources.staging),
        "labels": [list(pair) for pair in resources.labels],
    }


def _sync_directory(path: Path) -> None:
    """Flush a directory's entries to storage."""
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_synced(path: Path, data: bytes) -> None:
    """Write bytes to a new file and flush them to storage."""
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _capture(tree: Path, target: Path) -> list[dict[str, object]]:
    """Copy the tree's entries beneath a new snapshot directory."""
    (target / "blobs").mkdir()
    entries: list[dict[str, object]] = []
    pending = [(tree, PurePosixPath())]
    while pending:
        directory, prefix = pending.pop()
        for child in sorted(directory.iterdir(), key=str, reverse=True):
            if not prefix.parts and child.name == ".git":
                continue
            relative = prefix / child.name
            info = child.lstat()
            entry: dict[str, object] = {
                "path": str(relative),
                "mode": stat.S_IMODE(info.st_mode),
            }
            if stat.S_ISLNK(info.st_mode):
                entry |= {"type": "link", "target": str(child.readlink())}
            elif stat.S_ISDIR(info.st_mode):
                entry["type"] = "dir"
                pending.append((child, relative))
            elif stat.S_ISREG(info.st_mode):
                data = child.read_bytes()
                blob = str(len(entries))
                _write_synced(target / "blobs" / blob, data)
                entry |= {
                    "type": "file",
                    "blob": blob,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            else:
                operation = "checkpoint"
                raise StateError(operation, f"special file {relative}")
            entries.append(entry)
    _sync_directory(target / "blobs")
    return entries


def _object(value: Json) -> dict[str, Json]:
    """Narrow decoded JSON to an object."""
    if isinstance(value, dict):
        return value
    message = "expected a JSON object"
    raise ValueError(message)


def _array(value: Json) -> list[Json]:
    """Narrow decoded JSON to an array."""
    if isinstance(value, list):
        return value
    message = "expected a JSON array"
    raise ValueError(message)


def _text(value: Json) -> str:
    """Narrow decoded JSON to a string."""
    if isinstance(value, str):
        return value
    message = "expected a JSON string"
    raise ValueError(message)


def _mode(value: Json) -> int:
    """Narrow decoded JSON to a permission mode."""
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value == stat.S_IMODE(value)
    ):
        return value
    message = "expected a permission mode"
    raise ValueError(message)


def _verified(
    base: Path, token: str, binding: dict[str, str]
) -> list[tuple[dict[str, Json], bytes]]:
    """Check a whole snapshot against its token and binding before any replay."""
    try:
        text = (base / "manifest.json").read_text(encoding="utf-8")
        parsed: object = json.loads(text)
        manifest = _object(codec.json_value(parsed))
        if manifest["token"] != token or any(
            manifest[key] != value for key, value in binding.items()
        ):
            raise RecoveryError((token,), "checkpoint belongs to another job or tree")
        checked: list[tuple[dict[str, Json], bytes]] = []
        directories: set[PurePosixPath] = set()
        for item in _array(manifest["entries"]):
            entry = _object(item)
            path = PurePosixPath(_text(entry["path"]))
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] == ".git"
                or (path.parent.parts and path.parent not in directories)
            ):
                raise RecoveryError((token,), "checkpoint entry escapes the tree")
            data = b""
            kind = _text(entry["type"])
            _mode(entry["mode"])
            if kind == "dir":
                directories.add(path)
            elif kind == "file":
                blob = PurePosixPath(_text(entry["blob"])).name
                data = (base / "blobs" / blob).read_bytes()
                if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    raise RecoveryError((token,), "checkpoint content is damaged")
            elif kind == "link":
                _text(entry["target"])
            else:
                raise RecoveryError((token,), "checkpoint entry has unknown type")
            checked.append((entry, data))
    except (KeyError, TypeError, ValueError, OSError, RecordError) as error:
        raise RecoveryError((token,), "checkpoint is unreadable") from error
    return checked


def _replay(tree: Path, checked: list[tuple[dict[str, Json], bytes]]) -> None:
    """Replace the tree's entries, but never its .git, with a verified snapshot."""
    for child in tree.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    directories: list[tuple[Path, int]] = []
    for entry, data in checked:
        destination = tree / str(entry["path"])
        mode = _mode(entry["mode"])
        if entry["type"] == "dir":
            destination.mkdir()
            directories.append((destination, mode))
        elif entry["type"] == "link":
            destination.symlink_to(str(entry["target"]))
        else:
            destination.write_bytes(data)
            destination.chmod(mode)
    for destination, mode in reversed(directories):
        destination.chmod(mode)


class JobStore:
    """Own a job's exclusive writer and durable record files."""

    def __init__(self, job: Path) -> None:
        """Bind storage to the caller's explicit job directory."""
        self._job = job
        self._lock: int | None = None

    def __enter__(self) -> Self:
        """Acquire a nonblocking advisory lock for this job."""
        path = self._job / ".lock"
        if self._lock is not None:
            raise StorageError(str(path), "lock", None)
        descriptor: int | None = None
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if descriptor is not None:
                os.close(descriptor)
            raise StorageError(str(path), "lock", error.errno) from error
        self._lock = descriptor
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Release the operating-system lock even after a body failure."""
        descriptor = self._lock
        self._lock = None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as error:
                raise StorageError(
                    str(self._job / ".lock"), "unlock", error.errno
                ) from error

    def load(self) -> State:
        """Read authoritative state and regenerate its trace projection."""
        self._require_lock()
        state = self._read_state()
        self.repair_trace(state)
        return state

    def create(self, state: State) -> None:
        """Publish a validated initial snapshot without overwriting state."""
        self._require_lock()
        path = self._job / "state.json"
        try:
            path.lstat()
        except FileNotFoundError:
            pass
        except OSError as error:
            raise StorageError(str(path), "stat", error.errno) from error
        else:
            operation = "create"
            raise StateError(operation, "state already exists")
        text = self._state_text(state)
        self._publish(path, text)
        self.repair_trace(state)

    def save(self, state: State, *, expected_revision: int) -> None:
        """Validate and commit one successor revision before its projection."""
        self._require_lock()
        text = self._state_text(state)
        current = self._read_state()
        if (
            current.revision != expected_revision
            or state.revision != expected_revision + 1
        ):
            operation = "save"
            raise StateError(operation, "revision mismatch")
        self._publish(self._job / "state.json", text)
        self.repair_trace(state)

    def repair_trace(self, state: State) -> None:
        """Replace the derived ledger using only the canonical trace codec."""
        self._require_lock()
        self._publish(
            self._job / "trace.jsonl",
            "".join(codec.encode_trace(row) for row in state.launches),
        )

    def resources(self, effect: str, dispatch: int) -> LaunchResources:
        """Allocate and durably describe the resources for one effect dispatch."""
        self._require_lock()
        found = _allocate(self._job, effect, dispatch)
        home = found.folder.parent
        try:
            home.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise StorageError(str(home), "mkdir", error.errno) from error
        saved = self._saved(found.identity)
        if saved is None:
            self._publish(home / "meta.json", json.dumps(_record(found)) + "\n")
        elif saved != _record(found):
            raise RecoveryError((effect,), "saved resources name something else")
        for folder in (found.folder, found.staging):
            try:
                folder.mkdir(mode=0o700, exist_ok=True)
            except OSError as error:
                raise StorageError(str(folder), "mkdir", error.errno) from error
        return found

    def checkpoint(self, effect: str, dispatch: int, tree: Path) -> str:
        """Capture the workspace before an effect and return its token."""
        self._require_lock()
        token = _digest("checkpoint", str(self._job), effect, dispatch)
        final = self._job / "checkpoints" / token
        if final.exists():
            binding = {"job": str(self._job), "tree": str(tree)}
            _verified(final, token, binding)
            return token
        temporary: Path | None = None
        try:
            temporary = Path(tempfile.mkdtemp(dir=self._job, prefix=".snapshot-"))
            manifest = {
                "token": token,
                "job": str(self._job),
                "effect": effect,
                "dispatch": dispatch,
                "tree": str(tree),
                "entries": _capture(tree, temporary),
            }
            _write_synced(temporary / "manifest.json", json.dumps(manifest).encode())
            _sync_directory(temporary)
            final.parent.mkdir(exist_ok=True)
            temporary.rename(final)
            temporary = None
            _sync_directory(final.parent)
            _sync_directory(self._job)
        except OSError as error:
            raise StorageError(str(final), "checkpoint", error.errno) from error
        finally:
            if temporary is not None:
                shutil.rmtree(temporary, ignore_errors=True)
        return token

    def restore(self, token: str, tree: Path) -> None:
        """Restore the workspace from a checkpoint token."""
        self._require_lock()
        if _TOKEN.fullmatch(token) is None:
            raise RecoveryError((token,), "not a checkpoint token")
        binding = {"job": str(self._job), "tree": str(tree)}
        checked = _verified(self._job / "checkpoints" / token, token, binding)
        try:
            _replay(tree, checked)
        except OSError as error:
            raise StorageError(str(tree), "restore", error.errno) from error

    def release_resources(self, resources: LaunchResources) -> None:
        """Remove the owned paths a launch held, after matching saved metadata."""
        self._require_lock()
        effects = (resources.identity,)
        if _IDENTITY.fullmatch(resources.identity) is None:
            raise RecoveryError(effects, "not a resource identity")
        if self._saved(resources.identity) != _record(resources):
            raise RecoveryError(effects, "resources do not match saved metadata")
        home = self._job / "launch" / resources.identity
        try:
            shutil.rmtree(home)
        except OSError as error:
            raise StorageError(str(home), "release", error.errno) from error

    def _saved(self, identity: str) -> object:
        """Read one dispatch's durable resource metadata, None when absent."""
        path = self._job / "launch" / identity / "meta.json"
        try:
            saved: object = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except OSError as error:
            raise StorageError(str(path), "read", error.errno) from error
        except ValueError as error:
            raise RecordError(str(path), "expected JSON resource metadata") from error
        return saved

    def _require_lock(self) -> None:
        """Keep every storage operation inside the exclusive context."""
        if self._lock is None:
            raise StorageError(str(self._job / ".lock"), "lock", None)

    @staticmethod
    def _state_text(state: State) -> str:
        """Delegate wire and whole-state validation to the core."""
        text = codec.encode_state(state)
        decoded = codec.decode_state(text)
        problems = state_problems(decoded)
        if problems:
            operation = "state"
            raise StateError(operation, "; ".join(problems))
        return text

    def _read_state(self) -> State:
        """Reject unreadable or corrupt authority without using other files."""
        path = self._job / "state.json"
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            raise StorageError(str(path), "read", error.errno) from error
        except UnicodeError as error:
            raise RecordError(str(path), "expected UTF-8 state") from error
        state = codec.decode_state(text)
        problems = state_problems(state)
        if problems:
            operation = "state"
            raise StateError(operation, "; ".join(problems))
        return state

    def _publish(self, path: Path, text: str) -> None:
        """Flush an owned exclusive temporary and atomically publish it."""
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self._job, delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
            _sync_directory(path.parent)
        except OSError as error:
            raise StorageError(str(path), "write", error.errno) from error
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError as error:
                    raise StorageError(str(temporary), "unlink", error.errno) from error
