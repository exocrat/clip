# Public-key and ciphertext storage boundary

**Date:** 2026-10-18
**Origin:** PD-08 Step 1.

## Question
What cryptographic information may persist on the server?

## Options considered
- Persist public keys, key versions and ciphertext metadata; retain private keys exclusively on clients.
- Persist server-recoverable private keys, contradicting the approved E2EE boundary.

## Selected choice
Store public keys, key versions and ciphertext metadata needed by the reviewed protocol. Private keys remain exclusively on clients. This direction preserves the one-active-browser-device MVP and does not provide server key recovery.

During Step 2, Mohit approved versioned public-key bundles (at most one active bundle per user) and protocol/version-tagged encrypted envelopes with required sender/recipient public-key-version references. Bundles are 1–16 KiB and envelopes 1–64 KiB encoded bytes. The envelope contains ciphertext and protocol-required public metadata; its precise cryptographic serialization is still owned by the reviewed CN-01 protocol. Sender/recipient key ownership and protocol compatibility must match the actual entry/thread; preserve referenced historical public versions while payloads remain.

## Rationale
The database can associate ciphertext with reviewed public-key versions without becoming a decryption-key store.

## Implications
The approved database representation still requires Conversations/Identity/security review for compatibility with the established protocol before dependent migration acceptance. CN-01 retains authenticated key distribution, protocol/library selection, serialization/nonce/authentication/wrapping details, key-change/tampering behavior and security tests. Encoded-byte ceilings do not select algorithm key sizes. No primitive, algorithm, recoverability or rotation policy is invented by this storage decision.

## Approver
Mohit (C), explicit Step 1 boundary approval followed by Step 2 representation/size-limit approval. The user later confirmed the PD-08 affected-owner/security gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). Implementation-specific security checks remain with the domain tasks.

## Supersedes
None; refines the existing PRD E2EE storage boundary.
