import importlib.util
from pathlib import Path

SRC = Path(__file__).with_name("files.py")


def load(monkeypatch, root, read="", write="", deny="", once="", copy="", hide=""):
    if root is None:
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    else:
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv("FENCE_READ", read)
    monkeypatch.setenv("FENCE_WRITE", write)
    monkeypatch.setenv("FENCE_DENY", deny)
    monkeypatch.setenv("FENCE_ONCE", once)
    monkeypatch.setenv("FENCE_COPY", copy)
    monkeypatch.setenv("FENCE_HIDE", hide)
    spec = importlib.util.spec_from_file_location("fence_files_under_test", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def put(root, rel, text="x\n"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p
