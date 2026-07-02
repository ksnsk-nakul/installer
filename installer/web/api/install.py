from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter()

# In-memory job registry: job_id -> {"status", "logs", "db_event", "db_result"}
_jobs: dict[str, dict[str, Any]] = {}


class InstallRequest(BaseModel):
    # Either a preset name (from Explore) or a path to an existing installer.yaml
    preset: str | None = None
    config_path: str | None = None
    project_path: str = "/var/www/app"
    domain: str = ""
    host: str | None = None
    user: str | None = None
    key: str | None = None


class DBConfigRequest(BaseModel):
    engine: str
    mode: str
    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None
    db_name: str | None = None
    backup_url: str | None = None


@router.post("/install")
async def start_install(req: InstallRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "pending",
        "logs": [],
        "db_event": asyncio.Event(),
        "db_result": None,
        "report": None,
    }
    background_tasks.add_task(_run_install, job_id, req)
    return {"job_id": job_id}


@router.get("/install/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "status": job["status"],
        "logs": job["logs"],
        "report": job.get("report"),
    }


@router.post("/install/{job_id}/db-config")
async def set_db_config(job_id: str, cfg: DBConfigRequest) -> dict[str, str]:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job["db_result"] = cfg.model_dump()
    job["db_event"].set()
    return {"status": "accepted"}


async def _run_install(job_id: str, req: InstallRequest) -> None:
    job = _jobs[job_id]
    job["status"] = "running"
    job["logs"].append("Install job started")

    try:
        from installer.core.config import load_config, PRESETS
        from installer.core.engine import Engine
        import subprocess

        if req.preset and not req.config_path:
            if req.preset not in PRESETS:
                raise ValueError(f"Unknown preset {req.preset!r}")
            import tempfile, yaml
            stack = PRESETS[req.preset]
            tmp = tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False)
            yaml.dump({
                "project_path": req.project_path,
                "domain": req.domain or f"{req.preset.lower()}.example.com",
                "preset": req.preset,
                "stack": stack,
            }, tmp)
            tmp.flush()
            cfg = load_config(tmp.name)
        else:
            cfg = load_config(req.config_path)

        class LocalRunner:
            def run(self, command: str) -> str:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip())
                return result.stdout

            def write_file(self, path: str, content: str) -> None:
                from pathlib import Path
                Path(path).write_text(content)

        runner = LocalRunner()

        def db_callback(db_cfg: dict) -> dict:
            # Pause and wait for Web UI to post db config
            job["logs"].append("Waiting for DB configuration from Web UI…")
            job["status"] = "waiting_db_config"
            # Block the background coroutine (sync context) — use threading event
            import threading
            ev = threading.Event()

            async def _wait():
                await job["db_event"].wait()
                ev.set()

            asyncio.run_coroutine_threadsafe(_wait(), asyncio.get_event_loop())
            ev.wait(timeout=300)
            job["status"] = "running"
            return job["db_result"] or db_cfg

        engine = Engine(cfg, runner, db_config_callback=db_callback)
        report = engine.run()
        job["report"] = report
        job["status"] = "done"
        job["logs"].append("Install complete.")
    except Exception as exc:
        job["status"] = "error"
        job["logs"].append(f"Error: {exc}")
