from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
import threading
from datetime import datetime, timezone

from sf_wizard.core.runs import RUNS
from sf_wizard.sfcli.query import sf_data_query
from sf_wizard.core.config import data_dir
from sf_wizard.core.storage import read_json, write_json_atomic, ensure_dir

# TODO: implement these two SF CLI helpers
from sf_wizard.sfcli.org_login import sf_org_login_web, sf_org_login_sfdx_url  # you create this

router = APIRouter()

STATE_FILE = "state/query.json"

class QueryBody(BaseModel):
    query: str
    includeDeleted: bool = False

class QueryState(BaseModel):
    # target can be alias OR username; v0.1.0.2 keeps it simple
    activeTarget: Optional[str] = None
    activeOrgId: Optional[str] = None
    activeAlias: Optional[str] = None
    lastUsedAt: Optional[str] = None

class SetQueryStateBody(BaseModel):
    activeTarget: str
    activeOrgId: Optional[str] = None
    activeAlias: Optional[str] = None

class LoginWebBody(BaseModel):
    # optional alias to suggest; if None, CLI may create one or just use username
    alias: Optional[str] = None

class LoginSfdxUrlBody(BaseModel):
    sfdxUrl: str
    alias: Optional[str] = None

def _state_path():
    return data_dir() / STATE_FILE

def _read_state() -> Dict[str, Any]:
    ensure_dir(data_dir() / "state")
    return read_json(_state_path(), default={})

def _write_state(payload: Dict[str, Any]) -> None:
    ensure_dir(data_dir() / "state")
    write_json_atomic(_state_path(), payload)

def _active_target() -> Optional[str]:
    st = _read_state()
    return st.get("activeTarget")

def _normalize_soql(soql: str, include_deleted: bool) -> str:
    s = (soql or "").strip()
    if include_deleted and "ALL ROWS" not in s.upper():
        s = f"{s} ALL ROWS"
    return s

@router.get("/query/state")
def get_query_state():
    return _read_state()

@router.post("/query/state")
def set_query_state(body: SetQueryStateBody):
    st = _read_state()
    st["activeTarget"] = body.activeTarget
    st["activeOrgId"] = body.activeOrgId
    st["activeAlias"] = body.activeAlias
    st["lastUsedAt"] = datetime.now(timezone.utc).isoformat()
    _write_state(st)
    return st

@router.post("/query/login/web")
def login_web(body: LoginWebBody):
    """
    Starts web login in a background thread and returns runId to poll via /query/login/status/{runId}.
    """
    run = RUNS.create(kind="login_web")
    RUNS.append_log(run.run_id, "Starting web login...")
    if body.alias:
        RUNS.append_log(run.run_id, f"Requested alias: {body.alias}")

    def worker():
        try:
            # This should block until login completes or fails
            res = sf_org_login_web(alias=body.alias)
            RUNS.append_log(run.run_id, "Web login completed.")
            RUNS.set_result(run.run_id, res or {"ok": True})
        except Exception as e:
            RUNS.append_log(run.run_id, f"ERROR: {e}")
            RUNS.set_error(run.run_id, str(e))

    threading.Thread(target=worker, daemon=True).start()
    return {"runId": run.run_id}

@router.post("/query/login/sfdx-url")
def login_sfdx_url(body: LoginSfdxUrlBody):
    """
    Login using an SFDX auth URL. This can be sync (fast) or you can make it async like web login.
    """
    sfdx_url = (body.sfdxUrl or "").strip()
    if not sfdx_url:
        raise HTTPException(status_code=400, detail="sfdxUrl is required.")
    if not sfdx_url.lower().startswith("force://"):
        raise HTTPException(status_code=400, detail="Invalid SFDX Auth URL. It should start with force://")

    try:
        res = sf_org_login_sfdx_url(sfdx_url=sfdx_url, alias=body.alias)
        return {"ok": True, "result": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/query/login/status/{run_id}")
def login_status(run_id: str):
    """
    The frontend polls this endpoint to know whether login finished.
    """
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    # Shape: { status: "pending"|"success"|"error", logs: [...], result?:..., error?:... }
    payload: Dict[str, Any] = {
        "status": run.status,
        "logs": run.logs,
    }
    if run.status == "success":
        payload["result"] = run.result
    if run.status == "error":
        payload["error"] = run.error
    return payload

@router.post("/query/run")
def run_query(body: QueryBody):
    active = _active_target()
    if not active:
        raise HTTPException(status_code=400, detail="No active org selected. Please select an org first.")

    soql = _normalize_soql(body.query, body.includeDeleted)

    run = RUNS.create(kind="query")
    RUNS.append_log(run.run_id, f"Selected org: {active}")
    RUNS.append_log(run.run_id, f"SOQL: {soql}")

    def worker():
        try:
            result = sf_data_query(soql=soql, target_org=active)
            records = result.get("records") or []
            total_size = result.get("totalSize")
            RUNS.append_log(run.run_id, f"Returned records: {len(records)} (totalSize={total_size})")
            RUNS.set_result(run.run_id, {
                "totalSize": total_size,
                "records": records,
            })
        except Exception as e:
            RUNS.append_log(run.run_id, f"ERROR: {e}")
            RUNS.set_error(run.run_id, str(e))

    threading.Thread(target=worker, daemon=True).start()
    return {"runId": run.run_id}