import logging
import logging.config
import os

import pint
import yaml
from dotenv import load_dotenv

load_dotenv()

ureg = pint.UnitRegistry()
Q = ureg.Quantity


# logging
def setup_logging(config_file_path='logging.config.yaml', logging_level=logging.INFO, env_key='LOG_CFG'):
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
