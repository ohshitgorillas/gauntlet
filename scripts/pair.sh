#!/usr/bin/env bash
#
# Move a block between the reviewer, the writer and the tree.
#
#   pair.sh open <slug>    cut the spec worktree, on the reviewed block only
#   pair.sh red <slug>     run the suite there, and remove whole-file targets
#   pair.sh merge <slug>   merge the spec branch, then check what landed
#
# The stdout of each is contract, and docs/agents.md carries the table. A
# blind writer reads these literals there, never here.
#
# `open` refuses on a mismatch because the approved spec is editable after the
# reviewer passed it and the round file is not. Comparing the two is what makes
# the block that reaches the writer the block that was reviewed, rather than
# the latest one someone typed.

set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

PYTEST=${PYTEST:-$ROOT/.venv/bin/pytest}

die() {
	echo "$1" >&2
	exit 2
}

spec_path() { echo "docs/gauntlet/specs/$1.txt"; }
worktree_path() { echo ".claude/worktrees/$1-spec"; }

#: everything below the divider is the reviewer's own output, verbatim
reviewer_section() {
	sed -n '/^--- reviewer ---$/,$p' "$1" | tail -n +2
}

#: the highest <N> the reviewer has written for this slug, or nothing
newest_round() {
	local slug=$1 newest= best=-1 n
	for f in docs/gauntlet/reviews/"$slug".[0-9]*.txt; do
		[ -e "$f" ] || continue
		n=${f##*"$slug".}
		n=${n%.txt}
		case $n in
		'' | *[!0-9]*) continue ;;
		esac
		if [ "$n" -gt "$best" ]; then
			best=$n
			newest=$f
		fi
	done
	echo "$newest"
}

#: `N. excise <target>` lines of the committed block, targets only
excise_targets() {
	sed -n 's/^[[:space:]]*[0-9][0-9]*\.[[:space:]]*excise[[:space:]]*//p' "$1"
}

block_kind() {
	sed -n 's/^kind:[[:space:]]*//p' "$1" | head -1
}

cmd_open() {
	local slug=$1 spec wt round
	spec=$(spec_path "$slug")
	wt=$(worktree_path "$slug")
	[ -f "$spec" ] || die "no approved spec at $spec"

	round=$(newest_round "$slug")
	[ -n "$round" ] || die "no reviewer round on disk for $slug"

	if ! diff -q <(reviewer_section "$spec") <(cat "$round") >/dev/null; then
		echo "MISMATCH $round"
		exit 1
	fi

	git worktree add "$wt" -b "spec/$slug" >/dev/null
	echo "OPEN $wt"
}

cmd_red() {
	local slug=$1 spec wt out target
	spec=$(spec_path "$slug")
	wt=$(worktree_path "$slug")
	[ -d "$wt" ] || die "no spec worktree at $wt"

	#: a single test is an Edit and the writer's; a whole file cannot be,
	#: because the lane hook denies every agent the shell it would take
	while IFS= read -r target; do
		[ -n "$target" ] || continue
		case $target in
		*::*) continue ;;
		esac
		rm -f "$wt/$target"
	done < <(excise_targets "$spec")

	mkdir -p state/red
	out=state/red/$slug.txt
	#: verbose, so a passing test is named rather than summarized as a dot:
	#: the juror rules on the names this file carries and on nothing else
	(cd "$wt" && "$PYTEST" -v) >"$out" 2>&1 || true
	echo "$out"
}

cmd_merge() {
	local slug=$1 spec kind base red out
	spec=$(spec_path "$slug")
	[ -f "$spec" ] || die "no approved spec at $spec"

	base=$(git merge-base HEAD "spec/$slug")
	git merge --no-edit -q "spec/$slug"

	kind=$(block_kind "$spec")
	case $kind in
	excision | repair)
		#: no implementation phase, so no window for a test to soften in:
		#: the mechanical check takes the gauntlet-bailiff's round
		python3 scripts/excision-diff.py --spec "$spec" --base "$base" --head HEAD
		;;
	*)
		red=state/red/$slug.txt
		mkdir -p state/merge
		out=state/merge/$slug.txt
		#: evidence by path, not by paste: the main agent only carries the
		#: brief, and the gauntlet-bailiff reads this file itself
		{
			echo "test files:"
			git diff --name-only "$base" HEAD -- tests/
			echo "diff:"
			git diff "$base" HEAD -- tests/
			echo "red output:"
			#: no red log on disk is a complete brief with an empty section,
			#: not an errexit abort that leaves the block unterminated
			[ -f "$red" ] && cat "$red" || true
		} >"$out"
		echo "TEST CHECK $slug"
		echo "spec commit: $(git rev-parse HEAD:"$spec" 2>/dev/null || echo unknown)"
		echo "red commit: $(git rev-parse "spec/$slug")"
		echo "merge output: $out"
		echo "END TEST CHECK"
		;;
	esac
}

main() {
	[ $# -ge 2 ] || die "usage: pair.sh open|red|merge <slug>"
	case $1 in
	open) cmd_open "$2" ;;
	red) cmd_red "$2" ;;
	merge) cmd_merge "$2" ;;
	*) die "usage: pair.sh open|red|merge <slug>" ;;
	esac
}

main "$@"
