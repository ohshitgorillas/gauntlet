# Copyright 2026 oh shit, gorillas!
"""Literal product process replies: seeded results in call order and a typed call history.

Design: docs/superpowers/specs/m2-launcher-kinds-design.md, `tests/support/process.py`. Replaces prospective local
launch/git/image fakes, not the differently typed gate FakeRunner in tests/support/fake.py. FakeSdk waits for its
launcher stubs (Order step 29a).
"""

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from gauntlet.core.errors import ProcessError
from gauntlet.seams.process import Command, Completed

_COLLABORATOR = "FakeRunner"


class RepliesExhaustedError(Exception):
    """A literal reply stream ended, naming its collaborator and the attempted-call count."""

    collaborator: str
    count: int

    def __init__(self, collaborator: str, count: int) -> None:
        """Keep the collaborator identity and attempted-call count at exhaustion."""
        super().__init__(f"{collaborator} replies exhausted at call {count}")
        self.collaborator = collaborator
        self.count = count


class FakeRunner:
    """A product Runner returning seeded literal replies in call order and recording each Command."""

    commands: list[Command]

    def __init__(self, replies: Sequence[Completed | ProcessError]) -> None:
        """Seed the literal replies."""
        self._replies = tuple(replies)
        self.commands = []

    def __call__(self, command: Command) -> Completed:
        """Return, or raise, the next seeded reply for this call."""
        self.commands.append(command)
        attempt = len(self.commands)
        if attempt > len(self._replies):
            raise RepliesExhaustedError(_COLLABORATOR, attempt)
        reply = self._replies[attempt - 1]
        if isinstance(reply, ProcessError):
            raise reply
        return reply


def completed(
    status: int = 0,
    stdout: str = "",
    stderr: str = "",
    *,
    timed_out: bool = False,
    outputs: Mapping[str, str | None] = MappingProxyType({}),
) -> Completed:
    """Return a Completed carrying exactly the supplied literal fields."""
    return Completed(status, stdout, stderr, timed_out=timed_out, outputs=outputs)
