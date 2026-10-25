"""Bounded real CPU inference probe, isolated from application runtime and labels.

Run only with the separate helper interpreter and verified adjacent artifacts.
No network, model Hub lookup, private input, database or public API activation.
"""

import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / ".tools/semantic"
WINDOW = 254
OVERLAP = 32
MAX_CHUNKS = 96


def chunk_ranges(length, window=WINDOW, overlap=OVERLAP, limit=MAX_CHUNKS):
    """Cover every content-token index with overlap, refusing overflow/truncation."""
    if type(length) is not int or length < 0 or not 0 <= overlap < window or limit < 1:
        raise ValueError("Invalid chunk bounds")
    if length == 0:
        return ((0, 0),)
    result = []
    start = 0
    while start < length:
        end = min(start + window, length)
        result.append((start, end))
        if len(result) > limit:
            raise ValueError("Chunk budget exceeded")
        if end == length:
            break
        start += window - overlap
    return tuple(result)


def long_description_fixture():
    """Controlled contract-sized text whose meaningful term occurs at the end."""
    return "ordinary filler " * 300 + " collectible telescope"


def event(phase):
    """Emit only phase timing so the parent watchdog can enforce deadlines."""
    print(json.dumps({"phase": phase, "started": time.monotonic()}), flush=True)


