"""
Core EAT analysis functions shared by GUI and backend.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, Optional, Tuple

import numpy as np
import nibabel as nib


def run_totalsegmentation(ct_path: str, out_dir: str, device: str = "cpu") -> tuple[str, Optional[str]]:
    """Run TotalSegmentator to produce pericardium mask and (optionally) myocardium mask.

    Returns a tuple `(pericardium_path, myocardium_path_or_none)`.
    If pericardium already exists, skips running. Myocardium path is detected
    by looking for files with 'myocardium' in the filename in the output directory.
    """
    pericardium_path = os.path.join(out_dir, "pericardium.nii.gz")
    myocardium_path: Optional[str] = None
    if os.path.exists(pericardium_path):
        # Try to discover myocardium file next to the pericardium mask
        myocardium_path = _find_label(out_dir, "myocardium")
        return pericardium_path, myocardium_path

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
            pericardium_path = found
        else:
            raise FileNotFoundError("Could not find pericardium.nii.gz after TotalSegmentator.")

    myocardium_path = _find_label(out_dir, "myocardium")
    return pericardium_path, myocardium_path


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


def run_totalsegmentation_task(
    ct_path: str, out_dir: str, task: str, device: str = "cpu", label_hint: str = "myocardium"
) -> Optional[str]:
    """Run TotalSegmentator for a specific `task` into `out_dir/task` and
    return the first file matching `label_hint` (case-insensitive), or None.
    If the mask already exists, the function will skip running TotalSegmentator.
    """
    task_dir = os.path.join(out_dir, task)
    # Try to find the label before running
    found = None
    if os.path.exists(task_dir):
        found = _find_label(task_dir, label_hint)
        if found:
            return found

    os.makedirs(task_dir, exist_ok=True)

    cmd = [
        "TotalSegmentator",
        "-i",
        ct_path,
        "-o",
        task_dir,
        "--task",
        task,
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
            "TotalSegmentator (task={}) failed (exit {}).\n\nCommand:\n{}".format(
                task, exc.returncode, " ".join(cmd)
            )
        ) from exc

    return _find_label(task_dir, label_hint)


def compute_myocardium_ff(ct_path: str, myocardium_path: Optional[str], low_hu: float, high_hu: float) -> Optional[float]:
    """Compute fat fraction inside myocardium mask.

    Returns fraction 0..1 or None if myocardium mask not available or shapes mismatch.
    """
    if not myocardium_path:
        return None
    try:
        ct_img = nib.load(ct_path)
        ct_data = ct_img.get_fdata()
        myo_img = nib.load(myocardium_path)
        myo_data = myo_img.get_fdata()
    except Exception:
        return None

    if myo_data.shape != ct_data.shape:
        return None

    myocardium_mask = myo_data > 0
    total = int(np.sum(myocardium_mask))
    if total == 0:
        return 0.0

    fat_mask = np.logical_and(myocardium_mask, np.logical_and(ct_data >= low_hu, ct_data <= high_hu))
    fat_count = int(np.sum(fat_mask))
    return float(fat_count / total)


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
    ff_myocardium: Optional[float] = None,
) -> str:
    """Write a one-line CSV summary and return the file path."""
    os.makedirs(out_dir, exist_ok=True)
    stats_csv = os.path.join(out_dir, "eat_statistics.csv")
    with open(stats_csv, "w", encoding="utf-8") as handle:
        handle.write("CT,Pericardium,EAT_Volume_ml,Mean_HU,Std_HU,Low_HU,High_HU,FF_Myocardium\n")
        handle.write(
            "{},{},{:.3f},{:.3f},{:.3f},{},{},{}\n".format(
                ct_path,
                pericardium_path,
                eat_volume,
                mean_hu,
                std_hu,
                low_hu,
                high_hu,
                "" if ff_myocardium is None else f"{ff_myocardium:.6f}",
            )
        )
    return stats_csv


def _find_pericardium(out_dir: str) -> Optional[str]:
    for root, _, files in os.walk(out_dir):
        for filename in files:
            if filename.lower() == "pericardium.nii.gz":
                return os.path.join(root, filename)
    return None


def _find_label(out_dir: str, label: str) -> Optional[str]:
    """Search `out_dir` for a file whose name contains `label` (case-insensitive).

    Returns the first matching path or None if not found.
    """
    lower_label = label.lower()
    for root, _, files in os.walk(out_dir):
        for filename in files:
            if lower_label in filename.lower():
                # Prefer exact .nii or .nii.gz files
                if filename.lower().endswith(".nii") or filename.lower().endswith(".nii.gz"):
                    return os.path.join(root, filename)
                return os.path.join(root, filename)
    return None
