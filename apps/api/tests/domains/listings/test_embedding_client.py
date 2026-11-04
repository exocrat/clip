"""Protocol faults/lifecycle only; real model acceptance is a separate local probe."""

import asyncio
from pathlib import Path
import sys

import pytest

from app.domains.listings.embedding_client import (
    SemanticHelper,
    HelperBusy,
    HelperLimits,
    HelperUnavailable,
)
from app.domains.listings.embedding_protocol import (
    decode_frame,
    encode_frame,
    chunk_ranges,
    validate_ranges,
)


class FaultClient(SemanticHelper):
    """Owned test subclass; production has no alternate-script/fake-mode setting."""

    def __init__(self, tmp_path, mode, limits=None):
        super().__init__(
            Path(sys.executable),
            tmp_path,
            limits=limits
            or HelperLimits(
                startup=1, inference=0.4, request=1, cleanup=1, restart_delay=0.01
            ),
        )
        self.mode = mode
        self.marker = tmp_path / "crashed-once"
        self.last_pid = None

    async def _launch(self):
        script = Path(__file__).parent / "doubles/embedding_helper.py"
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-B",
            str(script),
            self.mode,
            self.spec.pipeline_id.hex(),
            str(self.marker),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=2 * 1024 * 1024 + 1,
            env={"PATH": "/usr/bin:/bin"},
        )
        self.last_pid = process.pid
        return process


@pytest.mark.parametrize(
    "raw",
    [b'{"v":1,"v":2}\n', b"NaN\n", b"[]\n", b'{"x":Infinity}\n', b"{}", b"\xff\n"],
)
def test_bad_frame_refused_without_echo(raw):
    with pytest.raises(ValueError, match="Invalid helper frame"):
        decode_frame(raw, 100)


def test_frame_and_coverage_bounds():
    assert decode_frame(encode_frame({"ok": True}, 100), 100) == {"ok": True}
    with pytest.raises(ValueError):
        encode_frame({"text": "a" * 100}, 20)
    assert chunk_ranges(5000)[-1][1] == 5000
    for value in ([[False, True]], [[0.0, 1.0]], [[0, 2]], {"start": 0}):
        with pytest.raises(ValueError):
            validate_ranges(value, ((0, 1),))


@pytest.mark.parametrize(
    "settings",
    [
        {"request": 21},
        {"inference": 6},
        {"startup": 31},
        {"cleanup": 0},
        {"request": True},
        {"request": float("nan")},
    ],
)
def test_limits_cannot_exceed_reviewed_caps(settings):
    with pytest.raises(ValueError):
        HelperLimits(**settings)


@pytest.mark.parametrize("mode", ["wrong_ready", "startup_hang"])
def test_bad_startup_reaps_child(tmp_path, mode):
    async def scenario():
        client = FaultClient(
            tmp_path,
            mode,
            HelperLimits(
                startup=0.1, inference=0.1, request=0.2, cleanup=1, restart_delay=0.01
            ),
        )
        with pytest.raises(HelperUnavailable):
            await client.start()
        assert client.pid is None
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "mode",
    [
        "wrong_id",
        "private_extra",
        "bad_json",
        "duplicate",
        "oversize",
        "nan",
        "bad_coverage",
        "bool_coverage",
        "hang",
    ],
)
def test_bad_response_never_accepted_and_child_reaped(tmp_path, mode):
    async def scenario():
        client = FaultClient(tmp_path, mode)
        try:
            await client.start()
            with pytest.raises(HelperUnavailable):
                await client.encode_query("Controlled query")
            assert client.pid is None
        finally:
            await client.close()

    asyncio.run(scenario())


def test_real_model_not_loaded_by_protocol_fixture_and_context_closes(tmp_path):
    async def scenario():
        client = FaultClient(tmp_path, "echo")
        async with client:
            first = await client.encode_query("Controlled query")
            listing = await client.encode_listing(
                "Controlled title", "Controlled description"
            )
            assert len(first.vector) == 384 and len(listing.parts) == 2
            assert "1.0" not in repr(first)
            assert client.starts == 1
        assert client.pid is None
        with pytest.raises(HelperUnavailable):
            await client.encode_query("Closed query")

    asyncio.run(scenario())


