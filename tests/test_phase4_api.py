"""Phase 4 backend additions: /api mount, NDJSON stream, suggestions, causal graph, p10/p90 bands."""
import json

import pytest
from fastapi.testclient import TestClient

from nexus.agentic.guardrails import check_input
from nexus.agentic.intent_fallback import parse
from nexus.api.vercel_app import app


@pytest.fixture(scope="module")
def c(monkeypatch_module=None):
    mp = pytest.MonkeyPatch()
    mp.setenv("NEXUS_DISABLE_LLM", "1")
    yield TestClient(app)
    mp.undo()


def test_mounted_under_api(c):
    assert c.get("/api/health").json()["status"] == "ok"
    assert c.get("/health").status_code == 404


def test_stream_emits_real_stages_then_result(c):
    with c.stream("POST", "/api/agent/analyze/stream", json={"question": "What happens if gasoline prices rise 20% for 12 months?", "n_paths": 100}) as r:
        lines = [json.loads(x) for x in r.iter_lines() if x]
    stages = [l["stage"] for l in lines if l["type"] == "trace"]
    assert stages[0] == "input_guardrail" and "reality_guard" in stages and "simulation" in stages and "grounding" in stages
    assert stages.index("reality_guard") < stages.index("simulation")
    res = lines[-1]
    assert res["type"] == "result" and res["result"]["status"] == "ok"
    assert len([l for l in lines if l["type"] == "trace"]) == len(res["result"]["trace"])


def test_suggestions_supported_by_backend(c):
    s = c.get("/api/agent/suggestions").json()["suggestions"]
    assert len(s) >= 4
    for q in s:
        assert check_input(q)[0], q
        assert parse(q).action in ("simulate", "explain_model"), q


def test_causal_graph(c):
    g = c.get("/api/knowledge/causal-graph").json()
    assert g["version"] and len(g["edges"]) >= 10


def test_bands_include_p10_p90(c):
    r = c.post("/api/simulation/monte-carlo", json={"scenario": {"name": "g", "interventions": [
        {"variable": "gasoline_price", "operation": "multiply", "value": 1.2}]}, "n_paths": 100}).json()
    b = r["bands"]["vmt"]["g"]
    assert all(lo <= m <= hi for lo, m, hi in zip(b["p10"], b["median"], b["p90"]))
