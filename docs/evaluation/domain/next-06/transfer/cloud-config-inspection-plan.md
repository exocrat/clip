# NEXT-06 next checkpoint: read-only configuration inspection

State: prepared, awaiting explicit human approval. This scope follows successful
non-root identity/resource inspection; it authorizes no mutation by itself.

Profile mohitmahapa1, account335523638354 only, ap-south-1. Repeat STS first;
stop on mismatch/root/unavailable credentials. Use no automatic retries, bounded
connect/read timeouts, maximum16CLI/APIoperations and only returned related IDs.
No secret values, general IAM discovery or unrelated account resources.

Approved-scope proposal:

1. STS GetCallerIdentity (1).
2. ECS DescribeTaskDefinition for shared service revision11 (1): image/task-role/
   execution-role IDs and an allowlist of nonsecret CLIP environment fields only:
   environment, auth/storage provider, image bucket/region/prefix, sensitivity
   threshold, Hybrid/worker flags/helper paths, browser origin. Never output
   arbitrary environment values. Secret parameter references may be recorded as
   names/ARNs only, with no SSM/SecretsManager read.
3. RDS DescribeDBInstances for clip-shared-test-postgres (1): endpoint/port,
   subnet/security-group/VPC IDs and resource settings, no SQL/secret access.
4. EC2 DescribeSecurityGroups and DescribeSubnets only for those returned related
   IDs (2). Record private connection-route metadata; do not change networking.
5. ECS DescribeClusters for clip-shared-test, DescribeCapacityProviders for only
   its returned provider, AutoScaling DescribeAutoScalingGroups for that returned
   ASG (3): existing capacity IDs/counts and instance type if present. Stop if
   ambiguous/multiple unrelated resources; no starts/scaling/launch-template reads.
6. For clip-test-listings-images-ap-south-1-li02 only: S3HeadBucket,
   GetBucketLocation, GetBucketEncryption, GetPublicAccessBlock,
   GetBucketPolicyStatus, GetBucketCors, GetBucketVersioning,
   GetBucketOwnershipControls (8). Use expected bucket owner335523638354.
   No list-objects/get-object/body/policy text reads, signing, uploads or changes.

Record denied/absent settings accurately without attempting repairs, alternate
roles or broader enumeration. Produce a sanitized configuration report and then
prepare a separate actual-target/cost/window/rollback load proposal. Nothing here
approves resource starts, deployment, uploads, SQL, role/grant changes, secret reads,
spend, commits, push or merge. Suraj's independent review/final acceptance remains
separate; the existing image/payload bundle and22judgments remain unchanged.
