# Local and CI PostgreSQL version

**Date:** 2026-10-18

**Origin:** PD-08 Step 4.

## Question
Which supported PostgreSQL version and local container layout should PD-08 use?

## Options considered
- PostgreSQL 17: supported, but a shorter remaining support window.
- PostgreSQL 18: supported through November 2030; current stable major with native UUID and full-text capabilities needed by the schema.
- PostgreSQL 19 release candidate: not a stable foundation target.

## Selected choice
PostgreSQL **18.6**, official image `postgres:18.6-bookworm`, for local development
and the CI database. The selected minor and OS family are explicit; no immutable
image digest or successful image execution is claimed. The publisher lists both
amd64 and arm64v8. Use PostgreSQL 18's `/var/lib/postgresql` volume mount and
versioned `/var/lib/postgresql/18/docker` PGDATA.

## Rationale
The [PostgreSQL version policy](https://www.postgresql.org/support/versioning/)
lists 18.6 as the current supported minor. Its
[release notes](https://www.postgresql.org/docs/release/18.6/) date it to
2026-08-13. The [official image tag registry](https://github.com/docker-library/official-images/blob/master/library/postgres)
lists the selected tag/platforms; the [image documentation](https://github.com/docker-library/docs/blob/master/postgres/README.md)
specifies the PostgreSQL 18 mount layout. Consult these sources again before a
later version change; mutable upstream listings are not runtime evidence.

## Implications
Root Compose contains one local-only database service, loopback publication,
required environment password, SCRAM host authentication, UTC time, UTF-8
initialization, readiness healthcheck and named project-scoped volume. It does
not apply migrations or configure the API. Step 5 owns safe lifecycle wrappers;
Step 6 owns actual migration/connectivity/repeatability verification. Docker and
Compose are presently unavailable on Mohit's Mac. PD-12/integration must use
18.6 in CI or record a compatibility reason for any difference; Stream 3 does
not edit CI or other streams' directories. Cloud versions/roles/TLS and backup
operations remain separately owned future tasks.

### Native verification route — Mohit, 2026-10-18

Mohit directed checking on macOS itself now and leaving other checks for later.
Use native PostgreSQL **18.6** with pinned dbmate **2.36.0** in temporary `/tmp`
locations; keep Compose as the eventual local/CI lifecycle target. The native
test creates a private disposable Unix-socket cluster with TCP disabled and
stops it afterward. This does not authorize a VM or global installation.
Native UTF-8/C locale and a minimal build without ICU/readline/zlib differ from
the Debian/C.UTF-8 image. Native apply/head/smoke/down-up/inventory repeatability
evidence is valid only for that route. The user later confirmed the previously
pending PD-08 platform, owner and CI acceptance gates complete on 2026-10-19;
see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence).
The retained Linux/ARM64 evidence remains route-specific. See
[historical database verification details](../evaluation/README.md).

## Approver
Implementation selection within Mohit's verified PD-08 Step 4 scope. The user
later confirmed the previously pending result, affected-owner and CI acceptance
gates complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence).

## Supersedes
None.
