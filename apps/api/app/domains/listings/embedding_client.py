"""Bounded async client for the owned offline embedding helper.

One child/serial exchange, eight waiting calls, no shell, no ambient credential
forwarding and explicit opt-in application lifecycle binding. Failures never use a fake model.
"""

import asyncio
from collections import OrderedDict
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
import os
import threading
import time
from typing import Any, Literal
from uuid import uuid4

from app.domains.listings.embedding_protocol import (
    INPUT_BYTES,
    OUTPUT_BYTES,
    VERSION,
    WINDOW,
    chunk_ranges,
    decode_frame,
    encode_frame,
    validate_request,
    validate_ranges,
)
from app.domains.listings.embedding_types import (
    EmbeddingPart,
    PipelineSpec,
    default_pipeline_spec,
    validate_parts,
    validated_vector,
)


class HelperUnavailable(RuntimeError):
    """Safe failure plus a fixed persistence code; no raw helper error is retained."""

    def __init__(
        self,
        message: str,
        *,
        failure_code: Literal[
            "timeout", "helper_unavailable", "invalid_vectors"
        ] = "helper_unavailable",
    ) -> None:
        """Keep classification separate from private transport diagnostics."""
        super().__init__(message)
        self.failure_code = failure_code


class HelperBusy(HelperUnavailable):
    """Reject immediately when eight callers already wait behind the active call."""


@dataclass(frozen=True)
class HelperLimits:
    """Only permit shorter operational/test limits, never raise reviewed ceilings."""

    startup: float = 30
    inference: float = 5
    request: float = 20
    cleanup: float = 5
    restart_delay: float = 1

    def __post_init__(self) -> None:
        """Reject invalid/unbounded settings before any child can start."""
        for name, maximum in (
            ("startup", 30),
            ("inference", 5),
            ("request", 20),
            ("cleanup", 5),
            ("restart_delay", 1),
        ):
            value = getattr(self, name)
            if type(value) not in {int, float} or not 0 < value <= maximum:
                raise ValueError("Invalid helper limits")


@dataclass(frozen=True)
class EncodedListing:
    """Private complete model output and validated source-token coverage metadata."""

    parts: tuple[EmbeddingPart, ...] = field(repr=False)
    title_tokens: int
    description_tokens: int
    ranges: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class EncodedQuery:
    """Private model vector; never part of the public summary response."""

    vector: tuple[float, ...] = field(repr=False)
    tokens: int


