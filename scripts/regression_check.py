"""Real-data regression check for EATCalc-classic.

Detects silent changes in EATCalc output after upgrading TotalSegmentator, its
model weights, or EATCalc itself. Use a fixed set of 5-10 reference CTs.

  # 1) once, on the current (trusted) setup
  python -m scripts.regression_check record  --ct-dir D:/eat_reference_cts --baseline eval/baseline
  # 2) after any upgrade
  python -m scripts.regression_check compare --ct-dir D:/eat_reference_cts --baseline eval/baseline

`compare` reruns TotalSegmentator in a fresh folder and reports, per case, the EAT
volume difference and the Dice overlap of the new vs baseline pericardium mask.
Exit code 1 if any case exceeds the tolerances.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np

from backend import eat_core


def _cases(ct_dir: Path) -> list[Path]:
    cts = sorted(p for p in ct_dir.iterdir() if p.name.lower().endswith((".nii", ".nii.gz")))
    if not cts:
        sys.exit(f"No NIfTI files found in {ct_dir}")
    return cts


def _case_id(ct: Path) -> str:
    return ct.name[:-7] if ct.name.lower().endswith(".nii.gz") else ct.stem


def _run_case(ct: Path, work: Path, device: str) -> tuple[dict, str]:
    work.mkdir(parents=True, exist_ok=True)
    peri, _ = eat_core.run_totalsegmentation(str(ct), str(work), device=device)
    res = eat_core.compute_eat_and_stats(
        str(ct), peri, eat_core.DEFAULT_LOW_HU, eat_core.DEFAULT_HIGH_HU, return_arrays=False
    )
    stats = {k: res[k] for k in ("eat_volume", "mean_hu", "std_hu")}
    return stats, peri


def dice(a: np.ndarray, b: np.ndarray) -> float:
    denom = a.sum() + b.sum()
    return 1.0 if denom == 0 else float(2 * np.logical_and(a, b).sum() / denom)


def record(ct_dir: Path, baseline: Path, device: str) -> int:
    baseline.mkdir(parents=True, exist_ok=True)
    summary = {"provenance": eat_core.get_provenance(device=device), "cases": {}}
    for ct in _cases(ct_dir):
        cid = _case_id(ct)
        stats, peri = _run_case(ct, baseline / cid, device)
        summary["cases"][cid] = {**stats, "ct_sha256": eat_core.file_sha256(str(ct)),
                                 "pericardium": str(Path(cid) / Path(peri).name)}
        print(f"{cid}: EAT {stats['eat_volume']:.2f} ml")
    (baseline / "baseline.json").write_text(json.dumps(summary, indent=2))
    print(f"Baseline written to {baseline / 'baseline.json'}")
    return 0


def compare(ct_dir: Path, baseline: Path, device: str, vol_tol_pct: float, dice_tol: float) -> int:
    base = json.loads((baseline / "baseline.json").read_text())
    print("Baseline:", {k: base["provenance"].get(k) for k in ("method_version", "totalsegmentator_version")})
    print("Current: ", {k: eat_core.get_provenance().get(k) for k in ("method_version", "totalsegmentator_version")})
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for ct in _cases(ct_dir):
            cid = _case_id(ct)
            ref = base["cases"].get(cid)
            if ref is None:
                print(f"{cid}: not in baseline, skipped")
                continue
            if eat_core.file_sha256(str(ct)) != ref["ct_sha256"]:
                print(f"{cid}: CT file differs from baseline input -> FAIL")
                failures += 1
                continue
            stats, peri = _run_case(ct, Path(tmp) / cid, device)
            d_pct = 100.0 * (stats["eat_volume"] - ref["eat_volume"]) / max(ref["eat_volume"], 1e-9)
            dsc = dice(nib.load(peri).get_fdata() > 0,
                       nib.load(str(baseline / ref["pericardium"])).get_fdata() > 0)
            ok = abs(d_pct) <= vol_tol_pct and dsc >= dice_tol
            failures += not ok
            print(f"{cid}: EAT {ref['eat_volume']:.2f} -> {stats['eat_volume']:.2f} ml "
                  f"({d_pct:+.2f}%), pericardium Dice {dsc:.4f}  {'OK' if ok else 'FAIL'}")
    print(f"{failures} case(s) outside tolerance (|dV| <= {vol_tol_pct}%, Dice >= {dice_tol}).")
    return 1 if failures else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["record", "compare"])
    ap.add_argument("--ct-dir", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--vol-tol-pct", type=float, default=1.0)
    ap.add_argument("--dice-tol", type=float, default=0.99)
    a = ap.parse_args()
    if a.mode == "record":
        sys.exit(record(a.ct_dir, a.baseline, a.device))
    sys.exit(compare(a.ct_dir, a.baseline, a.device, a.vol_tol_pct, a.dice_tol))


if __name__ == "__main__":
    main()
