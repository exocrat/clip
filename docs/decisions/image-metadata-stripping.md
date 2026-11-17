# Server-side image metadata stripping on confirm

**Date:** 2026-11-17

**Origin:** Red-team issue #73 (listing photos disclose the uploader's GPS location and device make/model/serial to any signed-in viewer, including temporary accounts).

## Question
Should listing images retain the uploader's embedded metadata (EXIF/GPS/XMP/ICC/thumbnail), or should the service remove it before the image is delivered to other users — and if so, how, given the deliberate choice to avoid full pixel re-encoding on the upload path?

## Options considered
- **User responsibility** — treat embedded metadata as the uploader's concern; serve the original bytes unchanged.
- **Client-side stripping** — re-encode in the browser before upload. Not authoritative: the API upload path still accepts original bytes.
- **Server-side full re-encode on confirm** — decode pixels and re-encode, dropping all metadata.
- **Server-side marker/chunk strip on confirm** (selected) — remove metadata containers without decoding pixels, with a re-encode fallback.

## Selected choice
Strip uploader metadata **server-side, during `confirm` (in `S3ListingsImageStorage.inspect_object`)**, before the image can ever be delivered to another user, and store the cleaned copy in place of the original.

- **JPEG / PNG:** a byte-level strip with **no pixel decode** — drop all `APPn`/`COM` segments and any data after the JPEG `EOI`; drop PNG `tEXt`/`zTXt`/`iTXt`/`eXIf`/`tIME` chunks and any data after `IEND`. This removes GPS/EXIF/XMP/ICC/thumbnail **and** appended-polyglot payloads.
- **WEBP / fallback:** if the lightweight strip does not re-validate (or for WEBP), fall back to a bounded full re-encode that copies pixels into a fresh image with empty info.
- Every stripped/re-encoded result is **re-validated** before it is stored, so a strip bug can never store a corrupt image; anything that still fails validation is rejected.
- Also **reject animated/multi-frame images** (animated WEBP, APNG) — a listing photo is a single still frame.
- `inspect_object` still returns the **uploaded** size so the caller's upload-integrity check (`stored size == declared size`) holds; only the stored bytes shrink. A clean image is not rewritten (no extra `PUT`).

## Rationale
The exposure is real and reachable (the red team confirmed byte-for-byte delivery, including GPS and device serial, to a temporary account), so "user responsibility" was not defensible as an evidence-based `invalid`; it is at most a severity/scope question for the mentor. Server-side stripping is the industry norm precisely because users do not know their photos carry location/device data and the harm (silent home-location disclosure) is high.

The original design deliberately avoided re-encoding to bound CPU and keep a no-full-decode posture (relevant to decompression-bomb safety and, after #61, to minimising reliance on the image decoder). **A benchmark on the actual `c7i-flex.large` host (Xeon Platinum 8488C) settled the approach:** marker/chunk strip **4.6 ms** vs full re-encode **143.7 ms** — the strip closes the same class (metadata + appended payload) at ~1/31 the cost, with **no pixel decode**, so it neither reopens the decoder attack surface #61 reduced nor re-compresses the image. The cost lands on `confirm` (publish), not on upload (direct S3 PUT, unchanged) or on viewing (served from S3, unchanged); the one added S3 `PUT` of the cleaned object is inherent to any server-side rewrite.

## Implications
- `apps/api/app/domains/listings/s3_storage.py`: `_validate_image` now rejects multi-frame images; new `_strip_jpeg`/`_strip_png`/`_reencode_image`/`_sanitize_image`; `inspect_object` sanitizes and rewrites the object. Tests in `test_s3_storage.py` cover JPEG EXIF+payload strip, PNG text strip, clean-image no-op, and animated rejection; verified end-to-end that GPS/model/EXIF/appended data are removed while pixels are preserved.
- Owner: Listings (Suraj).
- **Not changed:** delivery still relies on the stored (now validated) `Content-Type`; forcing `ResponseContentType`/disposition on the signed GET would need `media_type` threaded through the delivery store layer and is a marginal follow-up, since the served type is already correct and `attachment` would break inline display.
- Existing already-stored images are not retroactively stripped; only images confirmed after this change are cleaned. A backfill (re-inspect existing objects) is possible later if required.

## Approver
Aditya (Cumulonimbus dev decision for #73), 2026-11-17, after reviewing the measured latency on the real hardware. Live retest and mentor adjudication of severity remain open.

## Supersedes
None. Relates to [image-upload-staging](./image-upload-staging.md) and the Pillow upgrade in issue #61.
