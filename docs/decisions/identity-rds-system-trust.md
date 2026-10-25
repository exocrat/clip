# Shared API RDS system trust

**Date:** 2026-10-25
**Origin:** ID-01 Step12, authorized local image certificate correction.

## Question
How does the shared API image supply the roots required by the reviewed Identity
verify-full/system DB connection without changing its URI contract?

## Options considered
- Download the current regional bundle during each image build.
- Vendor reviewed regional roots and use the image's standard OS trust store.
- Change Identity's URI contract to a separate application-specific CA path.

## Selected choice
Vendor the official public ap-south-1 bundle as three individually pinned,
self-signed root `.crt` files with source/fingerprint/validity metadata under
Identity. The ordinary API Dockerfile installs them using update-ca-certificates,
preserving distribution roots, and explicitly sets
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt. The optional Hybrid image inherits
this only when rebuilt from the corrected ordinary API image.

## Rationale
The cached image lacked the regional roots. A stronger native image test also
found bundled libpq's compiled CA default was /host/tmp/libpq.build/cert.pem,
while Python's default used Debian's store. Installing roots alone did not make
the configured database client trust that store. The explicit image-level path
selects the installed system roots for both clients. PostgreSQL documents this
SSL_CERT_FILE behavior with sslrootcert=system; verify-full remains mandatory.
Vendoring makes certificate changes reviewable and avoids a mutable build download.

## Implications
The shared image trust store affects all its TLS clients that use system roots;
B/C/shared-owner review is required. Only regional root CAs are added; source
certificates contain no private keys or intermediates. Existing provider/session,
DB-role/URI and hostname-verification policy remains. Certificate changes require
reviewed source/manifest updates and image rebuild; no runtime download or rotation
job is introduced. Native local proof is separate from AMD64/Hybrid and deployed
RDS acceptance. No cloud permission, live call or deployment is authorized here.

## Approver
Aditya(A) authorized implementation of the certificate fix; routine packaging
choices follow the authorized local judgment. Human result verification and
independent/affected-owner image approval remain pending.

## Supersedes
None; implements the existing verify-full/system requirement.

## Sources
- [AWS root-only regional trust guidance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html)
- [PostgreSQL system trust and SSL_CERT_FILE semantics](https://www.postgresql.org/docs/18/libpq-connect.html#LIBPQ-CONNECT-SSLROOTCERT)
- [Pinned public certificates](../../apps/api/app/domains/identity/certificates/README.md)
