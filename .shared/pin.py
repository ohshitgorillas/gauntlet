import re
from pathlib import PurePath


def slug(path: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", PurePath(path).stem.lower()).strip("-")
