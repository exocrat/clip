# NEXT-06 staged Step 4 — exact RDS vector-production window

Prepared/native-tested; cloud writes not approved or executed. The human verified
the staged route after successful S3/RDS bulk load. Original Step3real app/auth/
normal creation/signed media and final Linuxruntime checks remain pending.

## Exact source, targets and requested operations

`vector-command-review.json` binds77source/dependency files, original corpus/
29migrations, model/tokenizer/interpreter and prior actual projection receipt.
`vector-target.proposed.json` is the exact target. Its bucket/prefix fields only
bind existing image SQLreferences; **no S3client or operation exists in controller**.
`vector-controller.proposed.py.txt` is the exact proposed executable. Approval
flag remains false and a real local negative trial proved0AWS calls/no starts.

Actor: non-root profilemohitmahapa1, IAMuser in335523638354/ap-south-1. Reuse existing
private RDSclip-shared-test-postgres/18.6 and hosti-086045c48487471de. Database is
only clip_next06_reference; shared32database/service, loader and runtime stay
unchanged/inactive. No ECSdeployment, image build, global install or provider send.

1. Verify every bound hash and current corpus/photo/source/measurement window
   (full remaining hour before December1). Require no ambient PG/AWS/CLIPoverrides,
   unused loopback5432, exact stopped host/RDS/type/endpoint/SG, idle ECS and safe
   ASG with Launch/Terminate already suspended. Stop on drift before starts.
2. Start existing RDS then host, require SSMOnline/repeat guards. Open only owned
   remote-host forwarding to fixed RDS5432, local127.0.0.1:5432. Verify owned
   process group and loopback listener, never wildcard exposure. Read only
   existing `/clip/test/database-master-password` once into memory; verify exact
   setup admin/target/owner/18.6/TLS/privacy. No host/master credential publication.
3. Verify actual29tracker versions and complete5,000user/1,000listing/image row
   projections against prior real load digest; no source edits or seed reload.
   New producer role `clip_next06_embeddings` must be absent; loader/runtime
   disabled. Require1000live sources and no existing pipeline/generation/chunk
   rows. Refuse PUBLICCONNECT on any other application DB; never repair it.
4. Create only the new producer as NOLOGIN/NOSUPERUSER/NOCREATEDB/NOCREATEROLE/
   NOINHERIT/NOREPLICATION/NOBYPASSRLS/connectionlimit2; fixed privacy defaults.
   New role/grants are one transaction. Exact privileges on this database only:

   | Scope | Grants | Purpose |
   |---|---|---|
   | clip_next06_reference | CONNECT | Dedicated producer only |
   | public/listings schemas | USAGE | Tracker, supported operator/worker/query functions |
   | public.schema_migrations; listings.sale_listings/categories/conditions/images | SELECT | Binding/source reads and actual query compiler/Hybrid summary SQL |
   | listings.sale_listings.id column only | UPDATE(id) | Required FORUPDATE row locks; immutable-id trigger blocks changing id |
   | listings.embedding_pipelines | SELECT/INSERT/UPDATE | Register/build/serve; no registry DELETE |
   | listings.embedding_generations | SELECT/INSERT/UPDATE/DELETE | Supported reconcile, lease, publish and fenced invalidation |
   | listings.embedding_chunks | SELECT/INSERT | Actual ready-part publication/completeness checks; no UPDATE/DELETE |

   No Identity/Conversations/schema CREATE/ownership/membership/S3rights. No listing
   description/price mutation privilege. In a separate guarded transaction activate
   this producer only with one in-memory random SCRAMpassword, expiry at most45min
   (controller caps to remaining40minphase); no persistent credential/parameter.
5. Use existing repo `.tools/semantic/venv/bin/python`3.13.12 and pinned real
   all-MiniLM-L6-v2 model/tokenizer. Helper gets minimal offline environment, not
   AWS/DBcredentials; one serial child/worker. Parent reads actual RDSlisting text
   through the normal EmbeddingStore/Worker, never precomputed/copied vectors.
   Verify actual producer current+session role,18.6 and private hostname-verified
   TLS before SQLpipeline mutation. Prepare/queue exactly1000through supported
   EmbeddingBootstrap, run exactly1000normal jobs, require published each and idle
   afterward. Any stale/deferred/failure/lease problem stops; no retry/reset loop.
6. Guardedly activate only full current coverage:1000live/ready, no missing/stale/
   pending/leased/failed/invalid parts/conflicting serving pipeline; exact pinned
   ID4b43fc307151933bf5b0fa80ff4e10f8cb4266194905cd2b15a3d01b2386d9ca.
   Report actual parts; native recipe has1000titles+1000descriptions,384dimensions,
   2006model windows including six queries. Real constraints validate vector shape,
   finiteness/current source and complete ordinals; no manual ready flags.
