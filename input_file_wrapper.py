import logging
from dataclasses import dataclass

import numpy as np
import yaml

from init import Q


@dataclass
class DualLiftingCases:
    crane_radius_a: np.array = None
    crane_radius_b: np.array = None
    rigging_weight_a: np.array = None
    rigging_weight_b: np.array = None
    weight_uncertainty_factor: np.array = None
    cog_uncertainty_factor: np.array = None
    tilt_factor: np.array = None
    lift_point_a: np.array = None
    lift_point_b: np.array = None
    crane_curve_a: list = None
    crane_curve_b: list = None
    weight: np.array = None
    cog: np.array = None
    cases: list = None

    filename: str = None
    data: str = None

    def __load_data(self):
        # Load data, either from file or data provided
        if self.data:
            self._logger.debug(f'Loading from string: {self.data}')
            self._content = yaml.load(self.data, Loader=yaml.SafeLoader)
        elif self.filename:
            self._logger.debug(f'Loading from file: {self.filename}')

            with open(self.filename) as stream:
                self._content = yaml.load(stream, Loader=yaml.SafeLoader)
        else:
            raise Exception("Either filename or data is required - neither are provided")

    def __post_init__(self):
        self._logger = logging.getLogger(__name__)
        self.__load_data()

        # Set data variables
        self.crane_radius_a = Q.from_list([Q(d['crane_radius_a']) for d in self._content.values()])
        self.crane_radius_b = Q.from_list([Q(d['crane_radius_b']) for d in self._content.values()])
        self.rigging_weight_a = Q.from_list([Q(d['rigging_weight_a']) for d in self._content.values()])
        self.rigging_weight_b = Q.from_list([Q(d['rigging_weight_b']) for d in self._content.values()])
        self.weight_uncertainty_factor = np.array([d['weight_uncertainty_factor'] for d in self._content.values()])
        self.cog_uncertainty_factor = np.array([d['cog_uncertainty_factor'] for d in self._content.values()])
        self.tilt_factor = np.array([d['tilt_factor'] for d in self._content.values()])
        self.crane_curve_a = [d['crane_curve_a'] for d in self._content.values()]
        self.crane_curve_b = [d['crane_curve_b'] for d in self._content.values()]
        self.weight = Q.from_list([Q(d['weight']) for d in self._content.values()])
        self.cases = list(self._content)

        tmp1 = [d['lift_point_a'] if isinstance(d['lift_point_a'], list) else [d['lift_point_a']] for d in self._content.values()]
        tmp2 = [d+[d[0]]*(2-len(d)) for d in tmp1]
        self.lift_point_a = self.__to_array([np.sort(Q.from_list([Q(s) for s in d])) for d in tmp2])

        tmp1 = [d['lift_point_b'] if isinstance(d['lift_point_b'], list) else [d['lift_point_b']] for d in self._content.values()]
        tmp2 = [d+[d[0]]*(2-len(d)) for d in tmp1]
        self.lift_point_b = self.__to_array([np.sort(Q.from_list([Q(s) for s in d])) for d in tmp2])

        tmp1 = [d['cog'] if isinstance(d['cog'], list) else [d['cog']] for d in self._content.values()]
        tmp2 = [[Q(s) for s in d] for d in tmp1]
        self.cog = self.__to_array([np.sort(Q.from_list(d+[np.NaN*d[0].units]*(3-len(d)))) for d in tmp2])

        # Print data variables for debug purposes
        self._logger.debug(f'Loaded content: {self._content}')
        self._logger.debug(f'cases: {self.cases}')
        self._logger.debug(f'crane_radius_a: {self.crane_radius_a}')
        self._logger.debug(f'crane_radius_b: {self.crane_radius_b}')
        self._logger.debug(f'rigging_weight_a: {self.rigging_weight_a}')
        self._logger.debug(f'rigging_weight_b: {self.rigging_weight_b}')
        self._logger.debug(f'weight_uncertainty_factor: {self.weight_uncertainty_factor}')
        self._logger.debug(f'cog_uncertainty_factor: {self.cog_uncertainty_factor}')
        self._logger.debug(f'tilt_factor: {self.tilt_factor}')
        self._logger.debug(f'crane_curve_a: {self.crane_curve_a}')
        self._logger.debug(f'crane_curve_b: {self.crane_curve_b}')
        self._logger.debug(f'weight: {self.weight}')
        self._logger.debug(f'lift_point_a: {self.lift_point_a}')
        self._logger.debug(f'lift_point_b: {self.lift_point_b}')
        self._logger.debug(f'cog: {self.cog}')

    def __to_array(self, arr):
        unit = arr[0].units
        a = [s.to(unit).magnitude for s in arr] * unit
        return a
