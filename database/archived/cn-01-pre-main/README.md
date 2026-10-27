# Superseded branch-only Conversations migrations

These four files retain the exact SQL bytes committed on Rahul's Conversations
branch before integration with `origin/main` at `3d6c270`. Their recorded runs
used disposable databases only; no shared application is recorded or authorized.
They are archival evidence, not executable migrations and not rollback scripts.

Main's 17 published migrations are authoritative and remain unchanged. In
particular, its retirement migration already supplies the owner pending fields,
operation ledger and `participant_writes_disabled_at` marker. Replaying the older
Conversations retirement migration would duplicate that schema.

The executable chain instead adds `20261026090000` through `20261026090300` after
main: local retirement hardening, ciphertext transport, public key directory and
protocol-control storage. Content recovery remains disabled.

Before using any persistent database, inspect its exact migration tracker and
data through the approved owner APIs. If it contains an archived version, stop:
it needs a separately reviewed upgrade/reconciliation plan. Never delete tracker
rows, rewrite published history, or assume an existing target is empty. Neither
this archive nor successful disposable checks authorizes shared migration apply.