def main():
    """Verify pinned artifacts, pool actual model output, measure controlled cases."""
    event("startup")
    network_attempts = []

    def audit(name, args):
        """Reject network/child-process activity even if a library tries silently."""
        if name in {"socket.connect", "socket.bind", "subprocess.Popen"}:
            network_attempts.append(name)
            raise RuntimeError("Probe forbids network/child processes")

    sys.addaudithook(audit)
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer

    started = time.monotonic()
    artifacts = json.loads((LOCAL / "artifacts.json").read_text())
    if artifacts["model_revision"] != "1110a243fdf4706b3f48f1d95db1a4f5529b4d41":
        raise ValueError("Model revision mismatch")
    # Stream hashing avoids retaining a model-sized Python buffer alongside ORT.
    for artifact in artifacts["artifacts"]:
        if artifact["kind"] != "model":
            continue
        path = LOCAL / "model" / artifact["filename"]
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if path.stat().st_size != artifact["bytes"] or digest != artifact["sha256"]:
            raise ValueError("Model artifact mismatch")
    pooling = json.loads((LOCAL / "model/1_Pooling/config.json").read_text())
    if (
        pooling["word_embedding_dimension"] != 384
        or not pooling["pooling_mode_mean_tokens"]
    ):
        raise ValueError("Unsupported pooling configuration")
    tokenizer = Tokenizer.from_file(str(LOCAL / "model/tokenizer.json"))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    cls = tokenizer.token_to_id("[CLS]")
    sep = tokenizer.token_to_id("[SEP]")
    pad = tokenizer.token_to_id("[PAD]")
    if None in (cls, sep, pad):
        raise ValueError("Missing model special tokens")
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session = ort.InferenceSession(
        str(LOCAL / "model/onnx/model.onnx"),
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )
    input_names = {item.name for item in session.get_inputs()}
    if input_names != {"input_ids", "attention_mask", "token_type_ids"}:
        raise ValueError("Unexpected ONNX inputs")
    startup_seconds = time.monotonic() - started
    durations = []
    calls = 0

    def encode_ids(ids, pad_to=None):
        """Run one <=256-token batch, mean-pool masked states and L2-normalize."""
        nonlocal calls
        if len(ids) > WINDOW or calls >= 30:
            raise ValueError("Inference budget exceeded")
        calls += 1
        event("inference")
        begin = time.monotonic()
        tokens = [cls, *ids, sep]
        padding = max(0, (pad_to or len(tokens)) - len(tokens))
        mask = np.array([[1] * len(tokens) + [0] * padding], dtype=np.int64)
        values = np.array([tokens + [pad] * padding], dtype=np.int64)
        output = session.run(
            None,
            {
                "input_ids": values,
                "attention_mask": mask,
                "token_type_ids": np.zeros_like(values),
            },
        )[0]
        if (
            output.shape != (1, len(tokens) + padding, 384)
            or not np.isfinite(output).all()
        ):
            raise ValueError("Invalid model tensor")
        weights = mask[..., None].astype(np.float32)
        pooled = (output * weights).sum(axis=1)[0] / weights.sum()
        norm = np.linalg.norm(pooled)
        if not np.isfinite(norm) or norm <= 0:
            raise ValueError("Invalid embedding norm")
        vector = pooled / norm
        duration = time.monotonic() - begin
        if duration > 5:
            raise ValueError("Inference deadline exceeded")
        durations.append(duration)
        event("preparation")
        return vector

    def encode(text):
        """Encode every description window; never silently use only its start."""
        ids = tokenizer.encode(text, add_special_tokens=False).ids
        return [encode_ids(ids[start:end]) for start, end in chunk_ranges(len(ids))]

    docs = (
        "A pedal powered bicycle for commuting around campus.",
        "A calculus textbook with worked exercises for university students.",
        "A wooden desk and comfortable chair for studying in a room.",
        "A refrigerator that keeps food and drinks cold.",
    )
    vectors = [encode(text)[0] for text in docs]
    scenarios = []
    for name, text, expected in (
        ("campus_transport", "something to ride to campus", 0),
        ("calculus_study", "study material for calculus", 1),
        ("study_furniture", "furniture for studying", 2),
    ):
        query = encode(text)[0]
        scores = [float(np.dot(query, vector)) for vector in vectors]
        order = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
        scenarios.append(
            {
                "scenario": name,
                "top_fixture": order[0],
                "expected_fixture": expected,
                "expected_top": order[0] == expected,
                "similarities": scores,
            }
        )
    repeat = encode(docs[0])[0]
    repeat_delta = float(np.max(np.abs(repeat - vectors[0])))
    if repeat_delta > 1e-6:
        raise ValueError("Embedding repeatability failed")
    ids = tokenizer.encode(docs[0], add_special_tokens=False).ids
    padded = encode_ids(ids, pad_to=256)
    padding_delta = float(np.max(np.abs(padded - vectors[0])))
    if padding_delta > 2e-5:
        raise ValueError("Padding invariance failed")
    long_text = long_description_fixture()
    if len(long_text) > 5000:
        raise ValueError("Long fixture exceeds description contract")
    long_ids = tokenizer.encode(long_text, add_special_tokens=False).ids
    ranges = chunk_ranges(len(long_ids))
    long_vectors = encode(long_text)
    query = encode("telescope")[0]
    long_scores = [float(np.dot(query, vector)) for vector in long_vectors]
    # Tokenization-only maximum-length coverage avoids 23 unneeded model calls.
    boundary_ids = tokenizer.encode("界" * 5000, add_special_tokens=False).ids
    boundary_ranges = chunk_ranges(len(boundary_ids))
    if ranges[-1][1] != len(long_ids) or boundary_ranges[-1][1] != len(boundary_ids):
        raise ValueError("Description end omitted")
    if network_attempts:
        raise ValueError("Unexpected network/child-process attempt")
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != "darwin":
        peak *= 1024
    report = {
        "preview_only": True,
        "nfr04_accepted": False,
        "human_review_verified": False,
        "python": platform.python_version(),
        "platform": sys.platform,
        "machine": os.uname().machine,
        "macos": platform.mac_ver()[0],
        "onnxruntime": ort.__version__,
        "numpy": np.__version__,
        "model_revision": artifacts["model_revision"],
        "providers": session.get_providers(),
        "inference_calls": calls,
        "startup_seconds": startup_seconds,
        "cold_inference_seconds": durations[0],
        "warm_median_seconds": float(np.median(durations[1:])),
        "max_inference_seconds": max(durations),
        "peak_helper_rss_bytes": peak,
        "vector_dimensions": 384,
        "finite_unit_vectors": all(
            abs(float(np.linalg.norm(vector)) - 1) < 1e-5 for vector in vectors
        ),
        "repeat_max_abs_delta": repeat_delta,
        "padding_max_abs_delta": padding_delta,
        "long_description_characters": len(long_text),
        "long_description_tokens": len(long_ids),
        "long_description_chunks": len(ranges),
        "long_best_chunk": int(np.argmax(long_scores)),
        "long_last_chunk": len(ranges) - 1,
        "long_chunk_scores": long_scores,
        "max_description_characters": 5000,
        "max_description_tokens": len(boundary_ids),
        "max_description_chunks": len(boundary_ranges),
        "full_token_coverage": True,
        "controlled_cases": scenarios,
        "network_attempts": 0,
    }
    (LOCAL / "probe-result.json").write_text(json.dumps(report, indent=2) + "\n")
    event("complete")
    print(
        json.dumps({"status": "local_probe_complete", "inference_calls": calls}),
        flush=True,
    )


if __name__ == "__main__":
    main()
