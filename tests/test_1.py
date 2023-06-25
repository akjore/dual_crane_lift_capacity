import matplotlib.pyplot as plt
import pytest
import yaml

import dualCraneLiftCapacity.dual_crane_lift

KEYS = ['crane_curve_a', 'crane_curve_b', 'crane_radius_a', 'crane_radius_b', 'rigging_weight_a', 'rigging_weight_b', 'weight_uncertainty_factor', 'cog_uncertainty_factor', 'tilt_factor', 'lift_point_a', 'lift_point_b', 'weight', 'cog']
SOME_KEYS = ['crane_radius_a', 'crane_radius_b', 'rigging_weight_a', 'rigging_weight_b', 'weight_uncertainty_factor', 'cog_uncertainty_factor', 'tilt_factor', 'lift_point_a', 'lift_point_b', 'weight', 'cog']


@pytest.fixture()
def input_sample():
    sample = {'Sample 1': {
        'crane_curve_a': 'S7000.main.fixed_1.5',
        'crane_curve_b': 'S7000.main.fixed_1.5',
        'crane_radius_a': '50.0 m',
        'crane_radius_b': '50.0 m',
        'rigging_weight_a': '495 t',
        'rigging_weight_b': '380 t',
        'weight_uncertainty_factor': '1.03',
        'cog_uncertainty_factor': '1.02',
        'tilt_factor': '1.02',
        'lift_point_a': '[43.73 m]',
        'lift_point_b': '[82. m]',
        'weight': '10295 t',
        'cog': '61.668 m'
    }}
    return sample


def test_valid_input(input_sample):
    """
    Check that the sample case runs successfully

    Args:
        input_sample: dict representing a valid input file
    """
    ret = dualCraneLiftCapacity.dual_crane_lift.main(data=yaml.dump(input_sample), interactive=False)

    assert type(ret) is dict
    assert type(ret['Sample 1']) is plt.Figure


def test_crane_curve(input_sample):
    """
    Check that specifying a non-existent crane curve returns an error

    Args:
        input_sample: dict representing a valid input file
    """
    input_sample['Sample 1']['crane_curve_a'] = "blabla"

    with pytest.raises(KeyError):
        dualCraneLiftCapacity.dual_crane_lift.main(data=yaml.dump(input_sample), interactive=False)


@pytest.mark.parametrize("key", KEYS)
def test_missing_parameter(input_sample, key):
    """
    Check that any missing parameter returns a KeyError

    Args:
        input_sample: dict representing a valid input file
        key: key to be removed from input_sample
    """
    del input_sample['Sample 1'][key]
    with pytest.raises(KeyError):
        dualCraneLiftCapacity.dual_crane_lift.main(data=yaml.dump(input_sample), interactive=False)


@pytest.mark.parametrize("key", SOME_KEYS)
def test_wrong_dimension(input_sample, key):
    """
    Check that wrong dimensions return a ValueError

    Args:
        input_sample: dict representing a valid input file
        key: key with dimensionality to be modified
    """
    input_sample['Sample 1'][key] = '1 cubic meter'  # valid inputs are either lengths, masses, or dimensionless.
    with pytest.raises(ValueError):
        dualCraneLiftCapacity.dual_crane_lift.main(data=yaml.dump(input_sample), interactive=False)


def test_no_input():
    """
    Check that no or empty input returns an Exception
    """
    with pytest.raises(Exception):
        dualCraneLiftCapacity.dual_crane_lift.main(data='', interactive=False)


def test_wrong_input():
    """
    Check that wrong input returns a TypeError
    """
    with pytest.raises(TypeError):
        dualCraneLiftCapacity.dual_crane_lift.main(data='abc123:', interactive=False)
