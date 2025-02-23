import logging

from datetime import timedelta
from typing import Optional

from mixdiscer.configuration import load_config, MIXDISC_DIRECTORY_CONFIG
from mixdiscer.playlists import get_playlists
from mixdiscer.music_service import MusicService, Track
from mixdiscer.music_service.spotify import SpotifyMusicService

LOG = logging.getLogger(__name__)


def calculate_duration(tracks: list[Optional[Track]]) -> timedelta:

    total_duration = timedelta()

    for track in tracks:
        if track is None:
            continue

        total_duration += track.duration

    return total_duration


def run(config_path: str):
    """ Main function for Mixdiscer """

    LOG.info("Running Mixdiscer with config %s", config_path)

    config = load_config(config_path)
    mixdisc_directory = config.get(MIXDISC_DIRECTORY_CONFIG)

    spotify_music_service: MusicService = SpotifyMusicService()

    output = []

    for playlist in get_playlists(mixdisc_directory):
        spotify_tracks = spotify_music_service.process_playlist(playlist)

        duration = calculate_duration(spotify_tracks)

        LOG.info("Playlist %s by %s has a total duration of %s", playlist.title, playlist.user, duration)
