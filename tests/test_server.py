"""End-to-end API test with TotalSegmentator mocked (no GPU / model weights needed)."""

from __future__ import annotations

import json
import shutil

import numpy as np
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from backend import server  # noqa: E402
from tests.test_eat_core import _save  # noqa: E402


def test_analyze_writes_provenance(tmp_path, monkeypatch):
    ct = np.full((6, 6, 2), 40, dtype=np.int16)
    ct[1:5, 1:5, 0] = -100                      # 16 fat voxels inside pericardium
    peri = np.zeros_like(ct, dtype=np.uint8)
    peri[1:5, 1:5, :] = 1
    src = tmp_path / "src"
    src.mkdir()
    ct_file = _save(src / "P01_CT.nii.gz", ct)
    peri_file = _save(src / "pericardium.nii.gz", peri, dtype=np.uint8)

    def fake_totalseg(ct_path, out_dir, device="cpu"):
        dst = f"{out_dir}/pericardium.nii.gz"
        shutil.copy(peri_file, dst)
        return dst, None

    monkeypatch.setattr(server, "run_totalsegmentation", fake_totalseg)
    monkeypatch.setattr(server, "run_totalsegmentation_task", lambda *a, **k: None)
    monkeypatch.setattr(server, "get_provenance",
                        lambda lo, hi, device=None: {"method_version": "1.0.0", "hu_window": [lo, hi]})

    out_dir = tmp_path / "out"
    with open(ct_file, "rb") as fh:
        r = TestClient(server.app).post(
            "/api/analyze",
            files={"file": ("P01_CT.nii.gz", fh, "application/gzip")},
            data={"output_path": str(out_dir)},
        )
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    voxel_ml = 0.8 * 0.8 * 2.5 / 1000
    assert res["eatVolume"] == pytest.approx(16 * voxel_ml)
    prov = json.loads((out_dir / "eat_provenance.json").read_text())
    assert prov["hu_window"] == [-190.0, -30.0]
    assert len(prov["ct_sha256"]) == 64 and prov["ct_file"] == "P01_CT.nii.gz"
