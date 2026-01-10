from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Any, Dict

from sf_wizard.core.runs import RUNS, sse_stream

router = APIRouter()

@router.get("/runs/{run_id}")
def get_run(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "runId": run.run_id,
        "kind": run.kind,
        "status": run.status,
        "createdAt": run.created_at,
        "updatedAt": run.updated_at,
        "error": run.error,
    }

@router.get("/runs/{run_id}/events")
def run_events(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return StreamingResponse(
        sse_stream(run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

@router.get("/runs/{run_id}/result")
def run_result(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status == "running":
        return JSONResponse({"status": "running"}, status_code=202)
    if run.status == "error":
        return JSONResponse({"status": "error", "error": run.error}, status_code=500)
    return {"status": "success", "result": run.result}
