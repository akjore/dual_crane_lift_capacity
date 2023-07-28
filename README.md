# dual_crane_lift_capacity
## Install
```
python -m pip install dual_crane_lift_capacity
```

## Run
### From the command line
```
python -m dual_crane_lift_capacity.dual_crane_lift -i path/to/sample/input/file
```
### Using built-in flask application
Save the below in mwe.py, where threaded is False to avoid multiple calls to matplotlib (files otherwise occasionally get dropped when multiple files are submitted simultaneously).
```
from dual_crane_lift_capacity.webapp.dual_crane_lift_flaskapp import app
app.run(threaded=False)
```
Then run from the command line with:
```
python mwe.py
```
The application is normally available at https://localhost:5000.

There are some environmental variables that may be configured:
```
FLASK_SECRET_KEY=some_flask_secret
FLASK_PYTEST_OUTPUT_FILE=name_of_the_pytest_output_file
FLASK_TMP_FOLDER=/path/to/tmp/folder
FLASK_LOGGING_CONFIG=/path/to/logging.config.yaml
```
