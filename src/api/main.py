from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.runner import JobKind, Runner, JobResult
from agent.storage import ContextStore
from agent.firecracker import MicroVMManager

app = FastAPI(title="Sandboxed Coding Agent", version="0.1.0")

# Thread pool for blocking workload
_EXEC = ThreadPoolExecutor(max_workers=4)

# ---------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------
class ScheduleRequest(BaseModel):
    kind: JobKind = Field(..., description="Type of job: shell/python/typescript/gui")
    code: str = Field(..., description="Source code or shell/xdot snippet to execute")


class StatusResponse(BaseModel):
    state: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None


# ---------------------------------------------------------------------
# In-memory job registry (prototype)
# ---------------------------------------------------------------------
_JOBS: Dict[str, Dict] = {}
_STORE = ContextStore(Path.home() / ".sandboxed_agent" / "history.jsonl")

_runner = Runner()
_vm_mgr = MicroVMManager()


async def _run_job(job_id: str, kind: JobKind, code: str) -> None:
    # Mark as running
    _JOBS[job_id]["state"] = "running"

    loop = asyncio.get_running_loop()

    # Prototype: run inside (mock) micro-VM context
    def _execute_inside_vm() -> JobResult:
        with _vm_mgr.microvm() as vm:
            # In a real implementation, you'd copy *code* into the VM's FS
            # and execute via an SSH/serial console.  For the prototype we
            # just run on the host.
            return _runner.run(kind, code)

    result: JobResult = await loop.run_in_executor(_EXEC, _execute_inside_vm)

    _JOBS[job_id].update({
        "state": "succeeded" if result.ok else "failed",
        "stdout": result.stdout,
        "stderr": result.stderr,
    })

    # Persist conversation context (naive example)
    _STORE.append("assistant", f"Job {job_id} completed with state={_JOBS[job_id]['state']}")


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.post("/schedule", response_model=dict)
async def schedule(req: ScheduleRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {"state": "queued", "stdout": None, "stderr": None}

    _STORE.append("user", f"Scheduled {req.kind} job {job_id}")

    background_tasks.add_task(_run_job, job_id, req.kind, req.code)
    return {"job_id": job_id}


@app.get("/status/{job_id}", response_model=StatusResponse)
async def status(job_id: str):
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return StatusResponse(**job) 