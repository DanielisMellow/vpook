set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

python := "python"
pip := python + " -m pip"
lint_cfg := "./pyproject.toml"
py_dirs := "src/ apps/"

# Display available recipes
help:
    @just --list

# -------- Installation --------

# Install vpook in editable mode in the active environment
install:
    {{ pip }} install --upgrade setuptools wheel
    {{ pip }} install -e . --no-build-isolation

# Install vpook with Windows audio extras in editable mode
install-windows:
    {{ pip }} install --upgrade setuptools wheel
    {{ pip }} install -e ".[windows-audio]" --no-build-isolation

# -------- Run --------

# Run the overlay service (fake audio by default)
run *args:
    {{ python }} apps/overlay_service.py {{ args }}

# Run the overlay service targeting Discord audio
run-discord *args:
    {{ python }} apps/overlay_service.py --process --target-process discord {{ args }}

# Run the overlay service bound to all interfaces for LAN access (WASAPI)
run-lan *args:
    {{ python }} apps/overlay_service.py --host 0.0.0.0 --wasapi {{ args }}

# -------- Linting (dev) --------

# Run ruff check (concise, non-failing)
lint:
    -ruff check --config {{ lint_cfg }} --output-format concise {{ py_dirs }}

# Run ruff check (full output, non-failing)
lint-verbose:
    -ruff check --config {{ lint_cfg }} {{ py_dirs }}

# -------- Formatting (dev) --------

# Apply ruff formatting to the repository
format:
    ruff format {{ py_dirs }} --config {{ lint_cfg }}

# Show formatting diff using ruff
format-diff:
    ruff format --diff {{ py_dirs }} --config {{ lint_cfg }}
