from dataclasses import dataclass
from typing import Callable, TypedDict

from pin import slug

SLOTS = 12
STRETCH = 12
REPAIRS = 5
CAP = 200
IDLE = 1


@dataclass(frozen=True)
class OwnerCase:
    verdict: str
    case: str
    options: tuple[tuple[str, str], ...]
    summary: bool
    ends: str


@dataclass(frozen=True)
class Profile:
    folder: str
    author: str
    reviewer: str
    letter: str
    verdicts: tuple[str, ...]
    retire: str | None
    non_responsive: str
    attempts: tuple[str, ...]
    owner_cases: tuple[OwnerCase, ...]
    filed: Callable[[str, str, int], bool]
    iterations: bool = False


class State(TypedDict):
    round: int
    slug: str
    file: str
    owed: str
    next: str
    start: int
    since: int
    attempts: int
    non_responsive: int
    stretch: int
    repairs: int
    base: int
    rulings: list[str]
    review: str
    verdict: str


class Docket(TypedDict):
    case: str
    ask: bool
    attention: str
    options: list[list[str]]
    round: int
    summary: bool
    verdict: str
    idle: int
    reason: bool


class Closing(TypedDict):
    outcome: str
    file: str
    summary: str


def cited(folder: str, slug: str, round: int) -> bool:
    return False


def state(p: Profile, slug: str, start: int | None, first: int = 1) -> State:
    return State()


def docket(p: Profile, slug: str, first: int = 1) -> Docket:
    return Docket()


def screen(p: Profile, slug: str, round: int, quote: str) -> str:
    return ""


def record(p: Profile, slug: str, round: int, case: str, decision: str, text: str) -> str:
    return ""


def close(p: Profile, slug: str) -> Closing:
    return Closing()


def main(p: Profile) -> int:
    return 0
