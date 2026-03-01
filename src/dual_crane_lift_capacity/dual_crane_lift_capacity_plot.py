"""Main module for creating lift capacity plots."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import matplotlib.axes
import matplotlib.pyplot as plt
import numpy as np

from . import Q, dual_crane_lift_capacity, lift_cases, ureg

if TYPE_CHECKING:
    import pint

logger = logging.getLogger(__name__)


def create_plots(lift_cases: lift_cases.LiftCases,
        lift_case_capacities: dual_crane_lift_capacity.DualCraneLiftCapacity) -> dict:
    """Prepare plots for all cases and return to caller."""
    logger.debug("Start preparing plots")
    # Create plots
    figures = {}
    for i in range(len(lift_cases.cases)):
        figures[lift_cases.cases[i]] = _create_plot(
            lift_cases.cases[i],
            lift_cases.weight_original_unit[i],
            lift_cases.cog_original_unit[i],
            lift_cases.lift_point_a[i],
            lift_cases.lift_point_b[i],
            lift_cases.crane_radius_a[i],
            lift_cases.crane_radius_b[i],
            lift_cases.rigging_weight_a[i],
            lift_cases.rigging_weight_b[i],
            lift_cases.crane_curve_a[i],
            lift_cases.crane_curve_b[i],
            lift_case_capacities.crane_capacity_a[i],
            lift_case_capacities.crane_capacity_b[i],
            lift_cases.tilt_factor[i],
            lift_cases.cog_uncertainty_factor[i],
            lift_cases.weight_uncertainty_factor[i],
            {"x": lift_case_capacities.lift_capacity_curve_x[i], "y": lift_case_capacities.lift_capacity_curve_y[i]},
            lift_case_capacities.lift_capacity_at_cog[i],
            lift_case_capacities.cog_limit_at_given_weight[i],
            lift_case_capacities.true_hook_load_a[i],
            lift_case_capacities.true_hook_load_b[i],
            lift_case_capacities.factored_hook_load_a[i],
            lift_case_capacities.factored_hook_load_b[i])
    logger.debug("Plots prepared.")
    return figures


def _create_plot(
        case: str, weight: pint.Quantity, cog: pint.Quantity, lift_point_a: pint.Quantity, lift_point_b: pint.Quantity,
        crane_radius_a: pint.Quantity, crane_radius_b: pint.Quantity, rigging_weight_a: pint.Quantity,
        rigging_weight_b: pint.Quantity, crane_a: str, crane_b: str, crane_capacity_a: pint.Quantity,
        crane_capacity_b: pint.Quantity, tilt_factor: float, cog_uncertainty_factor: float,
        weight_uncertainty_factor: float, lift_capacity_curve: dict, lift_capacity_at_cog: pint.Quantity,
        cog_limit_at_given_weight: pint.Quantity, true_hook_load_a: pint.Quantity, true_hook_load_b: pint.Quantity,
        factored_hook_load_a: pint.Quantity, factored_hook_load_b: pint.Quantity) -> plt.Figure:
    """Prepare lift capacity plot for a single case as provided by the inputs, and associated tables.

    :param case:                       case id
    :param weight:                     module weight (mass)
    :param cog:                        module CoG location, using same coordinate system as for hook locations.
    :param lift_point_a:               coordinates of hook a, which may consider float (i.e. a range)
    :param lift_point_b:               coordinates of hook b, which may consider float (i.e. a range)
    :param crane_radius_a:             lifting radius for crane a
    :param crane_radius_b:             lifting radius for crane b
    :param rigging_weight_a:           weight of rigging at hook a
    :param rigging_weight_b:           weight of rigging at hook b
    :param crane_a:                    identifier, crane a (i.e. crane curve)
    :param crane_b:                    identifier, crane b (i.e. crane curve)
    :param crane_capacity_a:           crane capacity for crane a at current radius
    :param crane_capacity_b:           crane capacity for crane b at current radius
    :param tilt_factor:                tilt factor
    :param cog_uncertainty_factor:     cog uncertainty factor
    :param weight_uncertainty_factor:  weight uncertainty factor
    :param lift_capacity_curve:        x and y coordinates, crane capacity curve
    :param lift_capacity_at_cog:       maximum lifting weight at current cog (vertical intercept)
    :param cog_limit_at_given_weight:  max and min cog location (horisontal intercepts)
    :param true_hook_load_a:           true hook load, crane a
    :param true_hook_load_b:           true hook load, crane b
    :param factored_hook_load_a:       factored hook load, crane a
    :param factored_hook_load_b:       factored hook load, crane b

    :returns pyplot figure
    """
    ureg.setup_matplotlib(enable=True)
    plt.rcParams["figure.figsize"] = (11.69, 8.27)      # A4 paper size in inches
    fig = plt.figure(num=case)

    ax = plt.subplot2grid((3, 3), (0, 0), colspan=3, rowspan=2)
    plt.title(case)

    # some array's were (possibly) oversized to allow for vectorised calculations. Reduce to only include non nan values
    # to facilitate plotting and reporting.
    cog = cog[~np.isnan(cog.magnitude)]
    lift_capacity_at_cog = lift_capacity_at_cog[~lift_capacity_at_cog.magnitude.mask]

    # weight and CoG plotted first - ensures units used in input will be used on the plot
    _add_cog(weight, cog)
    _add_lift_capacity_curve(ax, lift_capacity_curve)

    # add markers for weight margin
    colours = ["red", "green", "red"]
    if cog.size == 1:
        colours = ["green"]
    elif cog.size == 2:
        colours = ["red"]

    plt.scatter(cog, lift_capacity_at_cog, marker=".", linestyle="None", color=colours, label="Weight margin")

    # add markers for CoG margin
    plt.plot(cog_limit_at_given_weight, weight.repeat(2), marker=".", linestyle="None", markeredgecolor="red",
             label="CoG margin")

    # add miscellaneous annotations
    _add_annotations(ax, weight, cog_limit_at_given_weight, cog, lift_capacity_at_cog, lift_capacity_curve)

    plt.grid(visible=True)

    # add info tables
    _add_info_tables(weight, cog, lift_point_a, lift_point_b, crane_radius_a, crane_radius_b, rigging_weight_a,
                     rigging_weight_b, crane_a, crane_b, crane_capacity_a, crane_capacity_b, true_hook_load_a,
                     true_hook_load_b, factored_hook_load_a, factored_hook_load_b, tilt_factor, cog_uncertainty_factor,
                     weight_uncertainty_factor)

    plt.tight_layout()
    return fig


def _add_lift_capacity_curve(ax: matplotlib.axes.Axes, curve: dict) -> None:
    # axes labels
    plt.xlabel(f"Module CoG [{ax.xaxis.units}]")
    plt.ylabel(f"Weight [{ax.yaxis.units}]")

    # add lift capacity curve and annotate
    plt.plot(curve["x"], curve["y"], marker="_", label="Lift capacity curve")

    h_align = np.repeat("right", curve["x"].size / 2)
    h_align = np.append(h_align, np.repeat("left", curve["x"].size / 2))

    for (x, y, h) in zip(curve["x"], curve["y"], h_align):
        ax.annotate(f"  {y.to(ax.yaxis.units).magnitude}  ", (x, y), textcoords="data", verticalalignment="center",
                    horizontalalignment=h)


def _add_cog(weight: pint.Quantity, cog: pint.Quantity) -> None:
    # add weight and CoG to plot
    if cog.size == 1:		        # CoG only provided
        plt.plot(cog, weight, "go", label="CoG")
    elif cog.size == 2:		        # Envelope only provided
        w = Q.from_list([weight] * 2)
        plt.plot(cog, w, "r", label="CoG")
    elif cog.size == 3:		        # CoG and envelope
        cg = Q.from_list([cog[0], cog[2]])
        w = Q.from_list([weight] * 2)
        plt.plot(cg, w, "r", label="CoG envelope")
        plt.plot(cog[1], weight, "go", label="CoG")


def _add_info_tables(weight: pint.Quantity, cog: pint.Quantity, lift_point_a: pint.Quantity,
                     lift_point_b: pint.Quantity, crane_radius_a: pint.Quantity, crane_radius_b: pint.Quantity,
                     rigging_weight_a: pint.Quantity, rigging_weight_b: pint.Quantity, crane_a: str, crane_b: str,
                     crane_capacity_a: pint.Quantity, crane_capacity_b: pint.Quantity, true_hook_load_a: pint.Quantity,
                     true_hook_load_b: pint.Quantity, factored_hook_load_a: pint.Quantity,
                     factored_hook_load_b: pint.Quantity, tilt_factor: float, cog_uncertainty_factor: float,
                     weight_uncertainty_factor: float) -> None:
    # display crane_a & b such that crane with lowest liftpoint is to the left
    crane_a_idx_offset = 0
    if min(lift_point_a) > min(lift_point_b):
        crane_a_idx_offset = 2

    # Add data table crane A
    _add_data_table("Crane A", _crane_table(crane_a, crane_radius_a, crane_capacity_a, rigging_weight_a, lift_point_a,
                                            true_hook_load_a, factored_hook_load_a), 0 + crane_a_idx_offset)

    # Add data table misc data
    if cog.size == 3:
        cog_tmp = cog - cog[1]
        cog_txt = f"{cog[1]:~0.3f} {cog_tmp[0]:+~0.3f} / {cog_tmp[2]:+~0.3f}"
    elif cog.size == 2:
        cog_prime = (np.max(cog) + np.min(cog)) / 2
        cog_tmp = cog - cog_prime
        cog_txt = fr"{cog_prime:~0.3f} $\pm$ {cog_tmp[1]:~0.3f}"
    elif cog.size == 1:
        cog_txt = f"{cog[0]:~0.3f}"

    cell_text = [["Weight", f"{weight:~0.0f}"],
                 ["CoG / envelope", cog_txt],
                 ["Tilt factor", f"{tilt_factor:0.3f}"],
                 ["CoG uncertainty factor", f"{cog_uncertainty_factor:0.3f}"],
                 ["Weight uncertainty factor", f"{weight_uncertainty_factor:0.3f}"]]
    _add_data_table("Lifted object", cell_text, 1)

    # Add data table crane B
    _add_data_table("Crane B", _crane_table(crane_b, crane_radius_b, crane_capacity_b, rigging_weight_b, lift_point_b,
                                            true_hook_load_b, factored_hook_load_b), 2 - crane_a_idx_offset)


def _crane_table(crane: str, crane_radius: pint.Quantity, crane_capacity: pint.Quantity, rigging_weight: pint.Quantity,
                 lift_point: pint.Quantity, true_hook_load: pint.Quantity, factored_hook_load: pint.Quantity) -> list:
    avg = (np.max(lift_point) + np.min(lift_point)) / 2
    flt = (np.max(lift_point) - np.min(lift_point)) / 2
    return [["Crane", crane],
                 ["Crane radius", f"{crane_radius:~0.1f}"],
                 ["Crane capacity", f"{crane_capacity:~0.0f}"],
                 ["Rigging weight", f"{rigging_weight:~0.0f}"],
                 ["Lift point", fr"{avg:~0.3f} $\pm$ {flt:~0.3f}"],
                 ["Hook load", f"{true_hook_load:~0.0f}"],
                 ["Factored hook load", f"{factored_hook_load:~0.0f}"]]


def _add_data_table(title: str, cell_text: str, loc_idx: int) -> None:
    ax = plt.subplot2grid((3, 3), (2, loc_idx))
    ax.set_title(title)
    ax.axis("off")
    tbl = ax.table(cellText=cell_text, loc="best")
    tbl.auto_set_font_size(value=False)
    tbl.set_fontsize(6)


def _add_annotations(
        ax: matplotlib.axes.Axes, weight: pint.Quantity, cog_limit_at_given_weight: pint.Quantity,
        cog: pint.Quantity, lift_capacity_at_cog: pint.Quantity, lift_capacity_curve: pint.Quantity) -> None:
    # CoG margins
    if cog.size == 3:
        x_cog = cog[1]
    elif cog.size == 2:
        x_cog = (cog[0] + cog[1]) / 2
    elif cog.size == 1:
        x_cog = cog[0]
    y1 = 2 / 3 * np.min(plt.ylim()) * ax.yaxis.units + 1 / 3 * weight   # draw approx 1/3rd off btm of chart
    x1 = min(cog_limit_at_given_weight)
    x2 = max(cog_limit_at_given_weight)
    _annotate_point_pair(ax, f"{x_cog-x1:~0.3f}", (x1, y1), (x_cog, y1))
    _annotate_point_pair(ax, f"{x2-x_cog:~0.3f}", (x_cog, y1), (x2, y1))

    # distance from CoG to peak
    indices_of_peak = np.where(lift_capacity_curve["y"] == lift_capacity_curve["y"].max())
    x_peak = lift_capacity_curve["x"][indices_of_peak]
    peak = np.sort(np.append(x_peak, x_cog))
    dist = np.diff(peak)                            		            # get the distance between each point
    y2 = 1 / 3 * np.min(plt.ylim()) * ax.yaxis.units + 2 / 3 * weight   # draw approx 2/3rd off btm of chart
    for i in range(dist.size):
        if dist[i] > 0.:
            _annotate_point_pair(ax, f"{dist[i]:~0.3f}", (peak[i], y2), (peak[i + 1], y2))

    y_peak = np.max(lift_capacity_curve["y"])
    arrowprops_dimline = {"arrowstyle": "-", "color": "lightgrey"}
    _annotate_point_pair(ax, None, (x_peak[0], y2), (x_peak[0], y_peak), arrowprops=arrowprops_dimline)
    _annotate_point_pair(ax, None, (x_cog, y2), (x_cog, weight), arrowprops=arrowprops_dimline)
    _annotate_point_pair(ax, None, (x_peak[1], y2), (x_peak[1], y_peak), arrowprops=arrowprops_dimline)

    # weight margins
    idx = np.argmin(lift_capacity_at_cog)
    x_min_weight_margin = cog[idx]
    y_min_weight_margin = lift_capacity_at_cog[idx]
    color = "green" if cog.size == 1 else "red"
    x_min = min(lift_capacity_curve["x"])
    x_max = max(lift_capacity_curve["x"])

    x = [x_min, x_max]
    xcg = [min(cog), max(cog)]
    if x_min_weight_margin > x_peak[0]:
        x.reverse()
        xcg.reverse()
    _annotate_point_pair(ax, f"{y_min_weight_margin-weight:~0.0f}", (x[0], weight), (x[0], y_min_weight_margin),
                         ha="left", va="center", color=color)
    _annotate_point_pair(ax, None, (x[0], weight), (xcg[0], weight), arrowprops=arrowprops_dimline)

    # this is ok for normal curves, but needs fixing for float
    if x_peak[0] == x_peak[1]:
        _annotate_point_pair(ax, None, (x[0], y_min_weight_margin), (xcg[0], y_min_weight_margin),
                             arrowprops=arrowprops_dimline)
    else:
        _annotate_point_pair(ax, None, (x[0], y_min_weight_margin), (x_peak[1], y_min_weight_margin),
                             arrowprops=arrowprops_dimline)

    if cog.size == 3:
        _annotate_point_pair(ax, f"{lift_capacity_at_cog[1]-weight:~0.0f}", (x[1], weight),
                             (x[1], lift_capacity_at_cog[1]), ha="left", va="center", color="green")
        _annotate_point_pair(ax, None, (x[1], weight), (xcg[1], weight), arrowprops=arrowprops_dimline)
        _annotate_point_pair(ax, None, (x[1], lift_capacity_at_cog[1]), (x_cog, lift_capacity_at_cog[1]),
                             arrowprops=arrowprops_dimline)


def _annotate_point_pair(ax: matplotlib.axes.Axes, text: str, xy_start: tuple, xy_end: tuple, xycoords: str="data",
                         arrowprops: str|None=None, ha: str="center", va: str="bottom", color: str="black") -> None:
    if arrowprops is None:
        arrowprops = {"arrowstyle": "<->", "shrinkA": 0., "shrinkB": 0., "color": color}
    offset = [0, 5]
    if ha != "center":
        offset.reverse()

    if not (np.isnan(xy_start[0]) or np.isnan(xy_start[1]) or np.isnan(xy_end[0]) or np.isnan(xy_end[1])):
        xy_text = ((xy_start[0] + xy_end[0]) / 2., (xy_start[1] + xy_end[1]) / 2.)

        ax.annotate("", xy=xy_end, xycoords=xycoords, xytext=xy_start, textcoords=xycoords, arrowprops=arrowprops)
        ax.annotate(text=text, xy=xy_text, xycoords=xycoords, xytext=offset, textcoords="offset points", ha=ha, va=va,
                    fontsize=7)
