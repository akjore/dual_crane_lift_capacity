import datetime
import logging
import logging.config
import os
import tempfile
import time
import zipfile
from io import BytesIO

import pytest
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from flask import (Flask, Response, jsonify, render_template, request,
                   send_from_directory)
from importlib.resources import files

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

import dual_crane_lift_capacity.dual_crane_lift


logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_prefixed_env()      # Loads all FLASK_xx variables in environment into app.config
app.secret_key = app.config.get('SECRET_KEY', 'default_key')

app.jinja_env.globals['GIT_HASH'] = None
app.jinja_env.globals['GIT_COMMIT_DATE'] = None
app.jinja_env.globals['TEST_RESULT_FILENAME'] = None
app.jinja_env.globals['TEST_RETCODE'] = None

app.config['UPLOAD_EXTENSIONS'] = ".yaml, .yml"
app.config['MAX_TMP_FILE_AGE'] = 12     # hours

TMP_FOLDER = 'TMP_FOLDER'
TEST_FOLDER = '../../tests'         # relative to package folder
SAMPLE_FOLDER = 'sample'            # relative to package folder


def get_version_info():
    '''
    Get current version and store in jinja_env.globals
    '''
    app.jinja_env.globals['VERSION'] = dual_crane_lift_capacity.__version__
    app.logger.debug(f"Version: {app.jinja_env.globals['VERSION']}")


def get_test_status():
    '''
    Runs pytest. The return code and the location of the the test report are stored in jinja_env.globals
    '''

    filename = app.config.get('PYTEST_OUTPUT_FILE')
    if not filename:
        filename = 'pytest.html'
        app.logger.warning(f'Config variable PYTEST_OUTPUT_FILE not set - writing test results to {filename}')

    if app.config.get(TMP_FOLDER):
        filename_with_path = os.path.join(app.config.get(TMP_FOLDER), filename)
    else:
        filename_with_path = filename
        app.logger.warning(f'Config variable TMP_FOLDER not set - writing test results to {filename_with_path}')

    test_folder = os.path.join(files('dual_crane_lift_capacity'), TEST_FOLDER)

    app.jinja_env.globals['TEST_RESULT_FILENAME'] = filename
    app.jinja_env.globals['TEST_RETCODE'] = pytest.main([test_folder, "--self-contained-html", f"--html={filename_with_path}"])
    app.logger.debug(f"Pytest result file: {app.jinja_env.globals['TEST_RESULT_FILENAME']}")
    app.logger.debug(f"Pytest return code: {app.jinja_env.globals['TEST_RETCODE']}")


def get_supported_crane_curves():
    '''
    Gets a list of the supported crane curves and stores in jinja_env.globals
    '''

    supported_crane_curves = dual_crane_lift_capacity.dual_crane_lift.crane_curve_ids()
    app.jinja_env.globals['SUPPORTED_CRANE_CURVE_IDS'] = supported_crane_curves
    app.logger.debug(f"Supported crane curves: {app.jinja_env.globals['SUPPORTED_CRANE_CURVE_IDS']}")


def clear_tmp_files():
    '''
    Goes through the files in path 'path', and deletes any older than 'max_age' hours
    '''
    path = app.config.get('TMP_FOLDER')
    max_age = app.config.get('MAX_TMP_FILE_AGE')
    now = time.time()
    for filename in os.listdir(path):
        if os.path.getmtime(os.path.join(path, filename)) < now - max_age * 60 * 60:
            if os.path.isfile(os.path.join(path, filename)):
                os.remove(os.path.join(path, filename))


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

    Raises:
        Exception: some error while processing the provided filecontent
    '''
    try:
        figures = dual_crane_lift_capacity.dual_crane_lift.dual_crane_lift(data=filecontent, interactive=False)
        app.logger.debug(f"Returned with {len(figures)} figure(s).")

        pngs = {k: make_png(v) for k, v in figures.items()}

        if len(pngs) == 1:
            # as only one file, write the figure to file as png
            with tempfile.NamedTemporaryFile(suffix=".png", dir=app.config[TMP_FOLDER], delete=False) as file:
                file.write(list(pngs.values())[0])
                file.flush()
        else:
            # multiple files -> bundle in a zip file
            file = tempfile.NamedTemporaryFile(suffix=".zip", dir=app.config[TMP_FOLDER], delete=False)
            with zipfile.ZipFile(file.name, 'w') as myzip:
                for case, png in pngs.items():
                    myzip.writestr(case+'.png', data=png)
            file.close()
        return os.path.basename(file.name)
    except Exception as e:
        app.logger.error(repr(e))
        raise e


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
            return "Invali  d file type", 400

        # all well - create plots and return to use
        app.logger.debug(f"Input file provided: {file.filename}")
        try:
            retfile = prepare_dual_crane_lift_plots(filecontent=file.read())
        except KeyError as ex:
            return f'Missing key {ex}', 400
        except ValueError as ex:
            return str(ex), 400
        except Exception as ex:
            return repr(ex), 400
        app.logger.debug(f"Result file created: {retfile}")

        results = {'datetime': datetime.datetime.now().replace(microsecond=0).isoformat(sep=" "),
                   'filename': file.filename,
                   'resultfile': retfile}
        app.logger.debug(f"Returning: {results}")
        return jsonify(results)

    return render_template('main.html')


@app.route("/get_file/<path:name>", defaults={'folder': None})
@app.route("/get_file/<path:folder>/<path:name>")
def get_file(folder, name):
    if not folder:
        return send_from_directory(directory=app.config[TMP_FOLDER], path=name)
    elif folder == "sample":
        sample_folder = os.path.join(files('dual_crane_lift_capacity'), SAMPLE_FOLDER)
        return send_from_directory(directory=sample_folder, path=name)


@app.route("/delete_file/<path:name>", methods=['DELETE'])
def delete_file(name):
    os.remove(os.path.join(app.config[TMP_FOLDER], name))
    return jsonify({'resultfile': name})


@app.route('/logger')
def logger():
    return render_template('logger.html')


@app.route('/stream')
def stream():
    def generate():
        import io
        with io.StringIO() as f:
#        with open('job.log') as f:
            while True:
                s = f.read()
                if s:
                    yield f"data:{s}\n\n"
                time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')


with app.app_context():
#    get_git_commit_info()
    get_version_info()
    get_test_status()
    get_supported_crane_curves()

# suppress logging from matplotlib, except errors
logger_pil = logging.getLogger('PIL')
logger_plt = logging.getLogger('matplotlib')
logger_pil.setLevel(logging.ERROR)
logger_plt.setLevel(logging.ERROR)

# set scheduler for deleting old files
# NOTE: Temporarily commented out as pythonanywhere does not support this
# sched = BackgroundScheduler(daemon=True)
# sched.add_job(clear_tmp_files, 'interval', minutes=60)
# sched.start()

if __name__ == "__main__":
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

    setup_logging
    app.run()
