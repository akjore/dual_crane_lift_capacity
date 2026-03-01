"""Main module for dual_crane_lift_capacity package."""
from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

from . import crane_curves, dual_crane_lift_capacity, dual_crane_lift_capacity_plot, lift_cases

# Configure logger
logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DualCraneLift:
    """Get the input data, calculate the combined crane capacities, and optionally create plots."""

    lift_cases: lift_cases.LiftCases = None
    dual_crane_lift_capacity_results: dual_crane_lift_capacity.DualCraneLiftCapacity = None
    _plots: dict = None

    @property
    def plots(self) -> dict[plt.Figure]:
        """Return plots - create them if not already done."""
        if not self._plots:
            self.plots = dual_crane_lift_capacity_plot.create_plots(self.lift_cases,
                self.dual_crane_lift_capacity_results)
        return self._plots


    @plots.setter
    def plots(self, var: dict[plt.Figure]) -> None:
        self._plots = var


    def __init__(self, filename: str="", data: str="") -> None:
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

        # what does this do?
#        if not interactive:
#            mpl.use("agg")

        self.lift_cases = lift_cases.LiftCases(filename=filename, data=data)

        self.dual_crane_lift_capacity_results = dual_crane_lift_capacity.DualCraneLiftCapacity(self.lift_cases)

    @property
    def crane_curve_ids(self) -> list:
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
            res = DualCraneLift(filename=args.inputfile)

            print("check if plots are created when accessing plots")
            print(res.plots)
            for case, plot in res.plots.items():
                plot.savefig(f"{case}.png")
        except Exception:
            logger.exception("")
    else:
        logger.error("No input file specified; quitting.")
