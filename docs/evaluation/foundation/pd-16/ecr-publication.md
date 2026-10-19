# PD-16 Step 7 — ECR publication

**Observed:** 2026-10-19 16:41:18 UTC. Execution passed; user subsequently verified the result and continued to Step 8. No Step 8 action performed.

## Artifact and remote verification

- User explicitly authorized uploading the supplied validated image and requested `sudo docker` for registry login.
- STS verified IAM user `adityalaxmi1`, account `335523638354`; target Region `ap-south-1`.
- Exact repository: `335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api`; preflight found no images, immutable tags and AES256 repository encryption. Caller/repository/empty-state checks were repeated immediately before upload.
- Immutable tag: `68d6179db03dcf983278b290d22a939af625bba1`, the native AMD64 build source accepted through main `68d9da9`; API/build inputs match that main revision.
- Preserved OCI manifest digest: `sha256:8f07c52fdfd5a15c29eedae5b7189e6923e5ab0c622459568f70f6d7581a2bed`.
- Configuration digest: `sha256:bcf4588afe87e681415f51b7581f99f627df04c6b39882022339a06e8c58f38c`, `linux/amd64`, user `10001:10001`. Archive/config/blob hashes were checked before mutation; native runtime evidence remains [the original build validation](native-amd64-image-validation.md).
- ECR PutImage returned the expected digest. BatchGetImage read back the tagged manifest; its raw SHA-256 matched the archive digest exactly. DescribeImages confirmed 49,476,193 stored image bytes. Upload completed in 47.99 seconds; [safe result manifest](ecr-publication-result.json).

**Pinned URI for the future Step 8 plan:**

```text
335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:8f07c52fdfd5a15c29eedae5b7189e6923e5ab0c622459568f70f6d7581a2bed
```

## Procedure and privacy

Login used `aws ecr get-login-password --profile adityalaxmi1 --region ap-south-1` piped directly into `sudo docker --config <private-temporary-directory> login --username AWS --password-stdin <exact-registry>`. Token output was never logged; the temporary login directory was removed and its absence verified.

A session-local Python helper `/tmp/clip-pd16-upload.py` used the existing AWS CLI, preserving the supplied archive's OCI representation instead of rebuilding/recompressing with Docker 26. It checked the exact archive/hash/platform/source identities and repository, then called ECR BatchCheckLayerAvailability, InitiateLayerUpload, bounded UploadLayerPart, CompleteLayerUpload and PutImage with the exact tag/digest. All eight configuration/layer blobs completed with matching hashes. Calls used the explicit account/profile/Region, bounded timeouts, no mutation retries and protected temporary chunk/manifest files. BatchGetImage/DescribeImages provided the independent remote read-back above. The temporary helper is not a new maintained project command or future tool prerequisite; its safe outcome is preserved here. See [AWS layer upload](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_UploadLayerPart.html) and [manifest publication](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_PutImage.html).

No registry token, credential, source archive bytes or secret values are in the evidence. Local image/archive are retained outside Git. No image execution, service deployment, RDS operation, IAM change, Terraform plan/apply or image deletion occurred.

## Cost and outstanding gates

Budgets refreshed to USD 0.04 actual and USD 1.232 forecast. Billing GetCredits required account/start date and then denied this IAM principal (`IAM user access not activated`); no fresh credit balance is claimed and no root/permission change was attempted. The earlier recorded USD 159.54 credit snapshot remains historical. At the proposal's recorded USD 0.10/GB-month reference, this approximately 0.0495 GB image adds under USD 0.01/month; this is a reference estimate, not a new full-environment budget acceptance. Refresh eligible headroom for the service plan; Step 12 cost/alert checks remain open.

Step 7 upload/remote verification passed. User result verification is recorded; Step 8 preparation is active. Service plan/client-image selection, real integration/lifecycle, exact test window/contact, original upstream/platform/independent acceptance and PD-16/PRE-00 closeout remain open. This upload authorizes no later cloud action.
