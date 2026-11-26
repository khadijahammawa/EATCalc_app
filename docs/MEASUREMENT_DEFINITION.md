# EATCalc-classic 1.0.0: measurement definition

## What EATCalc reports

**Intrapericardial adipose tissue volume (ml)**, used as a reproducible CT proxy for
epicardial adipose tissue (EAT), together with the mean and SD (population, ddof = 0)
of the HU values of the included voxels.

It is **not** a manual-equivalent EAT read. Report it as
"EAT (EATCalc-classic 1.0.0; intrapericardial fat, −190 to −30 HU)".

## Algorithm

1. **Pericardium region**: TotalSegmentator task `trunk_cavities`, label `pericardium`
   (open-weights task; nnU-Net run at 1.5 mm isotropic internally, per TotalSegmentator
   2.18 config, with output in the native CT grid).
2. **Fat**: voxels with `−190 ≤ HU ≤ −30` (both limits inclusive).
3. **EAT mask** = region from step 1 AND fat from step 2. No smoothing, erosion,
   connected-component filtering or resampling.
4. **Volume** = voxel count × voxel volume from the NIfTI header zooms.

Code: `backend/eat_core.py` (`compute_eat_mask` is the single implementation).
Locked by: `tests/test_eat_core.py`.

## Provenance stored with every result

`eat_provenance.json` (per analysis/participant) and the batch manifest record:
method name and version, HU window and whether it is the default, TotalSegmentator
version, EATCalc git commit (`-dirty` if uncommitted changes), device, Python, numpy and
nibabel versions, and the SHA-256 of the input CT.

Cached TotalSegmentator masks are reused only when they were produced from the same CT
(by content hash), the same task and the same TotalSegmentator version.

## Rules for comparable numbers

- Only compare values with the same `method_version` **and** `totalsegmentator_version`.
  After any upgrade, run `scripts/regression_check.py compare` on the reference cases.
- A non-default HU window (`hu_window_is_default: false`) gives a different measurement.
  Don't pool it with default-window results.
- Changing the algorithm means bumping `METHOD_VERSION` and updating the regression tests.

## Known sources of variation (not yet quantified; roadmap steps 1–2)

- Placement of the pericardium boundary by TotalSegmentator (main expected error source):
  paracardial fat included or EAT missed at the atrioventricular grooves, apex and great vessels.
- Partial-volume voxels at the pericardial boundary and at myocardium/blood interfaces.
  Image noise on low-dose CT can push non-fat voxels below −30 HU.
- Slice thickness, reconstruction kernel, kVp, iodinated contrast, ECG gating and motion
  (non-gated PET/CT vs. dedicated cardiac CT).
- Agreement with manual expert EAT segmentation has not been established yet.
- Some public datasets use −200 to −30 HU. Match the window when benchmarking.
