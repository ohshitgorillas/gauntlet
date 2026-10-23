# Copyright 2026 oh shit, gorillas!
"""Publish durable job snapshots and their derived launch ledger."""

from __future__ import annotations

import fcntl
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Self

from gauntlet.core import codec
from gauntlet.core.decide import state_problems
from gauntlet.core.errors import RecordError, StateError, StorageError

if TYPE_CHECKING:
    from types import TracebackType

    from gauntlet.core.records import State


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
            descriptor = os.open(self._job, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as error:
            raise StorageError(str(path), "write", error.errno) from error
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError as error:
                    raise StorageError(str(temporary), "unlink", error.errno) from error
