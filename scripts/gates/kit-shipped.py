#!/usr/bin/env python3
"""Gate: the kit a consumer installs is the kit this repository describes.

    scripts/gates/kit-shipped.py [--check]
    scripts/gates/kit-shipped.py --self-test

What a consumer gets is what the commit carries. A file that is on the author's
disk and in nobody's commit runs here and is absent there, and the lane it held
is off in every installed copy without a line anywhere saying so. The manifest,
the roster and the prose are three descriptions of one kit, and each of them can
drift from it on its own:

  * **The manifest names tracked files.** A wired hook that is untracked is a
    hook the install does not carry.
  * **The prose names tracked files.** A document naming `hooks/gone.py` sends
    a reader to a file the kit does not hold. Bare paths are checked here;
    `scripts/cite.py` resolves the ones carrying a line number.
  * **Every agent definition parses.** The frontmatter is what the host reads
    to spawn the agent, and its `name` is the key a hook matches on, so a file
    whose name and stem part is an agent nothing can reach.
  * **The roster is the agent set.** A row for a file that is not there, and a
    file no row names, are the same defect from two ends.
  * **The blind tables agree with the roster.** `no-impl-reads.py` carries a `BLIND`
    tuple, and the roster's Hooks column says which agents that hook holds.
    Either side moving alone leaves an agent the prose calls blind and the hook lets through.
  * **The version agrees with the changelog.** A manifest naming a version the
    changelog has no head for is a release nobody wrote down.

Every rule is read on every run, so one drifted description does not hide the
next.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]

HOOKS = ROOT / "hooks"

MANIFEST = ".claude-plugin/plugin.json"

ROSTER = "docs/agents.md"

CHANGELOG = "CHANGELOG.md"

AGENTS = "agents"

#: git answers about the index, and a slow answer is a broken checkout
TIMEOUT = 30

#: the keys the host reads out of an agent definition before it spawns one
FRONTMATTER = ("name", "description", "tools", "model")

#: a kit path as prose spells it: inside the kit, carrying an extension. The
#: template placeholders (`<gauntlet dir>`, `<slug>`) name no shipped file and
#: carry none of these extensions, so they never reach this pattern.
KIT_PATH = re.compile(r"(?:hooks|scripts|agents|\.claude-plugin)/[\w./-]+\.(?:py|sh|json|md)")

#: one roster row: the agent in the first cell, the hooks in the last
ROW = re.compile(r"^\|\s*`([a-z-]+)`\s*\|.*\|([^|]*)\|\s*$")

#: a released head of the changelog
HEAD = re.compile(r"^## \[([^\]]+)\]", re.MULTILINE)


def _load(name: str) -> ModuleType:
    """Import one hook module by path, since the hook names are hyphenated."""
    path = HOOKS / f"{name}.py"
    if str(HOOKS) not in sys.path:
        sys.path.insert(0, str(HOOKS))
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tracked(root: Path = ROOT) -> set[str]:
    """Every path the checkout's index carries, repo-relative."""
    done = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=False,
    )
    return set(done.stdout.split())


def manifest_paths(root: Path = ROOT) -> list[str]:
    """Every kit path the manifest's wired commands name, once each."""
    try:
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return []
    found = [
        match
        for listed in hooks.values()
        for group in listed
        for entry in group.get("hooks", [])
        if isinstance(entry, dict) and isinstance(entry.get("command"), str)
        for match in KIT_PATH.findall(entry["command"])
    ]
    return list(dict.fromkeys(found))


