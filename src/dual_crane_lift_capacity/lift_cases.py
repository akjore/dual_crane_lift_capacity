"""Module restructures the input yaml file."""
from __future__ import annotations

import logging

import numpy as np
import pint
import simplejson
import yaml

from . import Q, ureg
from .crane_curves import CraneCurves

logger = logging.getLogger(__name__)


class LiftCase:
    """Data related to a single lift case."""

    # Dataclass variables
    case: str
    _crane_radius_a: pint.Quantity
    _crane_radius_b: pint.Quantity
    _rigging_weight_a: pint.Quantity
    _rigging_weight_b: pint.Quantity
    _weight_uncertainty_factor: pint.Quantity
    _cog_uncertainty_factor: pint.Quantity
    _tilt_factor: pint.Quantity
    _lift_point_a: pint.Quantity
    _lift_point_b: pint.Quantity
    crane_curve_a: str
    crane_curve_b: str
    _weight: pint.Quantity
    _cog: pint.Quantity
    _cog_envelope: pint.Quantity
    _float_a: pint.Quantity
    _float_b: pint.Quantity
    _crane_capacity_a: pint.Quantity
    _crane_capacity_b: pint.Quantity

    def __init__(self, case: str, crane_radius_a: pint.Quantity, crane_radius_b: pint.Quantity,
                 rigging_weight_a: pint.Quantity, rigging_weight_b: pint.Quantity,
                 weight_uncertainty_factor: pint.Quantity, cog_uncertainty_factor: pint.Quantity,
                 tilt_factor: pint.Quantity, lift_point_a: pint.Quantity, lift_point_b: pint.Quantity,
                 crane_curve_a: str, crane_curve_b: str, weight: pint.Quantity, cog: pint.Quantity,
                cog_envelope: pint.Quantity, float_a: pint.Quantity, float_b: pint.Quantity) -> None:
        """Create an instance based on supplied values."""
        self.case = case
        self.crane_radius_a = crane_radius_a
        self.crane_radius_b = crane_radius_b
        self.rigging_weight_a = rigging_weight_a
        self.rigging_weight_b = rigging_weight_b
        self.weight_uncertainty_factor = weight_uncertainty_factor
        self.cog_uncertainty_factor = cog_uncertainty_factor
        self.tilt_factor = tilt_factor
        self.lift_point_a = lift_point_a
        self.lift_point_b = lift_point_b
        self.crane_curve_a = crane_curve_a
        self.crane_curve_b = crane_curve_b
        self.weight = weight
        self.cog = cog
        self.cog_envelope = cog_envelope
        self.float_a = float_a
        self.float_b = float_b

        self.crane_capacity_a = CraneCurves.crane_capacity(self.crane_curve_a, self.crane_radius_a)
        self.crane_capacity_b = CraneCurves.crane_capacity(self.crane_curve_b, self.crane_radius_b)

        # Print the variables for debug purposes
        inputs = locals()
        del inputs["self"]
        logger.debug(inputs)


    @classmethod
    def parse_quantity(cls, param: str) -> pint.Quantity:
        """Parse a string to a pint.Quantity."""
        # The CoG envelope is optional, however downstream calculations need the right units even for nan.
        # Default unit is then "m"
        default_unit = Q("m")
        if isinstance(param, list):
            return Q.from_list([Q(p) if p else np.nan*default_unit for p in param])
        if isinstance(param, dict):
            # json may pass back None - these need to be converted to np.nan to work with Quantities
            if isinstance(param["value"], list):
                param["value"] = [v if v else np.nan for v in param["value"]]

            # Assume a dict with a value (could be null) and unit as keys (json)
            return (param["value"]) * (Q(param["unit"]) if param["unit"] else Q("dimensionless"))

        return Q(param) if param else param


    @classmethod
    def from_dict(cls, data: dict) -> LiftCase:
        """Create an instance based on supplied dictionary."""
        # CoG envelope is optional
        cog_envelope = data.get("cog_envelope")
        cog_envelope = cog_envelope if cog_envelope else [None, None]

        return cls(
            case = data["case"],
            crane_radius_a = cls.parse_quantity(data["crane_radius_a"]),
            crane_radius_b = cls.parse_quantity(data["crane_radius_b"]),
            rigging_weight_a = cls.parse_quantity(data["rigging_weight_a"]),
            rigging_weight_b = cls.parse_quantity(data["rigging_weight_b"]),
            weight_uncertainty_factor = cls.parse_quantity(data["weight_uncertainty_factor"]),
            cog_uncertainty_factor = cls.parse_quantity(data["cog_uncertainty_factor"]),
            tilt_factor = cls.parse_quantity(data["tilt_factor"]),
            lift_point_a = cls.parse_quantity(data["lift_point_a"]),
            lift_point_b = cls.parse_quantity(data["lift_point_b"]),
            crane_curve_a = data["crane_curve_a"],
            crane_curve_b = data["crane_curve_b"],
            weight = cls.parse_quantity(data["weight"]),
            cog = cls.parse_quantity(data["cog"]),
            cog_envelope = cls.parse_quantity(cog_envelope),
            float_a = cls.parse_quantity(data.get("float_a", "0.0 m")),
            float_b = cls.parse_quantity(data.get("float_b", "0.0 m")),
        )


    def to_dict(self) -> dict:
        """Return input as a json-friendly dict."""
        def cnv_quantity(val: pint.Quantity | list) -> dict:
            if isinstance(val, pint.Quantity):
                val, unit = val.magnitude, val.units
                if isinstance(val, np.ndarray):
                    val = val.tolist()
                if isinstance(val, np.int64):
                    val = int(val)
                return {"value": val, "unit": f"{unit:~P}"}
            if isinstance(val, list):
                return [cnv_quantity(a) for a in val]
            return val

        # Create a list of all dataclass variables and manually created properties
        v = {name: getattr(self, name) for name, attr in self.__class__.__dict__.items() if isinstance(attr, property)}
        v["case"] = self.case
        v["crane_curve_a"] = self.crane_curve_a
        v["crane_curve_b"] = self.crane_curve_b

        return dict(zip(v.keys(), (cnv_quantity(li) for li in v.values()), strict=True))


    @property
    def crane_radius_a(self) -> pint.Quantity:
        """Return the lifting radius for crane A."""
        return self._crane_radius_a

    @crane_radius_a.setter
    @ureg.check("[]", "[length]")
    def crane_radius_a(self, value: pint.Quantity) -> None:
        self._crane_radius_a = value


    @property
    def crane_radius_b(self) -> pint.Quantity:
        """Return the lifting radius for crane B."""
        return self._crane_radius_b

    @crane_radius_b.setter
    @ureg.check("[]", "[length]")
    def crane_radius_b(self, value: pint.Quantity) -> None:
        self._crane_radius_b = value


    @property
    def rigging_weight_a(self) -> pint.Quantity:
        """Return the weight of the rigging attached to crane A."""
        return self._rigging_weight_a

    @rigging_weight_a.setter
    @ureg.check("[]", "[mass]")
    def rigging_weight_a(self, value: pint.Quantity) -> None:
        self._rigging_weight_a = value


    @property
    def rigging_weight_b(self) -> pint.Quantity:
        """Return the weight of the rigging attached to crane B."""
        return self._rigging_weight_b

    @rigging_weight_b.setter
    @ureg.check("[]", "[mass]")
    def rigging_weight_b(self, value: pint.Quantity) -> None:
        self._rigging_weight_b = value


    @property
    def weight_uncertainty_factor(self) -> pint.Quantity:
        """Return the weight uncertainty factor."""
        return self._weight_uncertainty_factor

    @weight_uncertainty_factor.setter
    @ureg.check("[]", "[]")
    def weight_uncertainty_factor(self, value: pint.Quantity) -> None:
        self._weight_uncertainty_factor = value


    @property
    def cog_uncertainty_factor(self) -> pint.Quantity:
        """Return the CoG uncertainty factor."""
        return self._cog_uncertainty_factor

    @cog_uncertainty_factor.setter
    @ureg.check("[]", "[]")
    def cog_uncertainty_factor(self, value: pint.Quantity) -> None:
        self._cog_uncertainty_factor = value


    @property
    def tilt_factor(self) -> pint.Quantity:
        """Return the tilt factor."""
        return self._tilt_factor

    @tilt_factor.setter
    @ureg.check("[]", "[]")
    def tilt_factor(self, value: pint.Quantity) -> None:
        self._tilt_factor = value


    @property
    def lift_point_a(self) -> pint.Quantity:
        """Return the coordinates of the lift point attached to crane B."""
        return self._lift_point_a

    @lift_point_a.setter
    @ureg.check("[]", "[length]")
    def lift_point_a(self, value: pint.Quantity) -> None:
        self._lift_point_a = value


    @property
    def lift_point_b(self) -> pint.Quantity:
        """Return the coordinates of the lift point attached to crane B."""
        return self._lift_point_b

    @lift_point_b.setter
    @ureg.check("[]", "[length]")
    def lift_point_b(self, value: pint.Quantity) -> None:
        self._lift_point_b = value


    @property
    def weight(self) -> pint.Quantity:
        """Return the weight of the lifted object."""
        return self._weight

    @weight.setter
    @ureg.check("[]", "[mass]")
    def weight(self, value: pint.Quantity) -> None:
        self._weight = value


    @property
    def cog(self) -> pint.Quantity:
        """Return the CoG of the lifted object."""
        return self._cog

    @cog.setter
    @ureg.check("[]", "[length]")
    def cog(self, value: pint.Quantity) -> None:
        self._cog = value


    @property
    def float_a(self) -> pint.Quantity:
        """Return the float for lifting point attached to crane A."""
        return self._float_a

    @float_a.setter
    @ureg.check("[]", "[length]")
    def float_a(self, value: pint.Quantity) -> None:
        self._float_a = value


    @property
    def float_b(self) -> pint.Quantity:
        """Return the float for lifting point attached to crane B."""
        return self._float_b

    @float_b.setter
    @ureg.check("[]", "[length]")
    def float_b(self, value: pint.Quantity) -> None:
        self._float_b = value


    @property
    def crane_capacity_a(self) -> pint.Quantity:
        """Return the lifting capacity for crane A."""
        return self._crane_capacity_a

    @crane_capacity_a.setter
    @ureg.check("[]", "[mass]")
    def crane_capacity_a(self, value: pint.Quantity) -> None:
        self._crane_capacity_a = value


    @property
    def crane_capacity_b(self) -> pint.Quantity:
        """Return the lifting capacity for crane B."""
        return self._crane_capacity_b

    @crane_capacity_b.setter
    @ureg.check("[]", "[mass]")
    def crane_capacity_b(self, value: pint.Quantity) -> None:
        self._crane_capacity_b = value


    @property
    def cog_envelope(self) -> pint.Quantity:
        """Return the CoG envelope."""
        return self._cog_envelope

    @cog_envelope.setter
    @ureg.check("[]", "[length]")
    def cog_envelope(self, value: pint.Quantity) -> None:
        self._cog_envelope = value


    @property
    def lift_point_a_wfloat(self) -> pint.Quantity:
        """Return the lift point a positions, considering float."""
        return Q.from_list([self.lift_point_a - self.float_a, self.lift_point_a + self.float_a])


    @property
    def lift_point_b_wfloat(self) -> pint.Quantity:
        """Return the lift point b positions, considering float."""
        return Q.from_list([self.lift_point_b - self.float_b, self.lift_point_b + self.float_b])


    @property
    def cog_offset_a(self) -> pint.Quantity:
        """Return the CoG offsets towards crane a."""
        return abs(self.cog - self.cog_envelope[0])


    @property
    def cog_offset_b(self) -> pint.Quantity:
        """Return the CoG offsets towards crane b."""
        return abs(self.cog_envelope[1] - self.cog)


    @property
    def distance_lift_point_a_to_cog(self) -> pint.Quantity:
        """Return the distance from lift point a to the CoG for all lift cases."""
        return abs(self.cog - self.lift_point_a)


    @property
    def distance_lift_point_b_to_cog(self) -> pint.Quantity:
        """Return the distance from lift point a to the CoG for all lift cases."""
        return abs(self.cog - self.lift_point_b)


    @property
    def distance_lift_point_a_to_lift_point_b(self) -> pint.Quantity:
        """Return the distance from lift point a to lift point b for all lift cases."""
        return abs(self.lift_point_a - self.lift_point_b)


    @property
    def combined_rigging_weight(self) -> pint.Quantity:
        """Return the sum of the rigging weights for cranes a and b for all lift cases."""
        return self.rigging_weight_a + self.rigging_weight_b


    @property
    def distance_lift_point_a_to_cog_offset_towards_a(self) -> pint.Quantity:
        """Return the distance from lift point a to end a of the CoG envelope for all lift cases."""
        return abs(self.cog_envelope[0] - self.lift_point_a)


    @property
    def distance_lift_point_a_to_cog_offset_towards_b(self) -> pint.Quantity:
        """Return the distance from lift point a to end b of the CoG envelope for all lift cases."""
        return abs(self.cog_envelope[1] - self.lift_point_a)


    @property
    def distance_lift_point_b_to_cog_offset_towards_a(self) -> pint.Quantity:
        """Return the distance from lift point b to end a of the CoG envelope for all lift cases."""
        return abs(self.cog_envelope[0] - self.lift_point_b)


    @property
    def distance_lift_point_b_to_cog_offset_towards_b(self) -> pint.Quantity:
        """Return the distance from lift point b to end b of the CoG envelope for all lift cases."""
        return abs(self.cog_envelope[1] - self.lift_point_b)



