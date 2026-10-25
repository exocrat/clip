# Deterministic synthetic-data tooling

## SE-01 isolated schema-shaped corpus

`data.generators.search_preview` reuses PD-09 IDs, hashing and private named-run
IO for the reviewed user/listing fields. Existing PD-09 commands and their
load refusal are unchanged. See [the Search preview format](formats/search-preview.md).

With locked dependencies installed, run from the repository root:

```bash
uv run --locked python -m data.generators.search_preview generate --name search-preview-42 --seed 42 --users 5000 --listings 1000 --logical-time 2026-10-24T09:00:00.000000Z
uv run --locked python -m data.generators.search_preview validate --name search-preview-42
```

On Mohit's checkout, `.venv/bin/python` can replace `uv run --locked python`
after repository-local locked setup. Logical time is explicit fixture input,
not the machine clock; reuse it for repeat generation. Choose a fresh run name;
there is no overwrite. Datasets are ignored; manifests can be retained.

The implemented PostgreSQL loader has not been exercised against PostgreSQL in
this checkout. It requires an independently prepared empty local database named
`clip_test_search_preview`, with role `clip_search_preview` owning the fixture
tables and every current repository migration/catalogue applied. Local database
setup/ordered migration execution remain pending until a PostgreSQL runtime is
available. Then supply its real canonical Unix-socket directory:

```bash
CLIP_ENVIRONMENT=test uv run --locked python -m data.generators.search_loader --name search-preview-42 --socket-dir /absolute/local/socket/directory --isolated-preview
```

The socket path must not traverse symlinks (use `/private/tmp` on macOS rather
than `/tmp`). Unset ambient `CLIP_DATABASE_URL`, `DATABASE_URL` and `PG*`
overrides; never supply application credentials to this fixture route. The
loader verifies fixed database/role/Unix transport, migration versions and active
catalogue, locks/checks empty tables, and inserts in one transaction. Deferred
constraints/counts must pass before commit. It creates no credentials or auth
bypass and performs no storage/provider calls.

There is **no reset command**: nonempty targets are refused. Destructive cleanup
requires separate exact-target review and approval. Synthetic image metadata
has no backing objects; it cannot validate LI-02 or support cloud measurement.
Real loading/FKs/indexes/images and final DATA-READY remain pending at SE-01
steps 2/4/9. Local fixture tests do not establish PostgreSQL ranking or NFRs.

PD-09 supplies **preview-only** records/manifests, not final domain data or a
database loader. [Prerequisites](prerequisites.md) assign real adapters/loading,
population/integrity/index validation and human relevance judgments to
SE-01/DATA-READY after actual ID-READY/LI-CORE schemas and DL-00 contracts.
PD-08 deferred acceptance remains recorded under Mohit's preparation exception.

## Setup and commands

From the repository root, use the existing locked Python 3.14 environment:

```bash
uv sync --locked
uv run --locked python -m data.generators --seed 42 --users 3 --listings 2
uv run --locked python -m data.generators.files generate --name preview-42 --seed 42 --users 3 --listings 2
uv run --locked python -m data.generators.files validate --name preview-42
```

The first generator streams controlled JSON Lines to stdout without file IO.
The file generator creates only `data/runs/preview-42/dataset.json` and
`manifest.json`; both commands print the validated logical fingerprint and exit
0 on success. Explicit signed-64-bit seed and counts each 0–100,000 are required.
Run names are 1–64 lowercase ASCII letters/digits, `_` or `-`, beginning with a
letter/digit. No arbitrary path, database URL or provider target is accepted.

The [preview API](generators/README.md) supplies stable UUIDv4-shaped fixture IDs,
synthetic labels, reserved `example.invalid` addresses and pure validation hooks.
The [manifest format](formats/manifest.md) identifies generator/config/preview
schema versions, seed/counts, UTC audit time and canonical logical fingerprint.
Changing only generation time leaves records/fingerprint unchanged. No real
contact, credential, private key, OTP, private message or live object is imported.

## Local safety, retention and reproducibility

- Existing run directories are refused, even if empty or incomplete. There is
  **no overwrite or reset command**. Choose a fresh name; inspect any old output
  and its retained manifest before separately deciding whether to remove it.
