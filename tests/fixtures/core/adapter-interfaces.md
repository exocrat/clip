# Shared test-adapter interfaces

**Origin:** PD-10 step 2. **Status:** Boundary approved by the Stream 1 contributor on 2026-10-17; implemented in PD-10 step 2.

## Scope

Use one generic scripted test provider for controlled outcomes. It supplies no Microsoft/token/OTP validation, email transport, S3 operations, or domain business behavior. Owning domain tasks adapt this test primitive only after reviewing their real provider contracts. Nothing here becomes a public API or automatically installs a FastAPI authentication override.

## Approved interface

```python
ProviderKind = Literal["identity", "email", "storage"]
FailureReason = Literal["unavailable", "timeout", "denied", "invalid"]

@dataclass(frozen=True)
class Return(Generic[T]):
    value: T  # excluded from repr

@dataclass(frozen=True)
class Fail:
    reason: FailureReason

class ScriptedTestProvider(Generic[T]):
    async def call(self) -> T: ...
    @property
    def call_count(self) -> int: ...
    @property
    def remaining(self) -> int: ...

def make_test_provider(
    settings: Settings,
    kind: ProviderKind,
    outcomes: Sequence[Return[T] | Fail],
) -> ScriptedTestProvider[T]: ...
```

Each call consumes one scripted outcome, in call-entry order, without sleeping, network/file access, automatic retries or successful fallback. Concurrent asyncio tasks on one event loop consume distinct outcomes; thread safety is not promised. A failure raises a safe `TestProviderFailure` containing only its reviewed reason; it does not promise the exception type of a future real adapter. `timeout` is a deterministic simulated failure, not measured elapsed time. An exhausted script raises `ScriptExhausted`, an assertion-style fixture error. Call counts include failed/exhausted attempts. Empty scripts are allowed so unexpected calls fail immediately.

The provider records only its kind, counts and unconsumed script; it accepts no credential, recipient, message or object-body arguments. Reprs/errors omit scripted return values. Return values remain test-owned; callers use the immutable shared fixtures where possible and must not supply real private data.

## Typed uses

| Kind | Example controlled value | Limit |
|---|---|---|
| Identity | Existing synthetic `CallerContext` | Does not validate credentials or establish HTTP identity. |
| Email | `None` for simulated completion, or a failure | Does not accept recipients/content or claim delivery. |
| Storage | A synthetic UUID reference, or a failure | Does not create objects, URLs, policies or access permissions. |

## Explicit selection

Construction requires local/test mode and the matching selector set explicitly to `fake`. Reuse `CLIP_IDENTITY_PROVIDER`/`CLIP_EMAIL_PROVIDER`; add `CLIP_STORAGE_PROVIDER` with the same `disabled`/`fake` values and disabled default. Tests may set process variables and load the existing validated Settings. The factory rechecks mode/selection and raises a safe configuration error when disabled or production; it never changes settings, falls back, or constructs a real provider.

Production startup rejects all three fake selectors and existing development-auth/debug controls. The test package stays on pytest's import path only. Step 3 adds the storage startup-rejection matrix; step 4 adds reusable scenario presets; step 5 reviews output/snapshots.

## Review decision

The contributor approved this generic boundary and storage selector before implementation. Provider-specific operation signatures stay with their owning contracts. Implementation: [providers.py](clip_test_fixtures/providers.py); startup guards remain in `app.core.config`.