def test_crash_recovery_starts_only_one_new_child_without_replaying_request(tmp_path):
    async def scenario():
        client = FaultClient(tmp_path, "crash_once")
        try:
            await client.start()
            first = client.pid
            with pytest.raises(HelperUnavailable):
                await client.encode_query("First controlled query")
            assert client.pid is None
            result = await client.encode_query("Second controlled query")
            assert (
                len(result.vector) == 384 and client.pid != first and client.starts == 2
            )
        finally:
            await client.close()

    asyncio.run(scenario())


def test_queue_cap_and_cancelled_waiter_do_not_kill_active_child(tmp_path):
    async def scenario():
        client = FaultClient(tmp_path, "slow")
        pending = []
        try:
            await client.start()
            pid = client.pid
            active = asyncio.create_task(client.encode_query("Active controlled query"))
            await asyncio.sleep(0.02)
            pending = [
                asyncio.create_task(client.encode_query("Queued controlled query"))
                for _ in range(8)
            ]
            await asyncio.sleep(0.02)
            assert client.waiting == 8
            with pytest.raises(HelperBusy):
                await client.encode_query("Overflow controlled query")
            pending[0].cancel()
            await asyncio.gather(pending[0], return_exceptions=True)
            assert client.pid == pid
            assert len((await active).vector) == 384
            await asyncio.gather(*pending[1:])
            assert client.starts == 1 and client.waiting == 0
        finally:
            for task in pending:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            await client.close()

    asyncio.run(scenario())


def test_active_cancellation_destroys_stream_before_next_request(tmp_path):
    async def scenario():
        client = FaultClient(tmp_path, "slow")
        try:
            await client.start()
            task = asyncio.create_task(client.encode_query("Cancel controlled query"))
            await asyncio.sleep(0.02)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert client.pid is None
            assert (
                len((await client.encode_query("Fresh controlled query")).vector) == 384
            )
            assert client.starts == 2
        finally:
            await client.close()

    asyncio.run(scenario())


def test_launch_preserves_venv_path_and_isolates_environment(tmp_path, monkeypatch):
    """Guard the real-import failure caused by resolving a venv executable symlink."""
    from unittest.mock import AsyncMock

    executable = tmp_path / "venv-python"
    executable.symlink_to(sys.executable)
    launch = AsyncMock()
    monkeypatch.setenv("CLIP_TEST_PARENT_MARKER", "controlled-parent-marker")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    client = SemanticHelper(executable, tmp_path)
    asyncio.run(client._launch())
    args, kwargs = launch.await_args
    assert args[0] == str(executable.absolute()) and args[1:3] == ("-I", "-B")
    if "CLIP_TEST_PARENT_MARKER" in kwargs["env"]:
        raise AssertionError("Ambient environment forwarded")
    assert kwargs["stderr"] == asyncio.subprocess.DEVNULL


def test_startup_cancellation_reaps_owned_child(tmp_path):
    async def scenario():
        client = FaultClient(tmp_path, "startup_hang")
        task = asyncio.create_task(client.start())
        try:
            async with asyncio.timeout(0.5):
                while client.pid is None:
                    await asyncio.sleep(0.001)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert client.pid is None
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await client.close()

    asyncio.run(scenario())


def test_close_interrupts_active_call_and_reaps_child(tmp_path):
    async def scenario():
        client = FaultClient(tmp_path, "hang")
        await client.start()
        task = asyncio.create_task(client.encode_query("Controlled query"))
        try:
            async with asyncio.timeout(0.2):
                while client.windows_started < 1:
                    await asyncio.sleep(0.001)
            await client.close()
            with pytest.raises(HelperUnavailable):
                await task
            assert client.pid is None
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await client.close()

    asyncio.run(scenario())


