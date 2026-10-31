"""Private typed embedding work/configuration; no public wire or worker activation."""

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Literal, Sequence
from uuid import UUID


@dataclass(frozen=True)
class PipelineSpec:
    """Canonical immutable encoding settings; its digest identifies one vector space."""

    canonical_encoding: str

    @property
    def pipeline_id(self) -> bytes:
        """Derive a binary SHA-256 key, independent of mutable serving state."""
        return hashlib.sha256(self.canonical_encoding.encode()).digest()

    @property
    def encoding(self) -> dict[str, Any]:
        """Return a fresh JSON object so callers cannot mutate the frozen config."""
        return dict(json.loads(self.canonical_encoding))


def pipeline_spec(document: dict[str, Any]) -> PipelineSpec:
    """Validate only the reviewed CPU encoder shape; config is not user input.

    Runtime versions must be independently supported before deployment; loading
    these pins does not import/invoke the helper or approve a serving pipeline.
    """
    expected = {
        "model",
        "model_revision",
        "model_sha256",
        "tokenizer_sha256",
        "encoder_version",
        "source_format",
        "dimensions",
        "window",
        "overlap",
        "max_description_chunks",
        "onnxruntime",
        "tokenizers",
        "numpy",
    }
    if set(document) != expected:
        raise ValueError("Invalid embedding pipeline")
    for key, size in (
        ("model_revision", 40),
        ("model_sha256", 64),
        ("tokenizer_sha256", 64),
    ):
        if not isinstance(document[key], str) or not re.fullmatch(
            f"[0-9a-f]{{{size}}}", document[key]
        ):
            raise ValueError("Invalid embedding pipeline")
    for key, value in (
        ("source_format", 1),
        ("dimensions", 384),
        ("window", 254),
        ("overlap", 32),
        ("max_description_chunks", 96),
    ):
        if type(document[key]) is not int or document[key] != value:
            raise ValueError("Invalid embedding pipeline")
    if (
        document["model"] != "sentence-transformers/all-MiniLM-L6-v2"
        or document["encoder_version"] != "masked-mean-l2-chunks-v1"
    ):
        raise ValueError("Invalid embedding pipeline")
    for key in ("onnxruntime", "tokenizers", "numpy"):
        if not isinstance(document[key], str) or not re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+", document[key]
        ):
            raise ValueError("Invalid embedding pipeline")
    return PipelineSpec(json.dumps(document, sort_keys=True, separators=(",", ":")))


def default_pipeline_spec() -> PipelineSpec:
    """Read only the checked local candidate manifest; performs no DB/model work."""
    return pipeline_spec(
        json.loads(Path(__file__).with_name("embedding_pipeline.json").read_text())
    )


@dataclass(frozen=True)
class EmbeddingJob:
    """Fenced internal work receipt; source plaintext is deliberately absent in repr."""

    listing_id: UUID
    pipeline_id: bytes
    generation_id: UUID
    source_fingerprint: bytes
    lease_token: UUID
    lease_until: datetime
    title: str = field(repr=False)
    description: str = field(repr=False)
    encoding: dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class EmbeddingPart:
    """One ordered title/description vector returned by a future real helper."""

    kind: Literal["title", "description"]
    ordinal: int
    vector: tuple[float, ...] = field(repr=False)


def validate_parts(
    parts: Sequence[EmbeddingPart], expected_description_parts: int
) -> tuple[EmbeddingPart, ...]:
    """Refuse partial/malformed helper output before any SQL writes.

    The trusted encoder must supply the actual full source window count; database
    completeness cannot independently tokenize text without the real runtime.
    Both layers check shape/counts; native SQL adds commit-time count constraints.
    """
    if (
        type(expected_description_parts) is not int
        or not 1 <= expected_description_parts <= 96
        or len(parts) != expected_description_parts + 1
    ):
        raise ValueError("Incomplete embedding parts")
    seen = set()
    for part in parts:
        if part.kind not in {"title", "description"} or type(part.ordinal) is not int:
            raise ValueError("Invalid embedding part")
        key = (part.kind, part.ordinal)
        if (
            key in seen
            or (part.kind == "title" and part.ordinal != 0)
            or (
                part.kind == "description"
                and not 0 <= part.ordinal < expected_description_parts
            )
        ):
            raise ValueError("Invalid embedding part")
        seen.add(key)
        validated_vector(part.vector)
    if seen != {("title", 0)} | {
        ("description", index) for index in range(expected_description_parts)
    }:
        raise ValueError("Incomplete embedding parts")
    return tuple(sorted(parts, key=lambda part: (part.kind != "title", part.ordinal)))


def validated_vector(value: object) -> tuple[float, ...]:
    """Validate private query/listing vector output without importing ML packages."""
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 384
        or any(
            type(item) not in {int, float}
            or not math.isfinite(item)
            or abs(item) > 1.001
            for item in value
        )
    ):
        raise ValueError("Invalid embedding vector")
    vector = tuple(float(item) for item in value)
    if abs(math.sqrt(math.fsum(item**2 for item in vector)) - 1.0) > 0.001:
        raise ValueError("Invalid embedding vector")
    return vector
