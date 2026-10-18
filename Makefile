.PHONY: check

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

check:
	git ls-files -z --cached --others --exclude-standard | xargs -0 uv run python -m gates.check_suppressions
