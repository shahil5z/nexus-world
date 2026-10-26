import pytest
from pydantic import ValidationError

from nexus.domain.scenario import Intervention, Scenario
from nexus.domain.state import VARIABLES


def test_every_variable_fully_described():
    for v in VARIABLES.values():
        assert v.name and v.unit and v.description and v.source and v.update
        assert v.valid_range[0] < v.valid_range[1]


@pytest.mark.parametrize("kw", [
    dict(variable="gasoline_price", operation="multiply", value=0),
    dict(variable="gasoline_price", operation="multiply", value=11),
    dict(variable="gasoline_price", operation="add", value=1),
    dict(variable="unemployment", operation="add", value=60),
    dict(variable="cpi", operation="multiply", value=1.1),
    dict(variable="gasoline_price", operation="multiply", value=float("nan")),
    dict(variable="gasoline_price", operation="multiply", value=1.1, start_month=99),
    dict(variable="gasoline_price", operation="multiply", value=1.1, evil=1),
])
def test_invalid_interventions_rejected(kw):
    with pytest.raises(ValidationError):
        Intervention(**kw)


def test_scenario_limits():
    iv = Intervention(variable="gasoline_price", operation="multiply", value=1.1)
    with pytest.raises(ValidationError):
        Scenario(name="x", interventions=(iv, iv))
    with pytest.raises(ValidationError):
        Scenario(name="<script>")
