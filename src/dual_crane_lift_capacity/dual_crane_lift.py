"""Main module for dual_crane_lift_capacity package."""
import logging
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

from . import crane_curves, dual_crane_lift_capacity, dual_crane_lift_capacity_plot, input_file_wrapper

logger = logging.getLogger(__name__)


def dual_crane_lift(filename: str="", data: str="", *, interactive: bool=True, create_plots: bool=True) \
        -> input_file_wrapper.DualLiftingCases:
    """Perform one or more dual crane lift calculations and return data to the caller.

    1. Based on selected crane curves and lifting radii, gets the cranes' lifting capacities.
    2. Gets the lift capacity curves and other misc results
    3. Calls for plots to be generated, and either displays or returns those.

    :param filename: filename containing input data to be processed
    :param data:                       input data to be processed
    :param interactive:                boolean, default True: whether or not to show the matplotlib plots
    :returns DualLiftingCases:         wrapper class for input data, computed falues and figures
    """
    logging.getLogger("mpl.font_manager").disabled = True
    if not interactive:
        mpl.use("agg")

    data_cls = input_file_wrapper.DualLiftingCases(filename=filename, data=data)

    # Get crane capacities for specified crane curves and radii
    data_cls.crane_capacity_a = crane_curves.get_crane_capacity(data_cls.crane_curve_a, data_cls.crane_radius_a)
    data_cls.crane_capacity_b = crane_curves.get_crane_capacity(data_cls.crane_curve_b, data_cls.crane_radius_b)

    dual_crane_lift_capacity.dual_crane_lift_capacity(data_cls)

    # Create plots
    if create_plots:
       dual_crane_lift_capacity_plot.create_plots(data_cls)

    if interactive:
        plt.show()
        return None

    return data_cls


def crane_curve_ids() -> list:
    """Return the list of known crane curve ids.

    :returns list of known crane curve ids
    """
    return crane_curves.crane_curve_ids()


if __name__ == "__main__":
    import argparse
    import logging.config

    import yaml

    # configure logging
    def setup_logging(config_file_path: str="logging.config.yaml", logging_level: str=logging.INFO) -> None:
        """Prepare the logging configuration.

        :param config_file_path:   if environment variable is not provided, use this file path
        :param logging_level:      logging level
        """
        file = Path(config_file_path) if config_file_path else None
        if file and file.exists():
            with file.open() as f:
                config = yaml.safe_load(f.read())
            logging.config.dictConfig(config)
        else:
            logging.basicConfig(level=logging_level)


    setup_logging()

    logger = logging.getLogger(__name__)
    logger_pil = logging.getLogger("PIL")
    logger_plt = logging.getLogger("matplotlib")
    logger_pil.setLevel(logging.ERROR)
    logger_plt.setLevel(logging.ERROR)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputfile", help="input yaml file", required=True)
    args = parser.parse_args()

    if args.inputfile:
        try:
            dual_crane_lift(filename=args.inputfile, interactive=True)
        except Exception:
            logger.exception()
    else:
        logger.error("No input file specified; quitting.")
