"""Regression tests for the EATCalc-classic measurement (backend/eat_core.py).

These use small synthetic volumes with a known answer, so they run without
TotalSegmentator. They lock the measurement definition: if any of these fail
after a code change, the numbers EATCalc reports have changed.

Run from the repo root:  python -m pytest tests -q
"""

from __future__ import annotations

import numpy as np
import nibabel as nib
import pytest

from backend import eat_core


ZOOMS = (0.8, 0.8, 2.5)  # mm -> voxel volume 1.6 mm^3 = 0.0016 ml


def _affine(zooms=ZOOMS):
    return np.diag([*zooms, 1.0])


def _save(path, data, zooms=ZOOMS, dtype=np.int16):
    img = nib.Nifti1Image(np.asarray(data, dtype=dtype), _affine(zooms))
    img.header.set_zooms(zooms)
    nib.save(img, str(path))
    return str(path)


@pytest.fixture()
def phantom(tmp_path):
    """10x10x4 CT with known HU values inside a known pericardium box."""
    ct = np.full((10, 10, 4), 40, dtype=np.int16)          # soft tissue
    peri = np.zeros_like(ct, dtype=np.uint8)
    peri[2:8, 2:8, :] = 1                                   # 6*6*4 = 144 voxels

    # Inside pericardium: place voxels at and around the window edges.
    ct[2, 2, 0] = -190   # low edge  -> included (inclusive)
    ct[2, 3, 0] = -30    # high edge -> included (inclusive)
    ct[2, 4, 0] = -191   # just below -> excluded
    ct[2, 5, 0] = -29    # just above -> excluded
    ct[3, 2:8, 1] = -100 # 6 fat voxels
    # Outside pericardium: fat that must NOT be counted (paracardial).
    ct[0, :, :] = -100   # 40 voxels outside

    ct_path = _save(tmp_path / "ct.nii.gz", ct)
    peri_path = _save(tmp_path / "pericardium.nii.gz", peri, dtype=np.uint8)
    expected_voxels = 2 + 6
    expected_values = np.array([-190, -30] + [-100] * 6, dtype=float)
    return ct_path, peri_path, expected_voxels, expected_values, tmp_path


def test_default_window_is_locked():
    assert eat_core.DEFAULT_LOW_HU == -190.0
    assert eat_core.DEFAULT_HIGH_HU == -30.0
    assert eat_core.PERICARDIUM_TASK == "trunk_cavities"


def test_eat_volume_and_hu_stats(phantom):
    ct_path, peri_path, n_vox, values, _ = phantom
    res = eat_core.compute_eat_and_stats(ct_path, peri_path, -190, -30, return_arrays=True)

    voxel_ml = np.prod(ZOOMS) / 1000.0
    assert res["voxel_volume_ml"] == pytest.approx(voxel_ml)
    assert res["eat_mask"].sum() == n_vox
    assert res["eat_volume"] == pytest.approx(n_vox * voxel_ml)
    assert res["mean_hu"] == pytest.approx(values.mean())
    assert res["std_hu"] == pytest.approx(values.std())  # population SD (ddof=0)
    assert res["total_slices"] == 4


def test_window_edges_inclusive_and_outside_fat_excluded(phantom):
    ct_path, peri_path, _, _, _ = phantom
    res = eat_core.compute_eat_and_stats(ct_path, peri_path, -190, -30)
    m = res["eat_mask"]
    assert m[2, 2, 0] and m[2, 3, 0]
    assert not m[2, 4, 0] and not m[2, 5, 0]
    assert not m[0].any()


def test_empty_mask_returns_zeros(tmp_path):
    ct = np.full((4, 4, 2), 40, dtype=np.int16)
    peri = np.ones_like(ct, dtype=np.uint8)
    res = eat_core.compute_eat_and_stats(
        _save(tmp_path / "ct.nii.gz", ct),
        _save(tmp_path / "p.nii.gz", peri, dtype=np.uint8),
        -190, -30,
    )
    assert res["eat_volume"] == 0.0
    assert res["mean_hu"] == 0.0 and res["std_hu"] == 0.0


