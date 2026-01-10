import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator

from sf_wizard.core.storage import read_json, write_json_atomic, ensure_dir
from sf_wizard.core.config import data_dir

@dataclass
class Run:
    run_id: str
    kind: str
    status: str = "running"  # running|success|error
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    logs: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class RunManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: Dict[str, Run] = {}
        self._dir = data_dir() / "runs"
        ensure_dir(self._dir)

    def _path(self, run_id: str) -> Path:
        return self._dir / f"{run_id}.json"

    def create(self, kind: str) -> Run:
        run_id = uuid.uuid4().hex
        run = Run(run_id=run_id, kind=kind)
        with self._lock:
            self._runs[run_id] = run
        self._persist(run)
        return run

    def get(self, run_id: str) -> Optional[Run]:
        with self._lock:
            run = self._runs.get(run_id)
        if run:
            return run
        # Lazy load from disk (useful after restart)
        data = read_json(self._path(run_id), default=None)
        if not data:
            return None
        run = Run(
            run_id=data["run_id"],
            kind=data["kind"],
            status=data.get("status", "running"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            logs=data.get("logs", []),
            result=data.get("result"),
            error=data.get("error"),
        )
        with self._lock:
            self._runs[run_id] = run
        return run

    def append_log(self, run_id: str, line: str) -> None:
        run = self.get(run_id)
        if not run:
            return
        with self._lock:
            run.logs.append(line)
            run.updated_at = time.time()
        self._persist(run)

    def set_result(self, run_id: str, result: Dict[str, Any]) -> None:
        run = self.get(run_id)
        if not run:
            return
        with self._lock:
            run.result = result
            run.status = "success"
            run.updated_at = time.time()
        self._persist(run)

    def set_error(self, run_id: str, error: str) -> None:
        run = self.get(run_id)
        if not run:
            return
        with self._lock:
            run.error = error
            run.status = "error"
            run.updated_at = time.time()
        self._persist(run)

    def _persist(self, run: Run) -> None:
        write_json_atomic(self._path(run.run_id), {
            "run_id": run.run_id,
            "kind": run.kind,
            "status": run.status,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "logs": run.logs,
            "result": run.result,
            "error": run.error,
        })

RUNS = RunManager()

def sse_stream(run_id: str) -> Iterator[str]:
    """Very simple SSE stream: emits new log lines until run finishes."""
    last_idx = 0
    # Send an initial ping so the client can attach quickly
    yield "event: ping\ndata: {}\n\n"
    while True:
        run = RUNS.get(run_id)
        if not run:
            payload = json.dumps({"message": "Run not found"})
            yield f"event: error\ndata: {payload}\n\n"
            return

        # Emit new logs
        while last_idx < len(run.logs):
            line = run.logs[last_idx]
            payload = json.dumps({"line": line})
            yield f"event: log\ndata: {payload}\n\n"
            last_idx += 1

        # If finished, emit status and stop
        if run.status in ("success", "error"):
            payload = json.dumps({"status": run.status})
            yield f"event: status\ndata: {payload}\n\n"
            return

        time.sleep(0.25)
