import logging
from pathlib import Path

import yaml

LOG = logging.getLogger(__name__)

MIXDISC_DIRECTORY_CONFIG = "mixdisc_directory"


def load_config(filepath: str):

    config_path = Path(filepath)
    if not config_path.exists():
        LOG.error("Config file %s does not exist", config_path)
        raise FileNotFoundError(f"Config file {config_path} does not exist")

    with open(config_path, 'r', encoding="utf8") as config_file:
        config_data = yaml.load(config_file, Loader=yaml.FullLoader)

    return config_data