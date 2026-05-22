"""Web application front-end for dual crane lift."""
import logging
import os
from pathlib import Path

import yaml
from flask import Flask, render_template, request

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_prefixed_env()      # Loads all FLASK_xx variables in environment into app.config
app.secret_key = app.config.get("SECRET_KEY", "default_key")


@app.route("/", methods=["GET"])
@app.route("/dualCraneLift", methods=["GET", "POST"])
def dual_crane_lift() -> str:       # noqa: PLR0911
    """Main/default page for dual crane lift app.

    :returns
        GET: returns the main.html web page
    """
    app.logger.debug(f"Entering using method: {request.method}")

    return render_template("lift_cases.html")


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
