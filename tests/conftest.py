import pytest

from nexus.data.pipeline import run_pipeline
from nexus.simulation.engine import SimulationEngine


@pytest.fixture(scope="session")
def pipeline():
    return run_pipeline()


@pytest.fixture(scope="session")
def engine():
    return SimulationEngine()


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from nexus.api.app import app
    return TestClient(app)


GAS30 = {"name": "gas30", "interventions": [{"variable": "gasoline_price", "operation": "multiply", "value": 1.3,
                                              "duration_months": 12}]}
