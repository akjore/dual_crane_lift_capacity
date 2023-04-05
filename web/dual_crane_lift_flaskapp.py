import datetime
import logging
import logging.config
import os
import tempfile
import zipfile
from io import BytesIO

import git
import pytest
import yaml
from flask import Flask, jsonify, render_template, request, send_from_directory
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

import dualCraneLiftCapacity.dual_crane_lift

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
PYTEST_OUTPUT_FILE = os.environ.get('PYTEST_OUTPUT_FILE')

app.jinja_env.globals['GIT_HASH'] = None
app.jinja_env.globals['GIT_COMMIT_DATE'] = None
app.jinja_env.globals['TEST_RESULT_FILENAME'] = None
app.jinja_env.globals['TEST_RETCODE'] = None

app.config['UPLOAD_EXTENSIONS'] = ".yaml, .yml"
app.config['TMP_DIRECTORY'] = "tmp"


def setup_logging(config_file_path='../logging.config.yaml', logging_level=logging.INFO, env_key='LOG_CFG'):
    '''
    Setup logging configuration

    Args:
        env_key:            if environment variable provided, use file path specified here
        config_file_path:   if environment variable is not provided, use this file math
        logging_level:      logging level
    '''
    path = config_file_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=logging_level)


@app.before_first_request
def get_git_commit_info():
    '''
    Get current git hash code and commit date, and store these in jinja_env.globals
    '''
    repo = git.Repo(search_parent_directories=True)
    app.jinja_env.globals['GIT_HASH'] = repo.git.rev_parse(repo.head, short=True)
    app.jinja_env.globals['GIT_COMMIT_DATE'] = datetime.datetime.fromtimestamp(repo.head.object.committed_date).isoformat(sep=" ")
    app.logger.debug(f"Git hash: {app.jinja_env.globals['GIT_HASH']}")
    app.logger.debug(f"Git commit date: {app.jinja_env.globals['GIT_COMMIT_DATE']}")


@app.before_first_request
def get_test_status():
    '''
    Runs pytest. The return code and the location of the the test report are stored in jinja_env.globals
    '''
    filename = os.path.join(app.root_path, "tmp", PYTEST_OUTPUT_FILE)
    app.jinja_env.globals['TEST_RESULT_FILENAME'] = PYTEST_OUTPUT_FILE
    app.jinja_env.globals['TEST_RETCODE'] = pytest.main(["../tests", "--self-contained-html", f"--html={filename}"])
    app.logger.debug(f"Pytest result file: {app.jinja_env.globals['TEST_RESULT_FILENAME']}")
    app.logger.debug(f"Pytest return code: {app.jinja_env.globals['TEST_RETCODE']}")


# methods for dual crane lift
def make_png(figure):
    '''
    Takes a pyplot figure and writes it to a png in memory.

    Args:
        figure: pyplot.figure object

    Returns:
        figure as a png
    '''
    canvas = FigureCanvas(figure)
    png_output = BytesIO()
    canvas.print_png(png_output)
    png_output.seek(0)
    return png_output.getvalue()


def prepare_dual_crane_lift_plots(filecontent):
    '''
    Takes an input file, creates figures, converts to pngs, and writes to disk.
    If a single case is provided, the .png filename is returned.
    If multiple cases are provided, a .zip filename is returned.

    Args:
        filecontent: a yaml inputfile

    Returns:
        a filename, either a png or zip
    '''
    try:
        figures = dualCraneLiftCapacity.dual_crane_lift.main(data=filecontent, interactive=False)
        app.logger.debug(f"Returned with {len(figures)} figure(s).")

        pngs = {k: make_png(v) for k, v in figures.items()}

        if len(pngs) == 1:
            # as only one file, write the figure to file as png
            with tempfile.NamedTemporaryFile(suffix=".png", dir=app.config['TMP_DIRECTORY'], delete=False) as file:
                file.write(list(pngs.values())[0])
                file.flush()
        else:
            # multiple files -> bundle in a zip file
            file = tempfile.NamedTemporaryFile(suffix=".zip", dir=app.config['TMP_DIRECTORY'], delete=False)
            with zipfile.ZipFile(file.name, 'w') as myzip:
                for case, png in pngs.items():
                    myzip.writestr(case+'.png', data=png)
            file.close()
        return os.path.basename(file.name)
    except Exception as e:
        app.logger.error(repr(e))
        return None


@app.route("/", methods=['GET', 'POST'])
@app.route("/dualCraneLift", methods=['GET', 'POST'])
def dual_crane_lift():
    '''
    Main/default page for dual crane lift app

    Returns:
        GET: returns the main.html web page
        POST: processes input files and returns the name of the zip files
    '''

    app.logger.debug(f"Entering using method: {request.method}")
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            app.logger.error(f"'file' not found in request.files: {request.files}")
            return "No file provided", 400

        # check a filename was also provided
        file = request.files['file']
        if file.filename == '':
            app.logger.error("'file' does not have a file name.")
            return "No filename provided", 400

        # check filename extension is as expected
        file_ext = os.path.splitext(file.filename)[1]
        if file_ext not in app.config['UPLOAD_EXTENSIONS']:
            app.logger.error(f"File does not have a valid extension: {file_ext}")
            return "Invalid file type", 400

        # check filename is a valid input file
        # TODO

        # all well - create plots and return to use
        app.logger.debug(f"Input file provided: {file.filename}")
        retfile = prepare_dual_crane_lift_plots(filecontent=file.read())
        if not retfile:
            return "Error processing input file", 400
        app.logger.debug(f"Result file created: {retfile}")

        results = {'datetime': datetime.datetime.now().replace(microsecond=0).isoformat(sep=" "),
                   'filename': file.filename,
                   'resultfile': retfile}
        app.logger.debug(f"Returning: {results}")
        return jsonify(results)

    return render_template('main.html')


@app.route("/scratchDir/<path:name>")
def get_file(name):
    return send_from_directory(directory=app.config['TMP_DIRECTORY'], path=name)


@app.route("/test")
def test():
    import main

    data = """M10 fixed:
    crane_curve_a: S7000.main.fixed_1.5
    crane_curve_b: S7000.main.fixed_1.5
    crane_radius_a: 50.0 m
    crane_radius_b: 50.0 m
    rigging_weight_a: 495 t
    rigging_weight_b: 380 t
    weight_uncertainty_factor: 1.03
    cog_uncertainty_factor: 1.02
    tilt_factor: 1.02
    lift_point_a:
     - (43.73+3.03) m
     - (43.73-3.03) m
    lift_point_b: [82. m]
    weight: 10295 t
    cog: 61.668 m"""

    figure_json = main.main(data=data, interactive=False)


#    figjson = json.dumps(mpld3.fig_to_dict(fig))
    return render_template('test.html', figjson=figure_json)


setup_logging()

# suppress logging from matplotlib, except errors
logger_pil = logging.getLogger('PIL')
logger_plt = logging.getLogger('matplotlib')
logger_pil.setLevel(logging.ERROR)
logger_plt.setLevel(logging.ERROR)

if __name__ == "__main__":
    app.run()
