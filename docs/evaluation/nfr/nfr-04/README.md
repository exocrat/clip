# NFR-04 — Search usefulness retrieval

NFR-04 checks the PRD's Success@5 requirement: at least one reviewed relevant
listing must appear in the first five results for at least 80% of at least 20
included human-reviewed queries. Empty-relevance queries, failed requests and
timeouts stay in the denominator. NFR-02 is a separate search-speed check and
does not score relevance.

`manifest.template.json` binds one A or B retrieval to the accepted dataset,
schema, application, Hybrid contract, model and exact reviewed label bytes. Make
a run-specific copy only after those values and the target have been checked.
The `human_review` field points to the review record; it does not itself prove
that review happened.

Before retrieval, prepare a separate copy of `action-approval.template.json`.
The approval binds `run_id`, `configuration`, and the SHA-256 of the exact
manifest bytes; it also records the bounded authorization time window and
review reference. This file records a human decision but the program cannot
authenticate the person who made it. The command requires both `--execute` and
this separate record. It reads the session only after validating the manifest,
approval, final label binding and output location.

The adapter retrieves each included query from the planned HTTPS API and
records only query IDs, the first-page listing IDs, hit/failure categories,
and revision/data/label fingerprints. It follows no redirects or proxy, retains
no query text or response body, and writes a new report at the exact run-bound
evidence path. Its report always leaves NFR acceptance false. Before sending
queries it checks the hashed A/B target plan through the shared AWS/HTTPS
preflight, binds the plan's run, configuration, origin, application, data and
model revisions to the manifest, and verifies the supplied session's user ID
and account class. The manifest's separate expiring action approval is still
required. This read-only check does not prove that each B query was served by a
particular weighted backend or accept the NFR result. Preserve path-level
attribution as an open evidence question if separate Lambda/ECS Success@5
scores are required.
