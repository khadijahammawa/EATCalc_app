from __future__ import annotations

from pathlib import Path
import base64
import shutil
from io import BytesIO
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import nibabel as nib
from PIL import Image

from backend.eat_core import compute_eat_and_stats, run_totalsegmentation, save_stats_csv


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"
ANALYSIS_CACHE: dict[str, dict[str, object]] = {}

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

