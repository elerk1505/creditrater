from __future__ import annotations

import re
from typing import List, Tuple, Dict
from pathlib import Path
import tempfile

import fitz  # PyMuPDF

# Terms to CUT (ESG/CSR etc.)
GENERIC_CUT = [
    "environment", "climate", "sustainability", "csr", "esg", "sustainable",
    "human capital", "diversity & inclusion", "foundation", "community",
    "modern slavery", "ethical trading", "donations", "philanthropy",
    "glossary", "appendix", "table of contents", "contents",
    "forward-looking", "safe harbor", "statement of responsibility",
    "auditor independence", "assurance report", "non-audited",
    "legal disclaimer", "terms and conditions", "risk factors"
]

BLANK_MIN_CHARS = 25  # fewer chars than this ≈ blank/cover

RANGE_RE = re.compile(r"\s*,\s*")

def save_upload_to_tmp(upload) -> Path:
    """
    Save a FastAPI UploadFile to a temporary file, return Path.
    """
    suffix = Path(upload.filename).suffix or ".pdf"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="creditrater_")
    with open(fd, "wb") as f:  # type: ignore[arg-type]
        f.write(upload.file.read())
    return Path(tmp_path)

def get_page_count(pdf_path: Path) -> int:
    with fitz.open(pdf_path) as doc:
        return doc.page_count

def extract_text_by_page(pdf_path: Path, pages: List[int] | None = None) -> Dict[int, str]:
    """
    Returns {1-based page_index: text}
    """
    out = {}
    with fitz.open(pdf_path) as doc:
        idxs = pages or list(range(1, doc.page_count + 1))
        for p in idxs:
            page = doc.load_page(p - 1)
            out[p] = page.get_text("text") or ""
    return out

def parse_ranges(ranges: str, total_pages: int | None = None) -> List[int]:
    """
    '1-5, 7, 9-10' -> [1,2,3,4,5,7,9,10]
    """
    pages: List[int] = []
    if not ranges:
        return pages
    for token in RANGE_RE.split(ranges.strip()):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            if a.isdigit() and b.isdigit():
                lo, hi = int(a), int(b)
                if lo <= hi:
                    pages.extend(list(range(lo, hi + 1)))
        elif token.isdigit():
            pages.append(int(token))
    if total_pages:
        pages = [p for p in pages if 1 <= p <= total_pages]
    # unique & sorted
    return sorted(set(pages))

def autocut(pdf_path: Path, aggressive: bool = True) -> Tuple[List[int], Dict[int, str]]:
    """
    Very fast rule-based autocut. Returns (keep_pages, reasons_removed_dict).
    If aggressive=True, applies keyword filters; always drops near-blank pages.
    """
    reasons: Dict[int, str] = {}
    keep: List[int] = []
    with fitz.open(pdf_path) as doc:
        for i in range(doc.page_count):
            page_no = i + 1
            page = doc.load_page(i)
            text = page.get_text("text") or ""
            clean = " ".join(text.lower().split())

            # Blank/near-blank?
            if len(clean) < BLANK_MIN_CHARS:
                reasons[page_no] = "near-blank"
                continue

            # Keyword cut?
            if aggressive:
                if any(term in clean for term in GENERIC_CUT):
                    reasons[page_no] = "non-credit content (keyword)"
                    continue

            keep.append(page_no)
    # Safety: keep at least 1 page
    if not keep and doc.page_count > 0:
        keep = [1]
        reasons.pop(1, None)
    return keep, reasons
