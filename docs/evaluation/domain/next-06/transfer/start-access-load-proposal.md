# NEXT-06 start/access/load proposal

**State: prepared for verification. No cloud action in this proposal has run.**
This returns to original Step3real loading obligations; it does not declare the
local corpus or DATA-READY finally accepted. Human approval is requested only for
Phase A below, not the later setup/load/deployment phases.

## Targets, actor and source

| Binding | Exact proposed value |
|---|---|
| Account / region / actor |335523638354 / ap-south-1 / non-root profilemohitmahapa1 |
| RDS |clip-shared-test-postgres, PostgreSQL18.6, db.t4g.micro, existing20GiBgp3/private |
| Access host |i-086045c48487471de, existing stopped Linux t3.micro |
| Shared cluster/service |clip-shared-test / clip-test-api-ap-south-1-pd16; remain desired/running/pending0 |
| Shared ASG |clip-shared-test-ecs-host; no bounds/scaling/process changes approved |
| Private DB endpoint |clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com:5432 |
| Host IAM role |clip-shared-test-ecs-instance, exact EC2session for the named instance |
| One connection-secret reference |/clip/test/listings-database-url; value never returned in evidence |
| Probe source |scripts/evaluation/reference_db_inventory.py; exact SHA in db-inventory-command-review.json |
| Remote request |db-inventory-command.proposed.json; AWS-RunShellScript, named host only, timeout120s/concurrency1/maxerrors0 |
| Pinned cached image |shared API image digest97482cb4fb697eee230e66d134c165e557dac7d71a165e6034c88747f1738245 |

The source and secret-free SSMpayload are reviewable files, not placeholders for
arbitrary remote commands. No extra IAMgrant is needed merely to authenticate;
actual policy/SSM/secret/SQLauthorization is not assumed. Denial stops the phase.
The OS-level SSMcommand normally runs as root on this host; the AWScaller remains
non-root and the command is limited to the reviewed source. It uses no local
Session Manager plugin or global install.

## Phase A — requested exclusive start / read-only SQL inventory / stop window

1. Recheck non-root project identity, exact stopped DB/host/type/endpoint/SG,
   ECScluster/service/task counts0 and no other operator's active window. Require
   exclusive coordinated use of these shared resources. Inspect ASGmembership,
   suspended processes and lifecycle before any start. A stopped InService host
   in desired0group is not automatically safe to resume. Proceed with direct
   existing-host start only if metadata/owner coordination establishes no
   automatic replacement/termination/new-host action (e.g. Launch/Terminate already
   suspended). Otherwise STOP BEFORE ALL STARTS and propose the exact owner-reviewed
   ASGroute/template/type/cost change separately. Do not suspend, detach, scale,
   create replacement instances or modify group processes as a workaround.
2. Start only the named RDS once. Poll read-only status at30s intervals up to20min.
   If it fails or exceeds this bound, begin cleanup, not host start or repair.
3. Start only the named existing EC2host once; wait at most5min for running and5min
   for its SSMmanaged-node Online state. Recheck exact role/instance/group and
   absence of unexpected workloads/capacity changes. No ECSservice enable or app
   deployment. If SSM/tools/image are missing, stop; no dependency/agent install,
   image pull, fallback host, opened port or new role is approved.
4. Send exactly one approved AWS-RunShellScript command from the reviewed JSON.
   The standalone host probe checks its exact assumed-role identity, existing
   Docker and cached pinned image before reading the one named Parameter Store
   runtime secret. Host IAMrole performs its GetParameter with decryption; the
   operator never prints or saves its value. No master/admin/Conversations secret
   and no other Parameter Store path is authorized.
5. Pass that connection value through an in-memory stdin pipe to one uniquely
   named/labeled temporary container using --pull=never and the cached image.
   No credential in command arguments, DockerEnv, command JSON, files, SSMoutput or
   CloudWatchlogs. The fixed child imports no application startup; it binds
   host/port/verify-fullTLS/non-superuser/current-session/PostgreSQL18.6 and forces
   default_transaction_read_only=on plus SET TRANSACTION READ ONLY,5sstatement/
   1slock limits. Query only actual DB/login/version/read-only state, own/proposed
   loader/runtime role flags, public migration versions, domain schema names and
   whether candidate clip_next06_reference already exists. No user/listing/message
   bodies, data writes, grants, DDL or new DB. If restricted role cannot inspect
   metadata, report denial; do not fetch a stronger secret or change grants.
6. Collect only this new command's safe JSONmetadata and return code. Remote
   command bound120s, container60s and individual SQLstatements5s. Cleanup can
   remove only a container ID with the exact random run-label proof, never all
   containers or a name belonging to someone else. Missing cached image or
   unfamiliar output aborts rather than silently installing/running other code.
