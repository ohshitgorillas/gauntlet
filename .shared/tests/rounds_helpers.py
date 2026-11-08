import contextlib
import io
import json
import os
from pathlib import Path
from unittest import mock

PASS = "Verdict: ANOTHER PASS"
READY = "Verdict: READY"
LEAD = "Verdict: OBJECTION: LEADING"


def profile(rounds, folder, **over):
    owner = (
        rounds.OwnerCase("READY", "review", (("approve", "Approve"), ("revise", "Revise")), True, "approve"),
        rounds.OwnerCase("INVALID", "invalid", (("confirm", "Confirm"), ("revise", "Revise")), True, "confirm"),
        rounds.OwnerCase("APPROACH THE BENCH", "bench", (("reply", "Reply"),), False, ""),
    )
    fields = dict(
        folder=str(folder),
        author="speccer",
        reviewer="arbiter",
        letter="a",
        verdicts=("READY", "ANOTHER PASS", "APPROACH THE BENCH", "INVALID", "OBJECTION: LEADING", "OBJECTION: NON-RESPONSIVE", "SCREENED"),
        retire="OBJECTION: LEADING",
        non_responsive="OBJECTION: NON-RESPONSIVE",
        attempts=("ANOTHER PASS", "APPROACH THE BENCH"),
        owner_cases=owner,
        filed=lambda folder, slug, round: True,
        iterations=True,
    )
    fields.update(over)
    return rounds.Profile(**fields)


def put(folder, name, text="x\n"):
    path = Path(folder) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def round_file(folder, slug, n, text="a round\n"):
    return put(folder, f"{slug}.{n}.txt", text)


def review(folder, slug, n, first_line=PASS, body="the review text\n"):
    return put(folder, f"{slug}.review.{n}.txt", f"{first_line}\n{body}")


def ruling(folder, slug, n, case="review", decision="revise", text="the owner's words\n"):
    return put(folder, f"{slug}.ruling.{n}.txt", f"Case: {case}\nDecision: {decision}\nQuestion: q\nText: {text}")


def guard(folder, slug, n, markers=0, entries=1):
    entry = json.dumps({"case": "guard", "question": "q", "decision": "reply", "text": "t", "markers": markers})
    return put(folder, f"{slug}.guard.{n}.txt", (entry + "\n") * entries)


def cite(folder, slug, n, lines):
    text = "".join(json.dumps({"unresolved": line}) + "\n" for line in lines)
    return put(folder, f"{slug}.cite.{n}.txt", text)


def idle(folder, slug, k, text="why nothing moved\n"):
    return put(folder, f"{slug}.idle.{k}.md", text)


def summary(folder, slug, n, text="the summary\n"):
    return put(folder, f"{slug}-summary.{n}.md", text)


def iterations(folder, slug, count):
    return put(folder, f"{slug}.iter.txt", "x\n" * count)


def approved(folder, slug):
    return put(folder, f"approved/{slug}.txt", "approved text\n")


def hashed(folder, slug, digest):
    return put(folder, f"{slug}.items.sha256", digest + "\n")


def leading(count):
    files = []
    for n in range(1, count + 1):
        files += [("round", n), ("review", n, LEAD)]
    return files


KINDS = {
    "round": round_file,
    "review": review,
    "ruling": ruling,
    "guard": guard,
    "cite": cite,
    "idle": idle,
    "summary": summary,
    "iter": iterations,
    "approved": approved,
    "hash": hashed,
    "put": put,
}


def build(folder, slug, files):
    """Write a hearing's files. Each entry is (kind, *args) with a kind from KINDS."""
    Path(folder).mkdir(parents=True, exist_ok=True)
    for kind, *args in files:
        if kind == "put":
            put(folder, *args)
        else:
            KINDS[kind](folder, slug, *args)


def run_main(rounds, prof, **inputs):
    """Run main with INPUTS_* set to the given inputs. Returns (exit code, stdout text, parsed JSON or {})."""
    env = {f"INPUTS_{key.upper()}": str(value) for key, value in inputs.items()}
    out = io.StringIO()
    with mock.patch.dict(os.environ, env):
        for key in [k for k in os.environ if k.startswith("INPUTS_") and k not in env]:
            del os.environ[key]
        with contextlib.redirect_stdout(out):
            code = rounds.main(prof)
    text = out.getvalue()
    return code, text, json.loads(text) if text.strip() else {}
