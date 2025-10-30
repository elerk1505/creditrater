import json
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import pandas as pd

# --- Paths ---
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INDUSTRIES_FP = DATA / "industries_min.json"
FACTOR_SCALE_FP = DATA / "factor_scale.json"
AGG_BINS_FP = DATA / "aggregate_bins.csv"

# -------------------------
# Loaders
# -------------------------
def load_industries() -> Dict[str, Any]:
    """
    Returns a dict keyed by industry name.
    Each industry contains factors/subfactors with their weights and types (numeric/qualitative).
    """
    with open(INDUSTRIES_FP, "r", encoding="utf-8") as f:
        industries = json.load(f)
    return industries  # structure comes straight from your JSON


def load_factor_scales() -> Dict[str, Any]:
    """
    Returns scale definitions used to convert qualitative labels to numeric
    and numeric alpha buckets to numeric centers/ranges (for interpolation).
    """
    with open(FACTOR_SCALE_FP, "r", encoding="utf-8") as f:
        scales = json.load(f)
    return scales


def load_aggregate_bins() -> List[Tuple[float, float, str]]:
    """
    Reads aggregate_bins.csv with columns like: lower, upper, label
    Returns a list of tuples (lower_inclusive, upper_inclusive, label) sorted by lower.
    """
    df = pd.read_csv(AGG_BINS_FP)
    # Expect columns: lower, upper, label (labels like Aaa, Aa1, Aa2, ..., Ca, C)
    df = df.sort_values("lower").reset_index(drop=True)
    bins = []
    for _, r in df.iterrows():
        bins.append((float(r["lower"]), float(r["upper"]), str(r["label"]).strip()))
    return bins


# -------------------------
# Core helpers
# -------------------------
def qualitative_to_numeric(label: str, scales: Dict[str, Any]) -> float:
    """
    Convert qualitative alpha (Aaa, Aa, A, Baa, Ba, B, Caa, Ca) to numeric using factor_scale.json.
    """
    alpha_map = scales.get("qualitative_numeric", {})
    # Normalize label (e.g., "AAA" -> "Aaa") if needed
    norm = label.strip()
    return float(alpha_map[norm])


def interpolate_numeric_to_alpha_score(value: float, alpha_ranges: Dict[str, List[float]]) -> float:
    """
    Map a raw numeric metric to its numeric score via linear interpolation across the
    alpha category ranges defined in factor_scale.json (quantitative scale).
    The alpha_ranges is expected to have keys Aaa, Aa, A, Baa, Ba, B, Caa, Ca
    with [low, high] numeric score bounds per bucket (e.g., Aaa: [0.5, 1.5], Aa: [1.5, 4.5], ...).
    We linearly interpolate within the bucket ranges; when exact bucket thresholds are
    unknown for the metric, the caller should pass a pre-transformed “alpha-ranged” number.
    """
    # The quantitative scale in factor_scale.json already specifies the numeric score ranges by alpha bucket.
    # We choose the bucket in which `value` resides, then interpolate within that bucket.
    order = ["Aaa", "Aa", "A", "Baa", "Ba", "B", "Caa", "Ca"]
    for i, alpha in enumerate(order):
        lo, hi = alpha_ranges[alpha]
        if lo <= value <= hi:
            # Linear interpolation of value onto [lo, hi] -> numeric score in same [lo, hi]
            # Here, `value` is already expressed *on the Moody's numeric score axis* (0.5–20.5 scale).
            if hi == lo:
                return lo
            t = (value - lo) / (hi - lo)
            return lo + t * (hi - lo)
    # If below min or above max, clamp
    min_lo = alpha_ranges["Aaa"][0]
    max_hi = alpha_ranges["Ca"][1]
    return max(min(value, max_hi), min_lo)


def map_aggregate_numeric_to_rating(x: float, bins: List[Tuple[float, float, str]]) -> str:
    """
    Map the final aggregate numeric score to the Moody's alphanumeric rating using aggregate_bins.csv.
    """
    for lo, hi, label in bins:
        # Treat ranges as: lo < x <= hi, with Aaa being x <= 1.5 etc., matching Moody's exhibits.
        # We'll allow inclusive ends to match your CSV authoring.
        if lo <= x <= hi:
            return label
    # If above top or below bottom, extend per Moody’s table
    # (e.g., x > 20.5 -> C, x < 0.5 -> Aaa). Use nearest bin label.
    if x < bins[0][0]:
        return bins[0][2]
    return bins[-1][2]


