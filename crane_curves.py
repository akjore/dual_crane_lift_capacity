import logging
import os

import numpy as np
import pint
import yaml

from init import Q, ureg

logger = logging.getLogger(__name__)


class CraneCurve():
    def __load_crane_curves(self):
        # loads and returns the lift curves defined in the .yaml file
        alt_file = os.path.join(os.path.dirname(__file__), 'crane_curves.yaml')
        crane_curve_file = os.getenv('CRANE_CURVE_FILENAME', alt_file)

        logger.debug(f'Loading crane curves from {crane_curve_file}')
        with open(crane_curve_file) as stream:
            try:
                return yaml.load(stream, Loader=yaml.SafeLoader)
            except Exception as e:
                raise e

    def __cnv_str_to_qty(self, array, parameter_name):
        try:
            arr = Q.from_list(list(map(ureg, array)))
        except AttributeError:
            logger.error(f'Check {parameter_name} units.')
        except pint.errors.DimensionalityError:
            logger.error(f'Check {parameter_name} for mixed unit dimensionality.')
        return arr

    def __check_dimensionality(self, variable, expected_dimensionality):
        if not variable.check(expected_dimensionality):
            logger.error(f'Variable was expected to have dimensionality {expected_dimensionality}, however {variable.dimensionality} found.')

    def __init__(self, crane_curve_id=None):
        self.__crane_radii = None
        self.__crane_capacities = None
        self.__crane_curve_id = crane_curve_id

        self.__crane_curves = self.__load_crane_curves()
        if crane_curve_id is not None:
            array = np.array(self.__crane_curves[crane_curve_id])

            self.__crane_radii = self.__cnv_str_to_qty(array[:, 0], 'crane radius')
            self.__crane_capacities = self.__cnv_str_to_qty(array[:, 1], 'crane capacity')

        self.__check_dimensionality(self.__crane_radii, '[length]')
        self.__check_dimensionality(self.__crane_capacities, '[mass]')
        logger.debug(f'Available crane curve ids: {self.crane_curve_ids}')

    @property
    def crane_curve_id(self):
        return self.__crane_curve_id

    @property
    def crane_curve_radii(self):
        return self.__crane_radii

    @property
    def crane_curve_capacities(self):
        return self.__crane_capacities

    @property
    def crane_curve(self):
        return (self.crane_curve_radii, self.crane_curve_capacities)

    @ureg.check('', '[length]')
    def crane_capacity(self, radius):
        # given a radius, returns the capacity
        try:
            return np.interp(radius, self.__crane_radii, self.__crane_capacities, left=np.nan, right=np.nan)
        except Exception as e:
            raise e

    @property
    def crane_curve_ids(self):
        return [crane_curve_id for crane_curve_id, vals in self.__crane_curves.items()]


    def get_crane_capacity(curves, radii):
        return Q.from_list([CraneCurve(curve).crane_capacity(radius) for (curve, radius) in zip(curves, radii)])
