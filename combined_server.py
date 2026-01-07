"""
Combined Server - Single port serves everything:
- /og/* -> Static OG images
- /* -> Proxy to Streamlit dashboard
"""

import os
import httpx
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response, HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
GEN_DIR = BASE_DIR / "images" / "generated"
GEN_DIR.mkdir(parents=True, exist_ok=True)

# Streamlit runs on internal port
STREAMLIT_PORT = 8501

app = FastAPI(title="RoboVAI Creator")


# Health check
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# Mount static images at /og/
app.mount("/og", StaticFiles(directory=GEN_DIR, html=False), name="og")


# Proxy everything else to Streamlit
@app.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
)
async def proxy_to_streamlit(request: Request, path: str = ""):
    """Proxy all other requests to Streamlit"""

    # Build target URL
    target_url = f"http://127.0.0.1:{STREAMLIT_PORT}/{path}"
    if request.query_params:
        target_url += f"?{request.query_params}"

    # Get request body
    body = await request.body()

    # Forward headers (filter out host)
    headers = dict(request.headers)
    headers.pop("host", None)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )

            # Return response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except httpx.ConnectError:
        return HTMLResponse(
            content="<h1>Dashboard starting...</h1><p>Please refresh in a few seconds.</p>",
            status_code=503,
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Error</h1><p>{str(e)}</p>",
            status_code=500,
        )



def start_streamlit():
    """Start Streamlit as subprocess"""
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "dashboard.py",
        "--server.port",
        str(STREAMLIT_PORT),
        "--server.address",
        "127.0.0.1",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    print(f"📊 Starting Streamlit on internal port {STREAMLIT_PORT}...")
    subprocess.Popen(cmd, cwd=str(BASE_DIR))

    # Give Streamlit time to start
    time.sleep(3)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))

    # Start Streamlit first
    start_streamlit()

    print(f"🚀 Combined Server starting on port {port}")
    print(f"🖼️ Images: https://robovai-creator.onrender.com/og/<filename>")
    print(f"📊 Dashboard: https://robovai-creator.onrender.com/")

    # Run FastAPI
    uvicorn.run(app, host="0.0.0.0", port=port)
