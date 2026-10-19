# PD-16 Step 8 — first service plan failed validation

**Observed:** 2026-10-19. Non-applying plan authorized by the user; exit 1, no resource apply.

Preflight verified IAM `adityalaxmi1` in account `335523638354`, the exact initialized S3 shared/test backend/default workspace, published API digest, original private/encrypted/protected RDS in `stopped`, zero ECS services/running/pending tasks and zero ASG instances/desired capacity. Terraform 1.15.9 was used. Existing SSM/RDS state contained no ordinary parameter/password values.

A new probe credential was generated and retained only in the protected local artifact directory. The master credential was not manually retrieved: current instructions say to omit it for service phase. Provider validation then rejected the omitted master value:

- Existing master SecureString requires one of `insecure_value,value,value_wo` and requires the `value_wo`/`value_wo_version` pair.
- Existing RDS requires the `password_wo`/`password_wo_version` pair.

The existing version fields remain 1. State metadata records master parameter version 1 and write-only version 1. Omitting its unchanged value is therefore an invalid service configuration for this provider; changing version counters or using ordinary secret arguments is not an approved workaround.

Terraform saved a partial artifact even though planning failed. Private rendering confirms **`errored=true`**. It is labelled **FAILED / NOT FOR APPLY**, not usable or approved. Generated probe plaintext was absent from decompressed saved-plan entries, rendered JSON and captured output. S3 HeadObject returned 404 for the lock after Terraform exited; no manual lock deletion or backend change occurred. [Safe failure manifest](service-plan-failure-result.json).

Artifacts remain at `/tmp/clip-pd16-service-plan-dei22564` (0700; private files 0600), including failed plan, state snapshot, output/rendering and retained probe credential. These must not be committed. No RDS restart, service deployment, password rotation or resource apply ran.

A material task-definition correction is required before retry: supply the existing master through ephemeral input even for service plans, preserve versions, re-supply both values at apply, and document the same handling for later lifecycle plans. The proposed recovery uses a non-root in-memory Parameter Store read and a fresh non-applying plan with the same seven-resource scope. No master read or retry is authorized merely by this evidence record; await the user's decision on the reviewed correction proposal.
