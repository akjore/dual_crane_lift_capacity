import logging

import numpy as np

from . import ureg

logger = logging.getLogger(__name__)


def dual_crane_lift_capacity(crane_capacity_a, crane_capacity_b, **kwargs):
    """Lift capacity curve is centered on the maximum capacity; therefore determine location
    of peak (or range if float)
    Based on the intervals for the lift points considering float (degenerate: single point),
    determine the max possible object mass and cg range (if float) or point (if point).

    Args:
    ----
        crane_capacity_a:           crane capacity for crane a at current radius
        crane_capacity_b:           crane capacity for crane b at current radius
        kwargs:
            dictionary containing the following variables
                rigging_weight_a - weight of rigging at hook a
                rigging_weight_b - weight of rigging at hook b
                lift_point_a - coordinates of hook a, which may consider float (i.e. a range)
                lift_point_b - coordinates of hook b, which may consider float (i.e. a range)
                weight_uncertainty_factor - weight uncertainty factor
                cog_uncertainty_factor - cog uncertainty factor
                tilt_factor - tilt factor
                weight - module weight (mass)
                cog - module CoG location, using same coordinate system as for hook locations.

    Returns:
    -------
        Lift capacity curve
        Lift capacity at centre of gravity
        CoG limits at given module weight (mass)
        True hook loads
        Factored hook loads
    """
    rigging_weight_a = kwargs["rigging_weight_a"]
    rigging_weight_b = kwargs["rigging_weight_b"]
    lift_point_a = kwargs["lift_point_a"]
    lift_point_b = kwargs["lift_point_b"]
    weight_uncertainty_factor = kwargs["weight_uncertainty_factor"]
    cog_uncertainty_factor = kwargs["cog_uncertainty_factor"]
    tilt_factor = kwargs["tilt_factor"]
    weight = kwargs["weight"]
    cog = kwargs["cog"]

    max_lift_capacity = (crane_capacity_a + crane_capacity_b - rigging_weight_a - rigging_weight_b)

    # follows from moment equilibrium
    l_b = ((crane_capacity_a - rigging_weight_a) / max_lift_capacity)[:, None] * (lift_point_b - lift_point_a)
    cg_max_lift_capacity = (lift_point_b - l_b)
    logger.debug(f"cg_max_lift_capacity: {cg_max_lift_capacity}")

    lift_factors = weight_uncertainty_factor * cog_uncertainty_factor * tilt_factor

    # Determine the lift capacity for the CoG / CoG envelope
    lift_cap_cog = __lift_capacity(cog, cg_max_lift_capacity, crane_capacity_a, crane_capacity_b, rigging_weight_a, rigging_weight_b, lift_point_a, lift_point_b) / lift_factors[:, None]

    # Determine the CoG limits where lift capacity matches module weight
    cog_lim = __cog_limits(lift_factors, weight, crane_capacity_a, crane_capacity_b, rigging_weight_a, rigging_weight_b, lift_point_a, lift_point_b)

    # Create an overall x-axis to use as basis for the crane capacity curve
    x = __create_x(cog, cog_lim, cg_max_lift_capacity, 0.5 * ureg.meters)

    # determine the combined crane capacity (lift capacity) for each of the cg's in x
    lift_cap = __lift_capacity(x, cg_max_lift_capacity, crane_capacity_a, crane_capacity_b, rigging_weight_a, rigging_weight_b, lift_point_a, lift_point_b) / lift_factors[:, None]

    # Calculate the true hook load and factored hook load
    true_hook_load_a, true_hook_load_b = __hook_loads(weight, lift_point_a, lift_point_b, cog, rigging_weight_a, rigging_weight_b)
    factored_hook_load_a, factored_hook_load_b = __hook_loads(weight, lift_point_a, lift_point_b, cog, rigging_weight_a, rigging_weight_b, lift_factors)

    return {"lift_capacity_curve": {"x": x, "y": lift_cap}, "lift_capacity_at_cog": lift_cap_cog, "cog_limit_at_given_weight": cog_lim, "true_hook_load_a": true_hook_load_a, "true_hook_load_b": true_hook_load_b, "factored_hook_load_a": factored_hook_load_a, "factored_hook_load_b": factored_hook_load_b}


