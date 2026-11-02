"""Offline tests use synthetic session values and never start a workload."""

from collections.abc import Iterator, Mapping

import pytest

from scripts.evaluation.k6.comparison_session_handoff import (
    SESSION_VARIABLE,
    prepare_session_environment,
)

FAKE_SESSION = "__Host-clip_session=synthetic-test-value"


class UnreadableEnvironment(Mapping[str, str]):
    """Fail a test if a rejected preflight attempts to read a session."""

    def __getitem__(self, key: str) -> str:
        raise AssertionError("session accessed before preflight")

    def __iter__(self) -> Iterator[str]:
        return iter(())

    def __len__(self) -> int:
        return 0


def test_refuses_before_session_access() -> None:
    with pytest.raises(ValueError, match="comparison_preflight_required"):
        prepare_session_environment(
            {"local_inputs_checked": False}, UnreadableEnvironment()
        )
    with pytest.raises(ValueError, match="comparison_preflight_required"):
        prepare_session_environment(
            {"local_inputs_checked": 1}, UnreadableEnvironment()
        )


def test_only_session_is_copied_after_preflight() -> None:
    result = prepare_session_environment(
        {"local_inputs_checked": True},
        {SESSION_VARIABLE: FAKE_SESSION, "UNRELATED": "not-copied"},
    )
    assert result == {SESSION_VARIABLE: FAKE_SESSION}


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "other=value",
        "__Host-clip_session=",
        "__Host-clip_session=bad\r\nheader",
        "__Host-clip_session=bad;extra=x",
        "__Host-clip_session=" + "a" * 2049,
    ],
)
def test_invalid_session_is_refused_without_disclosure(value: str | None) -> None:
    source = {} if value is None else {SESSION_VARIABLE: value}
    with pytest.raises(ValueError) as error:
        prepare_session_environment({"local_inputs_checked": True}, source)
    if value:
        assert value not in str(error.value)
