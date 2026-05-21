"""Function testing of the package."""
# ruff: noqa: S101
import pytest

from dual_crane_lift_capacity.dual_crane_lift_capacity import DualCraneLiftCapacity
from dual_crane_lift_capacity.lift_cases import LiftCases


@pytest.fixture
def input_m10() -> dict:
    """Sample input data for test purposes.

    Refer to Mariner drawing file, C127-AD-V-MA-7004, Rev 02, Page 95.
    """
    return """
cases:
  - case: M10
    crane_curve_a: S7000.main.fixed_1.5
    crane_curve_b: S7000.main.fixed_1.5
    crane_radius_a: 50.0 m
    crane_radius_b: 50.0 m
    rigging_weight_a: 495 t
    rigging_weight_b: 380 t
    weight_uncertainty_factor: 1.015
    cog_uncertainty_factor: 1.01
    tilt_factor: 1.02
    lift_point_a: 41.050 m
    lift_point_b: 82.0 m
    weight: 10375 t
    cog: 61.780 m
    cog_envelope: [(61.780-0.560) m, (61.780+0.484) m]
"""


@pytest.fixture
def input_m10_float() -> dict:
    """Sample input data for test purposes.

    Refer to Mariner drawing file, C127-AD-V-MA-7004, Rev 02, Page 95.
    """
    return """
cases:
  - case: M10_float
    crane_curve_a: S7000.main.fixed_1.5
    crane_curve_b: S7000.main.fixed_1.5
    crane_radius_a: 50.0 m
    crane_radius_b: 50.0 m
    rigging_weight_a: 435 t
    rigging_weight_b: 360 t
    weight_uncertainty_factor: 1.03
    cog_uncertainty_factor: 1.02
    tilt_factor: 1.02
    lift_point_a: 43.230 m
    float_a: 3.030 m
    lift_point_b: 82.0 m
    weight: 9410 t
    cog: 62.750 m
    cog_envelope: [(62.750-1.500) m, (62.750+1.500) m]
"""


def test_results_m10(input_m10: str) -> None:
    """Check that M10 returns expected results.

    :param input_sample: dict representing a valid input file
    """
    liftcases = LiftCases().from_yaml(input_m10)
    ret = DualCraneLiftCapacity(liftcases)

    # check that the weight margin is approximately 0, with +/- 0.5 t tolerance
    assert ret.weight_margin[0].magnitude == pytest.approx(0, abs=0.5)

    # check that the lift capacity margin at the CoG is approximately 242t
    assert (ret.lift_capacity_at_cog[0]-liftcases.liftcases[0].weight).magnitude == pytest.approx(242, abs=0.5)


def test_results_m10_float(input_m10_float: str) -> None:
    """Check that M10 returns expected results.

    :param input_sample: dict representing a valid input file
    """
    liftcases = LiftCases().from_yaml(input_m10_float)
    ret = DualCraneLiftCapacity(liftcases)

    # check that the weight margin is approximately 1046, with +/- 0.5 t tolerance
    assert ret.weight_margin[0].magnitude == pytest.approx(1046, abs=0.5)

    # check that the lift capacity margin at the CoG is approximately 1046t
    assert (ret.lift_capacity_at_cog[0]-liftcases.liftcases[0].weight).magnitude == pytest.approx(1046, abs=0.5)

    # check that the lift capacity margin at the CoG envelope is approximately 1046t
    max_lift_capacity = (ret.lift_capacity_at_cog[0]-liftcases.liftcases[0].weight).magnitude
    assert max_lift_capacity == pytest.approx(1046, abs=0.5)

    # check width at top of capacity curve
    x = ret.lift_capacity_curve_x[0].magnitude
    y = ret.lift_capacity_curve_y[0].magnitude
    idx = len(y) // 2
    w = x[idx] - x[idx-1]
    assert w == pytest.approx(3.010, abs=0.001)
    assert liftcases.liftcases[0].cog.magnitude - x[idx-1] == pytest.approx(1.510, abs=0.001)
    assert x[idx] - liftcases.liftcases[0].cog.magnitude == pytest.approx(1.500, abs=0.001)

    # check that the intercepts with the crane capacity curve for the current weight are correct
    # Note that SAI's drawing contains some mistake.
    cog_max_min = ret.cog_limits_at_given_weight[0].magnitude
    assert cog_max_min[0] == pytest.approx(58.932, abs=0.001)
    assert cog_max_min[1] == pytest.approx(62.750+1.5+4*0.5, abs=0.001)
