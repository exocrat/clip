# NEXT-06 Step 3 — exact ephemeral-loader and S3/SQL load package

Prepared and locally tested, not approved or executed in AWS. Both resources were
last verified stopped at2026-10-30 19:20:00UTC. Existing isolated database29is
prepared; both dataset roles are NOLOGIN and business tables are empty as of setup.

## Review and owner gates

Exact target: `cloud-load-target.proposed.json`. Exact controller and52source/
dependency hashes: `cloud-load-command-review.json` and
`cloud-load-controller.proposed.py.txt`. **Storage maintainer approval is not yet
confirmed.** User replies “Proceed” during local preparation do not attest that
another maintainer reviewed the prefix. Record explicit confirmation plus exact
cloud-window approval before executing; controller refuses before any AWS call
while `storage_maintainer_approval` is false. Independent/affected-source review
requirements remain; pending review is not replaced by passing local tests.

Proposed bucket/prefix: `clip-test-listings-images-ap-south-1-id01`,
`id01/next06-reference-42-v1/`; exactly1,000known upload UUID keys, no other keys.
Operator Mohit/profilemohitmahapa1, account335523638354, ap-south-1; no AWSroot.
Shared service/runtime32 is not reconfigured. This is the isolated29schema load.

## Ordered live actions requested for a later approval

1. Verify every hash and original corpus/photo/source binding and measurement
   cutoff (require a full remaining hour); refuse ambient PG/AWS/CLIP overrides and local5432 already bound.
   Recheck exact stopped existing RDS/EC2/type/endpoint/SG, idle ECS and safe ASG
   membership with Launch/Terminate already suspended. Exclusive shared-resource
   window remains required. No starts until all these pass.
2. Start only existing RDS then host, as in verified prior windows; require SSM
   Online and repeat guards. Open one remote-host SSMforwarding session to fixed
   RDS5432, **local loopback5432** (changed from admin-inventory15432). Verify
   listener address and owned plugin process group; refuse wildcard listeners.
   No remote shell, port exposure, network/IAM/ASG change or new instance.
3. Read only existing `/clip/test/database-master-password` once into memory.
   Open fixed admin session to `clip_next06_reference`,18.6, verified hostname
   TLS through loopback and reviewed regional CA. Verify admin/owner/privacy,
   actual exact29tracker versions and planned500000paise threshold binding.
   Threshold is the proposed isolated profile setting, not a claim that the
   existing shared service's deployed configuration was measured or changed.
4. Inspect the exact bucket owner/region, all public blocks, nonpublic policy,
   SSE-S3/AES256 and BucketOwnerEnforced. List only exact new prefix, max1key;
   require empty. No overwrite/adoption. Any denial/drift/nonempty prefix stops
   without IAM/CORS/bucket policy repair. These are operator storage permissions;
   actual runtime-role signed delivery remains a later real-integration gate.
5. Create a fresh0600fsynced private object/SQL ledger under this window's0700
   receipt directory. Check fresh inactive loader/runtime flags, no membership
   or loader schema/relation ownership, exact admin-owned database and empty
   users/listings/uploads/images/pipeline registry. Generate one ephemeral random
   loader password only in memory. Set transaction-local SCRAM encryption, then
   activate only `clip_next06_loader` with bounded VALIDUNTIL at most45min (actual
   controller caps to remaining40minload window). Never activate runtime.
   No new Parameter Store secret or persistent credential is created; this
   supersedes the preliminary static-credential publication suggestion. Static
   project secrets still use the selected manager; this one-window credential is
   discarded and cleared at closeout. Password is not in env/args/files/evidence.
6. Open an actual restricted loader connection through the owned tunnel using
   the in-memory DSN and explicit loopback hostaddr/CA. The existing guarded
   cloud adapter verifies real account/user/session/transport/TLS/18.6,29exact
   migrations, empty target/pipelines, owner/count/catalogue/settings bindings.
   Preflight is repeated after object transfer, before locked insertion.
7. Upload exactly1,000approved real-image objects (925,881,224logical bytes,
   45source photos). For each, fsync attempted-key/hash **before** PUT; exact
   bucket owner, IfNoneMatch*, checksum, MIME and exact prepared key. Bound S3
   wrapper forbids unplanned keys, duplicate PUT/GET, deletes/config changes,
   owner drift and GET before an acknowledged new PUT. GET each new object once
   with a10MiB+1bound; verify full size/MIME/SHA256 **and actual AES256 encryption**
   before recording verified bytes. No Transfer Acceleration or multipart upload.
