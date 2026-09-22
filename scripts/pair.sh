#!/usr/bin/env bash
#
# The pair driver. Its name is a literal in `${CLAUDE_PLUGIN_ROOT}/docs/agents.md`, in the eight agent
# definitions and in `lanes.py`, so the name stays here and the work lives beside it in `scripts/pair/`.
#
# `exec`, so the driver is this process: an exit status, a signal and a
# terminal all reach it unchanged, and stdout stays the contract stream
# `${CLAUDE_PLUGIN_ROOT}/docs/agents.md` documents.

#: `shell_shapes.config()` reads the declaration from `$CLAUDE_PROJECT_DIR`, and
#: the variable is set for a hook but not for a `Bash` child. So the checkout is
#: resolved once here and exported for everything below. `--git-common-dir` is
#: the main checkout's `.git` from inside a worktree as well, and the checkout
#: is its parent: the declaration is the project's, and a worktree carries no
#: copy of it. A variable already set is the caller's and stands.
if [ -z "${CLAUDE_PROJECT_DIR:-}" ]; then
	if common_dir=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) &&
		[ -n "$common_dir" ]; then
		CLAUDE_PROJECT_DIR=$(dirname "$common_dir")
		export CLAUDE_PROJECT_DIR
	fi
fi

exec python3 "$(dirname "$0")/pair/cli.py" "$@"
