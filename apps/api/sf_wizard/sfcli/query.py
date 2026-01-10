from typing import Any, Dict, Optional

from sf_wizard.sfcli.runner import run_sf, SfCliError

def sf_data_query(soql: str, target_org: str) -> Dict[str, Any]:
    # `sf data query --query <SOQL> -o <alias> --json`
    res = run_sf(["sf", "data", "query", "--query", soql, "-o", target_org])
    if res.returncode != 0:
        raise SfCliError(res.raw_stderr or "sf data query failed")
    if not res.json_data:
        raise SfCliError("sf data query did not return valid JSON")
    return res.json_data.get("result", {})
