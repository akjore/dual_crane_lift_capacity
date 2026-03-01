"""Module restructures the input yaml file."""
from __future__ import annotations

import dataclasses
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import yaml

from . import Q

if TYPE_CHECKING:
    import pint

logger = logging.getLogger(__name__)

class DimensionalityValueError(ValueError):
    """Custom exception for unexpected dimensionality."""

    def __init__(self: DimensionalityValueError, varstr: str, actual_dim: str, expected_dim: str) -> None:
        """Init method for class DimensionalityValueError."""
        super().__init__(f"{varstr} has dimension [{actual_dim}] - {expected_dim} expected")


class MissingFileOrInputDataError(Exception):
    """Custom exception."""

    def __init__(self: MissingFileOrInputDataError) -> None:
        """Init method for class DimensionalityValueError."""
        super().__init__("Either filename or data is required - neither are provided")


@dataclasses.dataclass
class LiftCases:
    """Wrapper class around all provided cases."""

    # Input variables
    crane_radius_a: np.array = None
    crane_radius_b: np.array = None
    rigging_weight_a: np.array = None
    rigging_weight_b: np.array = None
    weight_uncertainty_factor: np.array = None
    cog_uncertainty_factor: np.array = None
    tilt_factor: np.array = None
    lift_point_a: np.array = None
    lift_point_b: np.array = None
    crane_curve_a: np.array = None
    crane_curve_b: np.array = None
    weight: np.array = None
    weight_original_unit: list = None
    cog: np.array = None
    cog_original_unit: list = None
    cases: list = None


    def __check_dim(self, varstr: pint.Quantity, dim: str) -> None:
        var = getattr(locals()["self"], varstr)
        if not var.check(dim):
            raise DimensionalityValueError(varstr, var.dimensionality, dim)


    def __load_data(self, filename: str|None=None, data: str|None=None) -> None:
        # Load data, either from file or data provided
        if data:
            logger.debug(f"Loading from string: {data}")
            self._content = yaml.load(data, Loader=yaml.SafeLoader)
        elif filename:
            file = Path(filename)
            if file.exists:
                logger.debug(f"Loading from file: {filename}")

                with file.open() as stream:
                    self._content = yaml.load(stream, Loader=yaml.SafeLoader)
            else:
                raise FileNotFoundError(filename)
        else:
            raise MissingFileOrInputDataError


    def __init__(self, filename: str|None=None, data: str|None=None) -> None:
        """Populate the class properties."""
        self.__load_data(filename=filename, data=data)

        # Set data variables
        self.crane_radius_a = Q.from_list([Q(d["crane_radius_a"]) for d in self._content.values()])
        self.crane_radius_b = Q.from_list([Q(d["crane_radius_b"]) for d in self._content.values()])
        self.rigging_weight_a = Q.from_list([Q(d["rigging_weight_a"]) for d in self._content.values()])
        self.rigging_weight_b = Q.from_list([Q(d["rigging_weight_b"]) for d in self._content.values()])
        self.weight_uncertainty_factor = Q.from_list([Q(d["weight_uncertainty_factor"]) for d in
                                                      self._content.values()])
        self.cog_uncertainty_factor = Q.from_list([Q(d["cog_uncertainty_factor"]) for d in self._content.values()])
        self.tilt_factor = Q.from_list([Q(d["tilt_factor"]) for d in self._content.values()])
        self.crane_curve_a = [d["crane_curve_a"] for d in self._content.values()]
        self.crane_curve_b = [d["crane_curve_b"] for d in self._content.values()]
        self.weight_original_unit = [Q(d["weight"]) for d in self._content.values()]
        self.weight = Q.from_list(self.weight_original_unit)
        self.cases = list(self._content)

        tmp1 = [d["lift_point_a"] if isinstance(d["lift_point_a"], list) else [d["lift_point_a"]] for d in
                self._content.values()]
        tmp2 = [d + [d[0]] * (2 - len(d)) for d in tmp1]
        self.lift_point_a = self.__to_array([np.sort(Q.from_list([Q(s) for s in d])) for d in tmp2])

        tmp1 = [d["lift_point_b"] if isinstance(d["lift_point_b"], list) else [d["lift_point_b"]] for d in
                self._content.values()]
        tmp2 = [d + [d[0]] * (2 - len(d)) for d in tmp1]
        self.lift_point_b = self.__to_array([np.sort(Q.from_list([Q(s) for s in d])) for d in tmp2])

        tmp1 = [d["cog"] if isinstance(d["cog"], list) else [d["cog"]] for d in self._content.values()]
        tmp2 = [[Q(s) for s in d] for d in tmp1]
        self.cog = self.__to_array([Q.from_list(d + [np.nan * d[0].units] * (3 - len(d))) for d in tmp2])

        self.cog_original_unit = [Q.from_list([Q(s) for s in d]) for d in tmp1]

        # Print data variables for debug purposes
        logger.debug(f"Loaded content: {self._content}")
        logger.debug(f"cases: {self.cases}")
        logger.debug(f"crane_radius_a: {self.crane_radius_a}")
        logger.debug(f"crane_radius_b: {self.crane_radius_b}")
        logger.debug(f"rigging_weight_a: {self.rigging_weight_a}")
        logger.debug(f"rigging_weight_b: {self.rigging_weight_b}")
        logger.debug(f"weight_uncertainty_factor: {self.weight_uncertainty_factor}")
        logger.debug(f"cog_uncertainty_factor: {self.cog_uncertainty_factor}")
        logger.debug(f"tilt_factor: {self.tilt_factor}")
        logger.debug(f"crane_curve_a: {self.crane_curve_a}")
        logger.debug(f"crane_curve_b: {self.crane_curve_b}")
        logger.debug(f"weight: {self.weight}")
        logger.debug(f"lift_point_a: {self.lift_point_a}")
        logger.debug(f"lift_point_b: {self.lift_point_b}")
        logger.debug(f"cog: {self.cog}")

        # Check all params have the required dimensionality
        self.__check_dim("crane_radius_a", "[length]")
        self.__check_dim("crane_radius_b", "[length]")
        self.__check_dim("rigging_weight_a", "[mass]")
        self.__check_dim("rigging_weight_b", "[mass]")
        self.__check_dim("weight_uncertainty_factor", "[]")
        self.__check_dim("cog_uncertainty_factor", "[]")
        self.__check_dim("tilt_factor", "[]")
        self.__check_dim("lift_point_a", "[length]")
        self.__check_dim("lift_point_b", "[length]")
        self.__check_dim("weight", "[mass]")
        self.__check_dim("cog", "[length]")


    def __to_array(self, arr: pint.Quantity) -> pint.Quantity:
        unit = arr[0].units
        return [s.to(unit).magnitude for s in arr] * unit
