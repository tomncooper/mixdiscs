import logging

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from mixdiscer.music_service import MusicService, Track
from mixdiscer.music_service.music_service import (
    MusicServicePlaylist,
    calculate_total_duration
)

LOG = logging.getLogger(__name__)


@dataclass
class SpotifyTrack(Track):
    """ Dataclass representing a Spotify Track and its metadata """
    uri: str
    track_id: str


class SpotifyMusicService(MusicService):
    """ Class representing a Spotify music service """

    def __init__(self):
        self.auth_manager = SpotifyClientCredentials()
        self.spotify = spotipy.Spotify(auth_manager=self.auth_manager)

    @property
    def name(self) -> str:
        """ Returns the name of the music service """
        return "spotify"

    def find_track(self, artist: str, track: str) -> Optional[SpotifyTrack]:
        LOG.debug("Searching Spotify for track %s by %s", track, artist)

        results = self.spotify.search(q=f'artist:{artist} track:{track}', type='track')

        if not results or results['tracks']['total'] == 0:
            LOG.warning("No tracks found for %s - %s", artist, track)
            return None        

        LOG.debug("Found %d tracks for %s - %s", results['tracks']['total'], artist, track)

        # In the absence of a better option just pick the first track
        first_track = results['tracks']['items'][0]

        return SpotifyTrack(
            artist=first_track['artists'][0]['name'],
            title=first_track['name'],
            album=first_track['album']['name'],
            duration=timedelta(milliseconds=first_track['duration_ms']),
            link=first_track['external_urls']['spotify'],
            uri=first_track['uri'],
            track_id=first_track['id'],
        )

    def process_user_playlist(self, playlist) -> MusicServicePlaylist:
        """ Process a user playlist and return a MusicServicePlaylist """
        tracks = [self.find_track(artist, track) for artist, track in playlist.playlist]
        total_duration = calculate_total_duration(tracks)

        return MusicServicePlaylist(
            service_name=self.name,
            tracks=tracks,
            total_duration=total_duration
        )
