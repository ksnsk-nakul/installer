from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from installer.web.api import projects, install, verify, clone, updates

_HERE = Path(__file__).parent

app = FastAPI(title="Installer Dashboard", version="0.1.0")

# Static files
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")

# Templates
templates = Jinja2Templates(directory=str(_HERE / "templates"))

# Register API routers
app.include_router(projects.router, prefix="/api")
app.include_router(install.router, prefix="/api")
app.include_router(verify.router, prefix="/api")
app.include_router(clone.router, prefix="/api")
app.include_router(updates.router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "base.html", {"section": "explore"})


@app.get("/{section}", response_class=HTMLResponse)
async def section_page(request: Request, section: str):
    valid = {"explore", "installed", "verify", "updates", "clone"}
    if section not in valid:
        section = "explore"
    return templates.TemplateResponse(request, "base.html", {"section": section})


def create_app() -> FastAPI:
    """Factory used by uvicorn and tests."""
    return app
