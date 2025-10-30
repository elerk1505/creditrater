from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from llm_ops import estimate_llm_cost, analyze_with_llm
from config_loader import Settings

app = FastAPI()

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

@app.get("/", response_class=HTMLResponse)
def root_redirect():
    return HTMLResponse(status_code=307, headers={"Location": "/app/"})

@app.get("/app/", response_class=HTMLResponse)
def serve_index():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        raise HTTPException(500, "frontend/index.html not found")
    return index.read_text(encoding="utf-8")

@app.get("/app/{path:path}")
def serve_frontend_assets(path: str):
    fp = FRONTEND_DIR / path
    if not fp.exists():
        raise HTTPException(404, f"{path} not found")
    return FileResponse(fp)

def _auth_from_headers(req: Request):
    key = req.headers.get("x-openai-key")
    model = req.headers.get("x-openai-model", "gpt-4.1-mini")
    if not key:
        raise HTTPException(400, "Missing X-OpenAI-Key header")
    return key, model

@app.post("/estimate_tokens_cost")
async def estimate_tokens_cost(req: Request, payload: dict):
    key, model = _auth_from_headers(req)
    # payload should include mode/pages or any other params you already send
    return estimate_llm_cost(payload, model=model, api_key=key)

@app.post("/analyze_llm")
async def analyze_llm(req: Request, payload: dict):
    key, model = _auth_from_headers(req)
    return await analyze_with_llm(payload, model=model, api_key=key)
