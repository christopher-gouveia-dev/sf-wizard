from typing import Any, Dict, List

from sf_wizard.sfcli.runner import run_sf, SfCliError

def sf_list_orgs() -> Dict[str, Any]:
    # `sf org list --json`
    res = run_sf(["sf", "org", "list"])
    if res.returncode != 0:
        raise SfCliError(res.raw_stderr or "sf org list failed")
    if not res.json_data:
        raise SfCliError("sf org list did not return valid JSON")
    return res.json_data.get("result", {})
