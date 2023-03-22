import matplotlib.pyplot as plt
import numpy as np

from init import ureg, Q


def create_plots(crane_capacity_a, crane_capacity_b, **kwargs):
    # Create plots
    figures = []
    for i in range(0, len(kwargs['cases'])):
        pass
        x = kwargs['lift_capacity_curve']['x'][i]
        y = kwargs['lift_capacity_curve']['y'][i]
        figures.append(
            _create_plot(
                kwargs['cases'][i],
                kwargs['weight_original_unit'][i],
                kwargs['cog_original_unit'][i],
                kwargs['lift_point_a'][i],
                kwargs['lift_point_b'][i],
                kwargs['crane_radius_a'][i],
                kwargs['crane_radius_b'][i],
                kwargs['rigging_weight_a'][i],
                kwargs['rigging_weight_b'][i],
                kwargs['crane_curve_a'][i],
                kwargs['crane_curve_b'][i],
                crane_capacity_a[i],
                crane_capacity_b[i],
                kwargs['tilt_factor'][i],
                kwargs['cog_uncertainty_factor'][i],
                kwargs['weight_uncertainty_factor'][i],
                {'x': x, 'y': y},
                kwargs['lift_capacity_at_cog'][i],
                kwargs['cog_limit_at_given_weight'][i],
                kwargs['true_hook_load_a'][i],
                kwargs['true_hook_load_b'][i],
                kwargs['factored_hook_load_a'][i],
                kwargs['factored_hook_load_b'][i]))


def _create_plot(
        case, weight, cog, lift_point_a, lift_point_b, crane_radius_a, crane_radius_b,
        rigging_weight_a, rigging_weight_b, crane_a, crane_b, crane_capacity_a, crane_capacity_b,
        tilt_factor, cog_uncertainty_factor, weight_uncertainty_factor,
        lift_capacity_curve, lift_capacity_at_cog, cog_limit_at_given_weight,
        true_hook_load_a, true_hook_load_b, factored_hook_load_a, factored_hook_load_b):
    '''
    Prepares lift capacity plot for a single case as provided by the inputs, and associated tables.

    Args:
        case:                       case id
        weight:                     module weight (mass)
        cog:                        module CoG location, using same coordinate system as for hook locations.
        lift_point_a:               coordinates of hook a, which may consider float (i.e. a range)
        lift_point_b:               coordinates of hook b, which may consider float (i.e. a range)
        crane_radius_a:             lifting radius for crane a
        crane_radius_b:             lifting radius for crane b
        rigging_weight_a:           weight of rigging at hook a
        rigging_weight_b:           weight of rigging at hook b
        crane_a:                    identifier, crane a (i.e. crane curve)
        crane_b:                    identifier, crane b (i.e. crane curve)
        crane_capacity_a:           crane capacity for crane a at current radius
        crane_capacity_b:           crane capacity for crane b at current radius
        tilt_factor:                tilt factor
        cog_uncertainty_factor:     cog uncertainty factor
        weight_uncertainty_factor:  weight uncertainty factor
        lift_capacity_curve:        x and y coordinates, crane capacity curve
        lift_capacity_at_cog:       maximum lifting weight at current cog (vertical intercept)
        cog_limit_at_given_weight:  max and min cog location (horisontal intercepts)
        true_hook_load_a:           true hook load, crane a
        true_hook_load_b:           true hook load, crane b
        factored_hook_load_a:       factored hook load, crane a
        factored_hook_load_b:       factored hook load, crane b

    Returns:
        pyplot figure
    '''
    ureg.setup_matplotlib(True)
    plt.rcParams["figure.figsize"] = (11.69, 8.27)      # A4 paper size in inches
    fig = plt.figure()

    ax = plt.subplot2grid((3, 3), (0, 0), colspan=3, rowspan=2)
    plt.title(case)

    # some array's were (possibly) oversized to allow for vectorised calculations. Reduce to only include non nan values to
    # facilitate plotting and reporting.
    cog = cog[~np.isnan(cog.magnitude)]
    lift_capacity_at_cog = lift_capacity_at_cog[~lift_capacity_at_cog.magnitude.mask]

    # weight and CoG plotted first - ensures units used in input will be used on the plot
    _add_cog(weight, cog)
    _add_lift_capacity_curve(ax, lift_capacity_curve)

    # add markers for weight margin
    colours = ['red', 'green', 'red']
    if cog.size == 1:
        colours = ['green']
    elif cog.size == 2:
        colours = ['red']

    plt.scatter(cog, lift_capacity_at_cog, marker='.', linestyle='None', color=colours)

    # add markers for CoG margin
    plt.plot(cog_limit_at_given_weight, weight.repeat(2), marker='.', linestyle='None', markeredgecolor='red')

    # add miscellaneous annotations
    _add_annotations(ax, weight, cog_limit_at_given_weight, cog, lift_capacity_at_cog, lift_capacity_curve)

    plt.grid(True)

    # add info tables
    _add_info_tables(weight, cog, lift_point_a, lift_point_b, crane_radius_a, crane_radius_b, rigging_weight_a, rigging_weight_b, crane_a,
                     crane_b, crane_capacity_a, crane_capacity_b, true_hook_load_a, true_hook_load_b,
                     factored_hook_load_a, factored_hook_load_b, tilt_factor, cog_uncertainty_factor, weight_uncertainty_factor)

    plt.tight_layout()
    return fig


