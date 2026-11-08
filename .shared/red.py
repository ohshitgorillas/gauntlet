import re

RESULT = re.compile(r"(PASSED|FAILED|ERROR) (.+?)\s*$")
HEADER = re.compile(r"exit=(-?\d+) timed_out=(true|false)")


def cut(text: str) -> str:
    return "\n".join(line.split(" - ", 1)[0] for line in text.split("\n"))


def listing(text: str) -> dict[str, str]:
    found = {}
    for line in cut(text).split("\n"):
        match = RESULT.match(line)
        if match:
            found[match.group(2)] = match.group(1)
    return found


def _status(text: str) -> tuple[int, bool]:
    match = HEADER.match(text)
    return int(match.group(1)), match.group(2) == "true"


def _failing(text: str) -> set[str]:
    return {name for name, result in listing(text).items() if result != "PASSED"}


def red(run: str, brief: str, head: str = "") -> bool:
    baselines = [brief] + ([head] if head else [])
    exit_code, timed_out = _status(run)
    if timed_out and not any(_status(b)[1] for b in baselines):
        return True
    failing = _failing(run)
    if failing - set().union(*(_failing(b) for b in baselines)):
        return True
    return exit_code != 0 and not failing and all(_status(b)[0] == 0 for b in baselines)
