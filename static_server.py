"""Static asset server for generated OG images.
Serves files from images/generated/ at /og/<filename>.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
GEN_DIR = BASE_DIR / "images" / "generated"
GEN_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RoboVAI Assets", version="1.0")

# Health check
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Static mount for generated images
app.mount("/og", StaticFiles(directory=GEN_DIR, html=False), name="og")
