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

import dual_crane_lift_capacity.dual_crane_lift

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
    supported_crane_curves = dual_crane_lift_capacity.dual_crane_lift.crane_curve_ids()
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
#        figures = dual_crane_lift_capacity.dual_crane_lift.dual_crane_lift(data=filecontent, interactive=False)
        data_cls = dual_crane_lift_capacity.dual_crane_lift.dual_crane_lift(data=filecontent, interactive=False)
        app.logger.debug(f"Returned with {len(data_cls.figures)} figure(s).")

        # grab the data from the plots
        data = []
        for _k, v in data_cls.figures.items():
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
                file_plot.write(list(pngs.values())[0])
                file_plot.flush()
        else:
            # multiple files -> bundle in a zip file
            file_plot = tempfile.NamedTemporaryFile(suffix=".zip", dir=app.config.get(TMP_FOLDER), delete=False)
            with zipfile.ZipFile(file_plot.name, "w") as myzip:
                for case, png in pngs.items():
                    myzip.writestr(case+".png", data=png)
            file_plot.close()
        return Path(file_plot.name).name, Path(file_data.name).name
    except Exception:
        app.logger.exception()
        raise


@app.route("/", methods=["GET", "POST"])
@app.route("/dualCraneLift", methods=["GET", "POST"])
def dual_crane_lift() -> str:
    """Main/default page for dual crane lift app.

    :returns
        GET: returns the main.html web page
        POST: processes input files and returns the name of the zip files
    """
    app.logger.debug(f"Entering using method: {request.method}")
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            app.logger.error(f"'file' not found in request.files: {request.files}")
            return "No file provided", 400

        # check a filename was also provided
        file = request.files["file"]
        if file.filename == "":
            app.logger.error("'file' does not have a file name.")
            return "No filename provided", 400

        # check filename extension is as expected
        file_ext = Path(file.filename).suffix

        if file_ext not in app.config.get("UPLOAD_EXTENSIONS"):
            app.logger.error(f"File does not have a valid extension: {file_ext}")
            return "Invalid file type", 400

        # all well - create plots and return to use
        app.logger.debug(f"Input file provided: {file.filename}")
        try:
            retfiles = prepare_dual_crane_lift_plots(filecontent=file.read())
        except KeyError as ex:
            return f"Missing key {ex}", 400
        except ValueError as ex:
            return str(ex), 400
        except Exception as ex:
            return repr(ex), 400
        app.logger.debug(f"Result files created: {retfiles}")

        results = {"datetime": datetime.datetime.now().replace(microsecond=0).isoformat(sep=" "),
                   "filename": file.filename,
                   "resultfiles": retfiles}
        app.logger.debug(f"Returning: {results}")
        return jsonify(results)

    return render_template("main.html")


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
    for key, _val in r.items():
        key_with_units = f"{key} ({r[key][0].units:~P}, {c[key][0].units:~P})"
        crane_curves[key_with_units] = list()
        for ri, ci in zip(r[key], c[key]):
            crane_curves[key_with_units].append({"x": ri.magnitude, "y": ci.magnitude})

    return render_template("crane_curves.html", crane_curves=crane_curves)


@app.route("/logger")
def logger() -> str:
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

    obj = dual_crane_lift_capacity.dual_crane_lift.dual_crane_lift(data=yaml.dump(case), interactive=False, 
                                                                   create_plots=False)
#    obj = dual_crane_lift_capacity.dual_crane_lift.dual_crane_lift(data=yaml.dump(case), interactive=False, 
#                                                                   create_plots=True)

    print("#############################")
    print(obj)
#    import matplotlib.pyplot as plt, mpld3
#    plt.plot([3,1,4,1,5], 'ks-', mec='w', mew=5, ms=20)
#    mpld3.show()
#    print(obj.figures)
#    figure = next(iter(obj.figures.values()))
#    a = mpld3.fig_to_html(figure)
#    print(a)
    print("+++++++++++++++++")
#    print(obj.to_json())
    print(obj.lift_capacity_curve_x.to_tuple())
    tmp = obj.lift_capacity_curve_x.to_tuple()
#    print(obj.lift_capacity_curve_x.tolist())
    tmp2 = (tmp[0].tolist(), tmp[1])
    tmp3 = obj.lift_capacity_curve_y.to_tuple()
    tmp4 = (tmp3[0].tolist(), tmp3[1])
    print(obj.lift_capacity_curve_y.tolist())
#    print(dir(obj.lift_capacity_curve_x))
    print()
    print(str(obj.lift_capacity_curve_x))
    print("#############################")
    # so:
    #   want the data returned as well, not just a plot
    #   some sort of json format perhaps?
#    img = make_png(next(iter(figure.values())))
#    import base64
#    return base64.b64encode(img).decode("utf-8"), 200
    print()
    a = obj.lift_capacity_curve_y.to_tuple()
    import pickle
#    serialized = pickle.dump(a, -1)
    serialized = pickle.dumps(a, -1)
    print(serialized)




    from flask import jsonify

#   for the below to work, the contents of the class needs to be serializable
#   this is done by converting the Quantity objects to str
#   ret = str(quantity)
#   this should be part of the dataclass somehow
#   temporarily create a return object
#   confirmed that client picks up this response
    obj2 = {
        "some response": 42,
        "other response": str(obj.lift_capacity_curve_x),
        "x": tmp2,
        "y": tmp4
    } 

    return jsonify(obj2)


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
