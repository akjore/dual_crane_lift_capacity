"""Function testing of the package."""
# ruff: noqa: S101
import pint
import pytest

from dual_crane_lift_capacity.dual_crane_lift_capacity import DualCraneLiftCapacity
from dual_crane_lift_capacity.lift_cases import LiftCases

KEYS = ["crane_curve_a", "crane_curve_b", "crane_radius_a", "crane_radius_b", "rigging_weight_a",
        "rigging_weight_b", "weight_uncertainty_factor", "cog_uncertainty_factor", "tilt_factor",
        "lift_point_a", "lift_point_b", "weight", "cog"]
SOME_KEYS = ["crane_radius_a", "crane_radius_b", "rigging_weight_a", "rigging_weight_b",
             "weight_uncertainty_factor", "cog_uncertainty_factor", "tilt_factor", "lift_point_a",
             "lift_point_b", "weight", "cog"]


@pytest.fixture
def input_sample() -> dict:
    """Sample input data for test purposes."""
    return """
cases:
  - &base_case
    case: Sample 1
    crane_curve_a: S7000.main.fixed_1.5
    crane_curve_b: S7000.main.fixed_1.5
    crane_radius_a: 50.0 m
    crane_radius_b: 50.0 m
    rigging_weight_a: 495 t
    rigging_weight_b: 380 t
    weight_uncertainty_factor: 1.03
    cog_uncertainty_factor: 1.02
    tilt_factor: 1.02
    lift_point_a: 43.73 m
    lift_point_b: 82.0 m
    weight: 10295 t
    cog: 61.668 m
"""

def test_valid_input(input_sample: str) -> None:
    """Check that the sample case runs successfully.

    :param input_sample: str representing a valid input file
    """
    lift_cases = LiftCases().from_yaml(input_sample)

    ret = DualCraneLiftCapacity(lift_cases)
    assert isinstance(ret, DualCraneLiftCapacity)


def test_crane_curve(input_sample: str) -> None:
    """Check that specifying a non-existent crane curve returns an error.

    :param input_sample: str representing a valid input file
    """
    # Load sample
    lift_cases = LiftCases().from_yaml(input_sample)

    # Modify sample to use a non-existing crane curve
    with pytest.raises(KeyError):
        lift_cases.liftcases[0].crane_curve_a = "blabla"


@pytest.mark.parametrize("key", KEYS)
def test_missing_parameter(input_sample: str, key: str) -> None:
    """Check that any missing parameter returns a KeyError.

    :param input_sample: str representing a valid input file
    :param key: key to be removed from input_sample
    """
    # Delete key from the input_sample and try to load
    lines = input_sample.splitlines()
    key_ = key + ":"
    input_list = [line for line in lines if key_ not in line]
    revised_input = "\n".join(input_list)

    with pytest.raises(KeyError):
        LiftCases().from_yaml(revised_input)


@pytest.mark.parametrize("key", SOME_KEYS)
def test_wrong_dimension(input_sample: str, key: str) -> None:
    """Check that wrong dimensions return a ValueError.

    :param input_sample: str representing a valid input file
    :param key: key with dimensionality to be modified
    """
    # valid inputs are either lengths, masses, or dimensionless.
    # Load a valid case
    lift_cases = LiftCases().from_yaml(input_sample)

    # Change the input using something with the wrong dimension
    with pytest.raises(pint.DimensionalityError):
        setattr(lift_cases.liftcases[0], key, "1 cubic meter")


def test_no_input() -> None:
    """Check that no or empty input returns an Exception."""
    with pytest.raises(TypeError):
        LiftCases().from_yaml("")


def test_wrong_input() -> None:
    """Check that wrong input returns a KeyError."""
    with pytest.raises(KeyError):
        LiftCases().from_yaml("abc123:")
