#!/usr/bin/env bash
#
# What a blind agent runs, in four subcommands. The agent holds no shell:
# `scripts/mcp/blind_server.py` execs `test`, `status` and `show` from typed
# tool arguments, and narrows what `test` prints before the agent sees it.
#
#   blind.sh test <path>             run the suite and the mechanical gates
#   blind.sh format <path>           rewrite that file with the fix tools
#   blind.sh status <slug>           is that block's approved spec committed
#   blind.sh show <commit> <slug>    print that block's approved spec
#
# Every subcommand runs under `bwrap` with the whole filesystem read-only, and
# one of them writes. The exception the mount table makes is the agent's own
# lane: a run binds the tree's `tests/` back writable, which is the directory
# `lanes.py` already lets that agent write, and `format` writes one tool's
# output into one path inside it. `test` stays read-only, so a green gate is
# evidence rather than a thing the verifier produced.
#
# It does not mask the implementation. A test run needs the code it tests on
# disk, and a mask turns the suite into a collect error, which separates
# nothing. The blindness holds on the two channels the agent has.
# `no-impl-reads.py` denies it every `Read`, `Grep` and `Glob` of the
# implementation, and the `test` tool of `scripts/mcp/blind_server.py` returns
# a narrowed report with no source line in it, so no line of the code reaches
# the agent through either.
#
# A slug names its worktree. `.claude/worktrees/<slug>-spec` is where a block's
# writer works, so `status` and `show` answer from that tree when it exists and
# from the main checkout when it does not. The tree's HEAD is the HEAD those
# two questions are about.

set -uo pipefail

#: Two trees. `CALLER` is the checkout the command was typed in, which is a
#: spec worktree when the caller's working directory sits inside one. `ROOT` is
#: the main checkout: `--git-common-dir` is the main checkout's `.git` from
#: inside a worktree as well, and the checkout is its parent. `.venv/` and the
#: worktrees live under `ROOT` and nowhere else, so a runner is found there
#: whatever tree the caller stands in; a bare test path is the caller's.
CALLER=$(git rev-parse --show-toplevel 2>/dev/null) || {
	echo "blind.sh: not inside a git checkout" >&2
	exit 2
}
common_dir=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
[ -n "$common_dir" ] || {
	echo "blind.sh: cannot resolve the main checkout" >&2
	exit 2
}
ROOT=$(dirname "$common_dir")
cd "$ROOT" || exit 2

#: `shell_shapes.config()` reads the declaration from `$CLAUDE_PROJECT_DIR`, and
#: the variable is set for a hook but not for a `Bash` child. So the main
#: checkout is exported for everything below: the declaration is the project's,
#: and a worktree carries no copy of it. A variable already set is the caller's
#: and stands.
if [ -z "${CLAUDE_PROJECT_DIR:-}" ]; then
	CLAUDE_PROJECT_DIR=$ROOT
	export CLAUDE_PROJECT_DIR
fi

die() {
	echo "blind.sh: $1" >&2
	exit 2
}

