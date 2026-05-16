"""Module restructures the input yaml file."""
from __future__ import annotations

import dataclasses
import logging
from typing import TYPE_CHECKING

import json
import numpy as np
import yaml


import pint

#from . import lift_cases, ureg


from . import Q
from .crane_curves import CraneCurves

#if TYPE_CHECKING:
#    import pint

logger = logging.getLogger(__name__)

class DimensionalityValueError(ValueError):
    """Custom exception for unexpected dimensionality."""

    def __init__(self: DimensionalityValueError, varstr: str, actual_dim: str, expected_dim: str) -> None:
        """Init method for class DimensionalityValueError."""
        super().__init__(f"{varstr} has dimension [{actual_dim}] - {expected_dim} expected")


@dataclasses.dataclass
class LiftCase:
    """Data related to a single lift case."""
    # Dataclass variables
    case: str
    crane_radius_a: pint.Quantity
    crane_radius_b: pint.Quantity
    rigging_weight_a: pint.Quantity
    rigging_weight_b: pint.Quantity
    weight_uncertainty_factor: float
    cog_uncertainty_factor: float
    tilt_factor: float
    lift_point_a: pint.Quantity
    lift_point_b: pint.Quantity
    crane_curve_a: str
    crane_curve_b: str
    weight: pint.Quantity
    cog: pint.Quantity
    cog_envelope: list[pint.Quantity]
    float_a: pint.Quantity
    float_b: pint.Quantity
    crane_capacity_a: pint.Quantity
    crane_capacity_b: pint.Quantity


    @classmethod
    def parse_quantity(self, param):
        # The CoG envelope is optional, however downstream calculations need the right units even for nan.
        # Default unit is then "m"
        default_unit = Q("m")
        if isinstance(param, list):
            l = [Q(p) if p else np.nan*default_unit for p in param]
            return Q.from_list(l)
        elif isinstance(param, dict):
            # Assume a dict with a value and a unit as keys (json)
            return param["value"] * (Q(param["unit"]) if param["unit"] else Q("dimensionless"))

        return Q(param) if param else param


    @classmethod
    def from_dict(self, data: dict) -> LiftCase:
        # CoG envelope is optional
        cog_envelope = data.get("cog_envelope")
        cog_envelope = cog_envelope if cog_envelope else [None, None]

        return self(
            case = data["case"],
            crane_radius_a = self.parse_quantity(data["crane_radius_a"]),
            crane_radius_b = self.parse_quantity(data["crane_radius_b"]),
            rigging_weight_a = self.parse_quantity(data["rigging_weight_a"]),
            rigging_weight_b = self.parse_quantity(data["rigging_weight_b"]),
            weight_uncertainty_factor = self.parse_quantity(data["weight_uncertainty_factor"]),
            cog_uncertainty_factor = self.parse_quantity(data["cog_uncertainty_factor"]),
            tilt_factor = self.parse_quantity(data["tilt_factor"]),
            lift_point_a = self.parse_quantity(data["lift_point_a"]),
            lift_point_b = self.parse_quantity(data["lift_point_b"]),
            crane_curve_a = data["crane_curve_a"],
            crane_curve_b = data["crane_curve_b"],
            weight = self.parse_quantity(data["weight"]),
            cog = self.parse_quantity(data["cog"]),
            cog_envelope = self.parse_quantity(cog_envelope),
            float_a = self.parse_quantity(data.get("float_a", "0 m")),
            float_b = self.parse_quantity(data.get("float_b", "0 m")),
            crane_capacity_a = None,        # populated in post_init
            crane_capacity_b = None,        # populated in post_init
        )


    def __post_init__(self) -> None:
        # Print data variables for debug purposes
        logger.debug(f"cases: {self.case}")
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
        logger.debug(f"cog_envelope: {self.cog_envelope}")

        # Check all params have the required dimensionality
        assert self.crane_radius_a.check("[length]")
        assert self.crane_radius_b.check("[length]")
        assert self.rigging_weight_a.check("[mass]")
        assert self.rigging_weight_b.check("[mass]")
        assert self.weight_uncertainty_factor.check("[]")
        assert self.cog_uncertainty_factor.check("[]")
        assert self.tilt_factor.check("[]")
        assert self.lift_point_a.check("[length]")
        assert self.lift_point_b.check("[length]")
        assert self.weight.check("[mass]")
        assert self.cog.check("[length]")
        assert self.cog_envelope.check("[length]")


        # Get crane capacities for specified crane curves and radii
        self.crane_capacity_a = CraneCurves.crane_capacity(self.crane_curve_a, self.crane_radius_a)
        self.crane_capacity_b = CraneCurves.crane_capacity(self.crane_curve_b, self.crane_radius_b)


