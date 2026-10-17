# Shared synthetic core fixtures

PD-10 step 1 supplies deterministic, schema-neutral user/listing UUID references, a fixed aware UTC clock, regular/temporary `CallerContext` values, and read-only approved error definitions. These are test inputs, not domain models, credentials, or a sign-in implementation. No contacts, messages or provider payloads are included.

The root pytest configuration adds this directory to the test import path; production startup does not. Factories are available from `clip_test_fixtures`. API tests obtain `synthetic_ids`, `synthetic_clock`, `regular_caller`, `temporary_caller` and `expected_errors` through their conftest. Other test owners may explicitly import those decorated functions from `clip_test_fixtures.pytest_fixtures` in their own test conftest; none is autouse.

Use `regular_caller.require_current(synthetic_clock.now)` for deterministic validity checks. The fixed clock is not the current machine time. Do not pass these contexts into a live runtime, silently patch global time, or treat their construction as credential validation. Tests needing HTTP callers must explicitly arrange their own test-only server dependency wiring.

Run `uv run --locked pytest tests/fixtures/core apps/api/tests/core/test_shared_fixtures.py -q -W error` from the repository root for the factory/consumer checks. The existing full pytest command collects them too. No provider, database, listener, credentials or extra dependency is needed. Schema-specific records and real integrations remain with their owning domain tasks; reviewed test-adapter interfaces precede PD-10 step 2 fakes.
