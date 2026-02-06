import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from pathlib import Path

app = FastAPI(title="Loto Bot Web App")

# Serve static files
web_dir = Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

@app.get("/")
async def read_index():
    return FileResponse(web_dir / "index.html")

def run_web_server(port: int = 8000):
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    run_web_server()
