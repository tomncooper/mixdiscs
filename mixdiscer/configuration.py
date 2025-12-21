import logging
from pathlib import Path

import yaml

LOG = logging.getLogger(__name__)

MIXDISC_DIRECTORY_CONFIG = "mixdisc_directory"
PLAYLIST_DURATION_THRESHOLD_CONFIG = "playlist_duration_threshold_mins"
TEMPLATE_DIR_CONFIG = "template_directory"
OUTPUT_DIR_CONFIG = "output_directory"
CACHE_FILE_CONFIG = "cache_file"
TRACK_CACHE_FILE_CONFIG = "track_cache_file"


def load_config(filepath: str):

    config_path = Path(filepath)
    if not config_path.exists():
        LOG.error("Config file %s does not exist", config_path)
        raise FileNotFoundError(f"Config file {config_path} does not exist")

    with open(config_path, 'r', encoding="utf8") as config_file:
        config_data = yaml.load(config_file, Loader=yaml.FullLoader)

    return config_data