"""Handles importing and interpolation of crane curves."""
import logging
import os
from pathlib import Path
from typing import ClassVar

import numpy as np
import pint
import yaml

from . import Q, ureg

logger = logging.getLogger(__name__)


class CraneCurves:
    """Load crane curves and process data for further use."""

    _crane_radii: ClassVar[dict] = {}
    _crane_capacities: ClassVar[dict] = {}
    _crane_curve_data: ClassVar[dict] = None


    @classmethod
    def crane_radii(cls) -> dict:
        """Return all crane curve radii as a dict of quantities, with crane curve id as key."""
        if not cls._crane_radii:
            cls._load_crane_curves()

        return cls._crane_radii


    @classmethod
    def crane_capacities(cls) -> dict:
        """Return all crane curve capacities as a dict of quantities, with crane curve id as key."""
        if not cls._crane_capacities:
            cls._load_crane_curves()

        return cls._crane_capacities


    @classmethod
    def crane_curves(cls) -> tuple:
        """Return all crane curves as a tuple.

        :returns: a tuple containing the radii and the capacities
        """
        if not cls._crane_radii:
            cls._load_crane_curves()

        return (cls.crane_radii, cls.crane_capacities)


    @classmethod
    def crane_curve_ids(cls) -> list:
        """Return all crane curve ids.

        :returns: a list of known crane curve ids
        """
        return cls.crane_curve_data().keys()


    @classmethod
    def crane_curve_data(cls) -> dict:
        """Return the crane data read from the source file."""
        if not cls._crane_curve_data:
            cls._load_crane_curves()

        return cls._crane_curve_data


    @classmethod
    def _load_crane_curves(cls) -> str:
        """Return the crane curve data. Load it from file, if required."""
        # loads and returns the lift curves defined in the user-specified .yaml file
        crane_curve_filename = "CRANE_CURVE_FILENAME"
        crane_curve_file = os.getenv(crane_curve_filename)
        file = Path(crane_curve_file) if crane_curve_file else None

        file_content = None
        if file and file.exists:
            logger.debug(f"Loading crane curves from {crane_curve_file}")
            with file.open() as stream:
                file_content = yaml.load(stream, Loader=yaml.SafeLoader)
        else:
            logger.error(f"""No crane curves found. Create an environment variable {crane_curve_filename}
                          and specify path to crane curves file.""")

        cls._crane_curve_data = file_content

        for crane_curve_id in file_content:
            array = np.array(file_content[crane_curve_id])
            cls._crane_radii[crane_curve_id] = Q.from_list(list(map(ureg, array[:, 0])))
            cls._crane_capacities[crane_curve_id] = Q.from_list(list(map(ureg, array[:, 1])))

        logger.debug(f"Valid crane curve ids: {list(cls.crane_curve_ids())}")


    @classmethod
    @ureg.check(None, None, "[length]")
    def crane_capacity(cls, curve: str, radius: np.array) -> pint.Quantity:
        """Return the crane capacity at a given radius for the specified crane curve.

        :returns: crane capacity at a given radius
        """
        if curve not in cls.crane_curve_ids():
            msg = f"Known crane curves are: {list(cls.crane_curve_ids())}. Requested crane curve is: {curve}"
            logger.error(msg)
            raise KeyError(msg)

        return np.interp(radius, cls.crane_radii()[curve], cls.crane_capacities()[curve], left=np.nan, right=np.nan)
