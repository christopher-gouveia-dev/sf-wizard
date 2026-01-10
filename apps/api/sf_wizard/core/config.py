import os
from pathlib import Path

def data_dir() -> Path:
    # Docker sets SF_WIZARD_DATA_DIR=/data
    # Local default: <repo>/data (if provided by env), else ./data relative to current working directory.
    raw = os.environ.get("SF_WIZARD_DATA_DIR")
    if raw:
        return Path(raw)
    return Path("data")
