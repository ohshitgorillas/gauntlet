import importlib.util
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent


def load(name):
    # .shared goes on sys.path so a module's own "from pin import slug" resolves as it does in production.
    if str(SHARED) not in sys.path:
        sys.path.insert(0, str(SHARED))
    spec = importlib.util.spec_from_file_location(f"shared_{name}_under_test", SHARED / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
