from __future__ import annotations

from pathlib import Path
import base64
import csv
import json
import re
from datetime import datetime, timezone
import shutil
from io import BytesIO
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import nibabel as nib
from PIL import Image

from backend.eat_core import (
    compute_eat_and_stats,
    run_totalsegmentation,
    save_eat_mask_nifti,
    save_stats_csv,
)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"
ANALYSIS_CACHE: dict[str, dict[str, object]] = {}

_ID_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")

app = FastAPI(title="EAT Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)


def _resolve_output_dir(output_path: Optional[str]) -> Path:
    if output_path:
        return Path(output_path).expanduser().resolve()
    return DEFAULT_OUTPUT_DIR


def _nifti_stem(filename: str) -> str:
    name = Path(filename).name
    lower = name.lower()
    if lower.endswith(".nii.gz"):
        return name[:-7]
    if lower.endswith(".nii"):
        return name[:-4]
    return Path(name).stem


def _derive_participant_id(filename: str) -> str:
    stem = _nifti_stem(filename)
    if "_" in stem:
        prefix = stem.split("_", 1)[0]
        if prefix:
            return prefix
    return stem or "participant"


def _sanitize_participant_id(value: str) -> str:
    cleaned = _ID_SAFE_PATTERN.sub("_", value).strip("._-")
    return cleaned or "participant"


def _unique_participant_dir(output_dir: Path, base_name: str, used: set[str]) -> tuple[Path, str]:
    index = 0
    while True:
        suffix = "" if index == 0 else f"_{index + 1}"
        name = f"{base_name}{suffix}"
        candidate = output_dir / name
        if name not in used and not candidate.exists():
            used.add(name)
            return candidate, name
        index += 1


def _write_batch_stats_csv(csv_path: Path, rows: list[dict[str, object]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Participant",
                "CT",
                "Pericardium",
                "EAT_Mask",
                "EAT_Volume_ml",
                "Mean_HU",
                "Std_HU",
                "Low_HU",
                "High_HU",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.get("participant_id", ""),
                    row.get("ct_path", ""),
                    row.get("pericardium_path", ""),
                    row.get("eat_mask_path", ""),
                    "{:.3f}".format(float(row.get("eat_volume", 0.0))),
                    "{:.3f}".format(float(row.get("mean_hu", 0.0))),
                    "{:.3f}".format(float(row.get("std_hu", 0.0))),
                    row.get("low_hu", ""),
                    row.get("high_hu", ""),
                ]
            )


def _analysis_or_404(analysis_id: str) -> dict[str, object]:
    analysis = ANALYSIS_CACHE.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found. Run analysis again.")
    return analysis


def _normalize_ct_slice(slice_data: np.ndarray) -> np.ndarray:
    data = np.asarray(slice_data, dtype=np.float32)
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return np.zeros(data.shape, dtype=np.uint8)
    vmin = float(np.percentile(finite, 1))
    vmax = float(np.percentile(finite, 99))
    if vmin == vmax:
        vmin = float(finite.min())
        vmax = float(finite.max())
        if vmin == vmax:
            vmax = vmin + 1.0
    scaled = (np.clip(data, vmin, vmax) - vmin) / (vmax - vmin)
    return (scaled * 255).astype(np.uint8)


def _png_data_url(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _mask_png(mask: np.ndarray, color: tuple[int, int, int]) -> str:
    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[..., 0] = color[0]
    rgba[..., 1] = color[1]
    rgba[..., 2] = color[2]
    rgba[..., 3] = (mask > 0).astype(np.uint8) * 255
    return _png_data_url(Image.fromarray(rgba, mode="RGBA"))


@app.get("/api/health")
def health_check() -> dict:
    return {"ok": True}


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    output_path: Optional[str] = Form(None),
    hu_low: float = Form(-190.0),
    hu_high: float = Form(-30.0),
    device: str = Form("cpu"),
    save_eat_mask: bool = Form(False),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No input file provided.")
    if hu_low >= hu_high:
        raise HTTPException(status_code=400, detail="HU low must be < HU high.")

    output_dir = _resolve_output_dir(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    ct_path = output_dir / file.filename
    try:
        with ct_path.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)

        pericardium_path = run_totalsegmentation(str(ct_path), str(output_dir), device=device)
        results = compute_eat_and_stats(
            str(ct_path),
            pericardium_path,
            low_hu=hu_low,
            high_hu=hu_high,
            return_arrays=False,
        )
        stats_csv = save_stats_csv(
            str(output_dir),
            str(ct_path),
            pericardium_path,
            hu_low,
            hu_high,
            eat_volume=results["eat_volume"],
            mean_hu=results["mean_hu"],
            std_hu=results["std_hu"],
        )
        if save_eat_mask:
            save_eat_mask_nifti(
                str(output_dir),
                str(ct_path),
                pericardium_path,
                hu_low,
                hu_high,
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        file.file.close()

    analysis_id = uuid4().hex
    ANALYSIS_CACHE[analysis_id] = {
        "ct_path": str(ct_path),
        "pericardium_path": pericardium_path,
        "hu_low": hu_low,
        "hu_high": hu_high,
        "total_slices": results["total_slices"],
    }

    return {
        "success": True,
        "results": {
            "analysisId": analysis_id,
            "eatVolume": results["eat_volume"],
            "meanHU": results["mean_hu"],
            "stdHU": results["std_hu"],
            "voxelZoom": list(results["zooms"]),
            "totalSlices": results["total_slices"],
            "outputPath": str(output_dir),
            "statsCsv": stats_csv,
        },
    }


@app.post("/api/analyze-batch")
async def analyze_batch(
    files: list[UploadFile] = File(...),
    output_path: Optional[str] = Form(None),
    hu_low: float = Form(-190.0),
    hu_high: float = Form(-30.0),
    device: str = Form("cpu"),
    save_eat_mask: bool = Form(False),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="No input files provided.")
    if hu_low >= hu_high:
        raise HTTPException(status_code=400, detail="HU low must be < HU high.")

    output_dir = _resolve_output_dir(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_id = uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat()
    used_names: set[str] = set()
    items: list[dict[str, object]] = []
    csv_rows: list[dict[str, object]] = []

    for file in files:
        if not file.filename:
            items.append(
                {
                    "status": "error",
                    "error": "Empty filename provided.",
                }
            )
            file.file.close()
            continue

        participant_source = _derive_participant_id(file.filename)
        participant_id = _sanitize_participant_id(participant_source)
        participant_dir, participant_folder = _unique_participant_dir(
            output_dir, participant_id, used_names
        )
        participant_dir.mkdir(parents=True, exist_ok=True)
        ct_path = participant_dir / Path(file.filename).name

        try:
            with ct_path.open("wb") as handle:
                shutil.copyfileobj(file.file, handle)

            pericardium_path = run_totalsegmentation(str(ct_path), str(participant_dir), device=device)
            results = compute_eat_and_stats(
                str(ct_path),
                pericardium_path,
                low_hu=hu_low,
                high_hu=hu_high,
                return_arrays=False,
            )
            stats_csv = save_stats_csv(
                str(participant_dir),
                str(ct_path),
                pericardium_path,
                hu_low,
                hu_high,
                eat_volume=results["eat_volume"],
                mean_hu=results["mean_hu"],
                std_hu=results["std_hu"],
            )
            eat_mask_path = None
            if save_eat_mask:
                eat_mask_path = save_eat_mask_nifti(
                    str(participant_dir),
                    str(ct_path),
                    pericardium_path,
                    hu_low,
                    hu_high,
                )

            item = {
                "participantId": participant_id,
                "participantIdSource": participant_source,
                "participantFolder": participant_folder,
                "inputFile": file.filename,
                "ctPath": str(ct_path),
                "outputDir": str(participant_dir),
                "status": "success",
                "outputs": {
                    "pericardium": pericardium_path,
                    "eatMask": eat_mask_path,
                    "statsCsv": stats_csv,
                },
                "stats": {
                    "eatVolume": results["eat_volume"],
                    "meanHU": results["mean_hu"],
                    "stdHU": results["std_hu"],
                    "lowHU": hu_low,
                    "highHU": hu_high,
                },
            }
            items.append(item)
            csv_rows.append(
                {
                    "participant_id": participant_id,
                    "ct_path": str(ct_path),
                    "pericardium_path": pericardium_path,
                    "eat_mask_path": eat_mask_path or "",
                    "eat_volume": results["eat_volume"],
                    "mean_hu": results["mean_hu"],
                    "std_hu": results["std_hu"],
                    "low_hu": hu_low,
                    "high_hu": hu_high,
                }
            )
        except Exception as exc:
            items.append(
                {
                    "participantId": participant_id,
                    "participantIdSource": participant_source,
                    "participantFolder": participant_folder,
                    "inputFile": file.filename,
                    "ctPath": str(ct_path),
                    "outputDir": str(participant_dir),
                    "status": "error",
                    "error": str(exc),
                }
            )
        finally:
            file.file.close()

    succeeded = sum(1 for item in items if item.get("status") == "success")
    failed = sum(1 for item in items if item.get("status") == "error")

    manifest_path = output_dir / f"batch_manifest_{batch_id}.json"
    manifest = {
        "batchId": batch_id,
        "createdAt": started_at,
        "outputRoot": str(output_dir),
        "settings": {
            "huLow": hu_low,
            "huHigh": hu_high,
            "device": device,
            "saveEATMask": save_eat_mask,
            "namingRule": "prefix_before_underscore",
        },
        "summary": {
            "total": len(files),
            "succeeded": succeeded,
            "failed": failed,
        },
        "items": items,
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    stats_csv_path = None
    if csv_rows:
        stats_csv_path = output_dir / f"eat_batch_statistics_{batch_id}.csv"
        _write_batch_stats_csv(stats_csv_path, csv_rows)

    return {
        "success": True,
        "results": {
            "batchId": batch_id,
            "outputPath": str(output_dir),
            "manifestPath": str(manifest_path),
            "statsCsv": str(stats_csv_path) if stats_csv_path else None,
            "total": len(files),
            "succeeded": succeeded,
            "failed": failed,
            "items": items,
        },
    }


@app.get("/api/slice")
def get_slice(analysis_id: str, slice: int) -> dict:
    analysis = _analysis_or_404(analysis_id)
    total_slices = int(analysis["total_slices"])
    if slice < 0 or slice >= total_slices:
        raise HTTPException(status_code=400, detail="Slice index out of range.")

    ct_img = nib.load(str(analysis["ct_path"]))
    peri_img = nib.load(str(analysis["pericardium_path"]))

    ct_slice = np.asarray(ct_img.dataobj[:, :, slice])
    peri_slice = np.asarray(peri_img.dataobj[:, :, slice]) > 0
    eat_slice = np.logical_and(
        peri_slice,
        np.logical_and(ct_slice >= analysis["hu_low"], ct_slice <= analysis["hu_high"]),
    )

    ct_png = _png_data_url(Image.fromarray(_normalize_ct_slice(ct_slice), mode="L"))
    pericardium_png = _mask_png(peri_slice, (34, 197, 94))
    eat_png = _mask_png(eat_slice, (239, 68, 68))

    return {
        "slice": slice,
        "totalSlices": total_slices,
        "ctPng": ct_png,
        "pericardiumPng": pericardium_png,
        "eatPng": eat_png,
    }