def test_shape_mismatch_raises(tmp_path):
    ct_path = _save(tmp_path / "ct.nii.gz", np.zeros((4, 4, 2)))
    peri_path = _save(tmp_path / "p.nii.gz", np.zeros((4, 4, 3)), dtype=np.uint8)
    with pytest.raises(ValueError):
        eat_core.compute_eat_and_stats(ct_path, peri_path, -190, -30)


def test_saved_mask_matches_computed_mask(phantom):
    ct_path, peri_path, _, _, tmp_path = phantom
    res = eat_core.compute_eat_and_stats(ct_path, peri_path, -190, -30)
    out = eat_core.save_eat_mask_nifti(str(tmp_path / "out"), ct_path, peri_path, -190, -30)
    assert out.endswith("EAT_mask_-190_-30.nii.gz")
    saved = nib.load(out)
    np.testing.assert_array_equal(saved.get_fdata() > 0, res["eat_mask"])
    np.testing.assert_allclose(saved.affine, nib.load(ct_path).affine)


def test_myocardium_fat_fraction(tmp_path):
    ct = np.full((4, 4, 1), 40, dtype=np.int16)
    ct[0, :, 0] = -100                       # 4 of 16 voxels fat
    myo = np.ones_like(ct, dtype=np.uint8)
    ff = eat_core.compute_myocardium_ff(
        _save(tmp_path / "ct.nii.gz", ct), _save(tmp_path / "m.nii.gz", myo, dtype=np.uint8), -190, -30
    )
    assert ff == pytest.approx(0.25)
    assert eat_core.compute_myocardium_ff(str(tmp_path / "ct.nii.gz"), None, -190, -30) is None


def test_segmentation_cache_rejects_other_ct(tmp_path, monkeypatch):
    """A pericardium cached from patient A must not be reused for patient B."""
    monkeypatch.setattr(eat_core, "get_totalsegmentator_version", lambda: "2.x-test")
    ct_a = _save(tmp_path / "a.nii.gz", np.zeros((4, 4, 2)))
    ct_b = _save(tmp_path / "b.nii.gz", np.ones((4, 4, 2)))
    eat_core._write_seg_cache_record(str(tmp_path), ct_a, eat_core.PERICARDIUM_TASK)

    assert eat_core._seg_cache_is_valid(str(tmp_path), ct_a, eat_core.PERICARDIUM_TASK)
    assert not eat_core._seg_cache_is_valid(str(tmp_path), ct_b, eat_core.PERICARDIUM_TASK)
    assert not eat_core._seg_cache_is_valid(str(tmp_path), ct_a, "heartchambers_highres")

    monkeypatch.setattr(eat_core, "get_totalsegmentator_version", lambda: "3.x-test")
    assert not eat_core._seg_cache_is_valid(str(tmp_path), ct_a, eat_core.PERICARDIUM_TASK)


def test_legacy_cache_without_record_is_stale(tmp_path):
    ct = _save(tmp_path / "ct.nii.gz", np.zeros((4, 4, 2)))
    assert not eat_core._seg_cache_is_valid(str(tmp_path), ct, eat_core.PERICARDIUM_TASK)


def test_provenance_fields(monkeypatch):
    monkeypatch.setattr(eat_core, "get_totalsegmentator_version", lambda: "2.x-test")
    prov = eat_core.get_provenance(-190, -30, device="cpu")
    assert prov["method"] == "EATCalc-classic"
    assert prov["hu_window"] == [-190.0, -30.0] and prov["hu_window_is_default"]
    assert prov["totalsegmentator_version"] == "2.x-test"
    assert not eat_core.get_provenance(-200, -30)["hu_window_is_default"]
