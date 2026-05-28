"""Handles the lift capacity calculations."""
import dataclasses
import logging

import numpy as np
import pint
import simplejson

from . import lift_cases, ureg

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DualCraneLiftCapacity:
    """Determine and return the lift capacity curve."""

    max_lift_capacity: np.array
    factored_lift_weight: np.array
    lift_capacity_at_cog: np.array
    lift_capacity_at_cog_envelope: np.array
    cog_limits_at_given_weight: np.array
    lift_capacity_curve_x: np.array
    lift_capacity_curve_y: np.array
    true_hook_load_a: np.array
    true_hook_load_b: np.array
    factored_hook_load_a: np.array
    factored_hook_load_b: np.array
    factored_lift_weight: np.array
    weight_margin: np.array                    # overall weight margin, i.e. min of weight_margin
    spare_capacity_a: np.array
    spare_capacity_b: np.array


    def __init__(self, lift_cases: lift_cases.LiftCases) -> None:
        """Create the lift capacity curve.

        The curve is centered on the maximum capacity; therefore determine location of peak (or range if float).

        Based on the intervals for the lift points considering float (degenerate: single point),
        determine the max possible object mass and cg range (if float) or point (if point).

        :lift_cases: class containing the following parameters:
                    rigging_weight_a - weight of rigging at hook a
                    rigging_weight_b - weight of rigging at hook b
                    lift_point_a - coordinates of hook a, which may consider float (i.e. a range)
                    lift_point_b - coordinates of hook b, which may consider float (i.e. a range)
                    weight_uncertainty_factor - weight uncertainty factor
                    cog_uncertainty_factor - cog uncertainty factor
                    tilt_factor - tilt factor
                    weight - module weight (mass)
                    cog - module CoG location, using same coordinate system as for hook locations.
                    crane_capacity_a - lifting capacity of crane a
                    crane_capacity_b - lifting capacity of crane b

        :returns
            Lift capacity curve
            Lift capacity at centre of gravity
            CoG limits at given module weight (mass)
            True hook loads
            Factored hook loads
        """
        # Store a copy of the lift cases provided as input
        self._lift_cases = lift_cases

        # For input purposes, CoGs and CoG envelopes are separated. However, for calculations there is no
        # need for distinction.
        # Create a combined array with CoG and CoG envelopes.
        # Stack left edge of CoG envelope, cog, then right edge of CoG envelope
        cogs = np.stack((lift_cases.cog_envelope[:,0], lift_cases.cog, lift_cases.cog_envelope[:,1]), axis=-1)

        self.max_lift_capacity = (
            lift_cases.crane_capacity_a +
            lift_cases.crane_capacity_b -
            lift_cases.rigging_weight_a -
            lift_cases.rigging_weight_b
        )

        # Follows from moment equilibrium
        l_b = ((lift_cases.crane_capacity_a - lift_cases.rigging_weight_a) / self.max_lift_capacity)[:, None] * \
            (lift_cases.lift_point_b_wfloat - lift_cases.lift_point_a_wfloat)

        cg_max_lift_capacity = (lift_cases.lift_point_b_wfloat - l_b)

        lift_factors = lift_cases.weight_uncertainty_factor * lift_cases.cog_uncertainty_factor * lift_cases.tilt_factor
        self.factored_lift_weight = lift_cases.weight * lift_factors

        # Determine the lift capacity for the CoG / CoG envelope
        lift_capacity_at_cog_and_env = self.__lift_capacity(cogs, cg_max_lift_capacity, lift_cases.crane_capacity_a,
                            lift_cases.crane_capacity_b, lift_cases.rigging_weight_a, lift_cases.rigging_weight_b,
                            lift_cases.lift_point_a_wfloat, lift_cases.lift_point_b_wfloat) / lift_factors[:, None]

        self.lift_capacity_at_cog = lift_capacity_at_cog_and_env[:, 1]
        self.lift_capacity_at_cog_envelope = lift_capacity_at_cog_and_env[:, (0, 2)]

        # Determine the CoG limits where lift capacity matches module weight
        self.cog_limits_at_given_weight = self.__cog_limits(lift_factors, lift_cases.weight,
                            lift_cases.crane_capacity_a, lift_cases.crane_capacity_b, lift_cases.rigging_weight_a,
                            lift_cases.rigging_weight_b, lift_cases.lift_point_a_wfloat,
                            lift_cases.lift_point_b_wfloat)

        # Create an overall x-axis to use as basis for the crane capacity curve
        self.lift_capacity_curve_x = self.__create_x(cogs, self.cog_limits_at_given_weight,
            cg_max_lift_capacity, lift_cases.lift_point_a_wfloat, lift_cases.lift_point_b_wfloat, 0.5 * ureg.meters)

        # determine the combined crane capacity (lift capacity) for each of the cg's in x
        self.lift_capacity_curve_y = self.__lift_capacity(self.lift_capacity_curve_x, cg_max_lift_capacity,
                            lift_cases.crane_capacity_a, lift_cases.crane_capacity_b, lift_cases.rigging_weight_a,
                            lift_cases.rigging_weight_b, lift_cases.lift_point_a_wfloat,
                            lift_cases.lift_point_b_wfloat) / lift_factors[:, None]

        # Calculate the true hook load and factored hook load
        self.true_hook_load_a, self.true_hook_load_b = self.__hook_loads(lift_cases.weight,
            lift_cases.lift_point_a_wfloat, lift_cases.lift_point_b_wfloat, cogs, lift_cases.rigging_weight_a,
            lift_cases.rigging_weight_b)

        self.factored_hook_load_a, self.factored_hook_load_b = self.__hook_loads(lift_cases.weight,
            lift_cases.lift_point_a_wfloat, lift_cases.lift_point_b_wfloat, cogs, lift_cases.rigging_weight_a,
            lift_cases.rigging_weight_b, lift_factors)

        # Calculate the weight margins
        weight_margin_cog_and_env = lift_capacity_at_cog_and_env.T - lift_cases.weight
        self.weight_margin = np.min(weight_margin_cog_and_env, axis=0)

        # Calculate the spare capacity for each crane
        self.spare_capacity_a = lift_cases.crane_capacity_a - np.max(self.factored_hook_load_a, axis=1)
        self.spare_capacity_b = lift_cases.crane_capacity_b - np.max(self.factored_hook_load_b, axis=1)


    def __hook_loads(self, weight: pint.Quantity, lift_point_a: pint.Quantity, lift_point_b: pint.Quantity,
                cog: pint.Quantity, rigging_weight_a: pint.Quantity, rigging_weight_b: pint.Quantity,
                lift_factors: float=1) -> tuple:
        """Compute the hook loads for the load based on mass, CoG, rigging weights, and lift factors.

        :param weight:                     module weight (mass)
        :param lift_point_a:               coordinates of hook a, which may consider float (i.e. a range)
        :param lift_point_b:               coordinates of hook b, which may consider float (i.e. a range)
        :param cog:                        module CoG location, using same coordinate system as for hook locations
        :param rigging_weight_a:           weight of rigging at hook a
        :param rigging_weight_b:           weight of rigging at hook b
        :param lift_factors:               combined lift factors

        :returns a tuple with
            Hook load for crane a
            Hook load for crane b
        """
        hook_load_a_1 = weight * lift_factors * (np.nanmin(lift_point_b, axis=1) - np.nanmin(cog, axis=1)) / \
            (np.nanmin(lift_point_b, axis=1) - np.nanmin(lift_point_a, axis=1)) + rigging_weight_a
        hook_load_a_2 = weight * lift_factors * (np.nanmax(lift_point_b, axis=1) - np.nanmax(cog, axis=1)) / \
            (np.nanmax(lift_point_b, axis=1) - np.nanmax(lift_point_a, axis=1)) + rigging_weight_a
        hook_load_b_1 = weight * lift_factors + rigging_weight_a + rigging_weight_b - hook_load_a_1
        hook_load_b_2 = weight * lift_factors + rigging_weight_a + rigging_weight_b - hook_load_a_2

        hook_load_a = np.concatenate((hook_load_a_1[:, None], hook_load_a_2[:, None]), axis=1)
        hook_load_b = np.concatenate((hook_load_b_1[:, None], hook_load_b_2[:, None]), axis=1)
        logger.debug(f"hook_load_a: {hook_load_a}")
        logger.debug(f"hook_load_b: {hook_load_b}")
        return hook_load_a, hook_load_b


    @ureg.wraps("=A", (None, "=A", "=A", "=A", "=A", "=A", "=A"))
    def __create_x(self, cog: pint.Quantity, cog_lim: pint.Quantity, cg_max_lift_capacity: pint.Quantity,
                   lift_point_a_wfloat: pint.Quantity, lift_point_b_wfloat: pint. Quantity,
                   dx_spacer: pint.Quantity) -> pint.Quantity:
        """Create a sensible x-axis to use as basis for the crane capacity curve.

        * The peak should be in the middle
        * cg, and therefore x, needs to remain between the two lifting points.

        ureg.wraps decorator used as pint does not support fmin/fmax
        :param cog_lim:                    limiting CoG positions at module weight (mass) that are still liftable
        :param cog:                        module cog locations
        :param cg_max_lift_capacity:       cg at maximum lift capacity

        :returns x coordinates
        """
        xmin_1 = np.nanmin(cog_lim, axis=1)
        xmin_2 = np.nanmin(cog, axis=1)
        dxmin = np.nanmin(cg_max_lift_capacity, axis=1) - np.fmin(xmin_1, xmin_2)

        xmax_1 = np.nanmax(cog_lim, axis=1)
        xmax_2 = np.nanmax(cog, axis=1)
        dxmax = np.fmax(xmax_1, xmax_2) - np.nanmax(cg_max_lift_capacity, axis=1)
        dx = np.fmax(dxmin, dxmax) + dx_spacer

        lp_min = np.minimum(lift_point_a_wfloat, lift_point_b_wfloat).min(axis=1)
        lp_max = np.maximum(lift_point_a_wfloat, lift_point_b_wfloat).max(axis=1)

        xmin = np.maximum(np.nanmin(cg_max_lift_capacity, axis=1) - dx, lp_min)
        xmax = np.minimum(np.nanmax(cg_max_lift_capacity, axis=1) + dx, lp_max)

        x_1 = np.array(
                [np.linspace(i, j, 7) for i, j in zip(xmin, np.nanmin(cg_max_lift_capacity, axis=1), strict=True)],
              )
        x_2 = np.array(
                [np.linspace(i, j, 7) for i, j in zip(np.nanmax(cg_max_lift_capacity, axis=1), xmax, strict=True)],
              )
        x = np.concatenate((x_1, x_2), axis=1)
        logger.debug(f"x: {x}")
        return x

    @ureg.wraps("=B", (None, "=A", "=A", "=B", "=B", "=B", "=B", "=A", "=A"))
    def __lift_capacity(self, x: pint.Quantity, cg_max_lift_capacity: pint.Quantity, crane_capacity_a: pint.Quantity,
                        crane_capacity_b: pint.Quantity, rigging_weight_a: pint.Quantity,
                        rigging_weight_b: pint.Quantity, lift_point_a: pint.Quantity, lift_point_b: pint.Quantity,
                        ) -> pint.Quantity:
        """Solve for module mass, such that at least one of the cranes is at capacity.

        As only 1 crane can be at capacity (2 at limiting cases or within area of float), the smaller mass governs the
        lift capacity. This function does not consider the lift-factor; needs to be accounted for elsewhere.
        In cases with float
            for x <= cg_max_lift_capacity, select the minimum for lift_point_a and lift_point_b
            for x >= cg_max_lift_capacity, select the maximum for lift_point_a and lift_point_b
            for other x; the capacity is the combined capacity of the cranes (float).

        :param x:                      a range of cog positions
        :param cg_max_lift_capacity:   the position of the cg giving the maximum lift capacity
        :param crane_capacity_a:       lifting capacity of crane a
        :param crane_capacity_b:       lifting capacity of crane b
        :param rigging_weight_a:       weight of rigging at lift point a
        :param rigging_weight_b:       weight of rigging at lift point b
        :param lift_point_a:           coordinate of lift point a
        :param lift_point_b:           coordinate of lift point b

        :returns the lift capacity associated with x
        """
        # Outside peak area, lp_A and lp_B will be at extremes of allowed float-range
        lp_a = lift_point_a.max(axis=1, keepdims=True) * (x > cg_max_lift_capacity.max(axis=1, keepdims=True))
        lp_a = lift_point_a.min(axis=1, keepdims=True) * (x < cg_max_lift_capacity.min(axis=1, keepdims=True)) + lp_a
        lp_b = lift_point_b.max(axis=1, keepdims=True) * (x > cg_max_lift_capacity.max(axis=1, keepdims=True))
        lp_b = lift_point_b.min(axis=1, keepdims=True) * (x < cg_max_lift_capacity.min(axis=1, keepdims=True)) + lp_b

        # Compute the crane capacity
        m_a = (crane_capacity_a - rigging_weight_a)[:, None] * (lp_b - lp_a) / (lp_b - x)
        m_b = (crane_capacity_b - rigging_weight_b)[:, None] * (lp_b - lp_a) / (x - lp_a)

        m = np.minimum(m_a, m_b)

        # Mask x's within float area
        m_masked = np.ma.masked_where((x >= cg_max_lift_capacity.min(axis=1, keepdims=True)) & \
                                          (x <= cg_max_lift_capacity.max(axis=1, keepdims=True)), m)

        # replace masked values (area within float, but not nan's) with capacity
        max_crane_cap = (crane_capacity_a + crane_capacity_b - rigging_weight_a - rigging_weight_b)[:, None] * \
            np.ones(m.shape)

        m_masked[np.ma.getmask(m_masked) & ~np.isnan(x)] = max_crane_cap[np.ma.getmask(m_masked) & ~np.isnan(x)]
        m_masked[np.isnan(x)] = np.nan

        return m_masked


    def __cog_limits(self, lift_factors: float, weight: pint.Quantity, crane_capacity_a: pint.Quantity,
                     crane_capacity_b: pint.Quantity, rigging_weight_a: pint.Quantity, rigging_weight_b: pint.Quantity,
                     lift_point_a: pint.Quantity, lift_point_b: pint.Quantity) -> pint.Quantity:
        """Given the module weight and lift factors, determine the extreme possible module CoGs.

        This means shifting the CoG until each of the cranes reaches capacity.
        Check CoG remains between lifting points.

        :params lift_factors:               combined lift factors
        :params weight:                     module weight (mass)
        :params crane_capacity_a:           crane capacity for crane a at current radius
        :params crane_capacity_b:           crane capacity for crane b at current radius
        :params rigging_weight_a:           weight of rigging at hook a
        :params rigging_weight_b:           weight of rigging at hook b
        :params lift_point_a:               coordinates of hook a, which may consider float (i.e. a range)
        :params lift_point_b:               coordinates of hook b, which may consider float (i.e. a range)

        :returns limiting CoG coordinates for given weight
        """
        gross_weight = weight * lift_factors + rigging_weight_a + rigging_weight_b

        # Load crane A either to maximum capacity, or gross weight, whichever comes first
        f_a_max_a = np.minimum(gross_weight - rigging_weight_b, crane_capacity_a)

        # Hook load crane B when crane A is loaded to maximum
        f_b_max_a = gross_weight - f_a_max_a

        # Maximum hook load crane B
        f_b_max_b = np.minimum(gross_weight - rigging_weight_a, crane_capacity_b)

        # Check if weight exceeds what can be lifted -> no intercepts -> set to np.nan
        is_not_liftable = f_b_max_a > crane_capacity_b
        f_b_max_a[is_not_liftable] = np.nan
        f_b_max_b[is_not_liftable] = np.nan

        # Number of calcs could be halved by checking if lpa > lpb or vv and combining with max or min as appropriate
        x0 = ((f_b_max_a - rigging_weight_b) / weight / lift_factors) * \
            (np.nanmin(lift_point_b, axis=1) - np.nanmin(lift_point_a, axis=1)) + np.nanmin(lift_point_a, axis=1)
        x1 = ((f_b_max_a - rigging_weight_b) / weight / lift_factors) * \
            (np.nanmax(lift_point_b, axis=1) - np.nanmax(lift_point_a, axis=1)) + np.nanmax(lift_point_a, axis=1)
        x2 = ((f_b_max_b - rigging_weight_b) / weight / lift_factors) * \
            (np.nanmin(lift_point_b, axis=1) - np.nanmin(lift_point_a, axis=1)) + np.nanmin(lift_point_a, axis=1)
        x3 = ((f_b_max_b - rigging_weight_b) / weight / lift_factors) * \
            (np.nanmax(lift_point_b, axis=1) - np.nanmax(lift_point_a, axis=1)) + np.nanmax(lift_point_a, axis=1)
        x = np.stack((x0, x1, x2, x3), axis=1)

        x0_prime = np.nanmin(x, axis=1)
        x1_prime = np.nanmax(x, axis=1)

        x_prime = np.stack((x0_prime, x1_prime), axis=1)

        # Overwrite non-physical solutions (CoGs outside lifting points)
        logger.debug(f"Calculation of intercepts: {x_prime}")

        return x_prime


    @property
    def combined_true_hookload(self) -> pint.Quantity:
        """Return sum of true hookloads."""
        if self.true_hook_load_a is not None and self.true_hook_load_b is not None:
            return self.true_hook_load_a + self.true_hook_load_b
        return None


    @property
    def combined_true_hookload_cog_offset_towards_a(self) -> pint.Quantity:
        """Return sum of true hookloads when CoG is shifted towards Crane A."""
        res = self.combined_true_hookload
        if res is not None:
            return res[:, 0]
        return None


    @property
    def combined_true_hookload_cog_offset_towards_b(self) -> pint.Quantity:
        """Return sum of true hookloads when CoG is shifted towards Crane B."""
        res = self.combined_true_hookload
        if res is not None:
            return res[:, 1]
        return None


    @property
    def combined_factored_hookload(self) -> pint.Quantity:
        """Return sum of factored hookloads."""
        if self.factored_hook_load_a is not None and self.factored_hook_load_b is not None:
            return self.factored_hook_load_a + self.factored_hook_load_b
        return None


    @property
    def combined_factored_hookload_cog_offset_towards_a(self) -> pint.Quantity:
        """Return sum of factored hookloads when CoG is shifted towards Crane A."""
        res = self.combined_factored_hookload
        if res is not None:
            return res[:, 0]
        return None


    @property
    def combined_factored_hookload_cog_offset_towards_b(self) -> pint.Quantity:
        """Return sum of factored hookloads when CoG is shifted towards Crane B."""
        res = self.combined_factored_hookload
        if res is not None:
            return res[:, 1]
        return None


    @property
    def true_hookload_a_with_cog_offset_towards_a(self) -> pint.Quantity:
        """Return true hookload in Crane A with CoG offset shifted towards Crane A."""
        if self.true_hook_load_a is not None:
            return self.true_hook_load_a[:, 0]
        return None


    @property
    def true_hookload_b_with_cog_offset_towards_a(self) -> pint.Quantity:
        """Return true hookload in Crane B with CoG offset shifted towards Crane A."""
        if self.true_hook_load_b is not None:
            return self.true_hook_load_b[:, 0]
        return None


    @property
    def true_hookload_a_with_cog_offset_towards_b(self) -> pint.Quantity:
        """Return true hookload in Crane A with CoG offset shifted towards Crane B."""
        if self.true_hook_load_a is not None:
            return self.true_hook_load_a[:, 1]
        return None


    @property
    def true_hookload_b_with_cog_offset_towards_b(self) -> pint.Quantity:
        """Return true hookload in Crane B with CoG offset shifted towards Crane B."""
        if self.true_hook_load_b is not None:
            return self.true_hook_load_b[:, 1]
        return None


    @property
    def factored_hookload_a_with_cog_offset_towards_a(self) -> pint.Quantity:
        """Return factored hookload in Crane A with CoG offset shifted towards Crane A."""
        if self.factored_hook_load_a is not None:
            return self.factored_hook_load_a[:, 0]
        return None


    @property
    def factored_hookload_b_with_cog_offset_towards_a(self) -> pint.Quantity:
        """Return factored hookload in Crane B with CoG offset shifted towards Crane A."""
        if self.factored_hook_load_b is not None:
            return self.factored_hook_load_b[:, 0]
        return None


    @property
    def factored_hookload_a_with_cog_offset_towards_b(self) -> pint.Quantity:
        """Return factored hookload in Crane A with CoG offset shifted towards Crane B."""
        if self.factored_hook_load_a is not None:
            return self.factored_hook_load_a[:, 1]
        return None


    @property
    def factored_hookload_b_with_cog_offset_towards_b(self) -> pint.Quantity:
        """Return factored hookload in Crane B with CoG offset shifted towards Crane B."""
        if self.factored_hook_load_b is not None:
            return self.factored_hook_load_b[:, 1]
        return None


    @property
    def distance_lift_point_a_to_cog(self) -> pint.Quantity:
        """Return the distance from lift point a to the CoG for all lift cases."""
        return self._lift_cases.distance_lift_point_a_to_cog


    @property
    def distance_lift_point_b_to_cog(self) -> pint.Quantity:
        """Return the distance from lift point a to the CoG for all lift cases."""
        return self._lift_cases.distance_lift_point_b_to_cog


    @property
    def distance_lift_point_a_to_lift_point_b(self) -> pint.Quantity:
        """Return the distance from lift point a to lift point b for all lift cases."""
        return self._lift_cases.distance_lift_point_a_to_lift_point_b


    @property
    def combined_rigging_weight(self) -> pint.Quantity:
        """Return the sum of the rigging weights for cranes a and b for all lift cases."""
        return self._lift_cases.combined_rigging_weight


    @property
    def distance_lift_point_a_to_cog_offset_towards_a(self) -> pint.Quantity:
        """Return the distance from lift point a to end a of the CoG envelope for all lift cases."""
        return self._lift_cases.distance_lift_point_a_to_cog_offset_towards_a


    @property
    def distance_lift_point_a_to_cog_offset_towards_b(self) -> pint.Quantity:
        """Return the distance from lift point a to end b of the CoG envelope for all lift cases."""
        return self._lift_cases.distance_lift_point_a_to_cog_offset_towards_b


    @property
    def distance_lift_point_b_to_cog_offset_towards_a(self) -> pint.Quantity:
        """Return the distance from lift point b to end a of the CoG envelope for all lift cases."""
        return self._lift_cases.distance_lift_point_b_to_cog_offset_towards_a


    @property
    def distance_lift_point_b_to_cog_offset_towards_b(self) -> pint.Quantity:
        """Return the distance from lift point b to end b of the CoG envelope for all lift cases."""
        return self._lift_cases.distance_lift_point_b_to_cog_offset_towards_b


    def to_json(self) -> str:
        """Return results as a json formatted string."""
        def cnv_quantity(val: pint.Quantity | np.ndarray | list) -> dict:
            if isinstance(val, pint.Quantity):
                val, unit = val.magnitude, val.units
                if isinstance(val, np.ndarray):
                    val = val.tolist()
                return {"value": val, "unit": f"{unit:~P}"}
            if isinstance(val, list):
                return [cnv_quantity(a) for a in val]
            return val

        # Create a list of all dataclass variables and manually created properties
        v = vars(self) | \
            {name: getattr(self, name) for name, attr in self.__class__.__dict__.items() if isinstance(attr, property)}
        del v["_lift_cases"]

        # Create a result set for each case
        results = [
            dict(
                zip(v.keys(), (v for v in val), strict=True),
            ) for val in zip(*v.values(), strict=True)
        ]

        # Normalize units
        results = self._normalize(results)

        # Serialize units
        results = [{key: cnv_quantity(val) for (key, val) in res.items()} for res in results]

        return simplejson.dumps(results, ignore_nan=True)

    def _normalize(self, v: list) -> list:
        """Convert results to use input unit."""
        # Anything with dimension length converted to same unit as CoG
        # Anything with dimension mass converted to same unit as weight
        v = [{
                key: val.to(case.cog.units if val.dimensionality == "[length]" else case.weight.units)
                for key, val in res.items()
            } for (res, case) in zip(v, self._lift_cases.liftcases, strict=True)
        ]

        return v
