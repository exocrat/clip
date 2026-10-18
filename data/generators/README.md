# Preview generator (PD-09 Step 2)

Run from the repository root with the pinned project environment:

```bash
uv run --locked python -m data.generators --seed 42 --users 3 --listings 2
```

This emits JSON Lines to stdout only: user placeholders first, then listing
placeholders, in one-based ordinal order. Seed is a signed 64-bit integer; each
explicit count is 0–100,000. No file/database/provider target is accepted by this
stdout command. Separate file-output commands are documented in
[the data guide](../README.md). Step 3's
[manifest format](../formats/manifest.md) and `manifest.build_bundle` /
`manifest.validate_bundle` now support versioned bundles in memory only.

`PreviewRecord` is an immutable scaffold, not an Identity/Listings schema.
Predictable SHA-256-derived UUIDs keep the approved lowercase UUIDv4 shape and
are exclusively test identifiers. Existing IDs do not change when counts grow.
Names are conspicuously synthetic; example addresses use `example.invalid`.
No contacts/credentials/private payloads or live object references are imported.

`stable_id` derives versioned IDs without global RNG state; `validate_record`
checks the closed synthetic shape; `generate_preview` accepts optional pure
validation hooks and propagates their failures; `main` validates explicit CLI
inputs and streams stable-key JSON. No domain adapter or loading is implemented.
See [later prerequisites](../prerequisites.md) for SE-01/DATA-READY obligations.