@dataclasses.dataclass
class LiftCases:
    """Wrapper class around all provided cases."""

    liftcases: list[LiftCase]
    _raw:  str

    def __init__(self):
        """Override the default __init__ for dataclasses."""
        pass


    def from_yaml(self, text: str) -> LiftCases:
        """Parse the provided text as yaml-input, and create a list of LiftCase objects."""
        # Keep a copy of the provided data
        self._raw = yaml.load(text, Loader=yaml.SafeLoader)
        self.liftcases = []

        for case in self._raw["cases"]:
            print(f"case: {case}")
            self.liftcases.append(LiftCase.from_dict(case))

        return self


    def from_json(self, text: str) -> LiftCases:
        """Parse the provided json-dict to a list of LiftCase objects."""
        # Keep a copy of the provided data
        self._raw = json.loads(text)
        self.liftcases = []

        print(self._raw)
        print(type(self._raw))

        for case in self._raw:
            print(f"case: {case}")
            self.liftcases.append(LiftCase.from_dict(case))

        return self


    def to_json(self) -> LiftCases:
        """Return inputs as a json formatted string."""
        def cnv_quantity(val):
            if isinstance(val, pint.Quantity):
                val, unit = val.magnitude, val.units
                if isinstance(val, np.ndarray):
                    val = val.tolist()
                return {"value": val, "unit": f"{unit:~P}"}
            if isinstance(val, list):
                return [cnv_quantity(a) for a in val]
            return val

        # Create a list of all dataclass variables and manually created properties
        v = vars(self) | {name: getattr(self, name) for name, attr in self.__class__.__dict__.items() if isinstance(attr, property)}

        del v["_raw"]
        del v["liftcases"]

        liftcases = [dict(zip(v.keys(), (cnv_quantity(li) for li in l))) for l in zip(*v.values())]

        # temporary
        #del liftcases[0]["distance_lift_points_a_to_cogs_offset_towards_a"]
        #del liftcases[0]["distance_lift_points_a_to_cogs_offset_towards_b"]
        #del liftcases[0]["distance_lift_points_b_to_cogs_offset_towards_a"]
        #del liftcases[0]["distance_lift_points_b_to_cogs_offset_towards_b"]
        #del liftcases[0]["cog_envelopes"]
        # end temporary

        return json.dumps(liftcases)


    # Slice across the list of LiftCase objects, and return a list or array with input data for all cases
    @property
    def case(self):
        """Return the ids of all lift cases."""
        return [liftcase.case for liftcase in self.liftcases]


    @property
    def crane_radius_a(self):
        """Return the crane a lifting radius for all lift cases."""
        return Q.from_list([liftcase.crane_radius_a for liftcase in self.liftcases])


    @property
    def crane_radius_b(self):
        """Return the crane b lifting radius for all lift cases."""
        return Q.from_list([liftcase.crane_radius_b for liftcase in self.liftcases])


    @property
    def rigging_weight_a(self):
        """Return the rigging weight suspended from crane a for all lift cases."""
        return Q.from_list([liftcase.rigging_weight_a for liftcase in self.liftcases])


    @property
    def rigging_weight_b(self):
        """Return the rigging weight suspended from crane b for all lift cases."""
        return Q.from_list([liftcase.rigging_weight_b for liftcase in self.liftcases])


    @property
    def weight_uncertainty_factor(self):
        """Return the weight_uncertainty_factor for all lift cases."""
        return Q.from_list([liftcase.weight_uncertainty_factor for liftcase in self.liftcases])


    @property
    def cog_uncertainty_factor(self):
        """Return the CoG uncertainty factor for all lift cases."""
        return Q.from_list([liftcase.cog_uncertainty_factor for liftcase in self.liftcases])


    @property
    def tilt_factor(self):
        """Return the tilt factor for all lift cases."""
        return Q.from_list([liftcase.tilt_factor for liftcase in self.liftcases])


    @property
    def crane_curve_a(self):
        """Return the crane curve for crane a for all lift cases."""
        return [liftcase.crane_curve_a for liftcase in self.liftcases]


    @property
    def crane_curve_b(self):
        """Return the crane curve for crane b for all lift cases."""
        return [liftcase.crane_curve_b for liftcase in self.liftcases]


    @property
    def weight(self):
        """Return the lifted weight for all lift cases."""
        return Q.from_list([liftcase.weight for liftcase in self.liftcases])


    @property
    def float_a(self):
        """Return the lift point floats for crane a for all lift cases."""
        return Q.from_list([liftcase.float_a for liftcase in self.liftcases])


    @property
    def float_b(self):
        """Return the lift point floats for crane b for all lift cases."""
        return Q.from_list([liftcase.float_b for liftcase in self.liftcases])


    @property
    def crane_capacity_a(self):
        """Return the crane a lifting capacity at the given lifting radius for all lift cases."""
        return Q.from_list([liftcase.crane_capacity_a for liftcase in self.liftcases])


    @property
    def crane_capacity_b(self):
        """Return the crane b lifting capacity at the given lifting radius for all lift cases."""
        return Q.from_list([liftcase.crane_capacity_b for liftcase in self.liftcases])


    @property
    def lift_point_a(self):
        """Return the lift point a positions for all lift cases."""
        # Create a numpy array with lift_point_a position for all cases - shape is (number of cases, )
        return Q.from_list([liftcase.lift_point_a for liftcase in self.liftcases])


    @property
    def lift_point_b(self):
        """Return the lift point b positions, considering float, for all lift cases."""
        # Create a numpy array with lift_point_a position for all cases - shape is (number of cases, )
        return Q.from_list([liftcase.lift_point_b for liftcase in self.liftcases])


    @property
    def lift_point_a_wfloat(self):
        """Return the lift point a positions, considering float, for all lift cases."""
        # Create a numpy array with lift_point_a position for all cases - shape is (number of cases, )
        a = self.lift_point_a

        # Deduct the float from the first column, add the float to the second column -> shape is (number of cases, 2)
        return np.stack((a-self.float_a, a+self.float_a), axis=-1)


    @property
    def lift_point_b_wfloat(self):
        """Return the lift point a positions, considering float, for all lift cases."""
        # Create a numpy array with lift_point_a position for all cases - shape is (number of cases, )
        a = self.lift_point_b

        # Deduct the float from the first column, add the float to the second column -> shape is (number of cases, 2)
        return np.stack((a-self.float_b, a+self.float_b), axis=-1)


    @property
    def cog(self):
        """Return the CoGs for all lift cases."""
        # Create a numpy array for the centres of gravity
        return Q.from_list([liftcase.cog for liftcase in self.liftcases])


    @property
    def cog_envelope(self):
        """Return the CoG envelopes for all lift cases."""
        # Create a numpy array for the centre of gravity envelopes
        # Separate out "left" and "right" CoG envelope edges
        l = Q.from_list([liftcase.cog_envelope[0] for liftcase in self.liftcases])
        r = Q.from_list([liftcase.cog_envelope[1] for liftcase in self.liftcases])

        # stack left edge of CoG envelope, right edge of CoG envelope
        return np.stack((l, r), axis=-1)


    @property
    def cog_offset_a(self):
        """Return the CoG offsets towards crane a for all lift cases."""
        return self.cog - self.cog_envelope[:, 0]


    @property
    def cog_offset_b(self):
        """Return the CoG offsets towards crane a for all lift cases."""
        return self.cog_envelope[:, 1] - self.cog


    @property
    def distance_lift_point_a_to_cog(self):
        """Return the distance from lift point a to the CoG for all lift cases."""
        return abs(self.cog - self.lift_point_a)


    @property
    def distance_lift_point_b_to_cog(self):
        """Return the distance from lift point a to the CoG for all lift cases."""
        return abs(self.cog - self.lift_point_b)


    @property
    def distance_lift_point_a_to_lift_point_b(self):
        """Return the distance from lift point a to lift point b for all lift cases."""
        return abs(self.lift_point_a - self.lift_point_b)


    @property
    def combined_rigging_weight(self):
        """Return the sum of the rigging weights for cranes a and b for all lift cases."""
        return self.rigging_weight_a + self.rigging_weight_b


    @property
    def distance_lift_point_a_to_cog_offset_towards_a(self):
        """Return the distance from lift point a to end a of the CoG envelope for all lift cases."""
        return abs(self.cog_envelope - self.lift_point_a)[:, 0]


    @property
    def distance_lift_point_a_to_cog_offset_towards_b(self):
        """Return the distance from lift point a to end b of the CoG envelope for all lift cases."""
        return abs(self.cog_envelope - self.lift_point_a)[:, 1]


    @property
    def distance_lift_point_b_to_cog_offset_towards_a(self):
        """Return the distance from lift point b to end a of the CoG envelope for all lift cases."""
        return abs(self.cog_envelope - self.lift_point_b)[:, 0]


    @property
    def distance_lift_point_b_to_cog_offset_towards_b(self):
        """Return the distance from lift point b to end b of the CoG envelope for all lift cases."""
        return abs(self.cog_envelope - self.lift_point_b)[:, 1]