7. Run six operator-only cases:cycle/cycel/vehicle/wheeled vehicle/books/office
   chair. Use actual PostgreSQLkeyword/typo compiler and production Hybrid SQL,
   real pinned query vectors and fixed500000paise profile setting. Verify keyword
   inclusion, unique paged results and no hidden availability leakage. This is
   authorized operator SQLdiagnosis, not a manufactured CallerContext/HTTProute,
   real user-session test or new human relevance labels. Keep22judgments intact.
8. Recompare every original logical source/image projection after publication.
   Close producer SQL and owned helper, disable new role/clear password/verify
   NOLOGINusing same OID/membership/privilege proof; close admin/tunnel/session,
   stop/verify exact resources. No runtime/loader activation, corpus change,
   object write or shared-app Hybridflag toggle. Retain actual stage/coverage/
   failure/timing/cleanup/source receipts. Do not wait for verification online.

## Bounds, costs and recovery

60minwork+15mincleanup, at most160management calls; producer phase at most40min
and remaining global window.1000serial jobs, hard2400model-window budget; existing
startup30s/inference5s/request20s/worker20s, SQLstatement5s/lock1s. One helper reports
peak memory below512MiB; this is not a complete process/NFRmemory claim. No new
model download, image build/registry publish, GPU, cloud model service or Docker
installation. Local CPU inference uses the existing Mac; RDSstores actual vectors.

USD1incremental operating envelope, not billing hard cap; prior verified Mumbai
base0.0322USD/hour, conservative75minbase0.04025USD, worst2+2vCPU surplus+base
0.35275USD. No S3calls; modest private SQL/model input/output network/DBcredit
buffer within envelope. Existing RDS/EBS/NAT/backups/retained~0.926GBimage storage,
account usage and tax remain excluded. Vector rows use existing20GiBallocation;
no resize or new network resource. Retain data after stopped closeout and review
stopped RDS before possible seven-day auto-restart; no scheduler created.

Creation/grants commit NOLOGIN before activation; an uncertain create leaves
reviewable inactive artifacts, no adoption or retry. An uncertain activation still
requires same-OIDdisable/password clearing. Failed/incomplete worker publication
retains real building/generation/lease/failure state; do not auto-delete/reset,
requeue failures, demote another pipeline, switch models or mark complete. If
coverage succeeds but a diagnostic fails, actual serving state may already exist:
retain that fact and exact stage for reviewed recovery, never pretend activation
rolled back. Cleanup uncertainty stays pending even if compute stops. Never drop
roles/databases or alter shared ACLs automatically.

## Prepared code and native evidence

- `reference_vector_access.py`: exact fresh-role/grant/ephemeral-access and OID
  cleanup procedure. No AWS or connection discovery.
- `reference_vector_pipeline.py`: bounded actual helper/operator/worker, actual
  producer target checks, full coverage activation and production SQLdiagnostics.
- `reference_vector_local.py`: native SCRAM/model/pipeline and negative-role checks.
- `reference_setup_local.py --local-rehearsal --credentials --vectors`: new optional
  native path on fresh Unix-only PG18.6 using existing tools/artifacts; stops its
  own helper/cluster and proves original row projection unchanged.
- `test_reference_vector_access.py`:18expiry/target/occupied-state/uncertainty/
  ownership/budget/coverage/cleanup controls, no fake production vectors.

[Final native receipt](vector-native-result.json):1000generations/2000parts,
100%current serving coverage,2006model windows, column-only row-lock privilege,
nine denied mutation/escalation/id-change tests; password revoked and cluster
stopped. Native helper peak265699328bytes (about253.4MiB). Six query
cases passed; e.g.wheeled vehicle17keyword/82Hybrid, office chair19/74. These are
engineering checks, not Success@5 or substituted human review. Native-only metadata
and real model proof do not establish cloud permission/latency/deployed runtime.

[Approval-gate receipt](vector-approval-gate-result.json) confirms exact prepared
controller refuses missing cloud approval before any AWS call. Full279data tests,
Black343files and boundary checks pass. Pins/current source binding verified;
secret scan/diff results are in the preparation receipt.

This is a human-verified staged Step4data checkpoint while originalStep3normal
real app/auth/create/edit/signed-media/new-vector tests remain pending. Linux/ECS
helper/worker/query packaging/deployment, final source/label bindings, owned real
rebuild/freeze/independent acceptance remain required. No DATA-READY, complete
NEXT-06 or final NFR claim. Request approval only for this exact window.
