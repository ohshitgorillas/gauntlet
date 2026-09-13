#!/usr/bin/env bash
# Run the nine gates of this repository, one after another, at idle priority.
#
# Each gate runs once. Its output is saved to state/gates/<gate>.txt and never
# printed; what prints is one PASS or FAIL line per gate with its wall time.
# A gate passes on exit status 0. The script exits 1 if any gate failed.
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
    "plans-lane|python3 .claude/hooks/plans-lane.py --self-test"
    "specs-lane|python3 .claude/hooks/specs-lane.py --self-test"
    "tests-lane|python3 .claude/hooks/tests-lane.py --self-test"
    "reviews-lane|python3 .claude/hooks/reviews-lane.py --self-test"
    "verdicts-lane|python3 .claude/hooks/verdicts-lane.py --self-test"
    "no-impl-reads|python3 .claude/hooks/no-impl-reads.py --self-test"
    "excision-diff|python3 scripts/excision-diff.py --self-test"
    "cite|python3 scripts/cite.py --self-test"
)

failed=0
for entry in "${gates[@]}"; do
    name=${entry%%|*}
    read -ra cmd <<<"${entry#*|}"
    start=$EPOCHREALTIME
    nice -n 19 ionice -c3 "${cmd[@]}" >"$out/$name.txt" 2>&1
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
