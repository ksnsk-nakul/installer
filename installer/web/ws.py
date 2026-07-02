from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@dataclass
class JobLog:
    job_id: str
    lines: list[str] = field(default_factory=list)
    done: bool = False
    _queues: list[asyncio.Queue] = field(default_factory=list, repr=False)

    def append(self, line: str) -> None:
        self.lines.append(line)
        for q in list(self._queues):
            q.put_nowait(line)

    def finish(self) -> None:
        self.done = True
        for q in list(self._queues):
            q.put_nowait(None)   # sentinel

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        # Replay existing lines immediately
        for line in self.lines:
            q.put_nowait(line)
        if self.done:
            q.put_nowait(None)
        self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._queues.remove(q)
        except ValueError:
            pass


class LogBroadcaster:
    """Registry of active job logs."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobLog] = {}

    def create(self, job_id: str) -> JobLog:
        log = JobLog(job_id=job_id)
        self._jobs[job_id] = log
        return log

    def get(self, job_id: str) -> JobLog | None:
        return self._jobs.get(job_id)

    def remove(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)


broadcaster = LogBroadcaster()


@router.websocket("/ws/logs/{job_id}")
async def ws_logs(websocket: WebSocket, job_id: str) -> None:
    """Stream log lines for a running job over WebSocket."""
    await websocket.accept()
    job = broadcaster.get(job_id)
    if not job:
        await websocket.send_text(f"[error] Job {job_id!r} not found")
        await websocket.close()
        return

    q = job.subscribe()
    try:
        while True:
            try:
                line = await asyncio.wait_for(q.get(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_text("[ping]")
                continue
            if line is None:
                await websocket.send_text("[done]")
                break
            await websocket.send_text(line)
    except WebSocketDisconnect:
        pass
    finally:
        job.unsubscribe(q)
