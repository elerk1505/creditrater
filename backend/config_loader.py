# backend/config_loader.py
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from dotenv import load_dotenv


# --- Resolve project paths ---
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR_DEFAULT = PROJECT_ROOT / "data"

# Load .env early (if present at project root)
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Settings:
    # API
    OPENAI_API_KEY: Optional[str]
    OPENAI_MODEL: str

    # Server
    BACKEND_HOST: str
    BACKEND_PORT: int

    # File size limits
    MAX_UPLOAD_MB: int

    # Pricing (per 1K tokens)
    PRICES_INPUT_PER_1K: float
    PRICES_OUTPUT_PER_1K: float

    # Data paths
    DATA_DIR: Path
    INDUSTRIES_JSON: Path
    FACTOR_SCALE_JSON: Path
    AGG_BINS_CSV: Path

    # UI defaults (optional – safe to ignore if unused)
    DEFAULT_PREPROCESS_MODE: str  # "text" | "text_layout" | "page_images"

def _env_path(key: str, default: Path) -> Path:
    """Read a path from env, falling back to default, and return as Path (expanded)."""
    val = os.getenv(key)
    if val and val.strip():
        return Path(val).expanduser().resolve()
    return default.resolve()

@lru_cache
def get_settings() -> Settings:
    """
    Build a Settings instance from environment variables with robust defaults.
    Cached so imports/use are cheap.
    """
    data_dir = _env_path("DATA_DIR", DATA_DIR_DEFAULT)

    return Settings(
        # API
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),

        # Server
        BACKEND_HOST=os.getenv("BACKEND_HOST", "127.0.0.1"),
        BACKEND_PORT=int(os.getenv("BACKEND_PORT", "5051")),

        # File size limits
        MAX_UPLOAD_MB=int(os.getenv("MAX_UPLOAD_MB", "80")),

        # Pricing (per 1K tokens) — adjust via .env if you want
        PRICES_INPUT_PER_1K=float(os.getenv("PRICES_INPUT_PER_1K", "0.15")),
        PRICES_OUTPUT_PER_1K=float(os.getenv("PRICES_OUTPUT_PER_1K", "0.60")),

        # Data paths
        DATA_DIR=data_dir,
        INDUSTRIES_JSON=_env_path("INDUSTRIES_JSON", data_dir / "industries_min.json"),
        FACTOR_SCALE_JSON=_env_path("FACTOR_SCALE_JSON", data_dir / "factor_scale.json"),
        AGG_BINS_CSV=_env_path("AGG_BINS_CSV", data_dir / "aggregate_bins.csv"),

        # UI defaults
        DEFAULT_PREPROCESS_MODE=os.getenv("DEFAULT_PREPROCESS_MODE", "text"),
    )

# -------- Helpers to read your data files -------- #

def read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_csv_df(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)

def load_industries(settings: Optional[Settings] = None) -> Dict[str, Any]:
    s = settings or get_settings()
    return read_json(s.INDUSTRIES_JSON)

def load_factor_scale(settings: Optional[Settings] = None) -> Dict[str, Any]:
    s = settings or get_settings()
    return read_json(s.FACTOR_SCALE_JSON)

def load_aggregate_bins(settings: Optional[Settings] = None) -> pd.DataFrame:
    s = settings or get_settings()
    return read_csv_df(s.AGG_BINS_CSV)
