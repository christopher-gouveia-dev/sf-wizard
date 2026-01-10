import json
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

def run_sf(cmd: List[str], timeout_sec: int = 300) -> SfCliResult:
    # Always enforce JSON output if the command supports it.
    if "--json" not in cmd:
        cmd = cmd + ["--json"]

    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )

    res = SfCliResult(
        raw_stdout=p.stdout or "",
        raw_stderr=p.stderr or "",
        returncode=p.returncode,
        json_data=None,
    )

    # Try to parse JSON when possible
    stdout = (p.stdout or "").strip()
    if stdout:
        try:
            res.json_data = json.loads(stdout)
        except json.JSONDecodeError:
            # Keep json_data as None; caller decides how strict to be.
            res.json_data = None

    return res
