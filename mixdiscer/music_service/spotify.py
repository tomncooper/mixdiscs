import logging
import re

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

    def extract_playlist_id(self, url: str) -> str:
        """
        Extract playlist ID from Spotify URL or URI.
        
        Supports formats:
        - https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
        - https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=...
        - spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
        
        Args:
            url: Spotify playlist URL or URI
            
        Returns:
            Playlist ID string
            
        Raises:
            ValueError: If URL format is invalid
        """
        # Pattern for web URL
        web_match = re.search(r'open\.spotify\.com/playlist/([a-zA-Z0-9]+)', url)
        if web_match:
            return web_match.group(1)
        
        # Pattern for URI
        uri_match = re.search(r'spotify:playlist:([a-zA-Z0-9]+)', url)
        if uri_match:
            return uri_match.group(1)
        
        raise ValueError(f"Invalid Spotify playlist URL or URI: {url}")

    def get_playlist_snapshot(self, playlist_url: str) -> str:
        """
        Get current snapshot_id for a playlist (lightweight metadata-only call).
        
        Args:
            playlist_url: Spotify playlist URL or URI
            
        Returns:
            Current snapshot_id string
            
        Raises:
            MusicServiceError: If playlist cannot be accessed
        """
        try:
            playlist_id = self.extract_playlist_id(playlist_url)
            result = self.spotify.playlist(playlist_id, fields="snapshot_id")
            return result['snapshot_id']
        except Exception as e:
            raise MusicServiceError(
                message=f"Failed to get snapshot for playlist {playlist_url}: {e}",
                service_name=self.name,
                original_exception=e
            ) from e

    def fetch_remote_playlist(self, playlist_url: str) -> MusicServicePlaylist:
        """
        Fetch all tracks from a remote Spotify playlist.
        
        Handles pagination automatically for playlists >100 tracks.
        
        Args:
            playlist_url: Spotify playlist URL or URI
            
        Returns:
            MusicServicePlaylist with tracks and metadata
            
        Raises:
            MusicServiceError: If playlist cannot be fetched
        """
        try:
            playlist_id = self.extract_playlist_id(playlist_url)
            
            # Get playlist metadata
            playlist_meta = self.spotify.playlist(playlist_id, fields="name,snapshot_id,tracks.total")
            LOG.info("Fetching remote playlist: %s (%d tracks)", 
                     playlist_meta['name'], playlist_meta['tracks']['total'])
            
            # Fetch tracks with pagination
            tracks = []
            offset = 0
            limit = 100
            
            while True:
                results = self.spotify.playlist_items(
                    playlist_id,
                    fields="items(track(id,name,artists,album,duration_ms,external_urls,uri)),next",
                    limit=limit,
                    offset=offset,
                    additional_types=('track',)
                )
                
                for item in results['items']:
                    track_data = item.get('track')
                    if not track_data or not track_data.get('id'):
                        # Skip episodes or unavailable tracks
                        tracks.append(None)
                        continue
                    
                    # Convert to SpotifyTrack
                    spotify_track = SpotifyTrack(
                        artist=track_data['artists'][0]['name'] if track_data.get('artists') else 'Unknown',
                        title=track_data['name'],
                        album=track_data['album']['name'] if track_data.get('album') else 'Unknown',
                        duration=timedelta(milliseconds=track_data['duration_ms']),
                        link=track_data['external_urls']['spotify'],
                        uri=track_data['uri'],
                        track_id=track_data['id']
                    )
                    tracks.append(spotify_track)
                
                # Check if more pages
                if results.get('next'):
                    offset += limit
                    LOG.debug("Fetching next page (offset: %d)", offset)
                else:
                    break
            
            total_duration = calculate_total_duration(tracks)
            
            LOG.info("Fetched %d tracks from remote playlist (total duration: %s)", 
                     len(tracks), total_duration)
            
            return MusicServicePlaylist(
                service_name=self.name,
                tracks=tracks,
                total_duration=total_duration
            )
            
        except Exception as e:
            raise MusicServiceError(
                message=f"Failed to fetch remote playlist {playlist_url}: {e}",
                service_name=self.name,
                original_exception=e
            ) from e

    def process_user_playlist(self, playlist) -> MusicServicePlaylist:
        """ Process a user playlist and return a MusicServicePlaylist """
        
        # Check if remote playlist
        if playlist.remote_playlist:
            LOG.info("Processing remote playlist: %s", playlist.title)
            return self.fetch_remote_playlist(playlist.remote_playlist)

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
        # Check if remote playlist
        if playlist.remote_playlist:
            LOG.info("Processing remote playlist: %s (incremental mode)", playlist.title)
            return self.fetch_remote_playlist(playlist.remote_playlist)
        
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
