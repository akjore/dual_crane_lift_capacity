"""Handles the lift capacity calculations."""
import dataclasses
import logging

import numpy as np
import pint

from . import lift_cases, ureg
from .crane_curves import CraneCurves

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DualCraneLiftCapacity:
    """Determine and return the lift capacity curve."""

    crane_curves = None
    crane_capacity_a = None
    crane_capacity_b = None
    lift_capacity_at_cog = None
    cog_limit_at_given_weight = None
    lift_capacity_curve_x = None
    lift_capacity_curve_y = None
    true_hook_load_a = None
    true_hook_load_b = None
    factored_hook_load_a = None
    factored_hook_load_b = None
    factored_lift_weight = None
    weight_margin = None


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

        :returns a dictionary with the following
            Lift capacity curve
            Lift capacity at centre of gravity
            CoG limits at given module weight (mass)
            True hook loads
            Factored hook loads
        """
        # Get crane capacities for specified crane curves and radii
        self.crane_curves = CraneCurves()

        self.crane_capacity_a = self.crane_curves.crane_capacity(lift_cases.crane_curve_a, lift_cases.crane_radius_a)
        self.crane_capacity_b = self.crane_curves.crane_capacity(lift_cases.crane_curve_b, lift_cases.crane_radius_b)

        self.max_lift_capacity = (self.crane_capacity_a + self.crane_capacity_b - lift_cases.rigging_weight_a -
                         lift_cases.rigging_weight_b)

        # follows from moment equilibrium
        l_b = ((self.crane_capacity_a - lift_cases.rigging_weight_a) / self.max_lift_capacity)[:, None] * \
            (lift_cases.lift_point_b - lift_cases.lift_point_a)

        cg_max_lift_capacity = (lift_cases.lift_point_b - l_b)
        logger.debug(f"cg_max_lift_capacity: {cg_max_lift_capacity}")

        lift_factors = lift_cases.weight_uncertainty_factor * lift_cases.cog_uncertainty_factor * lift_cases.tilt_factor
        self.factored_lift_weight = lift_cases.weight * lift_factors

        # Determine the lift capacity for the CoG / CoG envelope
        self.lift_capacity_at_cog = self.__lift_capacity(lift_cases.cog, cg_max_lift_capacity, self.crane_capacity_a,
                            self.crane_capacity_b, lift_cases.rigging_weight_a, lift_cases.rigging_weight_b,
                            lift_cases.lift_point_a, lift_cases.lift_point_b) / lift_factors[:, None]

        # Determine the CoG limits where lift capacity matches module weight
        self.cog_limit_at_given_weight = self.__cog_limits(lift_factors, lift_cases.weight, self.crane_capacity_a,
                            self.crane_capacity_b, lift_cases.rigging_weight_a, lift_cases.rigging_weight_b,
                            lift_cases.lift_point_a, lift_cases.lift_point_b)

        # Create an overall x-axis to use as basis for the crane capacity curve
        self.lift_capacity_curve_x = self.__create_x(lift_cases.cog, self.cog_limit_at_given_weight,
            cg_max_lift_capacity, 0.5 * ureg.meters)

        # determine the combined crane capacity (lift capacity) for each of the cg's in x
        self.lift_capacity_curve_y = self.__lift_capacity(self.lift_capacity_curve_x, cg_max_lift_capacity,
                            self.crane_capacity_a, self.crane_capacity_b, lift_cases.rigging_weight_a,
                            lift_cases.rigging_weight_b, lift_cases.lift_point_a, lift_cases.lift_point_b) \
                            / lift_factors[:, None]

        # Calculate the true hook load and factored hook load
        self.true_hook_load_a, self.true_hook_load_b = self.__hook_loads(lift_cases.weight, lift_cases.lift_point_a,
            lift_cases.lift_point_b, lift_cases.cog, lift_cases.rigging_weight_a, lift_cases.rigging_weight_b)

        self.factored_hook_load_a, self.factored_hook_load_b = self.__hook_loads(lift_cases.weight,
            lift_cases.lift_point_a, lift_cases.lift_point_b, lift_cases.cog, lift_cases.rigging_weight_a,
            lift_cases.rigging_weight_b, lift_factors)

        # Calculate the weight margin
        self.weight_margin = self.lift_capacity_at_cog - lift_cases.weight


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


    @ureg.wraps("=A", (None, "=A", "=A", "=A", "=A"))
    def __create_x(self, cog: pint.Quantity, cog_lim: pint.Quantity, cg_max_lift_capacity: pint.Quantity, dx_spacer:
                   pint.Quantity) -> pint.Quantity:
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

        xmin = np.nanmin(cg_max_lift_capacity, axis=1) - dx
        xmax = np.nanmax(cg_max_lift_capacity, axis=1) + dx

        x_1 = np.array([np.linspace(i, j, 7) for i, j in zip(xmin, np.nanmin(cg_max_lift_capacity, axis=1))])
        x_2 = np.array([np.linspace(i, j, 7) for i, j in zip(np.nanmax(cg_max_lift_capacity, axis=1), xmax)])
        x = np.concatenate((x_1, x_2), axis=1)
        logger.debug(f"x: {x}")
        return x


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
        # Mask x's within float area
        xp = ureg.Quantity(np.ma.masked_where((x >= cg_max_lift_capacity.min(axis=1, keepdims=True)) & \
                                          (x <= cg_max_lift_capacity.max(axis=1, keepdims=True)), x.magnitude), x.units)

        # Outside peak area, lp_A and lp_B will be at extremes of allowed float-range
        lp_a = lift_point_a.max(axis=1, keepdims=True) * (xp > cg_max_lift_capacity.max(axis=1, keepdims=True))
        lp_a = lift_point_a.min(axis=1, keepdims=True) * (xp < cg_max_lift_capacity.min(axis=1, keepdims=True)) + lp_a
        lp_b = lift_point_b.max(axis=1, keepdims=True) * (xp > cg_max_lift_capacity.max(axis=1, keepdims=True))
        lp_b = lift_point_b.min(axis=1, keepdims=True) * (xp < cg_max_lift_capacity.min(axis=1, keepdims=True)) + lp_b

        # Compute the crane capacity
        m_a = (crane_capacity_a - rigging_weight_a)[:, None] * (lp_b - lp_a) / (lp_b - xp)
        m_b = (crane_capacity_b - rigging_weight_b)[:, None] * (lp_b - lp_a) / (xp - lp_a)

        m = np.minimum(m_a, m_b)

        # replace masked values (area within float, but not nan's) with capacity
        max_crane_cap = (crane_capacity_a + crane_capacity_b - rigging_weight_a - rigging_weight_b)[:, None] * \
            np.ones(m.shape)
        m[np.ma.getmask(m) & ~np.isnan(x)] = max_crane_cap[np.ma.getmask(m) & ~np.isnan(x)]
        m[np.isnan(x)] = np.nan
        logger.debug(f"Lift capacity, m: {m}")
        return m


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
        # Hook load crane B when crane A is loaded to capacity
        f_b_max_a = (weight * lift_factors + rigging_weight_a + rigging_weight_b - crane_capacity_a)
        # crane B loaded to capacity. Multiply with 1 to create new object
        f_b_max_b = crane_capacity_b * 1

        # Logic check that computed hook load is within capacity
        is_not_liftable = f_b_max_a > crane_capacity_b

        # set to nan where hook load exceeds crane capacity (not liftable)
        f_b_max_a[is_not_liftable] = np.nan
        f_b_max_b[is_not_liftable] = np.nan

        # crane A has lower coordinates vs crane B
        if np.all(lift_point_a.min(1) < lift_point_b.min(1)):
            f_b_min = f_b_max_a
            f_b_max = f_b_max_b
        # else, crane B has lower coordinates vs crane A
        else:
            f_b_min = f_b_max_b
            f_b_max = f_b_max_a

        x0 = ((f_b_min - rigging_weight_b) / weight / lift_factors) * \
            (np.nanmin(lift_point_b, axis=1) - np.nanmin(lift_point_a, axis=1)) + np.nanmin(lift_point_a, axis=1)
        x1 = ((f_b_max - rigging_weight_b) / weight / lift_factors) * \
            (np.nanmax(lift_point_b, axis=1) - np.nanmax(lift_point_a, axis=1)) + np.nanmax(lift_point_a, axis=1)
        x = np.stack((x0, x1), axis=1)

        # Overwrite non-physical solutions (CoGs outside lifting points)
        logger.debug(f"Intermediate calculation of intercepts: {x}")
        # crane A has lower coordinates vs crane B
        if np.all(lift_point_a.min(1) < lift_point_b.min(1)):
            non_physical = (x < lift_point_a).any() or (x > lift_point_b).any()
        else:
            non_physical = (x > lift_point_a).any() or (x < lift_point_b).any()
        x[non_physical] = np.nan

        logger.debug(f"Calculation of intercepts after removing non-physical solutions: {x}")

        return x
