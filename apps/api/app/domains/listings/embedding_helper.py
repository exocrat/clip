"""Owned offline CPU helper executable, never imported by API startup.

Runs only with the explicitly supplied local interpreter/model directory. Stdout
is bounded IPC; stderr is suppressed by the client. No Hub methods, DB/identity
state, logs with source, network or child process creation is allowed.
"""

import hashlib
import json
from pathlib import Path
import resource
import sys
import time
from typing import Any

# -I deliberately excludes ambient/script import paths. Add only this fixed,
# reviewed sibling directory; these shared modules use Python3.13-compatible stdlib.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from embedding_protocol import (
    INPUT_BYTES,
    OUTPUT_BYTES,
    VERSION,
    WINDOW,
    chunk_ranges,
    decode_frame,
    encode_frame,
    validate_request,
)
from embedding_types import default_pipeline_spec


def peak_rss() -> int:
    """Report native peak bytes; diagnostics remain private to the owning process."""
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def send(value: dict[str, Any]) -> None:
    """Write one bounded private frame and flush, never printing input/errors."""
    sys.stdout.buffer.write(encode_frame(value, OUTPUT_BYTES))
    sys.stdout.buffer.flush()


def main() -> int:
    """Verify local hashes/runtime, announce ready, then encode serial requests."""
    if len(sys.argv) != 3 or sys.argv[1] != "--model-dir":
        return 2

    def audit(name: str, args: tuple[object, ...]) -> None:
        """Keep network and descendant process attempts disabled inside the helper."""
        if name in {"socket.connect", "socket.bind", "subprocess.Popen"}:
            raise RuntimeError("Helper forbids network/children")

    sys.addaudithook(audit)
    try:
        spec = default_pipeline_spec()
        config = spec.encoding
        root = Path(sys.argv[2]).resolve()
        for name, key in (
            ("onnx/model.onnx", "model_sha256"),
            ("tokenizer.json", "tokenizer_sha256"),
        ):
            with (root / name).open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != config[key]:
                    raise ValueError("Model artifact mismatch")
        import numpy as np

        # The pinned ONNX runtime ships no py.typed marker; tensor shape and
        # finiteness are checked below at this external-library boundary.
        import onnxruntime as ort  # type: ignore[import-untyped]
        import tokenizers
        from tokenizers import Tokenizer

        if (np.__version__, ort.__version__, tokenizers.__version__) != (
            config["numpy"],
            config["onnxruntime"],
            config["tokenizers"],
        ):
            raise ValueError("Runtime pin mismatch")
        tokenizer = Tokenizer.from_file(str(root / "tokenizer.json"))
        tokenizer.no_truncation()
        tokenizer.no_padding()
        cls = tokenizer.token_to_id("[CLS]")
        sep = tokenizer.token_to_id("[SEP]")
        if cls is None or sep is None:
            raise ValueError("Missing special tokens")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.log_severity_level = 4
        session = ort.InferenceSession(
            str(root / "onnx/model.onnx"),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        if {entry.name for entry in session.get_inputs()} != {
            "input_ids",
            "attention_mask",
            "token_type_ids",
        }:
            raise ValueError("Unexpected tensors")
        pipeline_id = spec.pipeline_id.hex()
        import os

        send(
            {
                "v": VERSION,
                "kind": "ready",
                "pipeline_id": pipeline_id,
                "pid": os.getpid(),
                "python_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
                "runtime": {
                    "numpy": np.__version__,
                    "onnxruntime": ort.__version__,
                    "tokenizers": tokenizers.__version__,
                },
                "threads": 1,
                "offline": True,
                "peak_rss_bytes": peak_rss(),
            }
        )
    except Exception:
        send({"v": VERSION, "kind": "fatal", "code": "helper_unavailable"})
        return 2
    while True:
        raw = sys.stdin.buffer.readline(INPUT_BYTES + 1)
        if not raw:
            return 0
        try:
            request = decode_frame(raw, INPUT_BYTES)
            validate_request(request, pipeline_id)
        except Exception:
            send({"v": VERSION, "kind": "fatal", "code": "invalid_request"})
            return 2
        identifier = request["request_id"]
        operation = request["operation"]
        begin = time.monotonic()
        parts = []

        def encode(ids: list[int], kind: str, ordinal: int) -> None:
            """Announce each window so the parent enforces a separate 5s deadline."""
            if len(ids) > WINDOW:
                raise ValueError("Token window exceeds bound")
            if time.monotonic() - begin > 20:
                raise TimeoutError
            send(
                {
                    "v": VERSION,
                    "kind": "progress",
                    "request_id": identifier,
                    "pipeline_id": pipeline_id,
                    "part_kind": kind,
                    "ordinal": ordinal,
                    "peak_rss_bytes": peak_rss(),
                }
            )
            started = time.monotonic()
            values = np.array([[cls, *ids, sep]], dtype=np.int64)
            mask = np.ones_like(values)
            output = session.run(
                None,
                {
                    "input_ids": values,
                    "attention_mask": mask,
                    "token_type_ids": np.zeros_like(values),
                },
            )[0]
            if output.shape != (1, len(ids) + 2, 384) or not np.isfinite(output).all():
                raise ValueError("Invalid tensor")
            # No padding in this batch; the all-one attention mask means the
            # canonical masked mean includes CLS/SEP and every content token.
            pooled = output.mean(axis=1)[0]
            norm = np.linalg.norm(pooled)
            if not np.isfinite(norm) or norm <= 0:
                raise ValueError("Invalid norm")
            vector = (pooled / norm).tolist()
            if time.monotonic() - started > 5:
                raise TimeoutError
            parts.append({"kind": kind, "ordinal": ordinal, "vector": vector})

        try:
            title_tokens = description_tokens = query_tokens = None
            if operation == "query":
                ids = tokenizer.encode(request["text"], add_special_tokens=False).ids
                query_tokens = len(ids)
                ranges: tuple[tuple[int, int], ...] = ((0, len(ids)),)
                encode(ids, "query", 0)
            else:
                ids = tokenizer.encode(request["title"], add_special_tokens=False).ids
                title_tokens = len(ids)
                encode(ids, "title", 0)
                ids = tokenizer.encode(
                    request["description"], add_special_tokens=False
                ).ids
                description_tokens = len(ids)
                ranges = chunk_ranges(len(ids))
                for ordinal, (start, end) in enumerate(ranges):
                    encode(ids[start:end], "description", ordinal)
            send(
                {
                    "v": VERSION,
                    "kind": "result",
                    "request_id": identifier,
                    "pipeline_id": pipeline_id,
                    "operation": operation,
                    "parts": parts,
                    "title_tokens": title_tokens,
                    "description_tokens": description_tokens,
                    "query_tokens": query_tokens,
                    "ranges": [list(pair) for pair in ranges],
                    "peak_rss_bytes": peak_rss(),
                }
            )
        except Exception as error:
            code = "timeout" if isinstance(error, TimeoutError) else "invalid_vectors"
            send(
                {
                    "v": VERSION,
                    "kind": "error",
                    "request_id": identifier,
                    "pipeline_id": pipeline_id,
                    "code": code,
                }
            )


if __name__ == "__main__":
    raise SystemExit(main())