8. With all1,000objects verified, recheck schema/empty target. Use actual shared
   `reference_rows.insert_rows`: lock four data tables, insert5,000synthetic users
   and1,000listings/confirmed uploads/images, preserve triggers/FKs, force deferred
   checks, compare all projections/owner joins,800discoverable records,1,000text
   vectors and actual GINindex. Commit SQL once; fsync committed-result evidence.
   No passwords/sessions/OTP/provider jobs or contacts for synthetic users.
9. On success, failure, uncertainty or deadline, close the loader SQL connection,
   verify same loader OID/privilege/membership and fixed admin target, execute
   NOLOGIN/PASSWORDNULL/VALIDUNTILepoch, and verify disabled. Close admin SQL,
   owned tunnel and SSMsession, then stop/verify exact host/RDS. Preserve drift
   or pending cleanup explicitly; no blind retry, forced session kill or delete.
   TTL bounds new authentication only; closing existing sessions is mandatory.
   Record all result/timing/call/cleanup evidence; leave runtime inactive.

## Bounds, costs and recovery

60minwork plus15mincleanup; load phase at most40min and remaining global window.
At most160management operations plus2,008S3logical calls: seven storage preflight
calls, one adapter HeadBucket,1,000PUT and1,000GET. SDK retries disabled,5sconnect/
30sobject-read bounds; SQL60sstatement/5slock. One added STScheck is counted through
the controller budget. Before provider dispatch, exact key/call/deadline guard
stops further operations. No automatic resume or broader recovery permissions.

Proposed **USD1incremental operating envelope**, not a hard AWSbilling cap.
Prior verified Mumbai rates remain in `cloud-price-evidence.json`: conservative
75minbasecompute0.04025USD, two-by-two-vCPU worst surplus+base0.35275USD;1,000PUT+
1,000GETbase0.0054USD;~0.926decimalGBstorage~0.0232USD/month. Reserve0.25USD within
the envelope for transfer/small private-session traffic/extra request effects;
this is an operating allowance, not a newly verified regional unit tariff or
actual bill. Direct image transfers run from this Mac to S3, not through the
private host/NAT. Do not assume unused free transfer allowance. Existing RDS/EBS/
NAT/backups/baseline, retention, tax and unrelated account spend are excluded.
No new NAT/network allocation, database resize or compute type change.
Public [S3 pricing](https://aws.amazon.com/s3/pricing/) distinguishes requests,
storage and transfer; [VPC pricing](https://aws.amazon.com/vpc/pricing/) describes
NAT/session-route effects. Current account-level billing is not inspected here.

SQL is atomic; S3 is not. On failed PUT/GET/timeout, keep fsynced exact attempted
keys and stop; do not insert confirmed SQL metadata. On SQLfailure rollback rows,
retain created objects for separate reviewed inspection/cleanup. A lost SQLcommit
acknowledgment needs actual database inspection, not a second load. Never delete
prefixes, retry uncertain PUTs, overwrite objects, reset tables, delete parameters
or drop databases/roles automatically. Every later invocation refuses a nonempty
prefix/target or previously-used expiry/role state; recovery requires exact
approval. Cleanup failures remain pending even if compute stops. RDS auto-restarts
after seven stopped days; storage retention continues. No scheduler is created.

## Local proof and limits

`reference_load_access.py` implements explicit ephemeral access, safe closeout,
fixed storage inspection, listener ownership and operation/key/deadline bounds.
`reference_cloud.py` additionally checks downloaded object's AES256 metadata;
`test_reference_cloud.py` covers wrong-encryption refusal as well as prior byte/
uncertain-write guards. `test_reference_load_access.py` covers permission/source/
expiry/uncertain activation, OIDcleanup, owner/prefix/privacy/storage bounds and
outcome classification. `reference_setup_local.py --local-rehearsal --credentials`
adds real SCRAM wrong/correct-password tests and proves NOLOGIN/NULLverifier/
old-password rejection after real restricted5,000user/1,000listing insertion.

Final native receipt and negative storage-gate receipt are retained beside this
plan. The gate execution was intentionally local:0AWS calls/no starts because
maintainer approval was unconfirmed. No cloud credentials read, objects uploaded
or real SQLbusiness rows inserted in preparation. Local native media keys are
references only; botocore/scripted storage checks are not deployed S3 acceptance.
Original real auth/media/model/vector/source-label/freeze gates remain pending;
no DATA-READY or final NEXT-06 completion. Existing22judgments and December1cutoff
are unchanged. Cloud execution and publication retain separate approvals.

[Local preparation results](cloud-load-preparation-result.json), [real native credential receipt](cloud-load-native-credential-result.json), [zero-AWS storage-gate refusal](cloud-load-storage-gate-result.json).261data tests,28access controls, Black339files, boundaries0 and pinned Gitleaks0findings.
