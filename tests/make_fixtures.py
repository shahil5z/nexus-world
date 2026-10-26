import json

from nexus.simulation.engine import SimulationEngine
from tests.test_regression import FIX, compute

if __name__ == "__main__":
    FIX.write_text(json.dumps(compute(SimulationEngine()), indent=1))
    print("wrote", FIX)
