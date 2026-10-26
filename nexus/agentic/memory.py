"""In-memory multi-turn session state with explicit scenario slots. The baseline is immutable."""
from __future__ import annotations

import secrets
import threading
import time
from collections import OrderedDict

SLOTS = ("A", "B", "C")
TTL_S, MAX_SESSIONS = 3600, 500


class SessionStore:
    def __init__(self):
        self._s: "OrderedDict[str, dict]" = OrderedDict()
        self._lock = threading.Lock()

    def get_or_create(self, sid: str | None) -> tuple[str, dict]:
        now = time.time()
        with self._lock:
            for k in [k for k, v in self._s.items() if now - v["touched"] > TTL_S]:
                del self._s[k]
            if sid and sid in self._s:
                s = self._s[sid]
                self._s.move_to_end(sid)
            else:
                sid = sid or secrets.token_hex(8)
                s = {"baseline": {"name": "baseline", "interventions": [], "immutable": True},
                     "slots": {}, "history": [], "created": now}
                self._s[sid] = s
                while len(self._s) > MAX_SESSIONS:
                    self._s.popitem(last=False)
            s["touched"] = now
            return sid, s

    @staticmethod
    def free_slot(s: dict) -> str:
        for k in SLOTS:
            if k not in s["slots"]:
                return k
        return min(s["slots"], key=lambda k: s["slots"][k]["updated"])  # replace oldest

    @staticmethod
    def compose(base: list[dict], new: list[dict]) -> list[dict]:
        """Add new interventions; one on the same variable and start month replaces the old one."""
        keyed = {(i["variable"], i["start_month"]): i for i in base}
        for i in new:
            keyed[(i["variable"], i["start_month"])] = i
        return list(keyed.values())

    @staticmethod
    def put(s: dict, slot: str, scenario: dict, horizon: int, run_id: str):
        if slot not in SLOTS:
            raise ValueError("slot must be A, B or C")
        s["slots"][slot] = {"scenario": scenario, "horizon_months": horizon, "run_id": run_id, "updated": time.time()}

    @staticmethod
    def public(s: dict) -> dict:
        return {"baseline": s["baseline"], "slots": {k: {kk: v[kk] for kk in ("scenario", "horizon_months", "run_id")}
                                                     for k, v in sorted(s["slots"].items())},
                "turns": len(s["history"])}


SESSIONS = SessionStore()
