from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from installer.core.config import PRESETS, load_manifest

router = APIRouter()

_DEFAULT_MANIFEST = Path("manifest.yaml")


@router.get("/projects")
async def list_projects() -> dict[str, Any]:
    if not _DEFAULT_MANIFEST.exists():
        return {"projects": []}
    manifest = load_manifest(_DEFAULT_MANIFEST)
    return {
        "projects": [
            {
                "name": p.name,
                "config": p.config,
                "servers": [{"host": s.host, "user": s.user} for s in p.servers],
            }
            for p in manifest.projects
        ]
    }


@router.get("/presets")
async def list_presets() -> dict[str, Any]:
    return {
        "presets": [
            {"name": name, "stack": stack}
            for name, stack in PRESETS.items()
        ]
    }


@router.get("/projects/{name}/status")
async def project_status(name: str) -> dict[str, Any]:
    """Stub — returns unknown until a real SSH connection is wired in."""
    return {"name": name, "status": "unknown", "checks": []}


@router.get("/health")
async def health() -> dict[str, str]:
    import socket
    return {"status": "ok", "host": socket.gethostname()}
