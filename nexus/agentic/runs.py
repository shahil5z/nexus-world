"""Run registry. Run ids link scenario, seed, model/data version, outputs, critique and explanation."""
from __future__ import annotations

import secrets
import threading
from collections import OrderedDict
from datetime import datetime, timezone

MAX_RUNS = 200
_RUNS: "OrderedDict[str, dict]" = OrderedDict()
_LOCK = threading.Lock()


def new_run_id() -> str:
    return f"NEXUS-{datetime.now(timezone.utc).year}-{secrets.token_hex(4)}"


def save(record: dict):
    with _LOCK:
        _RUNS[record["run_id"]] = record
        while len(_RUNS) > MAX_RUNS:
            _RUNS.popitem(last=False)


def get(run_id: str) -> dict | None:
    with _LOCK:
        return _RUNS.get(run_id)
