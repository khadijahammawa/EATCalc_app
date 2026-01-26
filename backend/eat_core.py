"""
Core EAT analysis functions shared by GUI and backend.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, Optional, Tuple

import numpy as np
import nibabel as nib


def run_totalsegmentation(ct_path: str, out_dir: str, device: str = "cpu") -> str:
    """Run TotalSegmentator to produce pericardium mask.

    Returns pericardium.nii.gz path. If already exists, skips running.
    """
    pericardium_path = os.path.join(out_dir, "pericardium.nii.gz")
    if os.path.exists(pericardium_path):
        return pericardium_path

    os.makedirs(out_dir, exist_ok=True)

    cmd = [
        "TotalSegmentator",
        "-i",
        ct_path,
        "-o",
        out_dir,
        "--task",
        "trunk_cavities",
        "--device",
        device,
    ]

    env = os.environ.copy()
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["OMP_NUM_THREADS"] = "1"

    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "TotalSegmentator failed (exit {}).\n\nCommand:\n{}".format(
                exc.returncode, " ".join(cmd)
            )
        ) from exc

    if not os.path.exists(pericardium_path):
        found = _find_pericardium(out_dir)
        if found:
            return found
        raise FileNotFoundError("Could not find pericardium.nii.gz after TotalSegmentator.")

    return pericardium_path


def compute_eat_and_stats(
    ct_path: str,
    pericardium_path: str,
    low_hu: float,
    high_hu: float,
    *,
    return_arrays: bool = True,
) -> Dict[str, Any]:
    """Compute EAT mask and stats from CT + pericardium mask."""
    ct_img = nib.load(ct_path)
    ct_data = ct_img.get_fdata()
    peri_img = nib.load(pericardium_path)
    peri_data = peri_img.get_fdata()

    if ct_data.ndim != 3:
        raise ValueError("CT data must be 3D. Got shape {}".format(ct_data.shape))

    if peri_data.shape != ct_data.shape:
        raise ValueError(
            "Mask shape {} does not match CT shape {}.".format(
                peri_data.shape, ct_data.shape
            )
        )

    pericardium_mask = peri_data > 0
    eat_mask = np.logical_and(
        pericardium_mask,
        np.logical_and(ct_data >= low_hu, ct_data <= high_hu),
    )

    zooms = tuple(float(z) for z in ct_img.header.get_zooms())
    voxel_volume_ml = float(np.prod(zooms) / 1000.0)
    eat_volume = float(np.sum(eat_mask) * voxel_volume_ml)

    eat_values = ct_data[eat_mask]
    mean_hu = float(eat_values.mean()) if eat_values.size else 0.0
    std_hu = float(eat_values.std()) if eat_values.size else 0.0

    results: Dict[str, Any] = {
        "eat_volume": eat_volume,
        "mean_hu": mean_hu,
        "std_hu": std_hu,
        "voxel_volume_ml": voxel_volume_ml,
        "zooms": zooms,
        "total_slices": int(ct_data.shape[2]),
        "mid_slice": int(ct_data.shape[2] // 2),
    }

    if return_arrays:
        results["ct_data"] = ct_data
        results["pericardium_mask"] = pericardium_mask
        results["eat_mask"] = eat_mask

    return results


def _format_hu_for_filename(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def save_eat_mask_nifti(
    out_dir: str,
    ct_path: str,
    pericardium_path: str,
    low_hu: float,
    high_hu: float,
) -> str:
    """Save EAT mask as NIfTI using CT affine/header for alignment."""
    os.makedirs(out_dir, exist_ok=True)

    ct_img = nib.load(ct_path)
    ct_data = ct_img.get_fdata()
    peri_img = nib.load(pericardium_path)
    peri_data = peri_img.get_fdata()

    if ct_data.ndim != 3:
        raise ValueError("CT data must be 3D. Got shape {}".format(ct_data.shape))

    if peri_data.shape != ct_data.shape:
        raise ValueError(
            "Mask shape {} does not match CT shape {}.".format(
                peri_data.shape, ct_data.shape
            )
        )

    pericardium_mask = peri_data > 0
    eat_mask = np.logical_and(
        pericardium_mask,
        np.logical_and(ct_data >= low_hu, ct_data <= high_hu),
    )

    header = ct_img.header.copy()
    header.set_data_dtype(np.uint8)
    mask_img = nib.Nifti1Image(eat_mask.astype(np.uint8), ct_img.affine, header=header)

    qform, qcode = ct_img.header.get_qform(coded=True)
    sform, scode = ct_img.header.get_sform(coded=True)
    if qform is not None:
        mask_img.set_qform(qform, int(qcode))
    if sform is not None:
        mask_img.set_sform(sform, int(scode))

    filename = "EAT_mask_{}_{}.nii.gz".format(
        _format_hu_for_filename(low_hu),
        _format_hu_for_filename(high_hu),
    )
    out_path = os.path.join(out_dir, filename)
    nib.save(mask_img, out_path)
    return out_path


def save_stats_csv(
    out_dir: str,
    ct_path: str,
    pericardium_path: str,
    low_hu: float,
    high_hu: float,
    *,
    eat_volume: float,
    mean_hu: float,
    std_hu: float,
) -> str:
    """Write a one-line CSV summary and return the file path."""
    os.makedirs(out_dir, exist_ok=True)
    stats_csv = os.path.join(out_dir, "eat_statistics.csv")
    with open(stats_csv, "w", encoding="utf-8") as handle:
        handle.write("CT,Pericardium,EAT_Volume_ml,Mean_HU,Std_HU,Low_HU,High_HU\n")
        handle.write(
            "{},{},{:.3f},{:.3f},{:.3f},{},{}\n".format(
                ct_path,
                pericardium_path,
                eat_volume,
                mean_hu,
                std_hu,
                low_hu,
                high_hu,
            )
        )
    return stats_csv


def _find_pericardium(out_dir: str) -> Optional[str]:
    for root, _, files in os.walk(out_dir):
        for filename in files:
            if filename.lower() == "pericardium.nii.gz":
                return os.path.join(root, filename)
    return None