def __hook_loads(weight, lift_point_a, lift_point_b, cog, rigging_weight_a, rigging_weight_b, lift_factors=1):
    """Based on the weight (mass), the centre of gravity, the rigging weights and the lift factor, compute the hook loads.

    Args:
    ----
        weight:                     module weight (mass)
        lift_point_a:               coordinates of hook a, which may consider float (i.e. a range)
        lift_point_b:               coordinates of hook b, which may consider float (i.e. a range)
        cog:                        module CoG location, using same coordinate system as for hook locations
        rigging_weight_a:           weight of rigging at hook a
        rigging_weight_b:           weight of rigging at hook b
        lift_factors:               combined lift factors

    Returns:
    -------
        Hook load for crane a
        Hook load for crane b
    """
    hook_load_a_1 = weight * lift_factors * (np.nanmin(lift_point_b, axis=1) - np.nanmin(cog, axis=1)) / (np.nanmin(lift_point_b, axis=1) - np.nanmin(lift_point_a, axis=1)) + rigging_weight_a
    hook_load_a_2 = weight * lift_factors * (np.nanmax(lift_point_b, axis=1) - np.nanmax(cog, axis=1)) / (np.nanmax(lift_point_b, axis=1) - np.nanmax(lift_point_a, axis=1)) + rigging_weight_a
    hook_load_b_1 = weight * lift_factors + rigging_weight_a + rigging_weight_b - hook_load_a_1
    hook_load_b_2 = weight * lift_factors + rigging_weight_a + rigging_weight_b - hook_load_a_2

    hook_load_a = np.concatenate((hook_load_a_1[:, None], hook_load_a_2[:, None]), axis=1)
    hook_load_b = np.concatenate((hook_load_b_1[:, None], hook_load_b_2[:, None]), axis=1)
    logger.debug(f"hook_load_a: {hook_load_a}")
    logger.debug(f"hook_load_b: {hook_load_b}")
    return hook_load_a, hook_load_b


