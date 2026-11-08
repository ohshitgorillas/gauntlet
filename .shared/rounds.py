import hashlib
import json
import os
import re
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypedDict

from pin import slug

SLOTS = 12
STRETCH = 12
REPAIRS = 5
CAP = 200
IDLE = 1
ATTEMPTS = 5
NON_RESPONSIVE = 2
MODES = ("state", "filing", "docket", "screen", "record", "close")


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


def _lines(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if line.strip()] if path.is_file() else []


def _unresolved(line: str) -> list:
    return json.loads(line).get("unresolved", [])


def _entry_markers(line: str) -> int:
    return int(json.loads(line).get("markers", 0))


def cited(folder: str, slug: str, round: int) -> bool:
    lines = _lines(Path(folder) / f"{slug}.cite.{round}.txt")
    return bool(lines) and not _unresolved(lines[-1])


def _numbered(folder: Path, slug: str, kind: str, first: int) -> dict[int, Path]:
    pattern = re.compile(rf"{re.escape(slug)}\.{kind}(\d+)\.(?:txt|md)")
    found = {}
    for entry in folder.iterdir() if folder.is_dir() else ():
        match = pattern.fullmatch(entry.name)
        if match and int(match.group(1)) >= first:
            found[int(match.group(1))] = entry
    return found


_MARKUP = re.compile(r"[*_`#>~]")


def _verdict(p: Profile, path: Path) -> str | None:
    first_line = path.read_text().splitlines()[:1]
    head = _MARKUP.sub("", first_line[0] if first_line else "").strip()
    match = re.match(r"verdict:\s*(.*)", head, re.IGNORECASE)
    named = [v for v in p.verdicts if match and match.group(1).lower().startswith(v.lower())]
    return max(named, key=len) if named else None


def _ends(p: Profile, path: Path) -> bool:
    """Whether the ruling's decision ends the hearing."""
    head = path.read_text().splitlines()[:2]
    case = head[0].removeprefix("Case: ") if head else ""
    decision = head[1].removeprefix("Decision: ") if len(head) > 1 else ""
    return any(c.case == case and c.ends and c.ends == decision for c in p.owner_cases)


@dataclass(frozen=True)
class _Hearing:
    p: Profile
    slug: str
    round: int
    reviews: dict[int, Path]
    rulings: dict[int, Path]
    guards: dict[int, Path]
    verdicts: dict[int, str | None]
    tried: tuple[int, ...]
    since: int
    attempts: int
    non_responsive: int
    stretch: int
    repairs: int
    guard_count: int
    review_case: str
    owed: str
    idle: int


def _repairs(folder: Path, slug: str, rnd: int, guards: dict[int, Path]) -> int:
    marked = sum(1 for line in _lines(folder / f"{slug}.cite.{rnd}.txt") if _unresolved(line))
    entries = _lines(guards[rnd]) if rnd in guards else []
    return max(0, marked - (_entry_markers(entries[-1]) if entries else 0))


def _review_case(p: Profile, verdicts: dict[int, str | None], tried: tuple[int, ...], since: int, guards: dict[int, Path], counts: tuple[int, int]) -> str:
    """The case the latest tried round's review opens, '' when none or when a ruling or guard record follows it."""
    latest = tried[-1] if tried else 0
    if latest not in verdicts or since >= latest or any(n > latest for n in guards):
        return ""
    verdict = verdicts[latest]
    opened = [c.case for c in p.owner_cases if c.verdict == verdict]
    if opened:
        return opened[0]
    if verdict is None:
        return "unknown"
    if counts[0] >= ATTEMPTS:
        return "deadlock"
    return "non-responsive" if counts[1] >= NON_RESPONSIVE else ""


def _read(p: Profile, slug: str, first: int) -> _Hearing:
    folder = Path(p.folder)
    rounds = _numbered(folder, slug, "", first)
    reviews = _numbered(folder, slug, "review\\.", first)
    rulings = _numbered(folder, slug, "ruling\\.", first)
    guards = _numbered(folder, slug, "guard\\.", first)
    verdicts = {n: _verdict(p, path) for n, path in reviews.items()}
    tried = tuple(sorted(set(reviews) | set(rulings)))
    since = max(rulings, default=0)
    latest = max(rounds, default=0)
    settled = latest in tried and p.filed(p.folder, slug, latest)
    rnd = latest + 1 if settled else (latest or first)
    open_after = [n for n in verdicts if n > since]
    attempts = sum(1 for n in open_after if verdicts[n] in p.attempts)
    non_responsive = sum(1 for n in open_after if verdicts[n] == p.non_responsive)
    repairs = _repairs(folder, slug, rnd, guards)
    stretch = sum(1 for n in tried if n > since and n >= max(guards, default=0)) + repairs
    guard_count = sum(len(_lines(path)) for path in guards.values())
    idle = guard_count + 1
    asked = _review_case(p, verdicts, tried, since, guards, (attempts, non_responsive))
    ended = bool(rulings) and _ends(p, rulings[max(rulings)])
    bounded = stretch >= STRETCH or repairs >= REPAIRS or (folder / f"{slug}.idle.{idle}.md").exists()
    authored = rnd in rounds and p.filed(p.folder, slug, rnd)
    held = [
        ("approved", (folder / "approved" / f"{slug}.txt").exists()),
        ("ended", ended),
        ("owner", bool(asked) or bounded),
        (p.reviewer, authored),
    ]
    owed = next((who for who, holds in held if holds), p.author)
    return _Hearing(p, slug, rnd, reviews, rulings, guards, verdicts, tried, since, attempts, non_responsive, stretch, repairs, guard_count, asked, owed, idle)


