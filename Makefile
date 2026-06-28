# Makefile for the Stream repository
UV       ?= uv
LINT_CFG := ./pyproject.toml
PY_DIRS  := src/ apps/

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  help              - Display this help message"
	@echo "  install           - Sync the environment (project + dev group)"
	@echo "  install-windows   - Sync the environment with Windows audio extras"
	@echo "  run               - Run the overlay service (fake audio by default)"
	@echo "  run-discord       - Run the overlay service targeting Discord audio"
	@echo "  run-lan           - Run the overlay service bound to all interfaces for LAN access (WASAPI)"
	@echo "  test              - Run the test suite"
	@echo "  lint              - Run ruff check (concise, non-failing)"
	@echo "  lint-verbose      - Run ruff check (full output, non-failing)"
	@echo "  format            - Apply ruff formatting to the repository"
	@echo "  format-diff       - Show formatting diff using ruff"

# -------- Installation --------
.PHONY: install
install:
	@$(UV) sync

.PHONY: install-windows
install-windows:
	@$(UV) sync --extra windows-audio

# -------- Run --------
.PHONY: run
run:
	@$(UV) run apps/overlay_service.py $(ARGS)

.PHONY: run-discord
run-discord:
	@$(UV) run apps/overlay_service.py --process --target-process discord $(ARGS)

.PHONY: run-lan
run-lan:
	@$(UV) run apps/overlay_service.py --host 0.0.0.0 --wasapi $(ARGS)

# -------- Test --------
.PHONY: test
test:
	@$(UV) run pytest

# -------- Linting (dev) --------
.PHONY: lint
lint:
	-@$(UV) run ruff check --config $(LINT_CFG) --output-format concise $(PY_DIRS)

.PHONY: lint-verbose
lint-verbose:
	-@$(UV) run ruff check --config $(LINT_CFG) $(PY_DIRS)

# -------- Formatting (dev) ---------
.PHONY: format
format:
	@$(UV) run ruff format $(PY_DIRS) --config $(LINT_CFG)

.PHONY: format-diff
format-diff:
	@$(UV) run ruff format --diff $(PY_DIRS) --config $(LINT_CFG)

# -------- Fail on Error (CI/CD) --------
