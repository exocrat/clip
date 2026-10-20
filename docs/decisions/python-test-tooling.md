# PD-04 — Python foundation test tooling

**Date:** 2026-10-17

## Question

Which additional Python quality tools are required before the Stream 1 API and shared-core implementation?

## Options considered

- Python's built-in unittest runner: no added dependency, but less direct support for the reusable fixtures and parameterized cases required by PD-06/PD-10.
- pytest: one test runner supports the upcoming API, core boundary, and fixture tests.
- Add lint and static type tools immediately: possible future checks, but no Python application code or required Python lint/type policy exists yet.

## Selected choice

Pin pytest 9.1.1 in the root uv development dependency group. Root `pyproject.toml` is the sole pytest configuration, with API/shared test roots and strict configuration/marker validation. Keep Black 26.10.1 as the formatter. Defer Python lint/static type tools until a concrete implementation requirement justifies selection; PD-12's Python lint/type gates apply only if selected. API-specific test clients or plugins are selected with the API implementation.

## Rationale

PD-05 explicitly requires API/configuration tests, PD-06 requires common primitive tests, and PD-10 requires reusable fixtures. pytest meets those needs without adding a speculative lint/type policy. Official [pytest release metadata](https://pypi.org/pypi/pytest/9.1.1/json) declares Python 3.14 support; installation and runner behavior are checked locally on Linux ARM64. Successful runner smoke checks do not prove the unimplemented API or domain behavior.

## Implications

PD-05/06/10 use this runner and extend the same root configuration if needed; PD-12 wires the actual suite into CI. Run `uv sync --locked` after receiving the updated lockfile. The test runner command is `uv run --locked pytest`; no test Make target is created under PD-04's formatter-only Makefile exception. Real tests are future task outputs; an empty suite is not a passing product test result.

## Approver

Not required for this routine tool choice within the approved PD-04 step 5 scope; Aditya verified the implementation result before step 6. Commits require separate approval.

## Supersedes

None.

## DL-00 Step 11 scoped typing check

Step 11 requires a consumer-owned Python test double to type-check against a
generated provider declaration. This is a concrete requirement beyond the
earlier pytest-only scope. Add pinned `mypy==2.0.0` to the development group and
limit its configured check to the Search-owned Listings double. This version
supports Python 3.14 syntax; do not extend it into an application-wide typing
policy without a separate task decision. Mypy runs locally and in the existing
PR CI aggregate. See the [Mypy Python 3.14 release notes](https://mypy.readthedocs.io/en/stable/changelog.html#python-3-14-support).
