"""Controlled-time checks for the human-approved shared OTP attempt window."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domains.identity.temporary_policy import (
    MAX_FAILURES,
    VerificationLimited,
    VerificationWindow,
)

NOW = datetime(2030, 1, 1, tzinfo=UTC)


def test_resend_preserves_failures_and_moves_expiry_to_latest_code():
    initial = VerificationWindow(NOW + timedelta(minutes=10))
    failed = initial.failed(NOW).failed(NOW)
    resent = failed.resend(NOW + timedelta(minutes=9))
    assert resent.failures == 2
    assert resent.expires_at == NOW + timedelta(minutes=19)
    resent.require_available(NOW + timedelta(minutes=18))
    exhausted = resent.failed(NOW + timedelta(minutes=18))
    assert exhausted.failures == MAX_FAILURES == 3
    for instant in (
        NOW + timedelta(minutes=18),
        resent.expires_at - timedelta(microseconds=1),
    ):
        with pytest.raises(VerificationLimited):
            exhausted.require_available(instant)
        with pytest.raises(VerificationLimited):
            exhausted.resend(instant)
    restarted = exhausted.resend(resent.expires_at)
    assert restarted.failures == 0
    assert restarted.expires_at == NOW + timedelta(minutes=29)


def test_expired_verification_cannot_charge_or_extend_window():
    window = VerificationWindow(NOW, failures=2)
    with pytest.raises(ValueError, match="expired"):
        window.failed(NOW)
    assert window.failures == 2 and window.expires_at == NOW


@pytest.mark.parametrize("failures", [-1, 4, True, 1.5])
def test_invalid_persisted_failure_count_is_rejected(failures):
    with pytest.raises(ValueError):
        VerificationWindow(NOW, failures)