def test_process_wide_owner_blocks_second_controller_until_close(tmp_path):
    """Two client instances cannot silently create two resident model helpers."""

    async def scenario():
        first = FaultClient(tmp_path, "echo")
        second = FaultClient(tmp_path, "echo")
        third = FaultClient(tmp_path, "echo")
        try:
            await first.start()
            pid = first.pid
            with pytest.raises(HelperUnavailable):
                await second.start()
            assert second.pid is None
            await second.close()
            assert len((await first.encode_query("Controlled query")).vector) == 384
            assert first.pid == pid
            await first.close()
            await third.start()
            assert third.pid is not None and third.pid != pid
        finally:
            await first.close()
            await second.close()
            await third.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "mode,code",
    [
        ("hang", "timeout"),
        ("error_timeout", "timeout"),
        ("crash_once", "helper_unavailable"),
        ("nan", "invalid_vectors"),
    ],
)
def test_failures_keep_only_fixed_job_classification(tmp_path, mode, code):
    async def scenario():
        client = FaultClient(tmp_path, mode)
        try:
            await client.start()
            with pytest.raises(HelperUnavailable) as caught:
                await client.encode_query("Controlled query")
            assert caught.value.failure_code == code
            assert "Controlled query" not in str(caught.value)
            assert client.pid is None
        finally:
            await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("length", [0, 1, 254, 255, 5000, 21344])
def test_protocol_windows_cover_every_token_without_gaps(length):
    ranges = chunk_ranges(length)
    assert ranges[0][0] == 0 and ranges[-1][1] == length
    assert len(ranges) <= 96 and all(end - start <= 254 for start, end in ranges)
    assert {index for start, end in ranges for index in range(start, end)} == set(
        range(length)
    )
    assert all(left[1] - right[0] == 32 for left, right in zip(ranges, ranges[1:]))


def test_protocol_window_overflow_is_explicit():
    with pytest.raises(ValueError):
        chunk_ranges(21345)


def test_cancellation_during_launch_keeps_ownership_until_child_is_reaped(tmp_path):
    """A shielded spawn cannot leave an untracked child when startup is cancelled."""

    class DelayedLaunch(FaultClient):
        def __init__(self):
            super().__init__(tmp_path, "echo")
            self.spawned = asyncio.Event()
            self.release = asyncio.Event()

        async def _launch(self):
            child = await super()._launch()
            self.spawned.set()
            await self.release.wait()
            return child

    async def scenario():
        client = DelayedLaunch()
        task = asyncio.create_task(client.start())
        try:
            await asyncio.wait_for(client.spawned.wait(), 1)
            task.cancel()
            client.release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert client.pid is None
        finally:
            client.release.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await client.close()

    asyncio.run(scenario())


def test_query_cache_reuses_only_live_checked_vectors_and_expires(tmp_path):
    """Identical warm queries save inference; expiry/closure never bypass guards."""
    import time

    async def scenario():
        client = FaultClient(tmp_path, "echo")
        try:
            first = await client.encode_query("Controlled repeated query")
            assert await client.encode_query("Controlled repeated query") == first
            assert client.windows_started == 1
            assert all(
                isinstance(key, bytes) and len(key) == 32 for key in client._query_cache
            )
            key = next(iter(client._query_cache))
            _, value = client._query_cache[key]
            client._query_cache[key] = (time.monotonic() - 1, value)
            assert await client.encode_query("Controlled repeated query") == first
            assert client.windows_started == 2
            with pytest.raises(ValueError):
                await client.encode_query(" ")
            assert client.windows_started == 2
        finally:
            await client.close()
        assert not client._query_cache
        with pytest.raises(HelperUnavailable):
            await client.encode_query("Controlled repeated query")

    asyncio.run(scenario())


def test_query_cache_is_bounded_lru_and_does_not_hide_a_dead_helper(tmp_path):
    """Eviction limits memory; a dead child must restart instead of serving a hit."""

    async def scenario():
        client = FaultClient(tmp_path, "echo")
        try:
            for index in range(128):
                await client.encode_query(f"Controlled query {index}")
            await client.encode_query("Controlled query 0")
            await client.encode_query("Controlled query 128")
            assert len(client._query_cache) == 128 and client.windows_started == 129
            await client.encode_query("Controlled query 1")
            assert client.windows_started == 130
            process = client._process
            assert process is not None
            process.kill()
            await process.wait()
            old_starts = client.starts
            await client.encode_query("Controlled query 1")
            assert client.starts == old_starts + 1
            assert len(client._query_cache) == 1
        finally:
            await client.close()

    asyncio.run(scenario())
