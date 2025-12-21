""" Unit tests for configuration.py """

import pytest
from pathlib import Path
import yaml

from mixdiscer.configuration import (
    load_config,
    MIXDISC_DIRECTORY_CONFIG,
    PLAYLIST_DURATION_THRESHOLD_CONFIG,
    TEMPLATE_DIR_CONFIG,
    OUTPUT_DIR_CONFIG,
    CACHE_FILE_CONFIG,
    TRACK_CACHE_FILE_CONFIG,
)


def test_load_config_valid_file(test_config):
    """Test loading a valid configuration file"""
    config = load_config(str(test_config))
    
    assert config is not None
    assert isinstance(config, dict)
    assert MIXDISC_DIRECTORY_CONFIG in config
    assert PLAYLIST_DURATION_THRESHOLD_CONFIG in config
    assert TEMPLATE_DIR_CONFIG in config
    assert OUTPUT_DIR_CONFIG in config


def test_load_config_returns_expected_values(test_config):
    """Test that loaded config contains expected values"""
    config = load_config(str(test_config))
    
    assert config[PLAYLIST_DURATION_THRESHOLD_CONFIG] == 80
    assert Path(config[MIXDISC_DIRECTORY_CONFIG]).name == "mixdiscs"
    assert Path(config[TEMPLATE_DIR_CONFIG]).name == "templates"
    assert Path(config[OUTPUT_DIR_CONFIG]).name == "output"


def test_load_config_missing_file():
    """Test that loading a non-existent config file raises FileNotFoundError"""
    with pytest.raises(FileNotFoundError, match="does not exist"):
        load_config("/nonexistent/config.yaml")


def test_load_config_invalid_yaml(tmp_path):
    """Test handling of malformed YAML"""
    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text("{ invalid yaml content: [")
    
    with pytest.raises(yaml.YAMLError):
        load_config(str(invalid_config))


def test_load_config_empty_file(tmp_path):
    """Test loading an empty config file"""
    empty_config = tmp_path / "empty.yaml"
    empty_config.write_text("")
    
    config = load_config(str(empty_config))
    # Empty YAML should return None or empty dict
    assert config is None or config == {}


def test_load_config_with_cache_paths(tmp_path):
    """Test that config with cache paths loads correctly"""
    config_path = tmp_path / "config_with_cache.yaml"
    cache_path = tmp_path / ".cache" / "playlists.json"
    track_cache_path = tmp_path / ".cache" / "tracks.json"
    
    config_content = f"""
mixdisc_directory: {tmp_path / "mixdiscs"}
playlist_duration_threshold_mins: 80
template_directory: {tmp_path / "templates"}
output_directory: {tmp_path / "output"}
cache_file: {cache_path}
track_cache_file: {track_cache_path}
"""
    config_path.write_text(config_content)
    
    config = load_config(str(config_path))
    
    assert CACHE_FILE_CONFIG in config
    assert TRACK_CACHE_FILE_CONFIG in config
    assert config[CACHE_FILE_CONFIG] == str(cache_path)
    assert config[TRACK_CACHE_FILE_CONFIG] == str(track_cache_path)