- Root/run/file symlinks and nonregular JSON files are rejected. Generation
  reserves a new owner-private directory and exclusively creates each file.
  Interrupted IO can leave partial output; missing/altered/mismatched files fail
  validation. Keep one writer and do not modify paths concurrently with a run.
- Validation is local only, rejects duplicate JSON keys and files over 128 MiB,
  and verifies records/config/counts/fingerprint plus matching manifest. Invalid
  arguments, unsafe targets, IO failures and integrity failures exit 2 with safe
  diagnostics. Fix the cause and use a fresh name; never guess a remote target.
- `.gitignore` excludes only `data/runs/*/dataset.json`, the regenerable preview
  payload. Source, formats, inputs and per-run manifests remain eligible for Git.
  Retain reviewed manifests for meaningful reproducibility/evaluation runs with
  the accepted code revision; do not indiscriminately commit disposable runs.
- Regenerate under a fresh run name with the retained manifest's seed/counts and
  the **same generator/config/schema versions and code revision**, then validate
  and compare fingerprints. Audit time differs intentionally. A retained preview
  manifest does not recreate a final domain dataset through this scaffold.
- Final evaluation source inputs, reviewed labels/manifests and evidence needed
  to reproduce results must be retained through SE-01's reviewed policy. No
  blanket JSON/data ignore rule hides them. No cleanup/cloud action is implied.

## Loading and readiness gates

```bash
uv run --locked python -m data.generators.files load
```

This deliberately exits **2**, naming required DL-00 contracts, ID-READY/LI-CORE
schemas and SE-01 adapter/loader validation. It performs no DB connection/write
and never claims data loaded. SE-01 later implements/registers actual safe
generate/load/reset/validate commands against the accepted domain schema.

DATA-READY requires actual >=5,000 users/>=1,000 listings with integrity,
availability and index checks, reproducible logical fingerprints, and >=20
human-reviewed representative queries/relevant listing IDs. NFR-04's final
Success@5 evaluation remains SE-01 work. PD-09 Step 5 supplies the
[query-label format and human-review procedure](formats/query-labels.md) and
[empty draft template](evaluation/query-labels.template.json). SE-01 stores the
reviewed final label set at `data/evaluation/query-labels.json`, derived from
that template; the template itself contains no final judgments or listing IDs.
Versioned NFR workload profiles belong under `data/evaluation/workloads/`.
Evaluator/load/recovery/restore source tools belong under
`scripts/evaluation/`, with exact commands registered by their owning tasks.

## Verification and review handoff

Run the persistent local suite and repository Python format check:

```bash
uv run --locked python -m pytest data/tests -q -W error
make check-python-format
```

Use `python -m pytest` so the repository root is importable without changing the
shared pytest configuration. The combined Python check is:

```bash
uv run --locked python -m pytest apps/api/tests tests data/tests -q -W error
```

Tests use only synthetic inputs and private temporary directories. They check
cross-process repeatability, IDs/RNG, count bounds/hooks, UTC/fingerprint and
tamper handling, path/symlink/overwrite/incomplete-output safety, CLI diagnostics,
missing loader prerequisites, draft-label safety and Git retention. Warnings
fail the run. A failed check needs its original cause fixed within ownership;
never bypass validation or reinterpret missing domain inputs as loaded data.

Step 6 local evidence: **63 PD-09 tests passed; 361 combined Python tests passed;
pinned Black check passed across 42 files**. These counts describe the current
checkpoint, not a permanent expected test count. PD-12/PD-13 must include the
explicit data-test invocation when integrating CI/common commands; root default
pytest discovery currently targets only `apps/api/tests` and `tests`.

Mohit verified all six local steps and the local closeout audit. This does not
accept PD-08, final domain adapters/population/labels, DATA-READY or any NFR.
Unfinished PD-08 work now belongs to pre-domain integration under the
[handoff decision](../docs/decisions/database-integration-handoff.md). PD-09 still
requires independent peer review and the accepted upstream/main handoff under the recorded preparation
exception. No task commit/push/merge is authorized by running these checks.
