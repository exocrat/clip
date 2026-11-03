from urllib.request import Request

from scripts.evaluation.nfr04_retrieval import _NoRedirect
from scripts.evaluation.nfr06_recovery import validate_plan as validate_recovery_plan
from scripts.evaluation.nfr07_restore_observer import (
    validate_plan as validate_restore_plan,
)


def test_live_observers_import_and_reject_redirects_without_network() -> None:
    request = Request("https://example.invalid/api/listings")
    assert (
        _NoRedirect().redirect_request(
            request, None, 302, "Found", {}, "https://other.invalid/api/listings"
        )
        is None
    )
    assert callable(validate_recovery_plan)
    assert callable(validate_restore_plan)
