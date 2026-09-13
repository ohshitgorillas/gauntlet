#!/usr/bin/env bash
#
# The whole shell of a blind agent, in three subcommands.
#
#   blind.sh test <path>             run the suite and the mechanical gates
#   blind.sh status <slug>           is that block's approved spec committed
#   blind.sh show <commit> <slug>    print that block's approved spec
#
# `.claude/hooks/blind-bash.py` denies the gauntlet-scrivener and the
# gauntlet-bailiff every command but these, matching the whole command text
# against one anchored pattern per subcommand. This script is the other half:
# the hook decides nothing about what a subcommand does, and this file offers
# no way to say anything the hook did not already admit.
#
# Every subcommand runs under `bwrap` with the whole filesystem read-only,
# because a blind agent's one command is not a way to write. The exception is
# the agent's own lane: a `test` run binds the tree's `tests/` back writable,
# which is the directory `tests-lane.py` already lets that agent write.
#
# It does not mask the implementation. A test run needs the code it tests on
# disk, and a mask turns the suite into a collect error, which separates
# nothing. The blindness that holds here is the blindness `no-impl-reads.py`
# holds: the agent cannot read the implementation, and cannot type a command
# that prints it.
#
# A slug names its worktree. `.claude/worktrees/<slug>-spec` is where a block's
# writer works, so `status` and `show` answer from that tree when it exists and
# from the main checkout when it does not. The tree's HEAD is the HEAD those
# two questions are about.

set -uo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
	echo "blind.sh: not inside a git checkout" >&2
	exit 2
}
cd "$ROOT" || exit 2

die() {
	echo "blind.sh: $1" >&2
	exit 2
}

usage() {
	echo "usage: blind.sh test <path> | status <slug> | show <commit> <slug>" >&2
	exit 2
}

#: the worktree a slug names, or the main checkout when it has none
tree_for_slug() {
	local wt=$ROOT/.claude/worktrees/$1-spec
	if [ -d "$wt" ]; then echo "$wt"; else echo "$ROOT"; fi
}

#: whole filesystem read-only, a private /tmp for whatever a tool caches, and
#: no view of any process outside. Extra arguments bind a path back writable.
sandbox() {
	bwrap \
		--ro-bind / / \
		--dev /dev \
		--proc /proc \
		--tmpfs /tmp \
		--tmpfs /run/user \
		--unshare-pid \
		--die-with-parent \
		"$@"
}

cmd_test() {
	[ $# -eq 1 ] || usage
	local path=$1 tree=$ROOT rel=$1 status=0 ran=0

	#: a path into a spec worktree names the tree it runs in; anything else is
	#: the main checkout, and the hook admits no third shape
	if [[ $path == .claude/worktrees/*-spec/* ]]; then
		tree=$ROOT/${path%%/tests/*}
		rel=tests/${path#*/tests/}
	fi
	[ -f "$tree/$rel" ] || die "no such test file: $path"

	run_gate() {
		local label=$1
		shift
		if [ ! -x "$1" ] && ! command -v "$1" >/dev/null 2>&1; then
			echo "SKIP  $label  (not installed)"
			return 0
		fi
		echo "--- $label"
		sandbox --bind "$tree/tests" "$tree/tests" \
			env -C "$tree" PYTHONPATH="$tree" PYTHONDONTWRITEBYTECODE=1 "$@"
		local rc=$?
		ran=1
		[ $rc -eq 0 ] || status=1
		return 0
	}

	if [[ $rel == *.py ]]; then
		run_gate pytest "$ROOT/.venv/bin/pytest" "$rel" -q -p no:cacheprovider
		run_gate ruff "$ROOT/.venv/bin/ruff" check tests
		run_gate black "$ROOT/.venv/bin/black" --check tests
	else
		run_gate node node --import ./tests/js/support/vendor-resolve.js --test "$rel"
		run_gate eslint npx eslint "$rel"
	fi

	[ "$ran" -eq 1 ] || die "no gate for $path is installed, so nothing ran"
	return $status
}

cmd_status() {
	[ $# -eq 1 ] || usage
	local tree
	tree=$(tree_for_slug "$1")
	sandbox env -C "$tree" git status --porcelain "gauntlet/specs/approved/$1.txt"
}

cmd_show() {
	[ $# -eq 2 ] || usage
	local tree
	tree=$(tree_for_slug "$2")
	sandbox env -C "$tree" git show "$1:gauntlet/specs/approved/$2.txt"
}

[ $# -ge 1 ] || usage
sub=$1
shift
case $sub in
test) cmd_test "$@" ;;
status) cmd_status "$@" ;;
show) cmd_show "$@" ;;
*) usage ;;
esac
