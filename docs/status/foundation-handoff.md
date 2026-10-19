# Foundation handoff — PD-19

**Status:** The local foundation audit and handoff are committed as `5993851`
on `task/pd17-19-foundation-handoff`. PD-19 Steps 1–7 are user-verified;
Steps 8–9 are recorded for combined review. PRE-00 is not yet accepted: the
independent review and separately authorized merge to `main` remain required.

This handoff describes the shared foundation and its limits. It does not claim
marketplace features, domain contracts, final data readiness, or NFR results.

## Ready now

| Area | Available capability and limit |
|---|---|
| API | FastAPI health endpoint, typed configuration, request IDs, safe logging and shared core. `/health` reports process liveness only. There are no marketplace operations. |
| Web | Local technical shell with approved routes and display placeholders. It does not call domain APIs or implement marketplace flows. |
| Database | PostgreSQL 18.6, dbmate 2.36.0, four migrations through `20261018152702`, and a small catalogue seed. Local schema/lifecycle checks passed; domain services and contracts are absent. |
| Contracts and boundaries | Health API contract generation/stale checks and API/web/domain-boundary checks are available. Domain operation contracts and the four domain `public.py` declarations belong to DL-00. |
| Test/data tooling | Deterministic synthetic preview generators, versioned manifests/fingerprints, and human-review label format are available. The final schema-aware dataset and final fingerprint are DATA-READY work. |
| CI and commands | PR-only local CI gates, pinned Black/pre-commit, and the root Make front door are documented. No hosted CI result for this handoff revision is claimed. |
| Shared cloud foundation | Last read-only inventory (2026-10-19) showed RDS stopped, ECS desired/running/pending at zero, and no domain-specific resources. Existing resources are not authorization for a new operation. |

## Run the local foundation

Use the prerequisites and safety details in [local setup](../environment/README.md).
The last clean-checkout validation ran on Linux ARM64; it is not evidence about
another contributor's local environment.

1. From the repository root, run `make setup`, `make install-hooks`, and
   `make help`.
2. Supply a local-only `CLIP_LOCAL_POSTGRES_PASSWORD` as described in the setup
   guide. Run `make start-db`, `make seed`, and `make migration-status`. The
   verified result was four migrations applied, zero pending, with eight
   catalogue categories and four conditions.
3. In separate terminals, run `make start-api` and `make start-web`. Check the
   API with `curl --fail http://127.0.0.1:8000/health`; open
   `http://127.0.0.1:5173` for the web shell. Stop each foreground process with
   Ctrl+C.
4. Run `make test`, `make check-python-format`, `make contracts-check`, and
   `make check`. The last clean snapshot passed `make test` (395 Python, 63
   data, 16 web tests), Black, contract freshness, and all 10 `make check`
   gates.
5. Stop the retained local database with `make stop-db`. This preserves its
   volume. Do not reset it just to resolve an unknown error.

For schema-independent preview data, choose a fresh run name and use
`make data-generate RUN_NAME=preview-42 SEED=42 USERS=3 LISTINGS=2`, then
`make data-validate RUN_NAME=preview-42`. The deliberately unavailable
`make data-load` still exits nonzero until DL-00, accepted schemas, and SE-01's
loader exist.

## Verification and evidence limits

- The clean Linux ARM64 snapshot `0747be6` passed locked setup, database
  migration/seed/status, API and web loopback smokes, `make test`, Black,
  contract freshness, and all 10 `make check` gates. Services were stopped and
  the local database volume retained. The exact commands and counts are in the
  [work log](work-log.md).
- PD-09's persistent generator suite passed 63 tests; the schema-independent
  preview example fingerprint is recorded in the [data guide](../../data/README.md).
  This is not a final marketplace dataset fingerprint. Final loading,
  validation, and at least 20 reviewed query labels belong to SE-01/DATA-READY.
- The user confirmed on 2026-10-20 that the previously deferred Linux AMD64
  and macOS checks passed on other machine(s). Their exact machine
  architecture, commands, and raw outputs are not present in this checkout;
  this handoff records the user's confirmation and does not claim an
  independently reproducible run here.
- Hosted CI run [39280676449](https://github.com/exocrat/clip/actions/runs/39280676449)
  passed for the earlier accepted PD-12 head `61dd7674`. It does not cover this
  PD-17–19 handoff revision. No current PR CI status is claimed.
- The last shared-cloud inventory is a read-only snapshot from 2026-10-19;
  refresh it before a later cloud operation. Follow the exact approvals and
  cleanup limits in the [PD-16 closeout](../evaluation/foundation/pd-16/closeout-review.md).

## Not implemented here

- Identity, Listings, Search, Conversations, offers, notifications, image
  storage, domain APIs, and domain UI behavior.
- DL-00's four domain contracts, combined contract, generated `public.py`
  declarations, and reviewed contract-bound test doubles.
- Real identity/email/storage providers, final data loading, final dataset
  fingerprint, final query labels, and domain-specific cloud resources.
- Performance, recovery, restore, and final budget/NFR acceptance results.

These items remain assigned to the single [domain task list](../tasks/domain-task-list.md)
and its named later milestones. Shared decisions remain in
[DEC-07](../decisions/shared-foundation-dependency-staging.md), the
[PD-08 integration handoff](../decisions/database-integration-handoff.md), and
the linked records in the task list; domain behavior is not inferred from
those decisions.

## Next task

After PD-17–19 receive independent review and are merged to `main`, complete and
human-accept PRE-00. Then start **DL-00, Steps 1–13**, defined in the
[single domain task list](../tasks/domain-task-list.md).
Do not start domain feature implementation before PRE-00 and DL-00 pass their
gates.
