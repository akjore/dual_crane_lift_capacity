import argparse
import dataclasses
import logging

import matplotlib.pyplot as plt

import crane_curves
import dual_crane_lift_capacity
import dual_crane_lift_capacity_plot
import input_file_wrapper


def main(filename='', data='', interactive=True):
    '''
    Main entry point if running dualCraneLiftCapacity from the console.
    1. Based on selected crane curves and lifting radii, gets the cranes' lifting capacities.
    2. Gets the lift capacity curves and other misc results
    3. Calls for plots to be generated, and either displays or returns those

    Args:
        filename:                   filename containing input data to be processed
        data:                       input data to be processed
        interactive:                boolean, default True: whether or not to show the matplotlib plots

    Returns:
        figures:                    lift capacity curve(s)
    '''
    data_cls = input_file_wrapper.DualLiftingCases(filename=filename, data=data)

    # get crane capacities for specified crane curves and radii
    crane_capacity_a = crane_curves.get_crane_capacity(data_cls.crane_curve_a, data_cls.crane_radius_a)
    crane_capacity_b = crane_curves.get_crane_capacity(data_cls.crane_curve_b, data_cls.crane_radius_b)

    ret = dual_crane_lift_capacity.dual_crane_lift_capacity(crane_capacity_a, crane_capacity_b, **dataclasses.asdict(data_cls))

    # Create plots
    figures = []
    for i in range(0, len(data_cls.cases)):
        x = ret['lift_capacity_curve']['x'][i]
        y = ret['lift_capacity_curve']['y'][i]
        figures.append(
            dual_crane_lift_capacity_plot.create_plot(
                data_cls.cases[i],
                data_cls.weight[i],
                data_cls.cog[i],
                data_cls.lift_point_a[i],
                data_cls.lift_point_b[i],
                data_cls.crane_radius_a[i],
                data_cls.crane_radius_b[i],
                data_cls.rigging_weight_a[i],
                data_cls.rigging_weight_b[i],
                data_cls.crane_curve_a[i],
                data_cls.crane_curve_b[i],
                crane_capacity_a[i],
                crane_capacity_b[i],
                data_cls.tilt_factor[i],
                data_cls.cog_uncertainty_factor[i],
                data_cls.weight_uncertainty_factor[i],
                {'x': x, 'y': y},
                ret['lift_capacity_at_cog'][i],
                ret['cog_limit_at_given_weight'][i],
                ret['true_hook_load_a'][i],
                ret['true_hook_load_b'][i],
                ret['factored_hook_load_a'][i],
                ret['factored_hook_load_b'][i]))

    if interactive:
        plt.show()
    else:
        plt.close('all')
        return figures


if __name__ == "__main__":
    import init

    init.setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputfile", help="input yaml file", required=True)
    args = parser.parse_args()

    plt.set_loglevel("info")

    if args.inputfile:
        try:
            main(filename=args.inputfile, interactive=True)
        except Exception as e:
            logger.error(e, exc_info=True)
    else:
        logger.error("No input file specified; quitting.")
