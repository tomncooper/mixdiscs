import logging

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from mixdiscer.music_service import MusicService, Track

LOG = logging.getLogger(__name__)


@dataclass
class SpotifyTrack(Track):
    """ Dataclass representing a Spotify Track and its metadata """

    uri: str
    url: str
    track_id: str


class SpotifyMusicService(MusicService):
    """ Class representing a Spotify music service """

    def __init__(self):
        self.auth_manager = SpotifyClientCredentials()
        self.spotify = spotipy.Spotify(auth_manager=self.auth_manager)

    def find_track(self, artist: str, track: str) -> Optional[SpotifyTrack]:
        LOG.debug("Searching Spotify for track %s by %s", track, artist)

        results = self.spotify.search(q=f'artist:{artist} track:{track}', type='track')

        if results['tracks']['total'] == 0:
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
            uri=first_track['uri'],
            url=first_track['external_urls']['spotify'],
            track_id=first_track['id']
        )

    def process_playlist(self, playlist) -> list[Optional[Track]]:
        """ Returns a list of Track objects for the given playlist """
        return [self.find_track(artist, track) for artist, track in playlist.playlist]
