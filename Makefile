# Makefile for the Stream repository
LINT_CFG := ./pyproject.toml
PY_DIRS  := src/ apps/

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  help              - Display this help message"
	@echo "  lint              - Run ruff check (concise, non-failing)"
	@echo "  lint-verbose      - Run ruff check (full output, non-failing)"
	@echo "  format            - Apply ruff formatting to the repository"
	@echo "  format-diff       - Show formatting diff using ruff"

# -------- Linting (dev) --------
.PHONY: lint
lint:
	-@ruff check --config $(LINT_CFG) --output-format concise $(PY_DIRS)

.PHONY: lint-verbose
lint-verbose:
	-@ruff check --config $(LINT_CFG) $(PY_DIRS)

# -------- Formatting (dev) ---------
.PHONY: format
format:
	@ruff format $(PY_DIRS) --config $(LINT_CFG)

.PHONY: format-diff
format-diff:
	@ruff format --diff $(PY_DIRS) --config $(LINT_CFG)

# -------- Fail on Error (CI/CD) --------