def _add_lift_capacity_curve(ax, curve):
    # axes labels
    plt.xlabel(f"Module CoG [{ax.xaxis.units}]")
    plt.ylabel(f"Weight [{ax.yaxis.units}]")

    # add lift capacity curve and annotate
    plt.plot(curve['x'], curve['y'], marker='_')

    h_align = np.repeat('right', curve['x'].size / 2)
    h_align = np.append(h_align, np.repeat('left', curve['x'].size / 2))
    for (x, y, h) in zip(curve['x'], curve['y'], h_align):
        ax.annotate('  %d  ' % y.to(ax.yaxis.units).magnitude, (x, y), textcoords='data', verticalalignment='center', horizontalalignment=h)


def _add_cog(weight, cog):
    # add weight and CoG to plot
    if cog.size == 1:		        # CoG only provided
        plt.plot(cog, weight, 'go')
    elif cog.size == 2:		        # Envelope only provided
        w = Q.from_list([weight] * 2)
        plt.plot(cog, w, 'r')
    elif cog.size == 3:		        # CoG and envelope
        cg = Q.from_list([cog[0], cog[2]])
        w = Q.from_list([weight] * 2)
        plt.plot(cg, w, 'r')
        plt.plot(cog[1], weight, 'go')


def _add_info_tables(weight, cog, lift_point_a, lift_point_b, crane_radius_a, crane_radius_b, rigging_weight_a, rigging_weight_b,
                     crane_a, crane_b, crane_capacity_a, crane_capacity_b, true_hook_load_a, true_hook_load_b,
                     factored_hook_load_a, factored_hook_load_b, tilt_factor, cog_uncertainty_factor, weight_uncertainty_factor):
    # display crane_a & B such that crane with lowest liftpoint is to the left
    crane_a_idx_offset = 0
    if min(lift_point_a) > min(lift_point_b):
        crane_a_idx_offset = 2

    # Add data table crane A
    _add_data_table("Crane A", _crane_table(crane_a, crane_radius_a, crane_capacity_a, rigging_weight_a, lift_point_a, true_hook_load_a,
                    factored_hook_load_a), 0 + crane_a_idx_offset)

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
    _add_data_table("Crane B", _crane_table(crane_b, crane_radius_b, crane_capacity_b, rigging_weight_b, lift_point_b, true_hook_load_b,
                    factored_hook_load_b), 2 + crane_a_idx_offset)


def _crane_table(crane, crane_radius, crane_capacity, rigging_weight, lift_point, true_hook_load, factored_hook_load):
    avg = (np.max(lift_point) + np.min(lift_point)) / 2
    flt = (np.max(lift_point) - np.min(lift_point)) / 2
    cell_text = [["Crane", crane],
                 ["Crane radius", f"{crane_radius:~0.1f}"],
                 ["Crane capacity", f"{crane_capacity:~0.0f}"],
                 ["Rigging weight", f"{rigging_weight:~0.0f}"],
                 ["Lift point", fr"{avg:~0.3f} $\pm$ {flt:~0.3f}"],
                 ["Hook load", f"{true_hook_load:~0.0f}"],
                 ["Factored hook load", f"{factored_hook_load:~0.0f}"]]
    return cell_text


def _add_data_table(title, cell_text, loc_idx):
    ax = plt.subplot2grid((3, 3), (2, loc_idx))
    ax.set_title(title)
    ax.axis('off')
    tbl = ax.table(cellText=cell_text, loc='best')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(6)


