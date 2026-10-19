.PHONY: check check-tests

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

check:
	git ls-files -z --cached --others --exclude-standard | xargs -0 uv run python -m gates.check_suppressions
	git ls-files -z --cached --others --exclude-standard | xargs -0 uv run python -m gates.check_mypy
	git ls-files -z --cached --others --exclude-standard | xargs -0 uv run python -m gates.check_pyright
	git ls-files -z --cached --others --exclude-standard | xargs -0 uv run python -m gates.check_cast

check-tests:
	git ls-files -z --cached --others --exclude-standard -- tests | xargs -0 uv run python -m gates.check_suppressions
	git ls-files -z --cached --others --exclude-standard -- tests | xargs -0 uv run python -m gates.check_mypy
	git ls-files -z --cached --others --exclude-standard -- tests | xargs -0 uv run python -m gates.check_pyright
	git ls-files -z --cached --others --exclude-standard -- tests | xargs -0 uv run python -m gates.check_cast
