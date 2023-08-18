"""Handles importing and interpolation of crane curves."""
import logging
import os
from pathlib import Path

import numpy as np
import pint
import pkg_resources
import yaml

from . import Q, ureg

logger = logging.getLogger(__name__)


def _load_crane_curves() -> str:
    # loads and returns the lift curves defined in the .yaml file
    file_content = None
    alt_file = pkg_resources.resource_filename(__name__, "crane_curves.yaml")
    crane_curve_file = os.getenv("CRANE_CURVE_FILENAME", alt_file)
    file = Path(crane_curve_file) if crane_curve_file else None

    if file and file.exists:
        logger.debug(f"Loading crane curves from {crane_curve_file}")
        with file.open() as stream:
            file_content = yaml.load(stream, Loader=yaml.SafeLoader)
    else:
        logger.error(f"Cannot load crane curves from {crane_curve_file} - file does not exist")
    return file_content


def _cnv_str_to_qty(array: np.array, parameter_name: str) -> pint.Quantity:
    try:
        arr = Q.from_list(list(map(ureg, array)))
    except AttributeError:
        logger.exception(f"Check {parameter_name} units.")
    except pint.errors.DimensionalityError:
        logger.exception(f"Check {parameter_name} for mixed unit dimensionality.")
    return arr


def _check_dimensionality(variable: pint.Quantity, expected_dimensionality: str) -> None:
    if not variable.check(expected_dimensionality):
        logger.error(f"Variable was expected to have dimensionality {expected_dimensionality}, \
                     however {variable.dimensionality} found.")


def _check() -> None:
    for crane_curve_id in _crane_curves:
        array = np.array(_crane_curves[crane_curve_id])

        global _crane_radii
        global _crane_capacities
        _crane_radii[crane_curve_id] = _cnv_str_to_qty(array[:, 0], "crane radius")
        _crane_capacities[crane_curve_id] = _cnv_str_to_qty(array[:, 1], "crane capacity")

        _check_dimensionality(_crane_radii[crane_curve_id], "[length]")
        _check_dimensionality(_crane_capacities[crane_curve_id], "[mass]")


def crane_curves() -> tuple:
    """Return all crane curves as a tuple.

    :returns: a tuple containing the radii and the capacities
    """
    global _crane_radii
    global _crane_capacities
    return (_crane_radii, _crane_capacities)


@ureg.check(None, "[length]")
def _crane_capacity(curve: str, radius: float) -> float:
    # given a radius, returns the capacity
    try:
        return np.interp(radius, _crane_radii[curve], _crane_capacities[curve], left=np.nan, right=np.nan)
    except KeyError as e:
        raise KeyError(f"Crane curve {curve}") from e
    except Exception:
        raise


def crane_curve_ids() -> list:
    """Return all crane curve ids.

    :returns: a list of known crane curve ids
    """
    return _crane_curves.keys()


def get_crane_capacity(curves: list, radii: np.array) -> pint.Quantity:
    """Return the crane capacity at a given radius.

    :returns: crane capacities at given radius
    """
    return Q.from_list([_crane_capacity(curve, radius) for (curve, radius) in zip(curves, radii)])


_crane_radii = {}
_crane_capacities = {}
_crane_curves = _load_crane_curves()
_check()
logger.debug(f"Valid crane curve ids: {list(crane_curve_ids())}")
