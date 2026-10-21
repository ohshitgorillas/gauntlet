"""A scripted stand-in for the process runner: canned replies in order, and a record of every Command it was given.

Design: the gates-core design spec under docs/superpowers/specs/, section 3, "fake.py". A test hands FakeRunner the
replies it wants, in order, and passes it wherever a Runner is taken. Each call appends its Command to `commands` and
returns the next reply; a call with no reply left raises AssertionError naming the Command's argv. `completed` builds one
reply.
"""

from collections import deque
from collections.abc import Mapping, Sequence
from types import MappingProxyType

from gates.core.checker import Command, Completed


class FakeRunner:
    """A Runner that returns its replies in order and records each Command it was called with."""

    commands: list[Command]

    def __init__(self, replies: Sequence[Completed]) -> None:
        self.commands = []
        self._replies = deque(replies)

    def __call__(self, command: Command) -> Completed:
        self.commands.append(command)
        if not self._replies:
            raise AssertionError(f"FakeRunner has no reply left for {command.argv!r}")
        return self._replies.popleft()


def completed(
    status: int = 0,
    stdout: str = "",
    stderr: str = "",
    outputs: Mapping[str, str | None] = MappingProxyType({}),
    *,
    timed_out: bool = False,
) -> Completed:
    """A reply: the status, the streams, whether the cap was hit, and the output files' text, None for one not written."""
    return Completed(status=status, stdout=stdout, stderr=stderr, timed_out=timed_out, outputs=outputs)
