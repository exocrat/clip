# NEXT-06 load preflight checkpoint proposal

State: prepared; awaits human verification/approval. Prior16operation config scope
is complete. This checkpoint prepares an executable load plan, not a cloud load.
Account335523638354/ap-south-1 only, profilemohitmahapa1, no root/other-account use.

## Findings that must not be skipped

- Shared ECSrevision11 uses S3id01bucket/prefixid01; Hybrid/worker false. The li02
  bucket is private/encrypted/owner-enforced but its CORS only permits localhost.
  Do not silently switch a shared runtime, bucket or prefix. Review compatible
  existing storage before proposing the run-owned target and owner coordination.
- RDS18.6db.t4g.micro/20GiBgp3/singleAZ is stopped/private. PostgreSQL5432ingress
  only from appSGsg-0a3c8d683731470b4. No SQL/admin secret read is authorized.
- ASGclip-shared-test-ecs-hostdesired0 but returns healthyInService instance
  i-086045c48487471de. Actual EC2state/type and usable SSMroute remain unknown;
  do not assume no running compute or change scaling as an inspection repair.
- The installed SDK browser-login provider requires an optional dependency absent
  in local Python; CLIlogin already works. Prepare/test a repository-local supported
  credential solution without exposing credentials, adding access keys, changing
  account policy, editing global AWSconfig or assuming CLIlogin implies SDK works.
- Source default Dockerfile does not package the separate semantic interpreter/
  model. Actual deployed image contents are unverified. A model-enabled runtime
  needs its reviewed build/integration plan and owner approval; existing flags
  cannot simply be enabled and assumed to work. PR22peer approval remains separate.

## Proposed grouped local and read-only work

A. Implement/test the minimal SDKlogin compatibility preparation locally, including
failure/redaction/expiry behavior as applicable. Use the existing reviewed AWS
login/credential-process mechanisms; no plaintext credential file, chat output,
key creation or new live data load. Dependency downloads, if necessary, require
one bounded execution permission request, repository-local only. Preserve current
input/photo hashes and human judgments. Do not change shared runtime/IAM config.

B. One grouped read-only cloud operation, maximum18APIcalls with retries disabled,
fixed timeouts and sanitized output. Stop on account mismatch or scope exhaustion:

1. STSGetCallerIdentity(1).
2. EC2DescribeInstances for i-086045c48487471de(1): state/type/network/role metadata.
3. SSMDescribeInstanceInformation filtered to that instance(1): managed/online only,
   no commands, sessions, parameters or secrets.
4. IAMListRolePolicies and ListAttachedRolePolicies for clip-shared-test-api-task(2).
   GetRolePolicy for at most2returned inline policies; GetPolicy/GetPolicyVersion
   for at most1relevant attached policy(4maximum). Read only permission statements;
   report AccessDenied without broader roles, privilege changes or key operations.
5. Inspect current runtime bucketclip-test-listings-images-ap-south-1-id01 through
   HeadBucket,GetBucketLocation,GetBucketEncryption,GetPublicAccessBlock,
   GetBucketPolicyStatus,GetBucketCors,GetBucketVersioning,GetBucketOwnershipControls
   with expected owner335523638354(8). No object/key listing or data/policy changes.
6. EC2DescribeSecurityGroups for appSGsg-0a3c8d683731470b4(1) to establish the existing
   route boundary. No security-group/routing/instance/ASG changes.

Total maximum18. Do not inspect unrelated resources or expand denied scopes.
A single reviewed batch is intended to avoid one execution-approval prompt per
independent APIcall; it remains visible/auditable and does not bypass sandbox policy.

## Outputs and later gates

Return SDKcompatibility checks and sanitized actual route/role/current storage
facts. Then propose exact isolated database/roles, approved run-owned image prefix,
reviewed source/migrations/runtime build, current pricing/cost cap/window, stop
conditions, rollback/cleanup and owner coordination. The next cloud mutation,
secret/SQL access, resource start, session/remote command, deploy/upload/grant and
any commit/push/merge require separate exact approval. This checkpoint does none.
User must verify results before advancing; originalSteps3/4/5/6real integration,
accepted source/labels/freeze/DATA-READY remain incomplete. No additional relevance
judgment review is needed for the unchanged22accepted cases.
