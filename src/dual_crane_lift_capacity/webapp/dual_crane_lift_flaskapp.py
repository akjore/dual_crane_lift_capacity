"""Web application front-end for dual crane lift."""
import datetime
import json
import logging
import os
import tempfile
import time
import zipfile
from importlib.resources import files
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
import yaml
from flask import Flask, Response, jsonify, render_template, request, send_from_directory
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from zoneinfo import ZoneInfo

import dual_crane_lift_capacity.dual_crane_lift
from dual_crane_lift_capacity.crane_curves import CraneCurves

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_prefixed_env()      # Loads all FLASK_xx variables in environment into app.config
app.secret_key = app.config.get("SECRET_KEY", "default_key")

app.jinja_env.globals["GIT_HASH"] = None
app.jinja_env.globals["GIT_COMMIT_DATE"] = None
app.jinja_env.globals["TEST_RESULT_FILENAME"] = None
app.jinja_env.globals["TEST_RETCODE"] = None

app.config["UPLOAD_EXTENSIONS"] = ".yaml, .yml"
app.config["MAX_TMP_FILE_AGE"] = 12     # hours

TMP_FOLDER = "TMP_FOLDER"
TEST_FOLDER = "tests"               # relative to package folder
SAMPLE_FOLDER = "sample"            # relative to package folder


def get_version_info() -> None:
    """Get current version and store in jinja_env.globals."""
    app.jinja_env.globals["VERSION"] = dual_crane_lift_capacity.__version__
    app.logger.debug(f"Version: {app.jinja_env.globals['VERSION']}")


def get_test_status() -> None:
    """Run pytest. The return code and the location of the the test report are stored in jinja_env.globals."""
    filename = app.config.get("PYTEST_OUTPUT_FILE")
    if not filename:
        filename = "pytest.html"
        app.logger.warning(f"Config variable PYTEST_OUTPUT_FILE not set - writing test results to {filename}")

    if app.config.get(TMP_FOLDER):
        filename_with_path = Path(app.config.get(TMP_FOLDER)) / filename
    else:
        filename_with_path = filename
        app.logger.warning(f"Config variable TMP_FOLDER not set - writing test results to {filename_with_path}")

    test_folder = Path(files("dual_crane_lift_capacity")) / TEST_FOLDER

    app.jinja_env.globals["TEST_RESULT_FILENAME"] = filename
    app.jinja_env.globals["TEST_RETCODE"] = pytest.main([test_folder, "--self-contained-html",
                                                         f"--html={filename_with_path}"])
    app.logger.debug(f"Pytest result file: {app.jinja_env.globals['TEST_RESULT_FILENAME']}")
    app.logger.debug(f"Pytest return code: {app.jinja_env.globals['TEST_RETCODE']}")


def get_supported_crane_curves() -> None:
    """Get a list of the supported crane curves and store in jinja_env.globals."""
    supported_crane_curves = CraneCurves().crane_curve_ids
    app.jinja_env.globals["SUPPORTED_CRANE_CURVE_IDS"] = supported_crane_curves
    app.logger.debug(f"Supported crane curves: {app.jinja_env.globals['SUPPORTED_CRANE_CURVE_IDS']}")


def clear_tmp_files() -> None:
    """Go through the files in path 'path', and delete any older than 'max_age' hours."""
    path = app.config.get("TMP_FOLDER")
    max_age = app.config.get("MAX_TMP_FILE_AGE")
    now = time.time()
    folder = Path(path)
    for file in folder:
        if file.is_file() and file.stat().st_mtime < now - max_age * 60 * 60:
            file.unlink()

def make_png(figure: plt.Figure) -> bytes:
    """Take a pyplot figure and write it to a png in memory.

    :param figure: pyplot.figure object
    :returns figure as a png
    """
    canvas = FigureCanvas(figure)
    png_output = BytesIO()
    canvas.print_png(png_output)
    png_output.seek(0)
    return png_output.getvalue()


def prepare_dual_crane_lift_plots(filecontent: str) -> tuple:
    """Take an input file, create figures, convert to pngs, and write to disk.

    If a single case is provided, the .png filename is returned.
    If multiple cases are provided, a .zip filename is returned.

    :param filecontent: a yaml inputfile
    :returns a filename, either a png or zip
    :raises Exception: some error while processing the provided filecontent
    """
    try:
        data_cls = dual_crane_lift_capacity.dual_crane_lift.dual_crane_lift(data=filecontent, interactive=False)
        app.logger.debug(f"Returned with {len(data_cls.figures)} figure(s).")

        # grab the data from the plots
        data = []
        for v in data_cls.figures.values():
            case = {}
            # assumption! axis 0 contains the main plot
            for line in v.axes[0].get_lines():
                # any lines containing one or more nans are not of interest - skip
                if not (np.isnan(line.get_xdata().magnitude).any() or np.isnan(line.get_ydata().magnitude).any()):
                    case[line.get_label()] = {"x": line.get_xdata().magnitude.tolist(),
                                              "y": line.get_ydata().magnitude.tolist()}

            data.append({v.axes[0].title.get_text(): case})

        pngs = {k: make_png(v) for k, v in data_cls.figures.items()}

        # save data as .json
        with tempfile.NamedTemporaryFile(suffix=".json", dir=app.config.get(TMP_FOLDER), delete=False) as file_data:
            file_data.write(bytes(json.dumps(data, indent=5), "ascii"))

        if len(pngs) == 1:
            # as only one file, write the figure to file as png
            with tempfile.NamedTemporaryFile(suffix=".png", dir=app.config.get(TMP_FOLDER), delete=False) as file_plot:
                file_plot.write(next(iter(pngs.values())))
                file_plot.flush()
        else:
            # multiple files -> bundle in a zip file
            with tempfile.NamedTemporaryFile(suffix=".zip", dir=app.config.get(TMP_FOLDER), delete=False) as file_plot,\
                 zipfile.ZipFile(file_plot.name, "w") as myzip:
                for case, png in pngs.items():
                    myzip.writestr(case+".png", data=png)

        return Path(file_plot.name).name, Path(file_data.name).name
    except Exception:
        app.logger.exception()
        raise