7. On success, error, interruption or deadline, stop only the exact host/DB that
   were stopped before and started/possibly-started by this approved window.
   Recheck no unexpected operator workloads/ownership drift before disruptive
   cleanup; if drift appears, preserve evidence/escalate instead of killing others.
   No termination, volume/snapshot deletion, DBreset, ASG/ECSscale, IAM/network/
   S3change. Both states must be verified stopped; no success inferred from an
   accepted asynchronous stop request. Do not leave resources running while
   waiting for the next human verification.
8. Retain sanitized start/end/identity/metadata/failure/cleanup/cost-estimate evidence.
   Phase A ends before any reference data upload, pipeline processing or public
   application change. Pause for verification and the next exact action approval.

### Bounds and stop budget

Proposed limit: **60minutes work,15minutes cleanup reserve, USD1incremental
operating budget**. Maximum160management/poll calls, retries disabled,30spolling,
5sconnect/10sread defaults. Stop new work at the work deadline; cancellation and
resource stop/verification remain allowed during cleanup. No benchmark/build/model
work is included. RDSstartup can take longer than expected and some transitional
states cannot stop immediately: record pending cleanup and escalate rather than
claiming a hard AWSbilling limit or issuing deletion/force actions. Do not silently
extend the window or keep resources online for future phases.

## Verified cost basis (USD, Mumbai)

Public AWSprice publications2026-10-29, retrieved during this preparation; exact
SKU/rate/source evidence is in [cloud-price-evidence.json](cloud-price-evidence.json).
No authenticated Pricing/CostExplorer/account API was called.

| Component | Current published rate / allowance |
|---|---|
| RDSPostgreSQL db.t4g.micro Single-AZ |0.021USD/hour |
| EC2Linux shared t3.micro |0.0112USD/hour |
| Base both running |0.0322USD/hour; conservative75min base0.04025USD |
| Worst full2vCPU surplus on both for75min |0.3125USDadditional, at EC2Linux0.05 and RDS0.075USD/vCPU-hour |
| Conservative compute allowance |0.35275USDfor75min, far above this idle metadata workload's normal compute |
| Requested window budget |1USDincremental, with traffic/request/log/rounding buffer; not a billing hard stop |

No credit/free-tier/tax discount is assumed. Existing20GiBRDSstorage at0.131USD/
GB-month is2.62USD/month and continues while stopped; retained EBS/backups/NAT/
other project baseline charges are not zero or included as new Phase Acost.
No volume/network allocation or retention change is approved. This phase does
not upload/read S3objects. Later1,000objects need about0.926decimalGB, roughly
0.0232USD/month conservative base storage plus0.0054USDfor1,000PUT+1,000GET before
transfer/extra requests/retention effects; those are **future**, separately approved.

AWSRDSstops are temporary and automatically restart after7stopped days. Record
that future review/deadline after cleanup; existing storage/backups continue.
This proposal creates no scheduler and promises no permanent zero compute bill.

Sources: [RDSprice table](https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/rds/USD/current/rds-postgresql-ondemand.json),
[EC2regional CSV](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/ap-south-1/index.csv),
[RDSstorage](https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/rds/USD/current/rds-storage.json),
[S3regional list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/ap-south-1/index.json),
[EC2credit pricing](https://aws.amazon.com/ec2/instance-types/t3/),
[RDSbilling/credits](https://aws.amazon.com/rds/postgresql/pricing/),
[RDSstop behavior](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_StopInstance.html).

## Later phases — not included in Phase Aapproval

B. Use actual inventory to review exact isolated DB/loader/runtime roles and
29migration compatibility. CandidateDBclip_next06_reference and roles
clip_next06_loader/clip_next06_runtime are proposals, not known existing grants.
No reset/adoption of an occupied target. Approve precise SQL/grants and source
revision/rollback separately; independent/affected-owner review remains required.

C. Prefer current id01storage with a new maintainer-reviewed run prefix such as
id01/next06-reference-42-v1, preserving existing keys. If li02is chosen instead,
resolve its runtime/CORS/permissions explicitly. Approve exact1,000object and
atomic schema-aware load with ledger/byte/ownership/current counts checks.
The189test SDK/adapter preparation and complete transfer archive remain available.
No current approval covers upload or database population.

D. Review the Linuxmodel/helper runtime packaging (not in standardAPIimage),
explicitly prepare/queue/process/activate pinned vectors, verify all1,000sources
and real normal create/edit/image/Identity paths. Never just enable Hybrid flags
without a working model/worker/current pipeline. Keep formal dependency gates.

E. Bind the unchanged22human-reviewed judgments to accepted source/contract/corpus,
finish actual cloud reproducibility/freeze/DATA-READY gates, then separately
approved final NFR/architecture runs. Retain the1December00UTCmeasurement cutoff.
Commit/push/merge and any cloud mutation remain their own approvals.