@ureg.wraps("=A", ("=A", "=A", "=A", "=A"))
def __create_x(cog, cog_lim, cg_max_lift_capacity, dx_spacer):
    """Create a sensible x-axis to use as basis for the crane capacity curve.
    * The peak should be in the middle
    * cg, and therefore x, needs to remain between the two lifting points.

    ureg.wraps decorator used as pint does not support fmin/fmax
    Args:
        cog_lim:                    limiting CoG positions at module weight (mass) that are still liftable
        cog:                        module cog locations
        cg_max_lift_capacity:       cg at maximum lift capacity

    Returns
    -------
        x coordinates
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


def __lift_capacity(x, cg_max_lift_capacity, crane_capacity_a, crane_capacity_b, rigging_weight_a, rigging_weight_b, lift_point_a, lift_point_b):
    """Solve for module mass, such that at least one of the cranes is at capacity.
    As only 1 crane can be at capacity (2 at limiting cases or within area of float), the smaller
    mass governs the lift capacity.
    This function does not consider the lift-factor; needs to be accounted for elsewhere.
    In cases with float
        for x <= cg_max_lift_capacity, select the minimum for lift_point_a and lift_point_b
        for x >= cg_max_lift_capacity, select the maximum for lift_point_a and lift_point_b
        for other x; the capacity is the combined capacity of the cranes (float).

    Args:
    ----
        x:                      a range of cog positions
        cg_max_lift_capacity:   the position of the cg giving the maximum lift capacity
        crane_capacity_a:       lifting capacity of crane a
        crane_capacity_b:       lifting capacity of crane b
        rigging_weight_a:       weight of rigging at lift point a
        rigging_weight_b:       weight of rigging at lift point b
        lift_point_a:           coordinate of lift point a
        lift_point_b:           coordinate of lift point b

    Returns:
    -------
        the lift capacity associated with x
    """
    # Mask x's within float area
    xp = ureg.Quantity(np.ma.masked_where((x >= cg_max_lift_capacity.min(axis=1, keepdims=True)) & (x <= cg_max_lift_capacity.max(axis=1, keepdims=True)), x.magnitude), x.units)

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
    max_crane_cap = (crane_capacity_a + crane_capacity_b - rigging_weight_a - rigging_weight_b)[:, None] * np.ones(m.shape)
    m[np.ma.getmask(m) & ~np.isnan(x)] = max_crane_cap[np.ma.getmask(m) & ~np.isnan(x)]
    m[np.isnan(x)] = np.nan
    logger.debug(f"Lift capacity, m: {m}")
    return m


def __cog_limits(lift_factors, weight, crane_capacity_a, crane_capacity_b, rigging_weight_a, rigging_weight_b, lift_point_a, lift_point_b):
    """Given the module weight and lift factors, determine the extreme possible module CoGs.
    This means shifting the CoG until each of the cranes reaches capacity.
    Check CoG remains between lifting points.

    Args:
    ----
        lift_factors:               combined lift factors
        weight:                     module weight (mass)
        crane_capacity_a:           crane capacity for crane a at current radius
        crane_capacity_b:           crane capacity for crane b at current radius
        rigging_weight_a:           weight of rigging at hook a
        rigging_weight_b:           weight of rigging at hook b
        lift_point_a:               coordinates of hook a, which may consider float (i.e. a range)
        lift_point_b:               coordinates of hook b, which may consider float (i.e. a range)

    Returns:
    -------
        limiting CoG coordinates for given weight
    """
    f_b_max_a = (weight * lift_factors + rigging_weight_a + rigging_weight_b - crane_capacity_a)    # Hook load crane B when crane A is loaded to capacity
    f_b_max_b = crane_capacity_b * 1															    # crane B loaded to capacity. Multiply with 1 to create new object

    is_not_liftable = f_b_max_a > crane_capacity_b												    # Logic check that computed hook load is within capacity
    f_b_max_a[is_not_liftable] = np.nan														        # set to nan where hook load exceeds crane capacity (not liftable)
    f_b_max_b[is_not_liftable] = np.nan

    if np.all(lift_point_a.min(1) < lift_point_b.min(1)):			                                # crane A has lower coordinates vs crane B
        f_b_min = f_b_max_a
        f_b_max = f_b_max_b
    else:														                                    # else, crane B has lower coordinates vs crane A
        f_b_min = f_b_max_b
        f_b_max = f_b_max_a

    x0 = ((f_b_min - rigging_weight_b) / weight / lift_factors) * (np.nanmin(lift_point_b, axis=1) - np.nanmin(lift_point_a, axis=1)) + np.nanmin(lift_point_a, axis=1)
    x1 = ((f_b_max - rigging_weight_b) / weight / lift_factors) * (np.nanmax(lift_point_b, axis=1) - np.nanmax(lift_point_a, axis=1)) + np.nanmax(lift_point_a, axis=1)
    x = np.stack((x0, x1), axis=1)

    # Overwrite non-physical solutions (CoGs outside lifting points)
    logger.debug(f"Intermediate calculation of intercepts: {x}")
    if np.all(lift_point_a.min(1) < lift_point_b.min(1)):			                                # crane A has lower coordinates vs crane B
        non_physical = (x < lift_point_a).any() or (x > lift_point_b).any()
    else:
        non_physical = (x > lift_point_a).any() or (x < lift_point_b).any()
    x[non_physical] = np.nan

    logger.debug(f"Calculation of intercepts after removing non-physical solutions: {x}")

    return x