def _add_annotations(ax, weight, cog_limit_at_given_weight, cog, lift_capacity_at_cog, lift_capacity_curve):
    # CoG margins
    if cog.size == 3:
        x_cog = cog[1]
    elif cog.size == 2:
        x_cog = (cog[0] + cog[1]) / 2
    elif cog.size == 1:
        x_cog = cog[0]
    y1 = 2/3 * np.min(plt.ylim()) * ax.yaxis.units + 1/3 * weight   # draw approx 1/3rd off btm of chart
    x1 = min(cog_limit_at_given_weight)
    x2 = max(cog_limit_at_given_weight)
    _annotate_point_pair(ax, f"{x_cog-x1:~0.3f}", (x1, y1), (x_cog, y1))
    _annotate_point_pair(ax, f"{x2-x_cog:~0.3f}", (x_cog, y1), (x2, y1))

    # distance from CoG to peak
    indices_of_peak = np.where(lift_capacity_curve['y'] == lift_capacity_curve['y'].max())
    x_peak = lift_capacity_curve['x'][indices_of_peak]
    peak = np.sort(np.append(x_peak, x_cog))
    dist = np.diff(peak)                            		        # get the distance between each point
    y2 = 1/3 * np.min(plt.ylim()) * ax.yaxis.units + 2/3 * weight   # draw approx 2/3rd off btm of chart
    for i in range(dist.size):
        if dist[i] > 0.:
            _annotate_point_pair(ax, f"{dist[i]:~0.3f}", (peak[i], y2), (peak[i+1], y2))

    y_peak = np.max(lift_capacity_curve['y'])
    arrowprops_dimline = {'arrowstyle': '-', 'color': 'lightgrey'}
    _annotate_point_pair(ax, None, (x_peak[0], y2), (x_peak[0], y_peak), arrowprops=arrowprops_dimline)
    _annotate_point_pair(ax, None, (x_cog, y2), (x_cog, weight), arrowprops=arrowprops_dimline)
    _annotate_point_pair(ax, None, (x_peak[1], y2), (x_peak[1], y_peak), arrowprops=arrowprops_dimline)

    # weight margins
    idx = np.argmin(lift_capacity_at_cog)
    x_min_weight_margin = cog[idx]
    y_min_weight_margin = lift_capacity_at_cog[idx]
    color = 'green' if cog.size == 1 else 'red'
    x_min = min(lift_capacity_curve['x'])
    x_max = max(lift_capacity_curve['x'])

    x = [x_min, x_max]
    xcg = [min(cog), max(cog)]
    if x_min_weight_margin > x_peak[0]:
        x.reverse()
        xcg.reverse()
    _annotate_point_pair(ax, f"{y_min_weight_margin-weight:~0.0f}", (x[0], weight), (x[0], y_min_weight_margin), ha='left', va='center', color=color)
    _annotate_point_pair(ax, None, (x[0], weight), (xcg[0], weight), arrowprops=arrowprops_dimline)

    # this is ok for normal curves, but needs fixing for float
    if x_peak[0] == x_peak[1]:
        _annotate_point_pair(ax, None, (x[0], y_min_weight_margin), (xcg[0], y_min_weight_margin), arrowprops=arrowprops_dimline)
    else:
        _annotate_point_pair(ax, None, (x[0], y_min_weight_margin), (x_peak[1], y_min_weight_margin), arrowprops=arrowprops_dimline)

    if cog.size == 3:
        _annotate_point_pair(ax, f"{lift_capacity_at_cog[1]-weight:~0.0f}", (x[1], weight), (x[1], lift_capacity_at_cog[1]), ha='left', va='center', color='green')
        _annotate_point_pair(ax, None, (x[1], weight), (xcg[1], weight), arrowprops=arrowprops_dimline)
        _annotate_point_pair(ax, None, (x[1], lift_capacity_at_cog[1]), (x_cog, lift_capacity_at_cog[1]), arrowprops=arrowprops_dimline)

    _annotate_point_pair(ax, None, (x_cog, y1), (x_cog, weight), arrowprops=arrowprops_dimline)
    _annotate_point_pair(ax, None, (x1, y1), (x1, weight), arrowprops=arrowprops_dimline)
    _annotate_point_pair(ax, None, (x2, y1), (x2, weight), arrowprops=arrowprops_dimline)


def _annotate_point_pair(ax, text, xy_start, xy_end, xycoords='data', arrowprops=None, ha='center', va='bottom', color='black'):
    if arrowprops is None:
        arrowprops = {'arrowstyle': '<->', 'shrinkA': 0., 'shrinkB': 0., 'color': color}
    offset = [0, 5]
    if ha != 'center':
        offset.reverse()

    xy_text = ((xy_start[0] + xy_end[0])/2., (xy_start[1] + xy_end[1])/2.)

    ax.annotate('', xy=xy_end, xycoords=xycoords, xytext=xy_start, textcoords=xycoords, arrowprops=arrowprops)
    label = ax.annotate(text=text, xy=xy_text,	xycoords=xycoords, xytext=offset, textcoords='offset points', ha=ha, va=va, fontsize=7)
    return label
