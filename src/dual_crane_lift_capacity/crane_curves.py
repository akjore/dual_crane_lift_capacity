"""Handles importing and interpolation of crane curves."""
import logging
import os
from importlib import resources as impresources
from pathlib import Path

import numpy as np
import pint
import yaml

from . import Q, resources, ureg

logger = logging.getLogger(__name__)


class CraneCurves:
    """Load crane curves and process data for further use."""

    _crane_radii = None
    _crane_capacities = None
    _crane_curve_data = None

    def _load_crane_curves(self) -> str:
        # loads and returns the lift curves defined in the user-specified .yaml file
        # if file not found, use the template in the repository
        crane_curve_filename = "CRANE_CURVE_FILENAME"
        file_content = None
        crane_curve_file = os.getenv(crane_curve_filename)
        file = Path(crane_curve_file) if crane_curve_file else None

        if not file:
            logger.warning(f"Environment variable {crane_curve_filename} not specified. Using template file.")
            file = impresources.files(resources) / "crane_curves.yaml.template"

        if file and file.exists:
            logger.debug(f"Loading crane curves from {crane_curve_file}")
            with file.open() as stream:
                file_content = yaml.load(stream, Loader=yaml.SafeLoader)
        else:
            logger.error(f"""No crane curves found. Create an environment variable {crane_curve_filename}
                          and specify path to crane curves file.""")

        return file_content


    def _cnv_str_to_qty(self, array: np.array, parameter_name: str) -> pint.Quantity:
        try:
            arr = Q.from_list(list(map(ureg, array)))
        except AttributeError:
            logger.exception(f"Check {parameter_name} units.")
        except pint.errors.DimensionalityError:
            logger.exception(f"Check {parameter_name} for mixed unit dimensionality.")
        return arr


    def _check_dimensionality(self, variable: pint.Quantity, expected_dimensionality: str) -> None:
        if not variable.check(expected_dimensionality):
            logger.error(f"Variable was expected to have dimensionality {expected_dimensionality}, \
                         however {variable.dimensionality} found.")


    @ureg.check(None, None, "[length]")
    def _crane_capacity(self, curve: str, radius: float) -> float:
        # given a radius, returns the capacity
        try:
            return np.interp(radius, self.crane_radii[curve], self.crane_capacities[curve], left=np.nan, right=np.nan)
        except KeyError as e:
            logger.exception(f"Crane curve {curve}")
            raise KeyError from e
        except Exception:
            raise


    def crane_capacity(self, curves: list, radii: np.array) -> pint.Quantity:
        """Return the crane capacity at a given radius.

        :returns: crane capacities at given radius
        """
        if not self.crane_curves_exist(curves):
            logger.error(
                f"Known crane curves are: {list(self.crane_curve_ids)}. Requested crane curves "
                f"are: {set(curves)}",
            )
            raise KeyError

        return Q.from_list([self._crane_capacity(curve, radius) for (curve, radius) in zip(curves, radii)])


    @property
    def crane_curve_data(self) -> dict:
        """Return the crane data read from the source file."""
        return self._crane_curve_data


    @crane_curve_data.setter
    def crane_curve_data(self, data: dict) -> None:
        self._crane_curve_data = data


    @property
    def crane_radii(self) -> dict:
        """Return all crane curve radii as a dict of quantities, with crane curve id as key."""
        return self._crane_radii


    @property
    def crane_capacities(self) -> dict:
        """Return all crane curve capacities as a dict of quantities, with crane curve id as key."""
        return self._crane_capacities


    @property
    def crane_curves(self) -> tuple:
        """Return all crane curves as a tuple.

        :returns: a tuple containing the radii and the capacities
        """
        return (self.crane_radii, self.crane_capacities)

    @property
    def crane_curve_ids(self) -> list:
        """Return all crane curve ids.

        :returns: a list of known crane curve ids
        """
        return self.crane_curve_data.keys()


    def crane_curves_exist(self, curves: list) -> bool:
        """Check that crane curves exist.

        Check that the craene curves in 'curves' all are known.

        :returns: a list of known crane curve ids
        """
        return set(curves).issubset(self.crane_curve_ids)


    def __init__(self) -> None:
        """Load crane data from file, and process for further use."""
        self._crane_radii = {}
        self._crane_capacities = {}

        self.crane_curve_data = self._load_crane_curves()

        for crane_curve_id in self.crane_curve_data:
            array = np.array(self.crane_curve_data[crane_curve_id])
            self._crane_radii[crane_curve_id] = self._cnv_str_to_qty(array[:, 0], "crane radius")
            self._crane_capacities[crane_curve_id] = self._cnv_str_to_qty(array[:, 1], "crane capacity")

            self._check_dimensionality(self.crane_radii[crane_curve_id], "[length]")
            self._check_dimensionality(self.crane_capacities[crane_curve_id], "[mass]")

        logger.debug(f"Valid crane curve ids: {list(self.crane_curve_ids)}")
