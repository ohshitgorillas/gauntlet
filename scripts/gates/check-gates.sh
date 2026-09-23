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
#
# coverage-hooks is a floor of its own for hooks/, under the whole-repo one.
# The kit's own bar is each hook's --self-test, which runs outside coverage, so
# the suite measures the hooks lower than it measures the scripts; a single
# figure over both lets hook coverage fall while the total holds. The number is
# a ratchet like file-length's allowances: it goes up and never down.
#
# The lint gates are ruff, black, mypy, vulture, shellcheck and coverage, run
# after pytest and before the self-tests. vulture reads its paths and its
# confidence floor from pyproject.toml, so it takes no argument here.
#
# The suite drives most of this kit as a subprocess, so the pytest gate puts
# scripts/coverage_subprocess on PYTHONPATH and names COVERAGE_PROCESS_START:
# the tracer then starts in each of those processes rather than measuring only
# the wrappers. COVERAGE_FILE is absolute because a subprocess run from a
# throwaway checkout would otherwise leave its data beside that checkout.
# coverage-combine folds the per-process files together before coverage reports.

set -u

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$root" || exit 2

venv=$root/.venv
if [[ ! -x $venv/bin/pytest ]]; then
    common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
    venv=$(dirname "$common")/.venv
fi
if [[ ! -x $venv/bin/pytest ]]; then
    echo "no .venv/bin/pytest in $root or the main checkout" >&2
    exit 2
fi

out=$root/state/gates
mkdir -p "$out"

