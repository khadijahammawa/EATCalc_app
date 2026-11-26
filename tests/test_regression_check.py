"""Smoke test of scripts/regression_check.py with TotalSegmentator mocked."""

from __future__ import annotations

import shutil

import numpy as np

from backend import eat_core
from scripts import regression_check as rc
from tests.test_eat_core import _save


def test_record_then_compare_passes_and_detects_drift(tmp_path, monkeypatch):
    ct_dir = tmp_path / "cts"
    ct_dir.mkdir()
    ct = np.full((6, 6, 2), 40, dtype=np.int16)
    ct[1:5, 1:5, :] = -100
    _save(ct_dir / "P01_CT.nii.gz", ct)
    peri = np.zeros_like(ct, dtype=np.uint8)
    peri[1:5, 1:5, :] = 1
    peri_src = _save(tmp_path / "peri.nii.gz", peri, dtype=np.uint8)

    def fake(ct_path, out_dir, device="cpu"):
        dst = f"{out_dir}/pericardium.nii.gz"
        shutil.copy(peri_src, dst)
        return dst, None

    monkeypatch.setattr(eat_core, "run_totalsegmentation", fake)
    monkeypatch.setattr(eat_core, "get_totalsegmentator_version", lambda: "test")
    base = tmp_path / "baseline"
    assert rc.record(ct_dir, base, "cpu") == 0
    assert rc.compare(ct_dir, base, "cpu", 1.0, 0.99) == 0

    peri[1, 1:5, :] = 0                         # simulate a changed segmentation model
    _save(tmp_path / "peri.nii.gz", peri, dtype=np.uint8)
    assert rc.compare(ct_dir, base, "cpu", 1.0, 0.99) == 1
