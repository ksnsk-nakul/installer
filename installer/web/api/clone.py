from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter()

_clone_jobs: dict[str, dict[str, Any]] = {}


class CloneRequest(BaseModel):
    source: str
    name: str | None = None       # new project name
    path: str | None = None       # target path (alias for target_path)
    host: str | None = None       # target server (alias for target_server)
    target_path: str | None = None
    target_server: str | None = None
    db_mode: str = "empty"

    @property
    def resolved_path(self) -> str:
        return self.path or self.target_path or f"/var/www/{self.source}-clone"


@router.post("/clone")
async def clone_project(req: CloneRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    job_id = str(uuid.uuid4())
    _clone_jobs[job_id] = {"status": "pending", "logs": []}
    background_tasks.add_task(_run_clone, job_id, req)
    return {"job_id": job_id, "message": f"Clone of '{req.source}' queued."}


@router.get("/clone/{job_id}")
async def get_clone_job(job_id: str) -> dict[str, Any]:
    job = _clone_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Clone job not found")
    return {"job_id": job_id, **job}


async def _run_clone(job_id: str, req: CloneRequest) -> None:
    job = _clone_jobs[job_id]
    job["status"] = "running"
    job["logs"].append(f"Cloning '{req.source}' → {req.resolved_path}")

    try:
        manifest_path = Path("manifest.yaml")
        if not manifest_path.exists():
            raise FileNotFoundError("manifest.yaml not found")

        from installer.core.config import load_manifest, load_config

        manifest = load_manifest(manifest_path)
        entry = next((p for p in manifest.projects if p.name == req.source), None)
        if not entry:
            raise ValueError(f"Project '{req.source}' not found in manifest")

        src_cfg = load_config(entry.config)
        target = Path(req.resolved_path)
        target.mkdir(parents=True, exist_ok=True)

        # Copy installer.yaml with overridden project_path
        import yaml
        cfg_data = yaml.safe_load(Path(entry.config).read_text())
        cfg_data["project_path"] = req.target_path
        if req.db_mode == "empty":
            cfg_data.setdefault("database", {}).pop("backup_url", None)
        (target / "installer.yaml").write_text(yaml.dump(cfg_data))

        job["logs"].append(f"installer.yaml written to {target / 'installer.yaml'}")
        job["logs"].append("Clone complete. Review .env credentials before installing.")
        job["status"] = "done"
    except Exception as exc:
        job["status"] = "error"
        job["logs"].append(f"Error: {exc}")
