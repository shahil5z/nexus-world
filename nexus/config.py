"""Central configuration: paths, versions, limits, splits. No secrets here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"

PIPELINE_VERSION = "1.0.0"
ENGINE_VERSION = "1.0.0"

# Temporal split (inclusive month boundaries). Respect time order, never shuffle.
TRAIN_END = "2012-12-01"
VAL_END = "2017-12-01"   # validation: 2013-01 .. 2017-12; test: 2018-01 .. last month

# Historical price-shock windows used for rolling-origin backtests.
SHOCK_WINDOWS = {
    "2008_oil_spike": ("2007-07-01", "2009-06-01"),
    "2014_2016_collapse": ("2014-07-01", "2016-06-01"),
    "2022_spike": ("2021-07-01", "2023-06-01"),
}

DEFAULT_SEED = 42

# Request limits (public demo caps).
MAX_HORIZON_MONTHS = 36
MAX_PATHS = 2000
MAX_SCENARIOS = 4
MAX_INTERVENTIONS = 4

# Documented physical assumptions (see docs/DATA-AND-MODEL.md).
FLEET_MPG = 22.0                 # ASSUMPTION: average on-road fleet fuel economy, miles per gallon
CO2_KG_PER_GALLON = 8.887        # EPA published factor for gasoline combustion
