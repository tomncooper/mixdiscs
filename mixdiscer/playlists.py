""" Module for loading playlists from YAML files """
import logging

from pathlib import Path
from dataclasses import dataclass
from typing import List, Generator, Tuple

import yaml

LOG = logging.getLogger(__name__)


@dataclass
class Playlist:
    """ Dataclass representing a Playlist and its metadata"""
    user: str
    title: str
    description: str
    genre: str
    tracks: List[Tuple[str, str]]


def get_playlists(directory: str) -> Generator[Playlist]:
    """ Generator that yields all the playlists in a directory """

    LOG.debug("Loading playlists from directory: %s", directory)

    path = Path(directory)

    if not path.exists():
        LOG.error("Directory %s does not exist", directory)
        raise FileNotFoundError(f"Directory {directory} does not exist")

    for playlist_filepath in path.glob('*.yaml'):
        try:
            yield load_playlist(playlist_filepath)
        except (yaml.YAMLError, IOError) as e:
            LOG.error("Error loading playlist %s: %s", playlist_filepath, e)
            continue


def load_playlist(filepath: Path) -> Playlist:
    """ Load a Playlist from a Playlist YAML file """

    LOG.debug("Loading playlist from %s", filepath)

    with open(filepath, 'r', encoding="utf8") as playlist_file:
        data = yaml.load(playlist_file, Loader=yaml.FullLoader)

    return Playlist(
        user=data['user'],
        title=data['title'],
        description=data['description'],
        genre=data['genre'],
        tracks=[get_artist_album_from_entry(entry) for entry in data['playlist']]
    )


def get_artist_album_from_entry(entry: str) -> tuple[str, str]:
    """ Extract the artist and album from a playlist entry """
    artist, album = entry.split(' - ')
    return artist, album