def _slot(h: _Hearing, start: int) -> str:
    leading = sum(1 for n, v in h.verdicts.items() if h.p.retire and v == h.p.retire and n > start)
    if leading >= SLOTS:
        return "vacant"
    return h.p.author if h.owed == h.p.author else f"{h.p.letter}{1 + leading}"


def state(p: Profile, slug: str, start: int | None, first: int = 1, filing: bool = False) -> State:
    h = _read(p, slug, first)
    folder = Path(p.folder)
    latest_tried = h.tried[-1] if h.tried else 0
    iter_file = folder / f"{slug}.iter.txt"
    guard_rulings = sorted([(n, 0, path) for n, path in h.guards.items()] + [(n, 1, path) for n, path in h.rulings.items()], key=lambda item: item[:2])
    out = State(
        round=h.round,
        slug=slug,
        file=f"{p.folder}/{slug}.{h.round}.txt",
        owed=h.owed,
        next=_slot(h, latest_tried if start is None else start),
        start=latest_tried if start is None else start,
        since=h.since,
        attempts=h.attempts,
        non_responsive=h.non_responsive,
        stretch=h.stretch,
        repairs=h.repairs,
        base=len(_lines(iter_file)) if start is None else 0,
        rulings=[f"{p.folder}/{path.name}" for _, _, path in guard_rulings],
        review=f"{p.folder}/{h.reviews[max(h.reviews)].name}" if h.reviews else "",
        verdict=(h.verdicts[max(h.verdicts)] or "") if h.verdicts else "",
    )
    if filing:
        with iter_file.open("a") as handle:
            handle.write(f"{h.round} {h.owed} {h.guard_count} {h.repairs}\n")
    return out


def _is_slug_file(slug: str, name: str) -> bool:
    return name.startswith(f"{slug}.") or (name.startswith(f"{slug}-summary.") and name.endswith(".md"))


def _create(path: Path, text: str) -> bool:
    """Write a file that must not exist yet; False when it does."""
    made = False
    with suppress(FileExistsError):
        with path.open("x") as handle:
            handle.write(text)
        made = True
    return made


def _set_aside(folder: Path, slug: str) -> None:
    n = 1
    while (folder / "stale" / f"{slug}.{n}").exists():
        n += 1
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if path.is_file() and rel.parts[0] != "stale" and _is_slug_file(slug, path.name):
            target = folder / "stale" / f"{slug}.{n}" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(path, target)


def _settle_items(p: Profile, slug: str, items: Path) -> None:
    """Outside the loop: write the item file's hash once, and set the slug's files aside when it changed."""
    folder = Path(p.folder)
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(items.read_bytes()).hexdigest()
    mark = folder / f"{slug}.items.sha256"
    if mark.exists() and mark.read_text().strip() != digest:
        _set_aside(folder, slug)
    _create(mark, digest + "\n")


def docket(p: Profile, slug: str, first: int = 1) -> Docket:
    return Docket()


def screen(p: Profile, slug: str, round: int, quote: str) -> str:
    return ""


def record(p: Profile, slug: str, round: int, case: str, decision: str, text: str) -> str:
    return ""


def close(p: Profile, slug: str) -> Closing:
    return Closing()


def _number(name: str) -> int | None:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else None


def _refusal(mode: str, items: str) -> str:
    """Why the inputs cannot be run, '' when they can."""
    given = {name: os.environ.get(name, "").strip() for name in ("INPUTS_START", "INPUTS_BASE", "INPUTS_ROUND")}
    if mode not in MODES:
        return f"INPUTS_MODE must be one of {', '.join(MODES)}"
    if not slug(items):
        return "INPUTS_ITEMS must name an item file"
    if mode == "state" and not given["INPUTS_START"] and not Path(items).is_file():
        return f"INPUTS_ITEMS is not a file: {items}"
    bad = [name for name, raw in given.items() if raw and not raw.isdigit()]
    return f"{', '.join(bad)} must be a whole number" if bad else ""


def _run(p: Profile, mode: str, items: str) -> State | Docket | Closing:
    name = slug(items)
    start = _number("INPUTS_START")
    if mode in ("state", "filing"):
        if start is None and mode == "state":
            _settle_items(p, name, Path(items))
        return state(p, name, start, filing=mode == "filing")
    return Docket()


def main(p: Profile) -> int:
    mode = os.environ.get("INPUTS_MODE", "")
    items = os.environ.get("INPUTS_ITEMS", "")
    refusal = _refusal(mode, items)
    if refusal:
        print(f"rounds.py: {refusal}", file=sys.stderr)
    else:
        print(json.dumps(_run(p, mode, items)))
    return 2 if refusal else 0
