from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from sf_wizard.sfcli.orgs import sf_list_orgs
from sf_wizard.core.config import data_dir
from sf_wizard.core.storage import read_json, write_json_atomic, ensure_dir

router = APIRouter()

RECENTS_FILE = "recent_orgs.json"

def _recents_path():
    d = data_dir()
    ensure_dir(d)
    return d / RECENTS_FILE

def _load_recents() -> Dict[str, Any]:
    return read_json(_recents_path(), default={"last_selected_alias": None, "orgs": {}})

def _save_recents(data: Dict[str, Any]) -> None:
    write_json_atomic(_recents_path(), data)

class SelectOrgBody(BaseModel):
    alias: str

@router.get("/orgs")
def get_orgs():
    try:
        result = sf_list_orgs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    recents = _load_recents()
    recent_map = recents.get("orgs", {})
    last_selected = recents.get("last_selected_alias")

    # Flatten org list into a single list for UI convenience
    orgs: List[Dict[str, Any]] = []
    for group_key in ("scratchOrgs", "nonScratchOrgs", "other", "sandboxes", "devHubs"):
        group = result.get(group_key)
        if isinstance(group, list):
            for o in group:
                alias = o.get("alias") or o.get("username")
                if not alias:
                    continue
                orgs.append({
                    "alias": alias,
                    "username": o.get("username"),
                    "orgId": o.get("orgId") or o.get("id"),
                    "isDefault": bool(o.get("isDefaultUsername") or o.get("isDefault")),
                    "isDevHub": bool(o.get("isDevHub")),
                    "connectedStatus": o.get("connectedStatus"),
                    "lastSelectedAt": recent_map.get(alias, {}).get("lastSelectedAt"),
                })

    # Sort: recent first (descending), then alias
    def sort_key(o: Dict[str, Any]):
        ts = o.get("lastSelectedAt")
        return (0 if ts else 1, -(int(datetime.fromisoformat(ts).timestamp()) if ts else 0), o["alias"].lower())

    orgs.sort(key=sort_key)

    return {"activeAlias": last_selected, "orgs": orgs}

@router.post("/orgs/select")
def select_org(body: SelectOrgBody):
    recents = _load_recents()
    alias = body.alias.strip()
    now = datetime.now(timezone.utc).astimezone().isoformat()

    recents["last_selected_alias"] = alias
    recents.setdefault("orgs", {})
    recents["orgs"][alias] = {"lastSelectedAt": now}
    _save_recents(recents)
    return {"activeAlias": alias, "lastSelectedAt": now}

@router.get("/orgs/active")
def active_org():
    recents = _load_recents()
    return {"activeAlias": recents.get("last_selected_alias")}
