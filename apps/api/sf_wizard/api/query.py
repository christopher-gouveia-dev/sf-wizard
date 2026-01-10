from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
import threading

from sf_wizard.core.runs import RUNS
from sf_wizard.sfcli.query import sf_data_query
from sf_wizard.core.config import data_dir
from sf_wizard.core.storage import read_json, ensure_dir

router = APIRouter()

class QueryBody(BaseModel):
    query: str
    includeDeleted: bool = False

def _active_alias() -> Optional[str]:
    ensure_dir(data_dir())
    recents = read_json(data_dir() / "recent_orgs.json", default={"last_selected_alias": None})
    return recents.get("last_selected_alias")

def _normalize_soql(soql: str, include_deleted: bool) -> str:
    s = (soql or "").strip()
    if include_deleted:
        # SOQL keyword to include deleted records is "ALL ROWS"
        # If user already included it, don't duplicate.
        if "ALL ROWS" not in s.upper():
            s = f"{s} ALL ROWS"
    return s

@router.post("/query/run")
def run_query(body: QueryBody):
    active = _active_alias()
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
