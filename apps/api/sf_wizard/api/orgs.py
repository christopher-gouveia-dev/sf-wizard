from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List, Optional

from sf_wizard.sfcli.orgs import sf_list_orgs

router = APIRouter()

# Groups returned by sf org list --json (result.*)
GROUP_KEYS = ("scratchOrgs", "nonScratchOrgs", "other", "sandboxes", "devHubs")


def _coerce_org_id(o: Dict[str, Any]) -> Optional[str]:
    # Some outputs may use orgId; older shapes may use id.
    return o.get("orgId") or o.get("id")


def _as_list(x: Any) -> List[Dict[str, Any]]:
    if isinstance(x, list):
        return [i for i in x if isinstance(i, dict)]
    return []


def _primary_label(aliases: List[str], username: Optional[str]) -> str:
    if aliases:
        return aliases[0].lower()
    return (username or "").lower()


def _normalize_orgs(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert sf org list result into a flat list:
    [
      {
        orgId, username, loginUrl, instanceUrl,
        aliases: [...],
        isScratch, isSandbox, isDevHub,
        isDefaultUsername, isDefaultDevHubUsername,
        connectedStatus, lastUsed
      },
      ...
    ]
    """
    by_org: Dict[str, Dict[str, Any]] = {}

    for group_key in GROUP_KEYS:
        for o in _as_list(result.get(group_key)):
            org_id = _coerce_org_id(o)
            username = o.get("username")
            alias = o.get("alias")

            # Skip entries with no orgId and no username: nothing stable to identify
            if not org_id and not username:
                continue

            key = org_id or f"username:{username}"

            existing = by_org.get(key)
            if not existing:
                existing = {
                    "orgId": org_id,
                    "username": username,
                    "loginUrl": o.get("loginUrl"),
                    "instanceUrl": o.get("instanceUrl"),
                    "aliases": [],
                    "isScratch": bool(o.get("isScratch")),
                    "isSandbox": bool(o.get("isSandbox")),
                    "isDevHub": bool(o.get("isDevHub")),
                    "isDefaultUsername": bool(o.get("isDefaultUsername") or o.get("isDefault")),
                    "isDefaultDevHubUsername": bool(o.get("isDefaultDevHubUsername")),
                    "connectedStatus": o.get("connectedStatus"),
                    "lastUsed": o.get("lastUsed"),
                }
                by_org[key] = existing

            # Merge fields if missing
            if not existing.get("orgId") and org_id:
                existing["orgId"] = org_id
            if not existing.get("username") and username:
                existing["username"] = username
            if not existing.get("loginUrl") and o.get("loginUrl"):
                existing["loginUrl"] = o.get("loginUrl")
            if not existing.get("instanceUrl") and o.get("instanceUrl"):
                existing["instanceUrl"] = o.get("instanceUrl")

            # Merge flags
            existing["isScratch"] = bool(existing.get("isScratch") or o.get("isScratch"))
            existing["isSandbox"] = bool(existing.get("isSandbox") or o.get("isSandbox"))
            existing["isDevHub"] = bool(existing.get("isDevHub") or o.get("isDevHub"))
            existing["isDefaultUsername"] = bool(existing.get("isDefaultUsername") or o.get("isDefaultUsername") or o.get("isDefault"))
            existing["isDefaultDevHubUsername"] = bool(existing.get("isDefaultDevHubUsername") or o.get("isDefaultDevHubUsername"))

            # lastUsed: keep the max lexicographically if both are ISO strings
            lu = o.get("lastUsed")
            if lu and (not existing.get("lastUsed") or str(lu) > str(existing["lastUsed"])):
                existing["lastUsed"] = lu

            # aliases: collect unique
            if alias:
                aliases = existing.setdefault("aliases", [])
                if alias not in aliases:
                    aliases.append(alias)

    # Sort aliases within each org (stable display)
    for org in by_org.values():
        org["aliases"] = sorted(org.get("aliases") or [], key=lambda s: s.lower())

    orgs = list(by_org.values())

    # Sort orgs: default usernames first, then lastUsed desc, then label
    def sort_key(o: Dict[str, Any]):
        is_def = 0 if o.get("isDefaultUsername") else 1
        # lastUsed is ISO string; sorting desc: use reverse later or negate with tuple trick
        last_used = o.get("lastUsed") or ""
        label = _primary_label(o.get("aliases") or [], o.get("username"))
        return (is_def, last_used, label)

    # We want lastUsed DESC, so sort ascending then reverse on lastUsed portion
    # Easier: sort with key and reverse=True but would reverse default flag too.
    # So do a two-pass stable sort:
    orgs.sort(key=lambda o: _primary_label(o.get("aliases") or [], o.get("username")))
    orgs.sort(key=lambda o: (o.get("lastUsed") or ""), reverse=True)
    orgs.sort(key=lambda o: 0 if o.get("isDefaultUsername") else 1)

    return orgs


@router.get("/orgs")
def get_orgs():
    try:
        result = sf_list_orgs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    payload = result.get("result") if isinstance(result, dict) else None
    orgs = _normalize_orgs(payload or {})

    return {"orgs": orgs}
