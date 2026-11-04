"""Actual staged module sets must include dependencies the source tree can hide."""

from pathlib import Path
import pytest
from scripts.evaluation.k6.real_run_coordinator import (
    NFR_MODULES,
    verify_import_closure,
)
from scripts.evaluation.k6.comparison_stage_run import MODULES

ROOT = Path(__file__).resolve().parents[2] / "scripts/evaluation/k6"


def test_every_real_run_bundle_contains_its_static_relative_imports():
    for names in [MODULES, *NFR_MODULES.values()]:
        verify_import_closure({name: (ROOT / name).read_bytes() for name in names})


def test_missing_transitive_core_dependency_is_rejected_before_execution():
    modules = {
        name: (ROOT / name).read_bytes()
        for name in NFR_MODULES["nfr-03"]
        if name != "core.js"
    }
    with pytest.raises(ValueError, match="load_module_dependency_missing"):
        verify_import_closure(modules)
