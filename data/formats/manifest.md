# Preview dataset manifest, version 1

**Origin:** PD-09 Step 3. This is a schema-independent preview format, not a
domain schema, database load receipt or DATA-READY evidence.

The UTF-8 JSON bundle has exactly two keys: `manifest` and `records`. Records
follow the [preview contract](../generators/README.md), ordered by user then
listing kind and one-based ordinal. No actual domain records are introduced.

| Manifest field | Meaning / required value |
|---|---|
| `manifest_version` | String `1`; changes to this envelope need an explicit format version. |
| `preview_only` | Boolean `true`; never production or readiness evidence. |
| `generator_version` | Generator algorithm version, currently string `1`. |
| `config_version` | Interpretation of seed/count configuration, currently string `1`. |
| `schema_version` | String `preview-1`; identifies this scaffold, not PD-08's migration head or a future final domain schema. |
| `seed` | Explicit signed 64-bit integer, never a boolean. |
| `requested_counts` | Exact `users` / `listings` integer counts, each 0–100,000. |
| `observed_counts` | Counts derived independently from the generated record kinds; must equal requests. |
| `generated_at` | Audit run time, aware UTC serialized with exactly six fractional digits and `Z`. |
| `logical_data_fingerprint` | `sha256:` plus 64 lowercase hexadecimal digits over the canonical logical payload below. |

The logical payload contains only `generator_version`, `config_version`,
`schema_version`, `seed`, `requested_counts` and `records`. It excludes
`generated_at` and other envelope/audit metadata. `observed_counts` are checked
separately and cannot be used to conceal missing records. Canonical serialization
uses sorted keys, no extra whitespace, UTF-8 with non-ASCII characters preserved,
finite JSON values only, and original array order. No implicit Unicode
normalization or float-to-money conversion occurs.

Same seed/count configuration and generator/schema versions must yield identical
logical records/fingerprint at different run times. Changed seed/counts/record
content/order or logical versions must change the fingerprint. A checksum is
not authentication, proof of safe production use, schema integrity, or a human
relevance judgment.

`data.generators.manifest.build_bundle` creates this in memory;
`validate_bundle` reconstructs the supported preview and rejects unknown/extra
fields, wrong versions/types/counts, noncanonical time, unsafe/altered records
and mismatched fingerprints without echoing supplied content. Step 4's
[safe local output commands](../README.md) now write/validate preview runs;
no database loader exists. Final
adapters and loaded-data validation remain [SE-01 prerequisites](../prerequisites.md).
