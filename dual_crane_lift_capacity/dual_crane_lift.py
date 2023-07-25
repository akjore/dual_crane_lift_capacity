import argparse
import dataclasses
import logging

import matplotlib
import matplotlib.pyplot as plt

import dualCraneLiftCapacity.lib.crane_curves
import dualCraneLiftCapacity.lib.dual_crane_lift_capacity
import dualCraneLiftCapacity.lib.dual_crane_lift_capacity_plot
import dualCraneLiftCapacity.lib.init
import dualCraneLiftCapacity.lib.input_file_wrapper


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

    logging.getLogger('matplotlib.font_manager').disabled = True
    if not interactive:
        matplotlib.use('agg')

    data_cls = dualCraneLiftCapacity.lib.input_file_wrapper.DualLiftingCases(filename=filename, data=data)

    # Get crane capacities for specified crane curves and radii
    crane_capacity_a = dualCraneLiftCapacity.lib.crane_curves.get_crane_capacity(data_cls.crane_curve_a, data_cls.crane_radius_a)
    crane_capacity_b = dualCraneLiftCapacity.lib.crane_curves.get_crane_capacity(data_cls.crane_curve_b, data_cls.crane_radius_b)

    ret = dualCraneLiftCapacity.lib.dual_crane_lift_capacity.dual_crane_lift_capacity(crane_capacity_a, crane_capacity_b, **dataclasses.asdict(data_cls))

    # Create plots
    figures = dualCraneLiftCapacity.lib.dual_crane_lift_capacity_plot.create_plots(crane_capacity_a, crane_capacity_b, **{**dataclasses.asdict(data_cls), **ret})

    if interactive:
        plt.show()
    else:
        return figures


def crane_curve_ids():
    return dualCraneLiftCapacity.lib.crane_curves.crane_curve_ids()


if __name__ == "__main__":
    import logging.config
    import os

    import yaml


    # configure logging
    def setup_logging(config_file_path='logging.config.yaml', logging_level=logging.INFO):
        '''
        Setup logging configuration

        Args:
            config_file_path:   if environment variable is not provided, use this file math
            logging_level:      logging level
        '''
        path = config_file_path
        if os.path.exists(path):
            with open(path, 'rt') as f:
                config = yaml.safe_load(f.read())
            logging.config.dictConfig(config)
        else:
            logging.basicConfig(level=logging_level)


    setup_logging()

    logger = logging.getLogger(__name__)
    logger_pil = logging.getLogger('PIL')
    logger_plt = logging.getLogger('matplotlib')
    logger_pil.setLevel(logging.ERROR)
    logger_plt.setLevel(logging.ERROR)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputfile", help="input yaml file", required=True)
    args = parser.parse_args()

    if args.inputfile:
        try:
            main(filename=args.inputfile, interactive=True)
        except Exception as e:
            logger.error(e, exc_info=True)
    else:
        logger.error("No input file specified; quitting.")
