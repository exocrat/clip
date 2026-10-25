# Search schema-shaped preview, version 1

SE-01 Step 2's isolated format adapts PD-09 scaffolds. It is not the final
reference corpus, a database load receipt, a label set, or DATA-READY evidence.

Bundles contain exactly `manifest`, `users`, and `listings`. A separate
`manifest.json` must equal the bundled manifest. Named-run IO reuses PD-09
size bounds, duplicate-key rejection and symlink/overwrite refusal.

The manifest contains `schema_version: search-preview-1`, `preview_only: true`,
`image_objects_verified: false`, explicit `seed`, requested/observed counts,
canonical UTC `logical_time` and `generated_at`, `source_fingerprint` and
`logical_data_fingerprint`. Source hashing includes relative names/bytes of all
migrations and `contracts/source/types.py`, `contracts/listings.md` and
`contracts/search.md`. Changed inputs require regeneration.

Logical SHA-256 hashes canonical JSON containing schema version, seed, requested
counts, logical time, source fingerprint, users and listings. Audit generation
time is excluded. Reconstructive validation rejects altered records, types,
counts, extra fields, versions and fingerprints. Stable IDs preserve UUIDv4
shape but are predictable test identifiers and never establish authorization.

Users are active regular synthetic accounts with no contacts or credentials.
Listings reference generated owners, reviewed catalogue codes, whole-rupee
integer paise, negotiability, optional pickup area, proof declaration and UTC
windows/timestamps. The loader resolves catalogue UUIDs from active codes.
Eight categories/four conditions, zero prices, price/recency ties and both
negotiability values are covered. Per ten rows: seven are available at the
logical time, one seller-unavailable, one future and one ended. These are
controlled fixtures, not relevance judgments or later wall-clock availability.

Each listing has one deterministic image UUID. The loader writes synthetic
upload/image metadata under `synthetic-search-preview/` with a one-byte PNG
declaration. No image object exists; this does not prove LI-02 content checks.
Upload creation/confirmation times are assigned from the load-time UTC clock,
not historical listing creation, so the 24-hour attachment window is valid.
These are load audit values and do not change the logical corpus fingerprint.
Replace/reconcile these references before final/cloud use. SQL publication
constraints are never disabled.

The local loader checks fixed server identity, empty tables and exact migration
versions, parameterizes inserts, forces deferred constraints and verifies counts
within one transaction. It has no delete/reset/upsert path. Actual PostgreSQL
execution and final schema/authorization/image/index checks remain pending;
mock refusal tests do not prove SQL correctness.