gates=(
    "pytest|env PYTHONPATH=$root/scripts/coverage_subprocess:$root COVERAGE_PROCESS_START=$root/pyproject.toml COVERAGE_FILE=$root/.coverage $venv/bin/coverage run -m pytest tests -q"
    "ruff|$venv/bin/ruff check ."
    "black|$venv/bin/black --check ."
    "mypy|$venv/bin/mypy hooks scripts"
    "vulture|$venv/bin/vulture"
    "shellcheck|shellcheck -S style scripts/pair.sh scripts/blind.sh scripts/gates/check-gates.sh"
    "coverage-combine|$venv/bin/coverage combine"
    "coverage|$venv/bin/coverage report"
    "coverage-hooks|$venv/bin/coverage report --include=hooks/* --fail-under=27"
    "lanes|python3 hooks/lanes.py --self-test"
    "no-impl-reads|python3 hooks/no-impl-reads.py --self-test"
    "gauntlet-off|python3 hooks/gauntlet-off.py --self-test"
    "bwrap-wrap|python3 hooks/bwrap-wrap.py --self-test"
    "blind-write|python3 hooks/blind-write.py --self-test"
    "shell-binds|python3 hooks/lib/shell_binds.py --self-test"
    "lane-audit|python3 hooks/lane-audit.py --self-test"
    "strike-diff|python3 scripts/strike-diff.py --self-test"
    "pair|python3 scripts/pair/cli.py --self-test"
    "cite|python3 scripts/cite.py --self-test"
    "init|python3 scripts/init.py --self-test"
    "blind-server|python3 scripts/mcp/blind_server.py --self-test"
    "blind-write-server|python3 scripts/mcp/blind_write_server.py --self-test"
    "pair-server|python3 scripts/mcp/pair_server.py --self-test"
    "symbol-closure|python3 scripts/gates/code/symbol-closure.py --self-test"
    "file-length|python3 scripts/gates/code/file-length.py --check"
    "file-length-self|python3 scripts/gates/code/file-length.py --self-test"
    "gates-wired|python3 scripts/gates/wiring/gates-wired.py --check"
    "gates-wired-self|python3 scripts/gates/wiring/gates-wired.py --self-test"
    "hooks-wired|python3 scripts/gates/hookgates/hooks-wired.py --check"
    "hooks-wired-self|python3 scripts/gates/hookgates/hooks-wired.py --self-test"
    "wrap-scale|python3 scripts/gates/wrap/wrap-scale.py --check"
    "wrap-scale-self|python3 scripts/gates/wrap/wrap-scale.py --self-test"
    "wrap-runtime|python3 scripts/gates/wrap/wrap-runtime.py --check"
    "wrap-runtime-self|python3 scripts/gates/wrap/wrap-runtime.py --self-test"
    "kit-live|python3 scripts/gates/wiring/kit-live.py --check"
    "kit-live-self|python3 scripts/gates/wiring/kit-live.py --self-test"
    "kit-probe|python3 hooks/kit-probe.py --self-test"
    "hook-latency|python3 scripts/gates/hookgates/hook-latency.py --check"
    "hook-latency-self|python3 scripts/gates/hookgates/hook-latency.py --self-test"
    "hook-degenerate|python3 scripts/gates/hookgates/hook-degenerate.py --check"
    "hook-degenerate-self|python3 scripts/gates/hookgates/hook-degenerate.py --self-test"
    "selftest-honest|python3 scripts/gates/wiring/selftest-honest.py --check"
    "selftest-honest-self|python3 scripts/gates/wiring/selftest-honest.py --self-test"
    "consumer-smoke|python3 scripts/gates/wiring/consumer-smoke.py --check"
    "consumer-smoke-self|python3 scripts/gates/wiring/consumer-smoke.py --self-test"
    "verdict-corpus|python3 scripts/gates/hookgates/verdict-corpus.py --check"
    "verdict-corpus-self|python3 scripts/gates/hookgates/verdict-corpus.py --self-test"
    "kit-shipped|python3 scripts/gates/wiring/kit-shipped.py --check"
    "kit-shipped-self|python3 scripts/gates/wiring/kit-shipped.py --self-test"
    "wrap-concurrency|python3 scripts/gates/wrap/wrap-concurrency.py --check"
    "wrap-concurrency-self|python3 scripts/gates/wrap/wrap-concurrency.py --self-test"
    "hook-cwd|python3 scripts/gates/hookgates/hook-cwd.py --check"
    "hook-cwd-self|python3 scripts/gates/hookgates/hook-cwd.py --self-test"
    "blind-no-shell|python3 scripts/gates/hookgates/blind-no-shell.py --check"
    "blind-no-shell-self|python3 scripts/gates/hookgates/blind-no-shell.py --self-test"
    "no-command-reads|python3 scripts/gates/hookgates/no-command-reads.py --check"
    "no-command-reads-self|python3 scripts/gates/hookgates/no-command-reads.py --self-test"
    "md-softwrap|python3 scripts/gates/code/md-softwrap.py --check"
    "md-softwrap-self|python3 scripts/gates/code/md-softwrap.py --self-test"
    "nesting|python3 scripts/gates/code/nesting.py"
    "nesting-self|python3 scripts/gates/code/nesting.py --self-test"
    "no-barrels|python3 scripts/gates/code/no-barrels.py"
    "no-barrels-self|python3 scripts/gates/code/no-barrels.py --self-test"
    "subprocess-timeout|python3 scripts/gates/code/subprocess-timeout.py"
    "subprocess-timeout-self|python3 scripts/gates/code/subprocess-timeout.py --self-test"
    "changelog|python3 scripts/gates/repo/changelog.py"
    "changelog-self|python3 scripts/gates/repo/changelog.py --self-test"
    "commit-msg|python3 scripts/gates/repo/commit-msg.py"
    "commit-msg-self|python3 scripts/gates/repo/commit-msg.py --self-test"
    "test-assertions|python3 scripts/gates/testpolicy/test-assertions.py"
    "test-assertions-self|python3 scripts/gates/testpolicy/test-assertions.py --self-test"
    "no-copy-assertions|python3 scripts/gates/testpolicy/no-copy-assertions.py"
    "no-copy-assertions-self|python3 scripts/gates/testpolicy/no-copy-assertions.py --self-test"
    "test-clocks|python3 scripts/gates/testpolicy/test-clocks.py"
    "test-clocks-self|python3 scripts/gates/testpolicy/test-clocks.py --self-test"
    "cite-check|python3 scripts/cite.py --check-all"
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
    printf '%s  %-23s %6ss\n' "$verdict" "$name" "$secs"
done

echo "output: ${out#"$root"/}/<gate>.txt"
exit "$failed"
