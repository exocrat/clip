# Default to inspection; formatting requires an explicit format target.
.DEFAULT_GOAL := check-python-format

.PHONY: help setup install-hooks start-api start-web preview-web start-db stop-db \
	migrate migration-status seed data-generate data-validate data-load \
	test test-python test-data test-web format format-python format-check \
	check-python-format contracts-generate contracts-check contracts-double-check check \
	terraform-format terraform-format-check terraform-validate terraform-check

help:
	@printf '%s\n' \
	  'setup / install-hooks: locked dependencies / one-time local Git hook' \
	  'start-db / stop-db: validated local PostgreSQL; stop retains data' \
	  'start-api / start-web / preview-web: foreground; Ctrl+C stops that server' \
	  'migrate / migration-status / seed: local migrations/catalogue, never reset' \
	  'data-generate: RUN_NAME=... SEED=... USERS=... LISTINGS=... (all required)' \
	  'data-validate: RUN_NAME=...; data-load: unavailable until domain readiness' \
	  'test / test-python / test-data / test-web: registered test/check commands' \
	  'format / format-check / contracts-generate / contracts-check / contracts-double-check / check' \
	  'terraform-format / terraform-format-check / terraform-validate / terraform-check'

# Setup does not start services or install a Git hook as a hidden side effect.
setup:
	uv sync --locked
	npm ci

install-hooks:
	uv run --locked pre-commit install

# Each application owns its foreground terminal; no daemon or broad process kill.
start-api:
	uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000

start-web:
	npm run dev

# Requires npm run build (also included by make check/test-web) beforehand.
preview-web:
	npm run preview

start-db:
	bash database/local-db.sh start

stop-db:
	bash database/local-db.sh stop

migrate:
	bash database/local-db.sh migrate

migration-status:
	bash database/local-db.sh status

# The catalogue is a versioned migration: reusing migrate is repeat-safe and
# never creates synthetic users/listings or rewrites an applied migration.
seed: migrate
	@printf '%s\n' 'Foundation seed: existing eight categories/four conditions applied through migrations.'

# Export input values rather than inserting them into shell source. All inputs
# remain mandatory and are validated by the existing PD-09 command.
data-generate data-validate: export CLIP_PREVIEW_NAME = $(RUN_NAME)
data-generate: export CLIP_PREVIEW_SEED = $(SEED)
data-generate: export CLIP_PREVIEW_USERS = $(USERS)
data-generate: export CLIP_PREVIEW_LISTINGS = $(LISTINGS)
data-generate:
	uv run --locked python -m data.generators.files generate --name "$$CLIP_PREVIEW_NAME" --seed "$$CLIP_PREVIEW_SEED" --users "$$CLIP_PREVIEW_USERS" --listings "$$CLIP_PREVIEW_LISTINGS"

data-validate:
	uv run --locked python -m data.generators.files validate --name "$$CLIP_PREVIEW_NAME"

# Preserve the existing fail-closed prerequisite diagnostic; no loader invented.
data-load:
	uv run --locked python -m data.generators.files load

test: test-python test-data test-web

test-python:
	uv run --locked python scripts/check.py python-tests

test-data:
	uv run --locked python scripts/check.py data-tests

test-web:
	uv run --locked python scripts/check.py web

format: format-python
format-python:
	uv run --locked black .

format-check: check-python-format
check-python-format:
	uv run --locked black --check --diff .

contracts-generate:
	uv run --locked python scripts/generate_contracts.py generate

contracts-check:
	uv run --locked python scripts/generate_contracts.py check

contracts-double-check:
	uv run --locked mypy --no-incremental apps/api/tests/domains/search/doubles/listings.py

# This exact mapping is checked by the shared CI parity guard.
check:
	uv run --locked python scripts/check.py

# Explicit local Terraform actions; deliberately excluded from the general check.
terraform-format:
	bash scripts/terraform-static-check.sh format

terraform-format-check:
	bash scripts/terraform-static-check.sh check-format

terraform-validate:
	bash scripts/terraform-static-check.sh validate

terraform-check:
	bash scripts/terraform-static-check.sh check
