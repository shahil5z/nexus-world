from tests.conftest import GAS30


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["llm_required"] is False


def test_run_and_validate(client):
    r = client.post("/simulation/run", json={"scenario": GAS30, "horizon_months": 12})
    assert r.status_code == 200
    j = r.json()
    assert len(j["months"]) == 12 and j["reality_guard"]["tier"] in {"HIGH", "MEDIUM", "LOW", "OOD"}
    assert "X-Run-Id" in r.headers
    assert client.post("/simulation/validate", json={"scenario": GAS30}).status_code == 200


def test_mc_and_compare(client):
    r = client.post("/simulation/monte-carlo", json={"scenario": GAS30, "n_paths": 100, "horizon_months": 12, "seed": 3})
    assert r.status_code == 200 and "not confidence intervals" in r.json()["range_type"]
    r2 = client.post("/simulation/monte-carlo", json={"scenario": GAS30, "n_paths": 100, "horizon_months": 12, "seed": 3})
    assert r.json()["summary"] == r2.json()["summary"]
    r3 = client.post("/simulation/monte-carlo", json={"scenario": GAS30, "n_paths": 50, "horizon_months": 6, "decompose": True})
    assert r3.status_code == 200 and "parameters" in r3.json()["uncertainty_decomposition"]["without"]
    b = dict(GAS30, name="b")
    r = client.post("/scenario/compare", json={"scenarios": [GAS30, b], "n_paths": 50, "horizon_months": 6})
    assert r.status_code == 200 and r.json()["scenarios"] == ["baseline", "gas30", "b"]


def test_errors_are_structured_without_traces(client):
    r = client.post("/simulation/run", json={"scenario": {"name": "x", "interventions": [
        {"variable": "gasoline_price", "operation": "multiply", "value": 99}]}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request"
    assert "Traceback" not in r.text
    r = client.post("/simulation/monte-carlo", json={"scenario": GAS30, "n_paths": 2000, "horizon_months": 36})
    assert r.status_code == 422
    r = client.post("/scenario/compare", json={"scenarios": [{"name": "baseline"}]})
    assert r.status_code == 422
    r = client.post("/simulation/run", content=b"x" * 70000, headers={"content-type": "application/json"})
    assert r.status_code == 413
    r = client.post("/simulation/run", json={"scenario": {"name": "u", "interventions": [
        {"variable": "unemployment", "operation": "add", "value": -20}]}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_scenario"


def test_model_endpoints(client):
    assert client.get("/model/status").status_code == 200
    j = client.get("/model/evaluate").json()
    assert "backtests" in j and "test" in j["holdout_metrics"]


def test_rate_limit_compute(client):
    import nexus.api.app as appmod
    appmod._hits.clear()
    body = {"scenario": {"name": "x", "interventions": []}, "horizon_months": 3}
    codes = [client.post("/simulation/validate", json=body).status_code for _ in range(appmod.RATE_LIMIT[0] + 1)]
    appmod._hits.clear()
    assert codes[:-1] == [200] * appmod.RATE_LIMIT[0] and codes[-1] == 429


def test_rate_limit(client):
    import nexus.api.app as appmod
    appmod._hits.clear()
    codes = [client.get("/health").status_code for _ in range(appmod.READ_RATE_LIMIT[0] + 1)]
    appmod._hits.clear()
    assert codes[-1] == 429 and codes[0] == 200


def test_no_training_endpoint(client):
    assert client.post("/model/train").status_code in (404, 405)
