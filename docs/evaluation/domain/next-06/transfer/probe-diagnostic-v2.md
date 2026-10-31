# Revised Phase A diagnostic payload — local preparation

Version 2 is prepared for verification, not approved for remote execution.
The original failure remains unexplained. No AWS operations were performed in
this correction; the last real receipt verifies both resources stopped.

The host reports fixed stages: tools, CLI version, host identity, cached image,
container-name collision, named parameter retrieval, SQL child and owned cleanup.
SQL failures retain a fixed stage/reason, exception class and optional SQLSTATE.
Reports reject unknown fields/types; raw errors and connection strings are never
forwarded. A missing tool/image/permission is reported, never repaired automatically.
The host source supports Python 3.9 syntax; the pinned container uses Python 3.14.

`phase-a-controller.v2.py.txt` is the proposed controller, not an executed receipt.
It validates the exact v2 report and derives the final window state from verified
stop flags, distinguishing failed/stopped from cleanup still pending. Its ordered
cloud call expressions are identical to the executed controller. Historical source,
command and receipts in `phase-a-20261030/` remain unchanged.

Review `db-inventory-command-review.json` for exact source, request and controller
hashes; `db-inventory-command.proposed.json` embeds the current source. A retry
requires separate approval under `start-access-load-proposal.md`: account
335523638354, profile mohitmahapa1, ap-south-1, exact existing host/RDS, one command,
one named runtime parameter, read-only metadata, mandatory stopped closeout;
1 USD incremental estimate envelope, 60 minutes work plus 15 minutes cleanup,
160 service calls maximum. No upload, grants, migrations, deployment, IAM/network
changes, image pulls or repair are included. Later phases remain separately gated.

Local checks: 26 focused diagnostic tests; 215 full data tests with warnings as
errors; Black and Python boundaries; source/request hash binding; controller syntax
and AST cloud-call comparison; secret scan. These are preparation checks, not real
SQL/cloud acceptance. Detailed results: [local check evidence](probe-diagnostic-v2-result.json). NEXT-06 and DATA-READY remain incomplete.
