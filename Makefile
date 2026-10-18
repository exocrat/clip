# Default to inspection; formatting requires an explicit format-python target.
.DEFAULT_GOAL := check-python-format

.PHONY: format-python check-python-format check

# Use the project lock and root Black configuration in the local uv environment.
format-python:
	uv run --locked black .

# Report formatting drift with a failing exit status, leaving source unchanged.
check-python-format:
	uv run --locked black --check --diff .

# Run the same ordered quality gates as CI; setup and local Docker are required.
check:
	uv run --locked python scripts/check.py
