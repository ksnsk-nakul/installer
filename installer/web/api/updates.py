from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()

# Known latest stable versions for runtime checks
_LATEST = {
    "php": "8.3",
    "node": "22",
    "python": "3.12",
    "java": "21",
}


@router.get("/updates")
async def list_updates() -> dict[str, Any]:
    """Compare installed runtime versions against known latest versions.

    Returns a list of projects with available updates.
    Actual version detection requires SSH — returns stub data when offline.
    """
    manifest_path = Path("manifest.yaml")
    if not manifest_path.exists():
        return {"updates": []}

    from installer.core.config import load_manifest, load_config

    manifest = load_manifest(manifest_path)
    updates = []
    for p in manifest.projects:
        try:
            cfg = load_config(p.config)
            framework = cfg.stack.backend.framework
            current_ver: str | None = None
            latest_ver: str | None = None
            if framework == "laravel":
                current_ver = cfg.stack.backend.php_version or "8.2"
                latest_ver = _LATEST["php"]
            elif framework == "node":
                current_ver = cfg.stack.backend.node_version or "20"
                latest_ver = _LATEST["node"]
            elif framework in ("django", "fastapi", "flask"):
                current_ver = cfg.stack.backend.python_version or "3.11"
                latest_ver = _LATEST["python"]
            elif framework == "java":
                current_ver = str(cfg.stack.backend.java_version or "17")
                latest_ver = _LATEST["java"]

            if current_ver and latest_ver and current_ver != latest_ver:
                updates.append({
                    "name": p.name,
                    "framework": framework,
                    "current_version": current_ver,
                    "available_version": latest_ver,
                    "security": False,
                })
        except Exception:
            pass

    return {"updates": updates}


@router.post("/updates/{name}")
async def update_project(name: str) -> dict[str, str]:
    """Trigger a re-deploy for the named project (re-runs Step 4)."""
    manifest_path = Path("manifest.yaml")
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="manifest.yaml not found")

    from installer.core.config import load_manifest
    manifest = load_manifest(manifest_path)
    entry = next((p for p in manifest.projects if p.name == name), None)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    return {"status": "queued", "project": name}
