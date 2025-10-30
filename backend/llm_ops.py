# backend/llm_ops.py
from __future__ import annotations

import os
import math
from typing import List, Dict, Any, Optional

import tiktoken

# OpenAI SDK v2.x
try:
    from openai import OpenAI
except Exception as e:
    OpenAI = None  # we'll guard below


# -----------------------
# Configuration helpers
# -----------------------

def _get_env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name)
    if val is None or val == "":
        if default is None:
            raise RuntimeError(f"Environment variable {name} is not set.")
        return default
    return val

def _to_float(value: str, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default

def _encoding_for_model(model: str):
    # Try specific encoding for the model, fall back to cl100k_base
    try:
        return tiktoken.encoding_for_model(model)
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


# -----------------------
# Public API
# -----------------------

def estimate_llm_cost(
    pages_text: List[str],
    model: Optional[str] = None,
    expected_output_tokens: int = 1500
) -> Dict[str, Any]:
    """
    Estimate tokens and cost for a set of page texts for the chosen model.

    Args:
        pages_text: list of strings (one per page or chunk).
        model: OpenAI model name. If None, uses env OPENAI_MODEL.
        expected_output_tokens: anticipated assistant output tokens.

    Returns:
        {
          "model": ...,
          "tokens_in": int,
          "tokens_out": int,
          "usd_in": float,
          "usd_out": float,
          "usd_total": float
        }
    """
    model_name = model or _get_env("OPENAI_MODEL", "gpt-4o-mini")

    enc = _encoding_for_model(model_name)
    tokens_in = 0
    for txt in pages_text:
        if not txt:
            continue
        tokens_in += len(enc.encode(txt))

    # Round up output tokens to an integer
    tokens_out = max(0, int(expected_output_tokens))

    # Pricing from env (USD per 1K tokens)
    usd_per_1k_in = _to_float(os.getenv("OPENAI_INPUT_USD_PER_1K", "0.00015"), 0.00015)
    usd_per_1k_out = _to_float(os.getenv("OPENAI_OUTPUT_USD_PER_1K", "0.00060"), 0.00060)

    usd_in = (tokens_in / 1000.0) * usd_per_1k_in
    usd_out = (tokens_out / 1000.0) * usd_per_1k_out
    usd_total = usd_in + usd_out

    return {
        "model": model_name,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "usd_in": round(usd_in, 6),
        "usd_out": round(usd_out, 6),
        "usd_total": round(usd_total, 6),
    }


def analyze_with_llm(
    prompt_text: str,
    mode: str = "text",
    model: Optional[str] = None,
    extra_system_instructions: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 1500
) -> Dict[str, Any]:
    """
    Run an LLM analysis with OpenAI Responses API v2.

    Args:
        prompt_text: The assembled user prompt (e.g., preprocessed PDF text + instructions).
        mode: "text" | "text+layout" | "pages" (used to label the run in the response).
        model: OpenAI model name (falls back to env).
        extra_system_instructions: optional system message to steer the LLM.
        temperature: sampling temperature.
        max_output_tokens: max tokens for the assistant output.

    Returns:
        {
          "model": ...,
          "mode": ...,
          "content": "assistant text",
          "usage": {
              "input_tokens": int | None,
              "output_tokens": int | None,
              "total_tokens": int | None
          }
        }
    """
    if OpenAI is None:
        raise RuntimeError(
            "The OpenAI SDK is not installed in this environment. "
            "Ensure `openai>=2.0.0` is in backend/requirements.txt and installed."
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env in the project root.")

    client = OpenAI(api_key=api_key)
    model_name = model or _get_env("OPENAI_MODEL", "gpt-4o-mini")

    system_content = extra_system_instructions or (
        "You are a careful financial analyst. Extract only information relevant to "
        "credit rating analysis. If something is missing, say so clearly."
    )

    # Responses API
    resp = client.responses.create(
        model=model_name,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        input=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"[Mode: {mode}]\n{prompt_text}"}
        ],
    )

    # Best-effort parse
    assistant_text = ""
    try:
        # For text responses, first item is typically the assistant message
        if resp.output and len(resp.output) > 0 and hasattr(resp.output[0], "content"):
            parts = resp.output[0].content
            # parts is a list of content blocks; join text blocks
            chunks = []
            for p in parts:
                if getattr(p, "type", None) == "output_text" and hasattr(p, "text"):
                    chunks.append(p.text)
            assistant_text = "\n".join(chunks).strip()
        elif hasattr(resp, "output_text"):
            assistant_text = (resp.output_text or "").strip()
    except Exception:
        # Fallback — don’t crash the server if the shape changes
        assistant_text = getattr(resp, "output_text", "") or ""

    usage = {
        "input_tokens": getattr(getattr(resp, "usage", None), "input_tokens", None),
        "output_tokens": getattr(getattr(resp, "usage", None), "output_tokens", None),
        "total_tokens": getattr(getattr(resp, "usage", None), "total_tokens", None),
    }

    return {
        "model": model_name,
        "mode": mode,
        "content": assistant_text,
        "usage": usage,
    }
