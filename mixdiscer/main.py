import logging

from datetime import timedelta
from pathlib import Path
from typing import Optional

from mixdiscer.configuration import (
    load_config,
    MIXDISC_DIRECTORY_CONFIG,
    PLAYLIST_DURATION_THRESHOLD_CONFIG,
    TEMPLATE_DIR_CONFIG,
    OUTPUT_DIR_CONFIG,
)
from mixdiscer.playlists import get_playlists
from mixdiscer.music_service import (
    Track,
    MusicService,
    MusicServicePlaylist,
    ProcessedPlaylist,
)
from mixdiscer.music_service.spotify import SpotifyMusicService
from mixdiscer.output.render import render_output

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
    playlist_duration_threshold = timedelta(
        minutes=config.get(PLAYLIST_DURATION_THRESHOLD_CONFIG)
    )
    template_dir = Path(config.get(TEMPLATE_DIR_CONFIG))
    output_dir = Path(config.get(OUTPUT_DIR_CONFIG))

    spotify_music_service: MusicService = SpotifyMusicService()

    output: list[ProcessedPlaylist] = []
    over_duration_playlists: list[ProcessedPlaylist] = []

    for playlist in get_playlists(mixdisc_directory):

        processed_playlist = ProcessedPlaylist(
            user_playlist=playlist,
            music_service_playlists=[]
        )

        spotify_playlist: MusicServicePlaylist = spotify_music_service.process_user_playlist(playlist)

        processed_playlist.music_service_playlists.append(spotify_playlist)

        if spotify_playlist.total_duration > playlist_duration_threshold:
            LOG.warning(
                "Playlist %s by %s is above the duration threshold of %s by %s",
                playlist.title,
                playlist.user,
                playlist_duration_threshold,
                (spotify_playlist.total_duration - playlist_duration_threshold),
            )
            over_duration_playlists.append(processed_playlist)
        else:
            LOG.info(
                "Processed playlist %s by %s (total duration: %s)",
                playlist.title,
                playlist.user,
                spotify_playlist.total_duration
            )
            output.append(processed_playlist)

    LOG.info(
        "Mixdiscer processing complete. Processed %d playlists.",
        len(output) + len(over_duration_playlists)
    )
    if over_duration_playlists:
        LOG.warning(
            "There were %d playlists over the duration threshold.",
            len(over_duration_playlists)
        )

    render_output(output, output_dir, template_dir)
