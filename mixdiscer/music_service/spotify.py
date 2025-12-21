import logging

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from mixdiscer.music_service import MusicService, Track
from mixdiscer.music_service.music_service import (
    MusicServiceError,
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
        # Disable token caching for client credentials flow
        # (tokens are short-lived and we fetch a new one each session)
        self.auth_manager = SpotifyClientCredentials(cache_handler=None)
        self.spotify = spotipy.Spotify(auth_manager=self.auth_manager)

    @property
    def name(self) -> str:
        """ Returns the name of the music service """
        return "spotify"

    def find_track(self, artist: str, track: str, album: Optional[str] = None) -> Optional[SpotifyTrack]:
        """
        Find track on Spotify with optional album specification.
        
        Args:
            artist: Artist name
            track: Track title
            album: Optional album name for specific version
            
        Returns:
            SpotifyTrack if found, None otherwise
        """
        # Try with album if specified
        if album:
            LOG.debug("Searching Spotify for %s - %s (album: %s)", artist, track, album)
            query = f'artist:{artist} track:{track} album:{album}'
            results = self.spotify.search(q=query, type='track')
            
            if results and results['tracks']['total'] > 0:
                first_track = results['tracks']['items'][0]
                LOG.debug("Found track with album: %s", first_track['name'])
                return SpotifyTrack(
                    artist=first_track['artists'][0]['name'],
                    title=first_track['name'],
                    album=first_track['album']['name'],
                    duration=timedelta(milliseconds=first_track['duration_ms']),
                    link=first_track['external_urls']['spotify'],
                    uri=first_track['uri'],
                    track_id=first_track['id'],
                )
            
            # Album not found - log and fall back
            LOG.warning(
                "Album '%s' not found for %s - %s on Spotify, falling back to default",
                album, artist, track
            )
        
        # No album specified or album not found - use default search
        LOG.debug("Searching Spotify for %s - %s (default)", artist, track)
        query = f'artist:{artist} track:{track}'
        results = self.spotify.search(q=query, type='track')

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

        tracks = []
        total_duration = timedelta()

        for artist, track, album in playlist.tracks:
            spotify_track = None
            try:
                spotify_track = self.find_track(artist, track, album)
                tracks.append(spotify_track)
            except Exception as e:
                msg = f"Error finding track {artist} - {track}: {e}"
                LOG.error(msg)
                raise MusicServiceError(
                    message=msg,
                    service_name=self.name,
                    original_exception=e
                ) from e

            if spotify_track is not None:
                total_duration += spotify_track.duration

        return MusicServicePlaylist(
            service_name=self.name,
            tracks=tracks,
            total_duration=total_duration
        )

    def process_user_playlist_incremental(
        self,
        playlist,
        track_cache_data: dict
    ) -> MusicServicePlaylist:
        """
        Process playlist using track cache for efficiency.
        Only queries Spotify for tracks not in cache.
        
        Args:
            playlist: Playlist object to process
            track_cache_data: Track cache dictionary
            
        Returns:
            MusicServicePlaylist with tracks and duration
        """
        from mixdiscer.track_cache import (
            get_cached_track,
            update_track_cache,
            normalize_track_key
        )
        
        tracks = []
        total_duration = timedelta()
        api_calls = 0
        cache_hits = 0
        fallbacks = 0
        
        for artist, track_title, album in playlist.tracks:
            # Try cache first
            cached_track = get_cached_track(
                artist,
                track_title,
                album,
                self.name,
                track_cache_data
            )
            
            if cached_track:
                # Cache hit - use it
                tracks.append(cached_track)
                cache_hits += 1
                if cached_track is not None:
                    total_duration += cached_track.duration
                LOG.debug("Track cache hit: %s - %s%s",
                         artist, track_title,
                         f" | {album}" if album else "")
            else:
                # Cache miss - query Spotify
                LOG.debug("Track cache miss: %s - %s%s",
                         artist, track_title,
                         f" | {album}" if album else "")
                
                try:
                    spotify_track = self.find_track(artist, track_title, album)
                    tracks.append(spotify_track)
                    api_calls += 1
                    
                    # Determine if this is a fallback (album requested but different album returned)
                    if album and spotify_track:
                        returned_album = spotify_track.album.lower().strip()
                        requested_album = album.lower().strip()
                        if returned_album != requested_album:
                            fallbacks += 1
                            LOG.info("Album fallback: requested '%s', got '%s' for %s - %s",
                                   album, spotify_track.album, artist, track_title)
                    
                    # Update cache
                    is_default = (album is None)  # Mark as default if no album specified
                    update_track_cache(
                        artist,
                        track_title,
                        album,
                        self.name,
                        spotify_track,
                        track_cache_data,
                        is_default=is_default
                    )
                    
                    if spotify_track is not None:
                        total_duration += spotify_track.duration
                        
                except Exception as e:
                    msg = f"Error finding track {artist} - {track_title}: {e}"
                    LOG.error(msg)
                    raise MusicServiceError(
                        message=msg,
                        service_name=self.name,
                        original_exception=e
                    ) from e
        
        LOG.info("Track processing stats: %d cache hits, %d API calls, %d fallbacks",
                cache_hits, api_calls, fallbacks)
        
        return MusicServicePlaylist(
            service_name=self.name,
            tracks=tracks,
            total_duration=total_duration
        )
