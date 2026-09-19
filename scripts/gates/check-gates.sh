#!/usr/bin/env bash
# Run the gates of this repository, one after another, at idle priority.
#
# Each gate runs once. Its output is saved to state/gates/<gate>.txt and never
# printed; what prints is one PASS or FAIL line per gate with its wall time.
# A gate passes on exit status 0. The script exits 1 if any gate failed.
#
# Each gate runs with GAUNTLET scrubbed from its environment, so the report is
# about the hooks as they are wired rather than about however the launching
# session happened to be started. A green report produced inside a bypassed
# session would otherwise be a report about nothing.
#
# Works from the main checkout and from a .claude/worktrees/* tree: the suite
# runs with PYTHONPATH set to the tree the script sits in, and a tree without
# its own .venv uses the main checkout's.

set -u

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$root" || exit 2

pytest=$root/.venv/bin/pytest
if [[ ! -x $pytest ]]; then
    common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
    pytest=$(dirname "$common")/.venv/bin/pytest
fi
if [[ ! -x $pytest ]]; then
    echo "no .venv/bin/pytest in $root or the main checkout" >&2
    exit 2
fi

out=$root/state/gates
mkdir -p "$out"

gates=(
    "pytest|env PYTHONPATH=$root $pytest tests -q"
    "lanes|python3 hooks/lanes.py --self-test"
    "no-impl-reads|python3 hooks/no-impl-reads.py --self-test"
    "blind-bash|python3 hooks/blind-bash.py --self-test"
    "gauntlet-off|python3 hooks/gauntlet-off.py --self-test"
    "bwrap-wrap|python3 hooks/bwrap-wrap.py --self-test"
    "lane-audit|python3 hooks/lane-audit.py --self-test"
    "pair-passthrough|python3 hooks/pair-passthrough.py"
    "strike-diff|python3 scripts/strike-diff.py --self-test"
    "pair|python3 scripts/pair/cli.py --self-test"
    "cite|python3 scripts/cite.py --self-test"
    "init|python3 scripts/init.py --self-test"
    "symbol-closure|python3 scripts/gates/symbol-closure.py --self-test"
    "file-length|python3 scripts/gates/file-length.py --check"
    "file-length-self|python3 scripts/gates/file-length.py --self-test"
)

failed=0
for entry in "${gates[@]}"; do
    name=${entry%%|*}
    read -ra cmd <<<"${entry#*|}"
    start=$EPOCHREALTIME
    env -u GAUNTLET nice -n 19 ionice -c3 "${cmd[@]}" >"$out/$name.txt" 2>&1
    status=$?
    secs=$(awk -v a="$start" -v b="$EPOCHREALTIME" 'BEGIN { printf "%.1f", b - a }')
    if ((status == 0)); then
        verdict=PASS
    else
        verdict=FAIL
        failed=1
    fi
    printf '%s  %-14s %6ss\n' "$verdict" "$name" "$secs"
done

echo "output: ${out#"$root"/}/<gate>.txt"
exit "$failed"
