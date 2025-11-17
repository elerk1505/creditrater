#!/usr/bin/env python3
"""
Run this in GitHub Codespaces or locally to fix JSON naming / typos in backend/data/.
"""

import json, re, os, sys

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA = os.path.join(ROOT, "backend", "data")
IND_FILE = os.path.join(DATA, "industries_min.json")

# --- Canonical factor names you want ---
CANONICAL = {
    r"DEBT/?\s*EBITDA": "Debt / EBITDA",
    r"Debt\s*/?\s*EBITDA": "Debt / EBITDA",
    r"RCF\s*/?\s*Debt": "RCF / Debt",
    r"RCF\s*/?\s*Net\s*Debt": "RCF / Net Debt",
    r"EBIT\s*/?\s*Interest": "EBIT / Interest Expense",
    r"\(EBITDA\s*-\s*Capex\)\s*/?\s*Interest": "(EBITDA - Capex) / Interest Expense",
    r"Debt\s*/?\s*Book": "Debt / Book Capitalization",
    r"Free\s*Cash\s*Flow\s*/?\s*Debt": "Free Cash Flow / Debt",
    r"Unencumbered\s*Assets": "Unencumbered Assets / Gross Assets",
}

def normalize_factor_name(name: str) -> str:
    for pat, repl in CANONICAL.items():
        if re.search(pat, name, flags=re.I):
            return repl
    return name.strip()

def clean_text(txt: str) -> str:
    """Basic typo cleanup."""
    replacements = {
        "vunrable": "vulnerable",
        "vunerable": "vulnerable",
        "resouces": "resources",
        "challanged": "challenged",
        "administratio n": "administration",
        "spo nsor": "sponsor",
        "cashs flow": "cash flow",
        "resullt": "result",
    }
    for a, b in replacements.items():
        txt = re.sub(a, b, txt, flags=re.I)
    return txt.strip()

def process_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    def recurse(obj):
        if isinstance(obj, dict):
            new = {}
            for k, v in obj.items():
                new[normalize_factor_name(k)] = recurse(v)
            return new
        elif isinstance(obj, list):
            return [recurse(x) for x in obj]
        elif isinstance(obj, str):
            return clean_text(obj)
        return obj

    fixed = recurse(data)
    out_path = path.replace(".json", "_fixed.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fixed, f, indent=2, ensure_ascii=False)
    print(f"✅ Fixed JSON written to {out_path}")

if __name__ == "__main__":
    if not os.path.exists(IND_FILE):
        print(f"❌ {IND_FILE} not found. Run from repo root.")
        sys.exit(1)
    process_json(IND_FILE)
