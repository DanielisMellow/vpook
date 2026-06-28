set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

uv := "uv"
lint_cfg := "./pyproject.toml"
py_dirs := "src/ apps/"

# Display available recipes
help:
    @just --list

# -------- Installation --------

# Sync the environment (project + dev group)
install:
    {{ uv }} sync

# Sync the environment with Windows audio extras
install-windows:
    {{ uv }} sync --extra windows-audio

# -------- Run --------

# Run the overlay service (fake audio by default)
run *args:
    {{ uv }} run apps/overlay_service.py {{ args }}

# Run the overlay service targeting Discord audio
run-discord *args:
    {{ uv }} run apps/overlay_service.py --process --target-process discord {{ args }}

# Run the overlay service bound to all interfaces for LAN access (WASAPI)
run-lan *args:
    {{ uv }} run apps/overlay_service.py --host 0.0.0.0 --wasapi {{ args }}

# -------- Test --------

# Run the test suite
test *args:
    {{ uv }} run pytest {{ args }}

# -------- Linting (dev) --------

# Run ruff check (concise, non-failing)
lint:
    -{{ uv }} run ruff check --config {{ lint_cfg }} --output-format concise {{ py_dirs }}

# Run ruff check (full output, non-failing)
lint-verbose:
    -{{ uv }} run ruff check --config {{ lint_cfg }} {{ py_dirs }}

# -------- Formatting (dev) --------

# Apply ruff formatting to the repository
format:
    {{ uv }} run ruff format {{ py_dirs }} --config {{ lint_cfg }}

# Show formatting diff using ruff
format-diff:
    {{ uv }} run ruff format --diff {{ py_dirs }} --config {{ lint_cfg }}
