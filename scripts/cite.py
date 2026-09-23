#!/usr/bin/env python3
"""Resolve the citations in a plan against the tree.

A plan's citations are retyped by hand out of a `detective` table, and
nothing checks the retyping. The tree is frozen while a plan is drafted and
reviewed, so a citation that does not resolve is a transcription error and
nothing else: a mistyped path, a grep hit cited instead of the construct, a bare
`:49` inheriting the wrong file, a range off the end, a number typed from
memory. The whole class is decidable without reading a sentence, which is what
makes it a script's job rather than a reviewer's.

A citation is a backticked `path:line` or `path:line-line`. The path may be
omitted -- `:49` -- to continue the nearest preceding full citation. A number in
prose without backticks is not a citation and is never resolved.

    --check DOC        one row per reported citation, exit 1 where any row fails
    --check-all [DOC...]
                       --check over several documents, each row prefixed with
                       its document, exit 1 where any document has a failing
                       row. Named no document it takes every tracked `*.md` of
                       the checkout it is run in, which is the whole of what
                       this repository ships as prose.
    --fix DOC          fill a number from its quoted anchor where the anchor is
                        unique in the file, refusing on zero matches or several

The failing rows are `MISSING` (no such path), `RANGE` (a number or span past
the end of the file), `AMBIGUOUS` (a basename more than one unignored path carries),
`ORPHAN` (a bare number with no full citation before it) and `QUOTE` (a number
pointing at a line that does not contain the text quoted beside it).

Two rows print whether or not they fail, and neither sets the exit code.
`INHERITED-FROM` prints on every bare continuation, and `CROSS-REPO` on every
citation resolving outside this checkout. They are the cases where the script
resolved something the author cannot see in the text they wrote. Plans here are
written mostly in continuations, so a screen of `INHERITED-FROM` rows is the
normal output of a clean document, not a warning.

The guarantee is one sentence: the number points at a line containing that
quote. A citation carrying no quoted text is checked for existence only, and
that is the majority shape. A green `--check` says nothing whatever about
whether a cited line supports the sentence around it -- that judgment is the
`prosecutor`'s check (b), and it is untouched by this script.

The checkout root is the nearest ancestor of the document that carries `.git`,
a directory or a worktree's file, so a plan in a project that installs this kit
as a plugin resolves against that project and not against the plugin checkout,
and a document in a worktree checks that worktree's own copy. A document under
no checkout falls back to this file's own checkout.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: `${CLAUDE_PLUGIN_ROOT}/...` names the kit's checkout, not the document's
PLUGIN_ROOT = Path(__file__).resolve().parent.parent

PLUGIN_ROOT_VAR = "${CLAUDE_PLUGIN_ROOT}/"


def checkout_of(doc: Path, fallback: Path = ROOT) -> Path:
    """The checkout a document sits in: its nearest ancestor carrying `.git`.

    `.git` is a directory in a main checkout and a file in a worktree, and either
    marks the root. A document under neither resolves against `fallback`.
    """
    here = doc.resolve().parent
    for ancestor in (here, *here.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return fallback


SKIP = {".git", ".venv", ".pytest_cache", "node_modules", "__pycache__"}

_SPAN = re.compile(r"`([^`\n]+)`")
_CITE = re.compile(r"^(?P<path>[^\s`]*):(?P<start>\d+)(?:-(?P<end>\d+))?$")
_QUOTE = re.compile(r'"([^"\n]+)"')

FAILING = ("MISSING", "RANGE", "AMBIGUOUS", "ORPHAN", "QUOTE")


class Citation:
    """One backticked citation, as written and where it sits in the document."""

    def __init__(
        self,
        path: str,
        start: int,
        end: int,
        row: int,
        col_start: int,
        col_end: int,
    ) -> None:
        self.path = path  # as written, "" on a bare continuation
        self.start = start
        self.end = end  # == start where the citation names one line
        self.row = row  # 0-based index into the document's lines
        self.col_start = col_start  # offsets of the text inside the backticks
        self.col_end = col_end
        self.anchor = ""  # the quoted text beside it, "" where none
        self.inherited = ""  # the path a bare continuation resolved to
        self.resolved: Path | None = None  # None where it did not resolve
        self.verdict = "OK"
        self.detail = ""

    @property
    def text(self) -> str:
        span = f"{self.start}" if self.end == self.start else f"{self.start}-{self.end}"
        return f"{self.path}:{span}"

    @property
    def bare(self) -> bool:
        return self.path == ""

    @property
    def named(self) -> str:
        """The path the citation is about: its own, or the one it inherited."""
        return self.path or self.inherited


REACH = 80  # how far from a citation a quote may sit and still be its anchor


def quotes_in(line: str) -> list[re.Match[str]]:
    """The double-quoted spans of one document line, code spans excluded.

    A quote inside backticks is source text a sentence is showing, not text the
    sentence claims a line carries: `sys.exit(... if "--self-test" in argv ...)`
    quotes nothing about the tree.
    """
    code = [(s.start(), s.end()) for s in _SPAN.finditer(line)]
    out = []
    for found in _QUOTE.finditer(line):
        if any(s <= found.start() and found.end() <= e for s, e in code):
            continue
        out.append(found)
    return out


def anchor_pairs(line: str, cites: list[Citation]) -> None:
    """Bind each quote on the line to at most one citation, and set anchors.

    A plan writes the quote after the citation -- `${CLAUDE_PLUGIN_ROOT}/docs/plans.md:37` requires
    them, "A claim about the tree carries `file:line`" -- far more often than
    before it, so a following quote is claimed first and a preceding one only
    by a citation that found none. One quote binds once: where two citations
    sit either side of it, the one it follows has already taken it, and the
    second is a citation with no anchor rather than one with the wrong anchor.

    A backtick in the gap ends the reach, and so does a sentence end. A code
    span between the two means the quote is about that span rather than this
    citation, and a quote in the next sentence is about the next sentence: the
    plans here are soft-wrapped, so one document line is a whole paragraph and
    an unbounded reach would pair a citation with a quote several claims away.
    """
    quotes = quotes_in(line)
    taken: set[int] = set()
    _bind_following(line, cites, quotes, taken)
    _bind_preceding(line, cites, quotes, taken)


def reachable(gap: str) -> bool:
    """Whether a citation reaches across this gap to a quote.

    Too far, a backtick, or a sentence end, and it does not.
    """
    if len(gap) > REACH or "`" in gap:
        return False
    return not any(end in gap for end in (". ", "; ", "! ", "? "))


def _bind_following(
    line: str,
    cites: list[Citation],
    quotes: list[re.Match[str]],
    taken: set[int],
) -> None:
    """First pass: each citation claims the nearest quote after it."""
    for cite in cites:
        for i, found in enumerate(quotes):
            if i in taken or found.start() < cite.col_end:
                continue
            if reachable(line[cite.col_end + 1 : found.start()]):
                cite.anchor = found.group(1)
                taken.add(i)
            break


def _bind_preceding(
    line: str,
    cites: list[Citation],
    quotes: list[re.Match[str]],
    taken: set[int],
) -> None:
    """Second pass: a citation that claimed nothing looks behind it."""
    for cite in cites:
        if cite.anchor:
            continue
        for i in reversed(range(len(quotes))):
            found = quotes[i]
            if i in taken or found.end() > cite.col_start:
                continue
            if reachable(line[found.end() : cite.col_start - 1]):
                cite.anchor = found.group(1)
                taken.add(i)
            break


def parse(text: str) -> list[Citation]:
    """Every citation in the document, in document order."""
    found = []
    for row, line in enumerate(text.splitlines()):
        here = []
        for span in _SPAN.finditer(line):
            hit = _CITE.match(span.group(1))
            if not hit:
                continue
            start = int(hit.group("start"))
            end = int(hit.group("end")) if hit.group("end") else start
            here.append(Citation(hit.group("path"), start, end, row, span.start(1), span.end(1)))
        anchor_pairs(line, here)
        found += here
    return found


def _ls(at: Path | str, *args: str) -> subprocess.CompletedProcess[str]:
    """`git ls-files -z` run at `at`; a failure is its return code, never a raise."""
    cmd = ["git", "-C", str(at), "ls-files", "-z", *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)


def candidates(name: str) -> list[Path]:
    """Every path carrying that basename: what git shows, ignored files out, or a walk."""
    git = _ls(ROOT, "--cached", "--others", "--exclude-standard")
    shown = (ROOT / n for n in git.stdout.split("\0") if n and Path(n).name == name)
    hits = []
    for path in ROOT.rglob(name) if git.returncode else shown:
        #: relative to ROOT: a root that is itself a worktree searches its own tree
        parts = path.relative_to(ROOT).parts
        if any(part in SKIP for part in parts):
            continue
        if "worktrees" in parts:
            continue  # a worktree carries a second copy of every path in the tree
        if path.is_file():
            hits.append(path)
    return sorted(hits)


def _settle(cite: Citation, target: Path) -> None:
    """Resolve to `target` where it is a file, MISSING otherwise."""
    if target.is_file():
        cite.resolved = target
    else:
        cite.verdict = "MISSING"


def resolve(cite: Citation) -> None:
    """Set `resolved`, and a failing verdict where the path does not land."""
    named = cite.named
    if not named:
        cite.verdict = "ORPHAN"
        return
    if named.startswith(PLUGIN_ROOT_VAR):
        _settle(cite, PLUGIN_ROOT / named[len(PLUGIN_ROOT_VAR) :])
        return
    path = Path(named)
    if path.is_absolute():
        try:
            path.relative_to(ROOT)
        except ValueError:
            cite.detail = "outside the checkout"
        _settle(cite, path)
        return
    if "/" in named:
        _settle(cite, ROOT / named)
        return
    hits = candidates(named)
    if not hits:
        cite.verdict = "MISSING"
    elif len(hits) > 1:
        cite.verdict = "AMBIGUOUS"
        cite.detail = ", ".join(str(h.relative_to(ROOT)) for h in hits)
    else:
        cite.resolved = hits[0]


def lines_of(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def judge(cite: Citation) -> None:
    """The verdict for one citation whose path resolved."""
    if cite.resolved is None:
        return
    rows = lines_of(cite.resolved)
    if cite.start < 1 or cite.end > len(rows) or cite.end < cite.start:
        cite.verdict = "RANGE"
        cite.detail = f"the file has {len(rows)} lines"
        return
    if not cite.anchor:
        return
    span = rows[cite.start - 1 : cite.end]
    if not any(cite.anchor in row for row in span):
        cite.verdict = "QUOTE"
        cite.detail = span[0].strip()


def check(text: str) -> list[Citation]:
    """Every citation in the document, resolved and judged, in order."""
    cites = parse(text)
    carried = ""
    for cite in cites:
        if cite.bare:
            cite.inherited = carried
        resolve(cite)
        if cite.resolved is not None:
            judge(cite)
        if not cite.bare:
            carried = str(cite.resolved) if cite.resolved is not None else cite.path
        if cite.bare and cite.inherited:
            cite.inherited = str(cite.resolved) if cite.resolved else cite.inherited
    return cites


def shown(path: Path | str) -> str:
    """A resolved path, repo-relative where it is in the checkout."""
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def rows_for(cite: Citation) -> list[str]:
    """The rows one citation prints: its standing rows, then its failure."""
    out = []
    if cite.bare:
        where = shown(cite.inherited) if cite.inherited else "nothing"
        out.append(f"INHERITED-FROM  `{cite.text}`  {where}")
    if cite.resolved is not None and cite.detail == "outside the checkout":
        out.append(f"CROSS-REPO      `{cite.text}`  {cite.resolved}")
    if cite.verdict in FAILING:
        where = shown(cite.resolved) if cite.resolved is not None else cite.named
        row = f"{cite.verdict:<15} `{cite.text}`  {where}"
        if cite.detail and cite.detail != "outside the checkout":
            row += f"  {cite.detail}"
        out.append(row)
    return out


def report(text: str) -> list[str]:
    out = []
    for cite in check(text):
        out += rows_for(cite)
    return out


def fixes(text: str) -> list[tuple[Citation, int | None]]:
    """One `(citation, number)` per citation this document can fill, and one
    `(citation, None)` per citation whose anchor is not unique in its file."""
    out = []
    for cite in check(text):
        if cite.verdict not in ("QUOTE", "RANGE") or not cite.anchor:
            continue
        if cite.resolved is None:
            continue
        hits = [i + 1 for i, row in enumerate(lines_of(cite.resolved)) if cite.anchor in row]
        out.append((cite, hits[0] if len(hits) == 1 else None))
    return out


def apply_fixes(text: str) -> tuple[str, list[str]]:
    """The document with every fillable number filled, and the rows to print."""
    rows: list[str] = []
    edits: list[tuple[Citation, int]] = []
    for cite, number in fixes(text):
        if number is None:
            rows.append(f"REFUSED         `{cite.text}`  the anchor is not unique")
            continue
        rows.append(f"FIXED           `{cite.text}`  -> `{cite.path}:{number}`")
        edits.append((cite, number))

    lines = text.splitlines(keepends=True)
    for cite, number in sorted(edits, key=lambda e: (e[0].row, e[0].col_start), reverse=True):
        line = lines[cite.row]
        lines[cite.row] = line[: cite.col_start] + f"{cite.path}:{number}" + line[cite.col_end :]
    return "".join(lines), rows


def tracked_markdown() -> list[str]:
    """Every tracked `*.md` of the checkout this run sits in, repo-relative: not a
    walk, so an unadded draft and an ignored file are not checked, and the set is
    the one a reviewer sees in the diff."""
    listed = _ls(".", "*.md")
    if listed.returncode != 0:
        raise SystemExit("--check-all with no document needs a checkout: git ls-files failed here")
    return [name for name in listed.stdout.split("\0") if name and Path(name).is_file()]


def check_all(paths: list[str]) -> int:
    """`--check-all`: every row of every document, each resolved against its
    own checkout, prefixed with the document it came from. Exits 1 where any
    document carries a failing row.

    Handed no path it takes `tracked_markdown()`, so the mode has a default set
    and a run over the whole tree needs no shell expansion to name it."""
    global ROOT
    failed = False
    for p in paths or tracked_markdown():
        doc = Path(p)
        text = doc.read_text(encoding="utf-8")
        ROOT = checkout_of(doc)
        rows = report(text)
        for row in rows:
            print(f"{doc}: {row}")
        if any(row.split()[0] in FAILING for row in rows):
            failed = True
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", metavar="DOC", help="resolve and report, exit 1 on a failing row")
    mode.add_argument(
        "--check-all",
        metavar="DOC",
        nargs="*",
        help="check several documents, or every tracked *.md when named none, "
        "exit 1 where any carries a failing row",
    )
    mode.add_argument("--fix", metavar="DOC", help="fill a number from its unique quoted anchor")
    args = ap.parse_args(argv)

    if args.check_all is not None:
        return check_all(args.check_all)

    doc = Path(args.check or args.fix)
    text = doc.read_text(encoding="utf-8")
    global ROOT
    ROOT = checkout_of(doc)

    if args.check:
        rows = report(text)
        for row in rows:
            print(row)
        return 1 if any(row.split()[0] in FAILING for row in rows) else 0

    fixed, rows = apply_fixes(text)
    for row in rows:
        print(row)
    if fixed != text:
        doc.write_text(fixed, encoding="utf-8")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from cite_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv[1:]))
