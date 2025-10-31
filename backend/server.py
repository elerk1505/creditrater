# backend/server.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, UploadFile, File, Form, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---- Local modules (as already in your repo)
# If any import below fails, double-check filenames in backend/ match these.
from config_loader import Settings
from pdf_ops import save_upload_to_tmp, autocut as pdf_autocut
from llm_ops import estimate_llm_cost, analyze_with_llm
from scoring import load_industries

# --------------------------------------------------------------------------------------
# App setup
# --------------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]        # repo root
FRONTEND_DIR = ROOT / "frontend"                   # served at /app/
DATA_DIR = ROOT / "data"                           # your CSV/JSON live here

app = FastAPI(title="CreditRater API", version="0.1.0")

# CORS (local development convenience)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten later if you host this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend (fixes 404 for /app/src/main.js)
if not FRONTEND_DIR.exists():
    logging.warning("frontend/ directory not found at %s", FRONTEND_DIR)
app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="app")


@app.get("/")
def root_redirect():
    """Redirect root to the single-page app."""
    return RedirectResponse(url="/app/")

# --------------------------------------------------------------------------------------
# Settings & shared state
# --------------------------------------------------------------------------------------

def _safe_settings() -> Settings:
    """
    Instantiate Settings with sane defaults even if config_loader.Settings
    was authored as a plain Pydantic model (and complains about missing args).
    """
    try:
        return Settings()  # preferred: BaseSettings with env defaults
    except TypeError:
        # Fallback: construct with minimal sensible defaults
        return Settings(  # type: ignore[call-arg]
            OPENAI_API_KEY="",
            OPENAI_MODEL="gpt-4o-mini",
            BACKEND_HOST="127.0.0.1",
            BACKEND_PORT=5051,
            MAX_UPLOAD_MB=50,
            PRICES_INPUT_PER_1K=0.0,
            PRICES_OUTPUT_PER_1K=0.0,
            DATA_DIR=str(DATA_DIR),
            INDUSTRIES_JSON=str(DATA_DIR / "industries_min.json"),
            FACTOR_SCALE_JSON=str(DATA_DIR / "factor_scale.json"),
            AGG_BINS_CSV=str(DATA_DIR / "aggregate_bins.csv"),
            DEFAULT_PREPROCESS_MODE="text",
        )

settings = _safe_settings()

# Preload industries once (scoring.load_industries reads your JSON/CSV)
INDUSTRIES: List[Dict[str, Any]] = load_industries()

# --------------------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------------------

class EstimateIn(BaseModel):
    file_id: str
    pages: Optional[str] = None
    mode: str = "text"           # "text" | "text+layout" | "images"
    api_key: Optional[str] = None

class AnalyzeIn(BaseModel):
    file_id: str
    pages: Optional[str] = None
    mode: str = "text"
    industry_id: Optional[str] = None
    manual_values: Optional[Dict[str, Any]] = None
    api_key: Optional[str] = None

class AutoCutIn(BaseModel):
    file_id: str

# --------------------------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------------------------

def _raise_400_if_no_file(file_id: Optional[str]) -> None:
    if not file_id:
        raise HTTPException(status_code=400, detail="file_id is required")

# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"ok": True, "version": app.version}

@app.get("/api/industries")
def api_industries():
    """
    Minimal list for the dropdown. scoring.load_industries() should return
    entries with at least {id, name}. If you have more fields, they’re ignored here.
    """
    return [{"id": x.get("id"), "name": x.get("name")} for x in INDUSTRIES]

@app.get("/api/industry-factors")
def api_industry_factors(id: str):
    """
    Returns factor metadata for manual input UI.
    Expected shape per factor: { code, name, kind: "quant"|"qual", weight?: number }
    If your scoring module exposes factors differently, adapt here.
    """
    match = next((x for x in INDUSTRIES if x.get("id") == id), None)
    if not match:
        return {"factors": []}
    factors = match.get("factors") or []
    return {"factors": factors}

# ---------- Upload ----------

@app.post("/upload")
async def upload(file: UploadFile = File(...), api_key: Optional[str] = Form(None)):
    """
    Accepts a PDF, stores it in a tmp location, and returns a file_id
    (your pdf_ops.save_upload_to_tmp already implements this).
    We accept api_key here solely so the UI can submit it once; we do NOT persist it.
    """
    try:
        file_id = save_upload_to_tmp(file)
        return {"file_id": file_id}
    except Exception as e:
        logging.exception("Upload failed")
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

# ---------- Autocut ----------

@app.post("/autocut")
def autocut(body: AutoCutIn):
    _raise_400_if_no_file(body.file_id)
    try:
        suggestion = pdf_autocut(body.file_id)  # returns a string like "1-3, 17, 78-90"
        return {"cut_suggestion": suggestion or ""}
    except Exception as e:
        logging.exception("Autocut failed")
        raise HTTPException(status_code=500, detail=f"Autocut failed: {e}")

# ---------- Estimate ----------

@app.post("/estimate")
def estimate(body: EstimateIn):
    _raise_400_if_no_file(body.file_id)
    try:
        result = estimate_llm_cost(
            file_id=body.file_id,
            pages=body.pages,
            mode=body.mode,
            api_key_override=body.api_key,   # <— do not store; pass through
        )
        # Expecting: {input_tokens, output_tokens, estimated_cost}
        return result
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Estimate failed")
        raise HTTPException(status_code=500, detail=f"Estimate failed: {e}")

# ---------- Analyse ----------

@app.post("/analyze")
def analyze(body: AnalyzeIn):
    _raise_400_if_no_file(body.file_id)
    try:
        out = analyze_with_llm(
            file_id=body.file_id,
            pages=body.pages,
            mode=body.mode,
            industry_id=body.industry_id,
            manual_values=body.manual_values or {},
            api_key_override=body.api_key,    # <— do not store; pass through
        )
        # Expecting: {breakdown:[...], composite_score, final_rating}
        return out
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Analyze failed")
        raise HTTPException(status_code=500, detail=f"Analyze failed: {e}")

# --------------------------------------------------------------------------------------
# Dev entrypoint (optional)
# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=getattr(settings, "BACKEND_HOST", "127.0.0.1"),
        port=int(getattr(settings, "BACKEND_PORT", 5051)),
        reload=True,
    )