usage() {
	echo "usage: blind.sh test <path> | format <path> | status <slug> | show <commit> <slug>" >&2
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

#: the values of `.claude/blind-reads.json`, through the same reader
#: the hooks use, so the lane this script binds writable is the lane
#: `lanes.py` guards, and the block it shows is the one the same file holds
#:
#: The reader is found beside this script rather than under `$ROOT`, because
#: `scripts/` and `hooks/` travel together as the plugin and `$ROOT` is the
#: checkout being worked on, which holds neither once the kit is installed
#: rather than copied. The declaration it reads is still the project's.
READER=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/lib/shell_shapes.py
cfg() {
	[ -f "$READER" ] || die "no $READER: scripts/ ships with hooks/, copy both"
	python3 "$READER" --config "$1"
}
SPECS=$(cfg specs_lane) || die "cannot read the approved-specs lane"

#: one configured runner invocation into an array, one word per line, so an
#: argument carrying a space stays one argument. A word with a slash is a path
#: in this checkout and is read from $ROOT: the run happens with the tree as its
#: working directory, and a bare word is left alone because it is on PATH.
read_runner() {
	local -n words=$1
	words=()
	local line
	while IFS= read -r line; do words+=("$line"); done < <(cfg "$2")
	[ ${#words[@]} -gt 0 ] || die "cannot read the $2 runner"
	case ${words[0]} in
	/*) ;;
	*/*) words[0]=$ROOT/${words[0]} ;;
	esac
}

#: the tree a path runs in, the path inside it, and the lane, for both verbs.
#: One helper, so `test` and `format` cannot part on which tree a worktree path
#: names. It sets `TREE`, `REL`, `TESTS`, and the two the gate runner keeps.
target() {
	local path=$1
	TREE=$CALLER
	REL=$path
	STATUS=0
	RAN=0
	TESTS=$(cfg tests_dir)

	#: a path into a spec worktree names the tree it runs in; anything else is
	#: the caller's own tree, and the hook admits no third shape. A blind
	#: writer's shell stands in the main checkout, so the worktree form is the
	#: one that reaches its tree; the bare form is for a caller already inside.
	if [[ $path == .claude/worktrees/*-spec/* ]]; then
		#: `$TESTS` is quoted inside both expansions because it is the needle,
		#: not the pattern: a `tests_dir` carrying `*` or `?` would otherwise
		#: match a directory it does not name.
		TREE=$ROOT/${path%%/"$TESTS"/*}
		REL=$TESTS/${path#*/"$TESTS"/}
	fi
	[ -f "$TREE/$REL" ] || die "no such test file: $path"
}

run_gate() {
	local label=$1
	shift
	if [ ! -x "$1" ] && ! command -v "$1" >/dev/null 2>&1; then
		echo "SKIP  $label  (not installed)"
		return 0
	fi
	echo "--- $label"
	#: the tree is read-only inside the sandbox and a fresh worktree has no
	#: `.ruff_cache`, which ruff cannot create there and fails on. Its cache
	#: goes under the sandbox's private `/tmp` instead; pytest already
	#: carries `-p no:cacheprovider`, and black's cache failure is silent.
	#:
	#: The lane is bound writable for both verbs, because it is the lane and
	#: not the mount that scopes a `format` run: the argument is one file, and
	#: a bind of that file alone would turn on whether a fix tool writes in
	#: place or renames through the directory.
	sandbox --bind "$TREE/$TESTS" "$TREE/$TESTS" \
		env -C "$TREE" PYTHONPATH="$TREE" PYTHONDONTWRITEBYTECODE=1 \
		RUFF_CACHE_DIR=/tmp/ruff-cache "$@"
	local rc=$?
	RAN=1
	[ $rc -eq 0 ] || STATUS=1
	return 0
}

cmd_test() {
	[ $# -eq 1 ] || usage
	target "$1"

	#: the runner for this file's extension, then the lint gates. The runner is
	#: `pytest_command` or `node_command` from `blind-reads.json`, so a project
	#: that deselects a marker or imports a loader names it there rather than
	#: here; the path and the flags below it are this script's own. `-rfEp`
	#: puts one summary line per passed, failed and errored id, which is the
	#: line `scripts/mcp/blind_server.py` narrows the run to. `-v` puts one line
	#: per id in collection order above it, which is where the server reads the
	#: bracket index it puts in place of a parametrize id.
	local -a runner
	if [ "${REL##*.}" = py ]; then
		read_runner runner pytest_command
		run_gate pytest "${runner[@]}" "$REL" -v -rfEp -p no:cacheprovider
		run_gate ruff "$ROOT/.venv/bin/ruff" check "$TESTS"
		run_gate black "$ROOT/.venv/bin/black" --check "$TESTS"
	else
		read_runner runner node_command
		run_gate node "${runner[@]}" "$REL"
		run_gate eslint npx eslint "$REL"
	fi

	[ "$RAN" -eq 1 ] || die "no gate for $1 is installed, so nothing ran"
	return $STATUS
}

#: the one writing verb. The fix tools of the file's extension, over the one
#: path the argument names and never the lane: that is what keeps a writer off
#: a test another block pinned. No `--unsafe-fixes`, because a fix that changes
#: what a test asserts is the writer's to make by hand, where the diff shows it.
cmd_format() {
	[ $# -eq 1 ] || usage
	target "$1"

	if [ "${REL##*.}" = py ]; then
		run_gate ruff "$ROOT/.venv/bin/ruff" check --fix "$REL"
		run_gate black "$ROOT/.venv/bin/black" "$REL"
	else
		run_gate eslint npx eslint --fix "$REL"
	fi

	[ "$RAN" -eq 1 ] || die "no gate for $1 is installed, so nothing ran"
	return $STATUS
}

cmd_status() {
	[ $# -eq 1 ] || usage
	local tree
	tree=$(tree_for_slug "$1")
	sandbox env -C "$tree" git status --porcelain "$SPECS/$1.txt"
}

cmd_show() {
	[ $# -eq 2 ] || usage
	local tree
	tree=$(tree_for_slug "$2")
	sandbox env -C "$tree" git show "$1:$SPECS/$2.txt"
}

[ $# -ge 1 ] || usage
sub=$1
shift
case $sub in
test) cmd_test "$@" ;;
format) cmd_format "$@" ;;
status) cmd_status "$@" ;;
show) cmd_show "$@" ;;
*) usage ;;
esac