# -------------------------
# Public scoring API
# -------------------------
def auto_band_numeric(raw_number: float, metric_to_numeric_axis) -> float:
    """
    Convert a raw user-entered numeric metric to a numeric 'score' on the Moody's 0.5–20.5 axis.
    This requires a 'metric_to_numeric_axis' callable you supply per metric to transform
    (e.g., map EBIT margin % -> an alpha bucket then to [0.5–20.5] number).
    In your app, supply per-metric logic derived from the industry JSON.
    """
    return float(metric_to_numeric_axis(raw_number))


def score_result(
    industry_key: str,
    provided_values: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Main entry point:
      - industry_key: key in industries_min.json
      - provided_values: { factor_or_subfactor_id: {"type": "numeric"/"qualitative", "value": ..., "to_axis": callable_or_None} }
        If 'type' == 'numeric', 'to_axis' should map raw numeric to the Moody’s numeric-axis value (0.5–20.5 scale).
        If 'type' == 'qualitative', 'value' should be one of Aaa/Aa/A/Baa/Ba/B/Caa/Ca.
    Returns:
      {
        "breakdown": [ { "id": ..., "weight": w, "raw": v, "score": s } ... ],
        "aggregate_numeric": X,
        "final_rating": "Ba2"
      }
    """
    industries = load_industries()
    scales = load_factor_scales()
    bins = load_aggregate_bins()

    if industry_key not in industries:
        raise ValueError(f"Unknown industry '{industry_key}'")

    scorecard = industries[industry_key]
    # numeric ranges per alpha bucket (quantitative scale) from factor_scale.json
    # Expected shape: {"quantitative_numeric_ranges": {"Aaa":[0.5,1.5], "Aa":[1.5,4.5], ...}}
    q_ranges = scales.get("quantitative_numeric_ranges")
    if not q_ranges:
        raise ValueError("quantitative_numeric_ranges missing in factor_scale.json")

    rows = []
    aggregate = 0.0

    # Traverse factors/subfactors as defined in the JSON
    for item in scorecard.get("factors", []):
        weight = float(item.get("weight", 0))
        fid = item.get("id") or item.get("name")
        ftype = item.get("type", "numeric")

        # If there are sub-factors, score at sub-factor level; else score factor directly
        subfs = item.get("subfactors")
        if subfs:
            for sub in subfs:
                sid = sub.get("id") or sub.get("name")
                sw = float(sub.get("weight", 0))
                val_info = provided_values.get(sid, {})
                vtype = val_info.get("type", sub.get("type", "numeric"))
                raw = val_info.get("value")

                if vtype == "qualitative":
                    # Convert Aaa/Aa/A/Baa/Ba/B/Caa/Ca -> 1/3/6/.../20
                    score_numeric = qualitative_to_numeric(str(raw), scales)
                else:
                    # Numeric: require a transform to the Moody’s numeric axis then interpolate
                    to_axis = val_info.get("to_axis")
                    if callable(to_axis):
                        axis_val = auto_band_numeric(float(raw), to_axis)
                    else:
                        # If no transform is given, assume raw is already expressed on the numeric axis
                        axis_val = float(raw)
                    score_numeric = interpolate_numeric_to_alpha_score(axis_val, q_ranges)

                rows.append({"id": sid, "weight": sw, "raw": raw, "score": score_numeric})
                aggregate += score_numeric * (sw / 100.0)
        else:
            val_info = provided_values.get(fid, {})
            vtype = val_info.get("type", ftype)
            raw = val_info.get("value")

            if vtype == "qualitative":
                score_numeric = qualitative_to_numeric(str(raw), scales)
            else:
                to_axis = val_info.get("to_axis")
                if callable(to_axis):
                    axis_val = auto_band_numeric(float(raw), to_axis)
                else:
                    axis_val = float(raw)
                score_numeric = interpolate_numeric_to_alpha_score(axis_val, q_ranges)

            rows.append({"id": fid, "weight": weight, "raw": raw, "score": score_numeric})
            aggregate += score_numeric * (weight / 100.0)

    final_rating = map_aggregate_numeric_to_rating(aggregate, bins)

    return {
        "breakdown": rows,
        "aggregate_numeric": round(aggregate, 3),
        "final_rating": final_rating,
    }
