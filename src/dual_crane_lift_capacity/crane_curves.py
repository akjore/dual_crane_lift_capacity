import logging
import os
import pkg_resources

import numpy as np
import pint
import yaml

from . import Q, ureg

logger = logging.getLogger(__name__)


def _load_crane_curves():
    # loads and returns the lift curves defined in the .yaml file
    # alt_file = os.path.join(os.path.dirname(__file__), 'crane_curves.yaml')
    alt_file = pkg_resources.resource_filename(__name__, 'crane_curves.yaml')
    crane_curve_file = os.getenv('CRANE_CURVE_FILENAME', alt_file)

    if os.path.exists(crane_curve_file):
        logger.debug(f'Loading crane curves from {crane_curve_file}')
        with open(crane_curve_file) as stream:
            try:
                return yaml.load(stream, Loader=yaml.SafeLoader)
            except Exception as e:
                raise e
    else:
        logger.error(f'Cannot load crane curves from {crane_curve_file} - file does not exist')


def _cnv_str_to_qty(array, parameter_name):
    try:
        arr = Q.from_list(list(map(ureg, array)))
    except AttributeError:
        logger.error(f'Check {parameter_name} units.')
    except pint.errors.DimensionalityError:
        logger.error(f'Check {parameter_name} for mixed unit dimensionality.')
    return arr


def _check_dimensionality(variable, expected_dimensionality):
    if not variable.check(expected_dimensionality):
        logger.error(f'Variable was expected to have dimensionality {expected_dimensionality}, however {variable.dimensionality} found.')


def _check():
    for crane_curve_id in _crane_curves.keys():
        array = np.array(_crane_curves[crane_curve_id])

        global _crane_radii
        global _crane_capacities
        _crane_radii[crane_curve_id] = _cnv_str_to_qty(array[:, 0], 'crane radius')
        _crane_capacities[crane_curve_id] = _cnv_str_to_qty(array[:, 1], 'crane capacity')

        _check_dimensionality(_crane_radii[crane_curve_id], '[length]')
        _check_dimensionality(_crane_capacities[crane_curve_id], '[mass]')


def crane_curves():
    global _crane_radii
    global _crane_capacities
    return (_crane_radii, _crane_capacities)


@ureg.check(None, '[length]')
def _crane_capacity(curve, radius):
    # given a radius, returns the capacity
    try:
        return np.interp(radius, _crane_radii[curve], _crane_capacities[curve], left=np.nan, right=np.nan)
    except KeyError as e:
        raise KeyError(f'Crane curve {curve}') from e
    except Exception as e:
        raise e


def crane_curve_ids():
    return _crane_curves.keys()


def get_crane_capacity(curves, radii):
    return Q.from_list([_crane_capacity(curve, radius) for (curve, radius) in zip(curves, radii)])


_crane_radii = {}
_crane_capacities = {}
_crane_curves = _load_crane_curves()
_check()
logger.debug(f'Valid crane curve ids: {list(crane_curve_ids())}')
