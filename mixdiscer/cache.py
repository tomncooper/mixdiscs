""" Module for caching playlist data to avoid redundant music service API calls """

import hashlib
import json
import logging

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from mixdiscer.playlists import Playlist
from mixdiscer.music_service import MusicServicePlaylist, Track

LOG = logging.getLogger(__name__)


def get_cache_key(playlist: Playlist) -> str:
    """
    Generate cache key from user and title.
    
    Args:
        playlist: Playlist object
        
    Returns:
        Cache key in format "user/title"
    """
    return f"{playlist.user}/{playlist.title}"


def compute_playlist_hash(filepath: Path) -> str:
    """
    Compute SHA256 hash of YAML file content.
    
    Args:
        filepath: Path to playlist YAML file
        
    Returns:
        Hex digest of file content hash
    """
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_cache(cache_path: Path) -> dict:
    """
    Load cache JSON from configured path.
    
    Args:
        cache_path: Path to cache file
        
    Returns:
        Cache data dictionary
    """
    if not cache_path.exists():
        LOG.debug("Cache file not found, creating empty cache structure")
        return {
            'version': '1.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'playlists': {}
        }
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            LOG.debug("Loaded cache from %s with %d playlists", cache_path, len(cache_data.get('playlists', {})))
            return cache_data
    except (json.JSONDecodeError, IOError) as e:
        LOG.warning("Failed to load cache from %s: %s. Starting with empty cache.", cache_path, e)
        return {
            'version': '1.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'playlists': {}
        }


def save_cache(cache_data: dict, cache_path: Path) -> None:
    """
    Save cache to configured path with timestamp update.
    
    Args:
        cache_data: Cache data dictionary
        cache_path: Path to cache file
    """
    # Ensure parent directory exists
    parent_dir = cache_path.parent
    if parent_dir.exists() and not parent_dir.is_dir():
        # Parent exists but is a file - need to remove it first
        LOG.warning("Removing file %s to create directory", parent_dir)
        parent_dir.unlink()
    parent_dir.mkdir(parents=True, exist_ok=True)
    
    cache_data['last_updated'] = datetime.now(timezone.utc).isoformat()
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2)
    
    LOG.debug("Saved cache to %s", cache_path)


def is_cache_valid(playlist: Playlist, cache_entry: dict) -> bool:
    """
    Check if cached data matches current playlist content by comparing hash.
    
    Args:
        playlist: Playlist object
        cache_entry: Cache entry dictionary
        
    Returns:
        True if cache is valid, False otherwise
    """
    current_hash = compute_playlist_hash(playlist.filepath)
    cached_hash = cache_entry.get('content_hash')
    return cached_hash == current_hash


def get_cached_music_service_playlist(
    cache_key: str,
    service_name: str,
    cache_data: dict
) -> Optional[MusicServicePlaylist]:
    """
    Retrieve cached MusicServicePlaylist for specific service.
    
    Args:
        cache_key: Cache key (user/title)
        service_name: Name of music service (e.g., "spotify")
        cache_data: Cache data dictionary
        
    Returns:
        MusicServicePlaylist if cached, None otherwise
    """
    playlist_cache = cache_data['playlists'].get(cache_key)
    if not playlist_cache:
        return None
    
    service_cache = playlist_cache.get('music_services', {}).get(service_name)
    if not service_cache:
        return None
    
    # Deserialize tracks
    tracks = []
    for track_data in service_cache['tracks']:
        if track_data is None:
            tracks.append(None)
        else:
            # Reconstruct Track object
            tracks.append(Track(
                artist=track_data['artist'],
                title=track_data['title'],
                album=track_data.get('album'),
                duration=timedelta(seconds=track_data['duration_seconds']),
                link=track_data.get('link')
            ))
    
    return MusicServicePlaylist(
        service_name=service_name,
        tracks=tracks,
        total_duration=timedelta(seconds=service_cache['total_duration_seconds'])
    )


def update_cache_entry(
    cache_key: str,
    playlist: Playlist,
    music_service_playlist: MusicServicePlaylist,
    cache_data: dict
) -> None:
    """
    Update cache entry for a specific music service.
    Creates playlist entry if it doesn't exist.
    
    Args:
        cache_key: Cache key (user/title)
        playlist: Playlist object
        music_service_playlist: Processed music service playlist
        cache_data: Cache data dictionary (modified in place)
    """
    if cache_key not in cache_data['playlists']:
        cache_data['playlists'][cache_key] = {
            'user': playlist.user,
            'title': playlist.title,
            'filepath': str(playlist.filepath),
            'content_hash': compute_playlist_hash(playlist.filepath),
            'music_services': {},
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
    
    playlist_entry = cache_data['playlists'][cache_key]
    
    # Update content hash in case playlist was modified
    playlist_entry['content_hash'] = compute_playlist_hash(playlist.filepath)
    playlist_entry['filepath'] = str(playlist.filepath)
    
    # Serialize tracks
    serialized_tracks = []
    for track in music_service_playlist.tracks:
        if track is None:
            serialized_tracks.append(None)
        else:
            track_data = {
                'artist': track.artist,
                'title': track.title,
                'album': track.album,
                'duration_seconds': int(track.duration.total_seconds()),
                'link': track.link
            }
            # Store service-specific data if available (e.g., SpotifyTrack.uri)
            if hasattr(track, '__dict__'):
                service_specific = {}
                for key, value in track.__dict__.items():
                    if key not in ['artist', 'title', 'album', 'duration', 'link']:
                        service_specific[key] = value
                if service_specific:
                    track_data['service_specific'] = service_specific
            serialized_tracks.append(track_data)
    
    # Update service-specific cache
    playlist_entry['music_services'][music_service_playlist.service_name] = {
        'total_duration_seconds': int(music_service_playlist.total_duration.total_seconds()),
        'tracks': serialized_tracks,
        'cached_at': datetime.now(timezone.utc).isoformat()
    }


def cleanup_stale_cache_entries(
    cache_data: dict,
    current_playlists: list[Playlist]
) -> int:
    """
    Remove cache entries for playlists that no longer exist.
    
    Args:
        cache_data: Cache data dictionary (modified in place)
        current_playlists: List of current playlists in repository
        
    Returns:
        Count of removed entries
    """
    current_keys = {get_cache_key(p) for p in current_playlists}
    cached_keys = set(cache_data['playlists'].keys())
    stale_keys = cached_keys - current_keys
    
    for key in stale_keys:
        LOG.info("Removing stale cache entry: %s", key)
        del cache_data['playlists'][key]
    
    return len(stale_keys)