class LiftCases:
    """Wrapper class around all provided cases."""

    liftcases: list[LiftCase]
    _raw:  str

    def from_yaml(self, text: str) -> LiftCases:
        """Parse the provided text as yaml-input, and create a list of LiftCase objects."""
        # Keep a copy of the provided data
        self._raw = yaml.load(text, Loader=yaml.SafeLoader)
        self.liftcases = []

        for case in self._raw["cases"]:
            self.liftcases.append(LiftCase.from_dict(case))

        return self


    def from_json(self, text: str) -> LiftCases:
        """Parse the provided json-dict to a list of LiftCase objects."""
        # Keep a copy of the provided data
        self._raw = simplejson.loads(text)

        self.liftcases = []
        for case in self._raw:
            self.liftcases.append(LiftCase.from_dict(case))

        return self


    def to_json(self) -> str:
        """Return inputs as a json formatted string."""
        liftcases = [liftcase.to_dict() for liftcase in self.liftcases]

        return simplejson.dumps(liftcases, ignore_nan=True)


    # Slice across the list of LiftCase objects, and return a list or array with input data for all cases
    @property
    def case(self) -> list:
        """Return the ids of all lift cases."""
        return [liftcase.case for liftcase in self.liftcases]


    @property
    def crane_radius_a(self) -> pint.Quantity:
        """Return the crane a lifting radius for all lift cases."""
        return Q.from_list([liftcase.crane_radius_a for liftcase in self.liftcases])


    @property
    def crane_radius_b(self) -> pint.Quantity:
        """Return the crane b lifting radius for all lift cases."""
        return Q.from_list([liftcase.crane_radius_b for liftcase in self.liftcases])


    @property
    def rigging_weight_a(self) -> pint.Quantity:
        """Return the rigging weight suspended from crane a for all lift cases."""
        return Q.from_list([liftcase.rigging_weight_a for liftcase in self.liftcases])


    @property
    def rigging_weight_b(self) -> pint.Quantity:
        """Return the rigging weight suspended from crane b for all lift cases."""
        return Q.from_list([liftcase.rigging_weight_b for liftcase in self.liftcases])


    @property
    def weight_uncertainty_factor(self) -> pint.Quantity:
        """Return the weight_uncertainty_factor for all lift cases."""
        return Q.from_list([liftcase.weight_uncertainty_factor for liftcase in self.liftcases])


    @property
    def cog_uncertainty_factor(self) -> pint.Quantity:
        """Return the CoG uncertainty factor for all lift cases."""
        return Q.from_list([liftcase.cog_uncertainty_factor for liftcase in self.liftcases])


    @property
    def tilt_factor(self) -> pint.Quantity:
        """Return the tilt factor for all lift cases."""
        return Q.from_list([liftcase.tilt_factor for liftcase in self.liftcases])


    @property
    def crane_curve_a(self) -> list[str]:
        """Return the crane curve for crane a for all lift cases."""
        return [liftcase.crane_curve_a for liftcase in self.liftcases]


    @property
    def crane_curve_b(self) -> list[str]:
        """Return the crane curve for crane b for all lift cases."""
        return [liftcase.crane_curve_b for liftcase in self.liftcases]


    @property
    def weight(self) -> pint.Quantity:
        """Return the lifted weight for all lift cases."""
        return Q.from_list([liftcase.weight for liftcase in self.liftcases])


    @property
    def float_a(self) -> pint.Quantity:
        """Return the lift point floats for crane a for all lift cases."""
        return Q.from_list([liftcase.float_a for liftcase in self.liftcases])


    @property
    def float_b(self) -> pint.Quantity:
        """Return the lift point floats for crane b for all lift cases."""
        return Q.from_list([liftcase.float_b for liftcase in self.liftcases])


    @property
    def crane_capacity_a(self) -> pint.Quantity:
        """Return the crane a lifting capacity at the given lifting radius for all lift cases."""
        return Q.from_list([liftcase.crane_capacity_a for liftcase in self.liftcases])


    @property
    def crane_capacity_b(self) -> pint.Quantity:
        """Return the crane b lifting capacity at the given lifting radius for all lift cases."""
        return Q.from_list([liftcase.crane_capacity_b for liftcase in self.liftcases])


    @property
    def lift_point_a(self) -> pint.Quantity:
        """Return the lift point a positions for all lift cases."""
        # Create a numpy array with lift_point_a position for all cases - shape is (number of cases, )
        return Q.from_list([liftcase.lift_point_a for liftcase in self.liftcases])


    @property
    def lift_point_b(self) -> pint.Quantity:
        """Return the lift point b positions, considering float, for all lift cases."""
        # Create a numpy array with lift_point_a position for all cases - shape is (number of cases, )
        return Q.from_list([liftcase.lift_point_b for liftcase in self.liftcases])


    @property
    def lift_point_a_wfloat(self) -> pint.Quantity:
        """Return the lift point a positions, considering float, for all lift cases."""
        # Create a numpy array with lift_point_a position for all cases - shape is (number of cases, )
        left = Q.from_list([liftcase.lift_point_a_wfloat[0] for liftcase in self.liftcases])
        right = Q.from_list([liftcase.lift_point_a_wfloat[1] for liftcase in self.liftcases])

        # stack left edge of CoG envelope, right edge of CoG envelope
        return np.stack((left, right), axis=-1)


    @property
    def lift_point_b_wfloat(self) -> pint.Quantity:
        """Return the lift point a positions, considering float, for all lift cases."""
        # Create a numpy array with lift_point_a position for all cases - shape is (number of cases, )
        left = Q.from_list([liftcase.lift_point_b_wfloat[0] for liftcase in self.liftcases])
        right = Q.from_list([liftcase.lift_point_b_wfloat[1] for liftcase in self.liftcases])

        # stack left edge of CoG envelope, right edge of CoG envelope
        return np.stack((left, right), axis=-1)


    @property
    def cog(self) -> pint.Quantity:
        """Return the CoGs for all lift cases."""
        # Create a numpy array for the centres of gravity
        return Q.from_list([liftcase.cog for liftcase in self.liftcases])


    @property
    def cog_envelope(self) -> pint.Quantity:
        """Return the CoG envelopes for all lift cases."""
        # Create a numpy array for the centre of gravity envelopes
        # Separate out "left" and "right" CoG envelope edges
        left = Q.from_list([liftcase.cog_envelope[0] for liftcase in self.liftcases])
        right = Q.from_list([liftcase.cog_envelope[1] for liftcase in self.liftcases])

        # stack left edge of CoG envelope, right edge of CoG envelope
        return np.stack((left, right), axis=-1)


    @property
    def cog_offset_a(self) -> pint.Quantity:
        """Return the CoG offsets towards crane a for all lift cases."""
        return Q.from_list([liftcase.cog_offset_a for liftcase in self.liftcases])


    @property
    def cog_offset_b(self) -> pint.Quantity:
        """Return the CoG offsets towards crane a for all lift cases."""
        return Q.from_list([liftcase.cog_offset_b for liftcase in self.liftcases])


    @property
    def distance_lift_point_a_to_cog(self) -> pint.Quantity:
        """Return the distance from lift point a to the CoG for all lift cases."""
        return Q.from_list([liftcase.distance_lift_point_a_to_cog for liftcase in self.liftcases])


    @property
    def distance_lift_point_b_to_cog(self) -> pint.Quantity:
        """Return the distance from lift point a to the CoG for all lift cases."""
        return Q.from_list([liftcase.distance_lift_point_b_to_cog for liftcase in self.liftcases])


    @property
    def distance_lift_point_a_to_lift_point_b(self) -> pint.Quantity:
        """Return the distance from lift point a to lift point b for all lift cases."""
        return Q.from_list([liftcase.distance_lift_point_a_to_lift_point_b for liftcase in self.liftcases])



    @property
    def combined_rigging_weight(self) -> pint.Quantity:
        """Return the sum of the rigging weights for cranes a and b for all lift cases."""
        return Q.from_list([liftcase.combined_rigging_weight for liftcase in self.liftcases])


    @property
    def distance_lift_point_a_to_cog_offset_towards_a(self) -> pint.Quantity:
        """Return the distance from lift point a to end a of the CoG envelope for all lift cases."""
        return Q.from_list([liftcase.distance_lift_point_a_to_cog_offset_towards_a for liftcase in self.liftcases])


    @property
    def distance_lift_point_a_to_cog_offset_towards_b(self) -> pint.Quantity:
        """Return the distance from lift point a to end b of the CoG envelope for all lift cases."""
        return Q.from_list([liftcase.distance_lift_point_a_to_cog_offset_towards_b for liftcase in self.liftcases])


    @property
    def distance_lift_point_b_to_cog_offset_towards_a(self) -> pint.Quantity:
        """Return the distance from lift point b to end a of the CoG envelope for all lift cases."""
        return Q.from_list([liftcase.distance_lift_point_b_to_cog_offset_towards_a for liftcase in self.liftcases])


    @property
    def distance_lift_point_b_to_cog_offset_towards_b(self) -> pint.Quantity:
        """Return the distance from lift point b to end b of the CoG envelope for all lift cases."""
        return Q.from_list([liftcase.distance_lift_point_b_to_cog_offset_towards_b for liftcase in self.liftcases])
