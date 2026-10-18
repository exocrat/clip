# Private offer-note and contact-share payloads

**Date:** 2026-10-18
**Origin:** PD-08 Step 1.

## Question
Which offer/contact fields may be readable by the server?

## Options considered
- Client-encrypted notes/contact-share payloads with structured offer amount/status metadata.
- Server-readable note/share payloads, exposing private conversation content to the backend.

## Selected choice
Encrypt offer notes and shared-contact payloads on clients. Keep offer amounts and statuses structured and server-readable for required offer filtering/sorting. Selected-own-contact retrieval remains separately authorized through Identity; encrypt the resulting share on the client before persisting the conversation payload. This does not claim that Identity's source contact records are hidden from its own authorized backend.

Mohit also approved keeping selected contact field names with their values inside the encrypted envelope. Do not store a plaintext `selected_fields` list in `contact_shares`; retain only its entry link and the minimum reviewed routing/type metadata. The Identity service still authorizes the requested own-contact fields before encryption.

## Rationale
The conversation stores private shared content as ciphertext while retaining the metadata required for offer management.

## Implications
PD-08 Step 2 specifies payload metadata and relationships for affected-owner review before dependent migrations; the approved [retention policy](private-data-retention.md) separately bounds content lifetime. DL-00/CN-01/CN-02 finalize protocol, exposure and authorization. Contact labels/values, notes and ciphertext remain excluded from logs/evidence. Moving labels into the payload does not conceal the server's minimum conversation-entry kind/routing metadata.

## Approver
Mohit (C), explicit approval in the execution session. Affected-owner/privacy review remains pending.

## Supersedes
None; resolves the encryption direction, not the remaining retention design.
