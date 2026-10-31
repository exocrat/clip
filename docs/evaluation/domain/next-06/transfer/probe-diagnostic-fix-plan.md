# Local diagnostic correction proposal — no cloud operations

The approved Phase Astarted and stopped the exact resources; the one probe failed
with only RuntimeError. Both stop statuses are verified. This next increment is
local source/test preparation, not a retry or cloud authorization.

1. Preserve the executed source/payload/receipt unchanged in phase-a-20261030.
2. Add fixed allowlisted stage/reason codes to the prepared host and SQLprobe:
   identity/CLIversion, cached image, name collision, named parameter operation,
   container start, connection/TLS/readonly/privilege/migration metadata, cleanup.
   No raw stdout/stderr, DSN, credential, private-record or parameter value output.
3. Preserve all exacttarget/role/readonly/no-pull/no-repair/ownership guards. Retain
   structured safe child failure type/SQLSTATE rather than discarding it when the
   child exitsnonzero. Validate fields/types and reject unexpected output.
4. Test every important refusal stage, error redaction and expiry/cleanup handling;
   rerun affected data/format/boundary/security checks. Correct the execution-summary
   failure label after verified cleanup; never change historical raw receipts.
5. Generate revised proposed payload and source hashes for human verification.
   No SSMcommand, secret retrieval, start/stop, dependency install, SQLconnection,
   grant, upload or commit/push occurs under this local-only increment. Any further
   cloud attempt requires approval of the revised exactpayload/window first.
