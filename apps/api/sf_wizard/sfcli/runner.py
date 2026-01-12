import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class SfCliResult:
    raw_stdout: str
    raw_stderr: str
    returncode: int
    json_data: Optional[Dict[str, Any]] = None

class SfCliError(Exception):
    pass

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _try_parse_json(stdout: str) -> Optional[Dict[str, Any]]:
    s = (stdout or "").strip()
    if not s:
        return None

    # 1) Happy path: whole stdout is JSON
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 2) Fallback: try to parse the last JSON object/array in stdout
    #    (useful if some banner/warning got printed before the JSON)
    last_obj = s.rfind("{")
    last_arr = s.rfind("[")
    start = max(last_obj, last_arr)
    if start >= 0:
        try:
            return json.loads(s[start:])
        except json.JSONDecodeError:
            return None

    return None

def run_sf(cmd: List[str], timeout_sec: int = 300) -> SfCliResult:
    #Run an sf CLI command: Forces SF CLI state into SF_WIZARD_DATA_DIR by overriding HOME.
    env = os.environ.copy()

    data_dir = env.get("SF_WIZARD_DATA_DIR", "/data")
    # Put everything sf-related under /data so it persists in Docker and in native mode.
    home_dir = os.path.join(data_dir, "sfcli-home")
    _ensure_dir(home_dir)

    # Most CLIs respect HOME; SF CLI uses it for .sf/.sfdx locations depending on version/setup.
    env["HOME"] = home_dir

    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        env=env,
    )

    res = SfCliResult(
        raw_stdout=p.stdout or "",
        raw_stderr=p.stderr or "",
        returncode=p.returncode,
        json_data=_try_parse_json(p.stdout or ""),
    )

    return res