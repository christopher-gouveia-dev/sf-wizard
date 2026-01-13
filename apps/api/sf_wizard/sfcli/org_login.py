from typing import Any, Dict, Optional
from sf_wizard.sfcli.runner import run_sf

def sf_org_login_web(alias: Optional[str] = None) -> Dict[str, Any]:
    cmd = ["sf", "org", "login", "web"]
    if alias:
        cmd += ["--alias", alias]
    # optionally: cmd += ["--set-default"]  (mais en v0.1.0.2, tu gères l’état dans SF Wizard, donc pas nécessaire)
    cmd += ["--json"]
    res = run_sf(cmd, timeout_sec=600)
    if res.returncode != 0:
        raise RuntimeError(res.raw_stderr or res.raw_stdout or "sf org login web failed")
    if not res.json_data:
        raise RuntimeError("sf org login web did not return JSON")
    return res.json_data

def sf_org_login_sfdx_url(sfdx_url: str, alias: Optional[str] = None) -> Dict[str, Any]:
    # sf org login sfdx-url reads from stdin if not using --sfdx-url-file,
    # safest is to pass via stdin. Here we use a fileless approach by echoing via shell would be messy,
    # so we can write a temp file if you prefer. Minimal version: use a temp file.
    import tempfile, os

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(sfdx_url)
        tmp = f.name

    try:
        cmd = ["sf", "org", "login", "sfdx-url", "--sfdx-url-file", tmp]
        if alias:
            cmd += ["--alias", alias]
        cmd += ["--json"]
        res = run_sf(cmd, timeout_sec=180)
        if res.returncode != 0:
            raise RuntimeError(res.raw_stderr or res.raw_stdout or "sf org login sfdx-url failed")
        if not res.json_data:
            raise RuntimeError("sf org login sfdx-url did not return JSON")
        return res.json_data
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass