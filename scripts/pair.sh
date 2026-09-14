#!/usr/bin/env bash
#
# Move a block between the reviewer, the writer and the tree.
#
#   pair.sh open <slug>    cut the spec worktree, on the reviewed block only
#   pair.sh red <slug>     run the suite there, and remove whole-file targets
#   pair.sh merge <slug>   merge the spec branch, then check what landed
#   pair.sh review <slug>  the path the next spec round is written to
#   pair.sh review plan <slug>   the same, for the next plan round
#   pair.sh restore <slug> <rev>   put the approved block back as it was at <rev>
#   pair.sh impl checkout <slug>   cut the implementation tree, or name the cut one
#   pair.sh impl merge <slug>      merge the implementation tree back
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

die() {
	echo "$1" >&2
	exit 2
}

#: the directories of `.claude/hooks/blind-reads.json`, through the reader the
#: hooks use: the lane this script diffs is the lane `tests-lane.py` guards,
#: and the two it writes are the lanes `specs-lane.py` and `reviews-lane.py` hold
READER=$ROOT/.claude/hooks/shell_shapes.py
[ -f "$READER" ] || die "no $READER: scripts/ ships with .claude/hooks/, copy both"
TESTS=$(python3 "$READER" --config tests_dir)
SPECS=$(python3 "$READER" --config specs_lane)
REVIEWS=$(python3 "$READER" --config reviews_lane)
[ -n "$TESTS" ] && [ -n "$SPECS" ] && [ -n "$REVIEWS" ] || die "no $READER: cannot read blind-reads.json"
PYTEST=${PYTEST:-$ROOT/.venv/bin/pytest}

spec_path() { echo "$SPECS/$1.txt"; }
worktree_path() { echo ".claude/worktrees/$1-spec"; }
impl_path() { echo ".claude/worktrees/$1-impl"; }

#: everything below the divider is the reviewer's own output, verbatim
reviewer_section() {
	sed -n '/^--- reviewer ---$/,$p' "$1" | tail -n +2
}

#: the highest <N> on disk for a slug in one round series, or 0 for none. The
#: series is named by its infix: empty for the spec rounds
#: `<slug>.<N>.txt`, `plan.` for the plan rounds `<slug>.plan.<N>.txt`.
highest_round() {
	local slug=$1 infix=$2 best=0 n
	for f in "$REVIEWS"/"$slug"."$infix"[0-9]*.txt; do
		[ -e "$f" ] || continue
		n=${f##*"$slug"."$infix"}
		n=${n%.txt}
		case $n in
		'' | *[!0-9]*) continue ;;
		esac
		if [ "$n" -gt "$best" ]; then
			best=$n
		fi
	done
	echo "$best"
}

#: the newest spec round the reviewer has written for this slug, or nothing
newest_round() {
	local slug=$1 n
	n=$(highest_round "$slug" "")
	[ "$n" -gt 0 ] || return 0
	echo "$REVIEWS/$slug.$n.txt"
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
			git diff --name-only "$base" HEAD -- "$TESTS/"
			echo "diff:"
			git diff "$base" HEAD -- "$TESTS/"
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

#: the path a reviewer writes its round to, counted here and handed to it in
#: its brief. A reviewer cannot count the directory itself: reviews-lane.py
#: denies it every read of the reviewers' lane, so a reviewer left to pick its
#: own `<N>` is guessing, and a guess that lands on a number already taken
#: overwrites a round that exists in no git object and is gone.
cmd_review() {
	local slug=$1 infix= n
	if [ "$slug" = plan ]; then
		infix=plan.
		slug=$2
	fi
	[ -n "$slug" ] || die "usage: pair.sh review [plan] <slug>"
	#: the reviewer's Write is its own; the directory it writes into is not
	mkdir -p "$REVIEWS"
	n=$(highest_round "$slug" "$infix")
	echo "REVIEW $REVIEWS/$slug.$infix$((n + 1)).txt"
}

#: the hand-carved `git restore --source` step of docs/approved-specs.md, given
#: a name: the classifier carves out that one shell shape, and a subcommand
#: keeps the carve-out in one place rather than in every transcript
cmd_restore() {
	local slug=$1 rev=$2 spec
	[ -n "$rev" ] || die "usage: pair.sh restore <slug> <rev>"
	spec=$(spec_path "$slug")
	git restore --source "$rev" -- "$spec"
	echo "RESTORED $spec $rev"
}

#: the implementation tree, cut beside the spec tree and merged back from it.
#: a second checkout of a slug already cut is the same tree, not a fresh one:
#: re-cutting would discard the implementation in progress in it
cmd_impl_checkout() {
	local slug=$1 impl
	impl=$(impl_path "$slug")
	if [ ! -d "$impl" ]; then
		git worktree add "$impl" -b "impl/$slug" >/dev/null
	fi
	echo "IMPL $impl"
}

cmd_impl_merge() {
	local slug=$1 impl
	impl=$(impl_path "$slug")
	[ -d "$impl" ] || die "no implementation worktree at $impl"
	git merge --no-edit -q "impl/$slug"
	echo "MERGED $slug $(git rev-parse HEAD)"
}

cmd_impl() {
	local verb=$1 slug=$2
	[ -n "$slug" ] || die "usage: pair.sh impl checkout|merge <slug>"
	case $verb in
	checkout) cmd_impl_checkout "$slug" ;;
	merge) cmd_impl_merge "$slug" ;;
	*) die "usage: pair.sh impl checkout|merge <slug>" ;;
	esac
}

USAGE="usage: pair.sh open|red|merge <slug> | review [plan] <slug> | restore <slug> <rev> | impl checkout|merge <slug>"

main() {
	[ $# -ge 2 ] || die "$USAGE"
	case $1 in
	open) cmd_open "$2" ;;
	review) cmd_review "$2" "${3-}" ;;
	restore) cmd_restore "$2" "${3-}" ;;
	red) cmd_red "$2" ;;
	merge) cmd_merge "$2" ;;
	impl) cmd_impl "$2" "${3-}" ;;
	*) die "$USAGE" ;;
	esac
}

main "$@"