@app.route("/", methods=["GET"])
@app.route("/dualCraneLift", methods=["GET", "POST"])
def dual_crane_lift() -> str:       # noqa: PLR0911
    """Main/default page for dual crane lift app.

    :returns
        GET: returns the main.html web page
    """
    app.logger.debug(f"Entering using method: {request.method}")

    return render_template("lift_cases.html")


@app.route("/get_file/<path:name>", defaults={"folder": None})
@app.route("/get_file/<path:folder>/<path:name>")
def get_file(folder: str, name: str) -> Response:
    """Provide file requested by user."""
    if not folder:
        return send_from_directory(directory=app.config.get(TMP_FOLDER), path=name)
    if folder == "sample":
        sample_folder = Path(files("dual_crane_lift_capacity")) / SAMPLE_FOLDER
        return send_from_directory(directory=sample_folder, path=name)
    return None


@app.route("/delete_file/<path:name>", methods=["DELETE"])
def delete_file(name: str) -> Response:
    """Delete specified file."""
    files = name.split(sep=",")
    for file in files:
        f = Path(app.config.get(TMP_FOLDER)) / file
        f.unlink()
    return jsonify({"resultfile": name})


@app.route("/crane_curves")
def crane_curves() -> Response:
    """Show the crane curves.

    :returns
        GET: shows the crane curves
    """
    app.logger.debug(f"Entering using method: {request.method}")
    r, c = dual_crane_lift_capacity.crane_curves.crane_curves()

    # reshape the data to suit the plotting tool
    crane_curves = {}
    for key in r:
        key_with_units = f"{key} ({r[key][0].units:~P}, {c[key][0].units:~P})"
        crane_curves[key_with_units] = []
        for ri, ci in zip(r[key], c[key]):
            crane_curves[key_with_units].append({"x": ri.magnitude, "y": ci.magnitude})

    return render_template("crane_curves.html", crane_curves=crane_curves)


@app.route("/log")
def log() -> str:
    """Show log file content."""
    return render_template("logger.html")


@app.route("/stream")
def stream() -> str:
    """Stream logging messages to user."""
    def generate() -> str:
        # with io.StringIO() as f:
        file = Path("tstlog.txt")
        with file.open() as f:
            # with ch as f:
            while True:
                s = f.read()
                if s:
                    yield f"data:{s}\n\n"
                time.sleep(1)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/gui")
def gui() -> str:
    """Launch interactive gui."""
    return render_template("single_calc.html")


@app.route("/api/calc_dual_crane_capacity", methods=["GET"])
def calc_dual_crane_capacity() -> str:
    """Calculate the dual crane capacity using the provided query parameters."""
    # get the query parameters
    args = request.args.to_dict()
    case = {"Interactive case": args}

    return dual_crane_lift_capacity.dual_crane_lift.dual_crane_lift(data=yaml.dump(case), interactive=False,
                                                                   create_plots=False)


# some preparatory work to do at start-up of the web server
with app.app_context():
    get_version_info()
    get_test_status()
    get_supported_crane_curves()

# suppress logging from matplotlib, except errors
logger_pil = logging.getLogger("PIL")
logger_plt = logging.getLogger("matplotlib")
logger_pil.setLevel(logging.ERROR)
logger_plt.setLevel(logging.ERROR)

# set scheduler for deleting old files
# NOTE: Temporarily commented out as pythonanywhere does not support this

# add a logger
if __name__ == "__main__":
    import logging.config

    def setup_logging(config_file_path: str="../logging.config.yaml", logging_level: str=logging.INFO,
                      env_key: str="LOG_CFG") -> None:
        """Prepare logging configuration.

        :param env_key:            if environment variable provided, use file path specified here
        :param config_file_path:   if environment variable is not provided, use this file math
        :param logging_level:      logging level
        """
        path = config_file_path
        value = os.getenv(env_key, None)
        if value:
            path = value
        file = Path(path)
        if file.file_exists():
            with file.open(path, "rt") as f:
                config = yaml.safe_load(f.read())
            logging.config.dictConfig(config)
        else:
            logging.basicConfig(level=logging_level)

    setup_logging()
    app.run()
