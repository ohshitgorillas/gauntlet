.PHONY: check check-tests

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

check:
	git ls-files -z --cached --others --exclude-standard | xargs -0 uv run python -m gates.check_suppressions
	git ls-files -z --cached --others --exclude-standard | xargs -0 uv run python -m gates.check_mypy
	git ls-files -z --cached --others --exclude-standard | xargs -0 uv run python -m gates.check_pyright
	git ls-files -z --cached --others --exclude-standard | xargs -0 uv run python -m gates.check_cast
	git ls-files -z --cached --others --exclude-standard | xargs -0 uv run python -m gates.check_pytest

TEST_PATHS = $(or $(FILES),tests)

check-tests:
	$(if $(filter-out tests/%,$(FILES)),$(error check-tests: FILES names a path outside tests/: $(filter-out tests/%,$(FILES))))
	git ls-files -z --cached --others --exclude-standard -- $(TEST_PATHS) | xargs -0 uv run python -m gates.check_suppressions
	git ls-files -z --cached --others --exclude-standard -- $(TEST_PATHS) | xargs -0 uv run python -m gates.check_mypy
	git ls-files -z --cached --others --exclude-standard -- $(TEST_PATHS) | xargs -0 uv run python -m gates.check_pyright
	git ls-files -z --cached --others --exclude-standard -- $(TEST_PATHS) | xargs -0 uv run python -m gates.check_cast
	git ls-files -z --cached --others --exclude-standard -- $(TEST_PATHS) | xargs -0 uv run python -m gates.check_pytest
