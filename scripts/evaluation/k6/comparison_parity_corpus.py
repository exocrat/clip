"""Build a non-executable search-parity corpus without inventing rankings.

This draft does not verify deployment, human review or the proposed protocol.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from scripts.evaluation.k6.prepare_comparison_corpus import (
    FINGERPRINT,
    FROZEN,
    LABELS,
    build_corpus,
)

FIELDS = {
    "format_version",
    "dataset_fingerprint",
    "schema_version",
    "search_contract_revision",
    "search_implementation_revision",
    "model_revision",
}


def build_parity_corpus(binding: Any, expected_revision: str) -> dict[str, Any]:
    """Bind the existing ten cases to search inputs without result order."""
    if not isinstance(expected_revision, str) or not re.fullmatch(
        r"[0-9a-f]{40}", expected_revision
    ):
        raise ValueError("invalid_search_revision")
    if not isinstance(binding, dict) or set(binding) != FIELDS:
        raise ValueError("invalid_binding_shape")
    frozen = json.loads(FROZEN.read_text())
    labels = json.loads(LABELS.read_text())
    if (
        type(binding["format_version"]) is not int
        or binding["format_version"] != 2
        or binding["dataset_fingerprint"] != FINGERPRINT
        or binding["schema_version"] != frozen["schema_version"]
        or binding["search_contract_revision"] != labels["search_contract_revision"]
        or binding["search_implementation_revision"] != expected_revision
        or binding["model_revision"] != frozen["model"]["revision"]
    ):
        raise ValueError("search_binding_mismatch")
    corpus = build_corpus()
    searches = [case for case in corpus["cases"] if case["request"]["kind"] == "search"]
    if len(searches) != 3 or any(case["expected"] is not None for case in searches):
        raise ValueError("invalid_search_draft")
    for case in searches:
        case["relevance_reference"][
            "ordered_response_state"
        ] = "not_required_in_proposed_parity_protocol"
    corpus["status"] = "parity_corpus_draft_not_executable"
    corpus["purpose"] = "EXP-02 proposed parity preparation; not authorization to run"
    corpus["review"]["hybrid"] = "search inputs bound; parity and owner review pending"
    corpus["review"]["search_binding"] = {
        **binding,
        "canonical_json_sha256": hashlib.sha256(
            json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    corpus["review"]["measurement_enabled"] = False
    return corpus


def main() -> None:
    """Read a bounded local binding and exclusively create a separate draft."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("binding", type=Path)
    parser.add_argument("--search-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
            raise ValueError("safe_file_access_unavailable")
        fd = os.open(args.binding, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("regular_binding_required")
            raw = source.read(64_001)
        if len(raw) > 64_000:
            raise ValueError("binding_too_large")
        corpus = build_parity_corpus(json.loads(raw), args.search_revision)
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(corpus, output, sort_keys=True, indent=2, ensure_ascii=False)
            output.write("\n")
        print(json.dumps({"draft_created": True, "measurement_authorized": False}))
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        parser.exit(2, "Parity corpus preparation failed; no workload started\n")


if __name__ == "__main__":
    main()
