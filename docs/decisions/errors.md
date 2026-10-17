# Shared safe FastAPI error responses

**Date:** 2026-10-17

**Origin:** Decision taken in PD-06 step 2.

## Question

Which shared shared safe fastapi error responses convention should domain consumers use?

## Options considered

- Use unmodified FastAPI detail responses.
- Use FastAPI exceptions/validation with a shared safe envelope.
- Adopt an RFC Problem Details envelope.

## Selected choice

Use shared handlers with error.code/message/optional details and request_id, and the canonical status/code table.

The authoritative details and examples are in [shared conventions section 3](../conventions/shared-conventions-and-cross-domain-contract-rules.md).

## Rationale

Default responses do not supply the required common stable codes/correlation shape; shared handlers meet the existing rules without another library.

## Implications

PD-06 steps 3–6 implement and verify the applicable shared boundary. PD-08/10/11 and later domain owners consume this canonical definition at their assigned checkpoints; real auth, persistence, providers, and domain integration remain their named tasks. Affected owners and an independent human peer review the shared handoff before main acceptance. This decision is not evidence of implemented behavior.

## Approver

Current Stream 1 contributor, by explicit approval in the execution session on 2026-10-17; no person's name inferred from the stream label.

## Supersedes

None.