class SemanticHelper:
    """Explicit lifecycle owner for one local helper; no DB/model-target discovery."""

    _owner_guard = threading.Lock()
    _owner: tuple[int, "SemanticHelper"] | None = None

    def __init__(
        self, interpreter: Path, model_dir: Path, *, limits: HelperLimits | None = None
    ) -> None:
        """Bind trusted explicit local paths. Construction performs no process work."""
        # Preserve the venv invocation path: resolving its executable symlink
        # would bypass pyvenv.cfg and lose the isolated inference dependencies.
        self._api_pid = os.getpid()
        self.interpreter = interpreter.absolute()
        self.model_dir = model_dir.resolve()
        self.spec = default_pipeline_spec()
        self.limits = limits or HelperLimits()
        self._lock = asyncio.Lock()
        self._process: asyncio.subprocess.Process | None = None
        self._waiting = 0
        self._closed = False
        self._broken = False
        self._last_failure: float | None = None
        self.starts = 0
        self.windows_started = 0
        self.helper_peak_rss_bytes = 0
        # Process-local immutable query vectors only:128 hashed keys,5minute
        # monotonic TTL. Never cache sessions, listing visibility or result pages.
        self._query_cache: OrderedDict[bytes, tuple[float, EncodedQuery]] = (
            OrderedDict()
        )

    @property
    def pid(self) -> int | None:
        """Expose only owned child identity for bounded local supervision/tests."""
        process = self._process
        return (
            process.pid if process is not None and process.returncode is None else None
        )

    @property
    def waiting(self) -> int:
        """Content-free queue depth; source values never enter diagnostic snapshots."""
        return self._waiting

    def _claim_owner(self) -> None:
        """Reserve exactly one controller per API process, including startup/restart."""
        if os.getpid() != self._api_pid:
            raise HelperUnavailable("helper_owner_mismatch")
        with SemanticHelper._owner_guard:
            prior = SemanticHelper._owner
            if prior is not None and prior[0] == self._api_pid and prior[1] is not self:
                raise HelperUnavailable("helper_owner_conflict")
            SemanticHelper._owner = (self._api_pid, self)

    async def _launch(self) -> asyncio.subprocess.Process:
        """Execute fixed reviewed code with isolated imports and minimal environment.

        Tests may override this method for protocol fault injection; production
        configuration/HTTP/environment cannot select a double or alternate script.
        """
        script = Path(__file__).with_name("embedding_helper.py")
        env = {
            "PATH": "/usr/bin:/bin",
            "HF_HUB_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
        }
        return await asyncio.create_subprocess_exec(
            str(self.interpreter),
            "-I",
            "-B",
            str(script),
            "--model-dir",
            str(self.model_dir),
            cwd=script.parent,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=OUTPUT_BYTES + 1,
        )

    async def _stop(self, *, failed: bool = False) -> None:
        """Kill/reap only this child; never start another if reaping fails."""
        self._query_cache.clear()
        if os.getpid() != self._api_pid:
            # Forked descendants never signal an inherited parent's helper.
            self._process = None
            self._broken = True
            return
        process = self._process
        if failed:
            self._last_failure = time.monotonic()
        if process is None:
            return
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        try:
            await asyncio.wait_for(process.wait(), self.limits.cleanup)
        except Exception:
            self._broken = True
            raise HelperUnavailable("helper_cleanup_failed") from None
        if process.stdin is not None:
            process.stdin.close()
        self._process = None

    async def _line(self, timeout: float) -> dict[str, Any]:
        """Bound reads; EOF/oversize/invalid JSON become safe failures, never fallback."""
        process = self._process
        if process is None or process.stdout is None:
            raise HelperUnavailable("helper_unavailable")
        raw = await asyncio.wait_for(process.stdout.readline(), timeout)
        if not raw:
            raise HelperUnavailable("helper_eof")
        return decode_frame(raw, OUTPUT_BYTES)

    def _peak(self, value: object) -> None:
        """Keep only typed bounded helper resource metadata, not arbitrary payloads."""
        if type(value) is not int or value < 0 or value >= 512 * 1024 * 1024:
            raise ValueError("Invalid helper resource metadata")
        self.helper_peak_rss_bytes = max(self.helper_peak_rss_bytes, value)

    async def _ensure_started(self) -> None:
        """Check exact model/runtime handshake before any request is sent."""
        if self._closed or self._broken:
            raise HelperUnavailable("helper_closed")
        self._claim_owner()
        if self._process is not None and self._process.returncode is None:
            return
        if self._process is not None:
            await self._stop(failed=True)
        if self._last_failure is not None:
            delay = self.limits.restart_delay - (time.monotonic() - self._last_failure)
            if delay > 0:
                await asyncio.sleep(delay)
        launch = asyncio.create_task(self._launch())
        try:
            self._process = await asyncio.shield(launch)
        except asyncio.CancelledError:
            # Retain ownership across cancellation in process creation. A late
            # child is killed; broken latch prevents additional launches.
            try:
                self._process = await asyncio.wait_for(
                    asyncio.shield(launch), self.limits.cleanup
                )
            except Exception:
                self._broken = True

                def kill_late(task: asyncio.Task[asyncio.subprocess.Process]) -> None:
                    """Kill only an eventual child from this already-owned launch."""
                    if not task.cancelled() and task.exception() is None:
                        child = task.result()
                        if child.returncode is None:
                            child.kill()

                launch.add_done_callback(kill_late)
            raise
        self.starts += 1
        if self._closed:
            raise HelperUnavailable("helper_closed")
        value = await self._line(self.limits.startup)
        expected = {
            "v",
            "kind",
            "pipeline_id",
            "pid",
            "python_minor",
            "runtime",
            "threads",
            "offline",
            "peak_rss_bytes",
        }
        config = self.spec.encoding
        if (
            set(value) != expected
            or type(value["v"]) is not int
            or value["v"] != VERSION
            or value["kind"] != "ready"
            or value["pipeline_id"] != self.spec.pipeline_id.hex()
            or type(value["pid"]) is not int
            or value["pid"] != self._process.pid
            or value["python_minor"] != "3.13"
            or value["runtime"]
            != {key: config[key] for key in ("numpy", "onnxruntime", "tokenizers")}
            or type(value["threads"]) is not int
            or value["threads"] != 1
            or value["offline"] is not True
        ):
            raise HelperUnavailable("helper_binding_mismatch")
        self._peak(value["peak_rss_bytes"])

    async def start(self) -> None:
        """Optional explicit prewarm, bounded to30s, with no automatic worker start."""
        async with self._lock:
            try:
                async with asyncio.timeout(self.limits.startup):
                    await self._ensure_started()
            except asyncio.CancelledError:
                await self._stop(failed=True)
                raise
            except Exception as error:
                await self._stop(failed=True)
                code: Literal["timeout", "helper_unavailable", "invalid_vectors"] = (
                    "timeout"
                    if isinstance(error, TimeoutError)
                    else "helper_unavailable"
                )
                raise HelperUnavailable(
                    "helper_start_failed", failure_code=code
                ) from None

    async def close(self) -> None:
        """Reject new work, interrupt active owned child, then reap it under the lock."""
        self._closed = True
        self._query_cache.clear()
        if os.getpid() != self._api_pid:
            self._process = None
            self._broken = True
            return
        process = self._process
        if process is not None and process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        async with self._lock:
            await self._stop()
        if not self._broken:
            with SemanticHelper._owner_guard:
                prior = SemanticHelper._owner
                if prior is not None and prior[0] == self._api_pid and prior[1] is self:
                    SemanticHelper._owner = None

    async def __aenter__(self) -> "SemanticHelper":
        """Prewarm an explicitly constructed local helper context."""
        try:
            await self.start()
        except BaseException:
            await self.close()
            raise
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Always stop/reap on scope exit, including caller failures."""
        await self.close()

    async def _request(
        self, operation: Literal["query", "listing"], fields: dict[str, str]
    ) -> dict[str, Any]:
        """Bound waiting/work to20s; cancellation of active work destroys its stream."""
        request = {
            "v": VERSION,
            "request_id": str(uuid4()),
            "pipeline_id": self.spec.pipeline_id.hex(),
            "operation": operation,
            **fields,
        }
        validate_request(request, self.spec.pipeline_id.hex())
        raw = encode_frame(request, INPUT_BYTES)
        if self._closed or self._broken:
            raise HelperUnavailable("helper_closed")
        if self._waiting >= 8:
            raise HelperBusy("helper_queue_full")
        self._waiting += 1
        acquired = False
        try:
            async with asyncio.timeout(self.limits.request):
                await self._lock.acquire()
                acquired = True
                self._waiting -= 1
                await self._ensure_started()
                process = self._process
                assert process is not None and process.stdin is not None
                process.stdin.write(raw)
                await process.stdin.drain()
                progress = 0
                while True:
                    value = await self._line(self.limits.inference)
                    if (
                        value.get("v") != VERSION
                        or type(value.get("v")) is not int
                        or value.get("request_id") != request["request_id"]
                        or value.get("pipeline_id") != request["pipeline_id"]
                    ):
                        raise HelperUnavailable("helper_binding_mismatch")
                    if value.get("kind") == "error":
                        if set(value) != {
                            "v",
                            "kind",
                            "request_id",
                            "pipeline_id",
                            "code",
                        } or value["code"] not in {
                            "timeout",
                            "helper_unavailable",
                            "invalid_vectors",
                        }:
                            raise ValueError("Invalid helper error")
                        raise HelperUnavailable(
                            "helper_remote_error", failure_code=value["code"]
                        )
                    if value.get("kind") == "progress":
                        if (
                            set(value)
                            != {
                                "v",
                                "kind",
                                "request_id",
                                "pipeline_id",
                                "part_kind",
                                "ordinal",
                                "peak_rss_bytes",
                            }
                            or type(value["ordinal"]) is not int
                        ):
                            raise ValueError("Invalid helper progress")
                        expected_kind = (
                            "query"
                            if operation == "query"
                            else ("title" if progress == 0 else "description")
                        )
                        expected_ordinal = (
                            0 if operation == "query" or progress == 0 else progress - 1
                        )
                        if (
                            value["part_kind"] != expected_kind
                            or value["ordinal"] != expected_ordinal
                            or progress >= (1 if operation == "query" else 97)
                        ):
                            raise ValueError("Invalid helper progress")
                        self._peak(value["peak_rss_bytes"])
                        self.windows_started += 1
                        progress += 1
                        continue
                    return self._result(value, operation, progress)
        except asyncio.CancelledError:
            if acquired:
                await self._stop(failed=True)
            raise
        except Exception as error:
            if acquired:
                await self._stop(failed=True)
            code: Literal["timeout", "helper_unavailable", "invalid_vectors"]
            if isinstance(error, HelperUnavailable):
                code = error.failure_code
            elif isinstance(error, TimeoutError):
                code = "timeout"
            elif isinstance(error, ValueError):
                code = "invalid_vectors"
            else:
                code = "helper_unavailable"
            raise HelperUnavailable(
                "helper_request_failed", failure_code=code
            ) from None
        finally:
            if acquired:
                self._lock.release()
            else:
                self._waiting -= 1

    def _result(
        self, value: dict[str, Any], operation: str, progress: int
    ) -> dict[str, Any]:
        """Validate complete source-token coverage and vector shape before returning."""
        if (
            set(value)
            != {
                "v",
                "kind",
                "request_id",
                "pipeline_id",
                "operation",
                "parts",
                "title_tokens",
                "description_tokens",
                "query_tokens",
                "ranges",
                "peak_rss_bytes",
            }
            or value["kind"] != "result"
            or value["operation"] != operation
        ):
            raise ValueError("Invalid helper result")
        self._peak(value["peak_rss_bytes"])
        if operation == "query":
            count = value["query_tokens"]
            if (
                type(count) is not int
                or not 0 <= count <= WINDOW
                or value["title_tokens"] is not None
                or value["description_tokens"] is not None
                or progress != 1
            ):
                raise ValueError("Invalid query coverage")
            validate_ranges(value["ranges"], ((0, count),))
            if not isinstance(value["parts"], list) or len(value["parts"]) != 1:
                raise ValueError("Invalid query vector")
            part = value["parts"][0]
            if (
                not isinstance(part, dict)
                or set(part) != {"kind", "ordinal", "vector"}
                or part["kind"] != "query"
                or type(part["ordinal"]) is not int
                or part["ordinal"] != 0
            ):
                raise ValueError("Invalid query vector")
            validated_vector(part["vector"])
        else:
            count = value["description_tokens"]
            title = value["title_tokens"]
            if (
                type(title) is not int
                or not 0 <= title <= WINDOW
                or type(count) is not int
                or value["query_tokens"] is not None
            ):
                raise ValueError("Invalid listing coverage")
            ranges = chunk_ranges(count)
            validate_ranges(value["ranges"], ranges)
            if progress != len(ranges) + 1 or not isinstance(value["parts"], list):
                raise ValueError("Incomplete listing coverage")
            parts = []
            for part in value["parts"]:
                if not isinstance(part, dict) or set(part) != {
                    "kind",
                    "ordinal",
                    "vector",
                }:
                    raise ValueError("Invalid listing vector")
                parts.append(
                    EmbeddingPart(
                        part["kind"], part["ordinal"], validated_vector(part["vector"])
                    )
                )
            validate_parts(parts, len(ranges))
        return value

    async def encode_query(self, text: str) -> EncodedQuery:
        """Reuse an identical checked query vector, never private search results.

        Exact text and immutable model identity form a hashed in-memory key.
        Entries expire after300monotonic seconds and the LRU holds at most128.
        Known dead/closed/broken or fork-inherited helpers cannot satisfy a hit;
        normal startup/recovery and all original protocol validation still apply.
        """
        validate_request(
            {
                "v": VERSION,
                "request_id": str(uuid4()),
                "pipeline_id": self.spec.pipeline_id.hex(),
                "operation": "query",
                "text": text,
            },
            self.spec.pipeline_id.hex(),
        )
        if self._closed or self._broken:
            raise HelperUnavailable("helper_closed")
        self._claim_owner()
        key = hashlib.sha256(
            self.spec.pipeline_id + b"\0" + text.encode("utf-8")
        ).digest()
        cached = self._query_cache.pop(key, None)
        if cached is not None and self.pid is not None and time.monotonic() < cached[0]:
            self._query_cache[key] = cached
            return cached[1]
        value = await self._request("query", {"text": text})
        result = EncodedQuery(
            validated_vector(value["parts"][0]["vector"]), value["query_tokens"]
        )
        if self.pid is not None and not self._closed and not self._broken:
            self._query_cache[key] = (time.monotonic() + 300, result)
            while len(self._query_cache) > 128:
                self._query_cache.popitem(last=False)
        return result

    async def encode_listing(self, title: str, description: str) -> EncodedListing:
        """Return every title/description window, safe for later fenced publication."""
        value = await self._request(
            "listing", {"title": title, "description": description}
        )
        parts = tuple(
            EmbeddingPart(
                part["kind"], part["ordinal"], validated_vector(part["vector"])
            )
            for part in value["parts"]
        )
        return EncodedListing(
            parts,
            value["title_tokens"],
            value["description_tokens"],
            chunk_ranges(value["description_tokens"]),
        )