def prose_paths(root: Path = ROOT) -> dict[str, set[str]]:
    """Every kit path the tracked prose names, document to the paths in it."""
    out: dict[str, set[str]] = {}
    for name in sorted(p for p in tracked(root) if p.endswith(".md") and p != CHANGELOG):
        try:
            text = (root / name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        named = {
            found for quoted in re.findall(r"`([^`]+)`", text) for found in KIT_PATH.findall(quoted)
        }
        if named:
            out[name] = named
    return out


def frontmatter(text: str) -> dict[str, str] | None:
    """The frontmatter of one agent definition, or None where there is none."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    fields = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep and not key.startswith(" "):
            fields[key.strip()] = value.strip()
    return fields


def roster(root: Path = ROOT) -> dict[str, set[str]]:
    """The roster as the table states it: agent to the hooks its row names."""
    try:
        text = (root / ROSTER).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    out = {}
    for line in text.splitlines():
        found = ROW.match(line)
        if found:
            out[found.group(1)] = set(re.findall(r"`([a-z-]+)`", found.group(2)))
    return out


def version(root: Path = ROOT) -> tuple[str | None, str | None]:
    """The version the manifest names and the newest released changelog head."""
    try:
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        data = {}
    named = data.get("version") if isinstance(data, dict) else None
    try:
        text = (root / CHANGELOG).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        text = ""
    released = [head for head in HEAD.findall(text) if head != "Unreleased"]
    return (named if isinstance(named, str) else None), (released[0] if released else None)


def judge_paths(named: list[str], prose: dict[str, set[str]], carried: set[str]) -> list[str]:
    """Every path a description names that the commit does not carry."""
    problems = [
        f"{MANIFEST} wires {path}, which no commit carries. The install has no such hook"
        for path in named
        if path not in carried
    ]
    problems += [
        f"{document} names {path}, which no commit carries"
        for document, found in prose.items()
        for path in sorted(found)
        if path not in carried
    ]
    return problems


def judge_agents(definitions: dict[str, str], listed: dict[str, set[str]]) -> list[str]:
    """Every agent definition that cannot be spawned, and every roster drift."""
    problems = []
    for stem, text in sorted(definitions.items()):
        fields = frontmatter(text)
        if fields is None:
            problems.append(f"{AGENTS}/{stem}.md carries no frontmatter block the host can read")
            continue
        missing = [key for key in FRONTMATTER if not fields.get(key)]
        if missing:
            problems.append(f"{AGENTS}/{stem}.md names no {', '.join(missing)} in its frontmatter")
        if fields.get("name") and fields["name"] != stem:
            problems.append(
                f"{AGENTS}/{stem}.md is named {fields['name']!r} in its frontmatter. "
                "A hook matches on the name and the roster reads the file"
            )
    problems += [
        f"{ROSTER} has a row for {name}, and there is no {AGENTS}/{name}.md"
        for name in sorted(listed)
        if name not in definitions
    ]
    problems += [
        f"{AGENTS}/{stem}.md ships, and {ROSTER} has no row for it"
        for stem in sorted(definitions)
        if stem not in listed
    ]
    return problems


def judge_blind(blind: dict[str, tuple[str, ...]], listed: dict[str, set[str]]) -> list[str]:
    """Every agent a hook holds that the roster does not, and the other way."""
    problems = []
    for hook, names in sorted(blind.items()):
        held = set(names)
        says = {name for name, hooks in listed.items() if hook in hooks}
        problems += [
            f"{hook}.py holds {name}, and {ROSTER} does not say so" for name in sorted(held - says)
        ]
        problems += [
            f"{ROSTER} says {hook} holds {name}, and its BLIND tuple does not"
            for name in sorted(says - held)
        ]
    return problems


def judge_version(named: str | None, head: str | None) -> list[str]:
    """Why the manifest's version and the changelog's head cannot both stand."""
    if named is None and head is None:
        return []
    if named is None:
        return [f"{CHANGELOG} released {head}, and {MANIFEST} names no version"]
    if head is None:
        return [f"{MANIFEST} names version {named}, and {CHANGELOG} has no head for it"]
    if named != head:
        return [f"{MANIFEST} names version {named}, and {CHANGELOG} heads at {head}"]
    return []


def audit(root: Path = ROOT) -> list[str]:
    """Every way the shipped kit and its three descriptions part, in one pass."""
    carried = tracked(root)
    definitions = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted((root / AGENTS).glob("*.md"))
        if f"{AGENTS}/{path.name}" in carried
    }
    listed = roster(root)
    blind = {name: tuple(_load(name).BLIND) for name in ("no-impl-reads",)}
    named, head = version(root)
    return (
        judge_paths(manifest_paths(root), prose_paths(root), carried)
        + judge_agents(definitions, listed)
        + judge_blind(blind, listed)
        + judge_version(named, head)
    )


def check(root: Path = ROOT) -> int:
    """Read every description of the kit against the kit the commit carries."""
    problems = audit(root)
    for problem in problems:
        print(problem)
    print(f"{len(manifest_paths(root))} wired path(s), {len(roster(root))} roster row(s)")
    if problems:
        print(f"\n{len(problems)} problem(s). A consumer installs the commit, not the disk.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from kit_shipped_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
