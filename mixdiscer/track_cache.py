""" Module for track-level caching to enable incremental playlist updates """

import hashlib
import json
import logging

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from mixdiscer.music_service import Track

LOG = logging.getLogger(__name__)


def normalize_track_key(artist: str, title: str) -> str:
    """
    Normalize track identifier for cache lookup (album-agnostic).
    
    Args:
        artist: Artist name
        title: Track title
        
    Returns:
        Normalized key: "artist - title" (lowercase, trimmed)
    """
    return f"{artist.strip().lower()} - {title.strip().lower()}"


def load_track_cache(cache_path: Path) -> dict:
    """
    Load track cache JSON from configured path.
    
    Args:
        cache_path: Path to track cache file
        
    Returns:
        Track cache data dictionary
    """
    if not cache_path.exists():
        LOG.debug("Track cache file not found, creating empty cache structure")
        return {
            'version': '2.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'tracks': {}
        }
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            LOG.debug("Loaded track cache from %s with %d tracks", 
                     cache_path, len(cache_data.get('tracks', {})))
            return cache_data
    except (json.JSONDecodeError, IOError) as e:
        LOG.warning("Failed to load track cache from %s: %s. Starting with empty cache.", 
                   cache_path, e)
        return {
            'version': '2.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'tracks': {}
        }


def save_track_cache(cache_data: dict, cache_path: Path) -> None:
    """
    Save track cache to configured path with timestamp update.
    
    Args:
        cache_data: Track cache data dictionary
        cache_path: Path to track cache file
    """
    # Ensure parent directory exists
    parent_dir = cache_path.parent
    if parent_dir.exists() and not parent_dir.is_dir():
        LOG.warning("Removing file %s to create directory", parent_dir)
        parent_dir.unlink()
    parent_dir.mkdir(parents=True, exist_ok=True)
    
    cache_data['last_updated'] = datetime.now(timezone.utc).isoformat()
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2)
    
    LOG.debug("Saved track cache to %s", cache_path)


def _deserialize_track_version(
    artist: str, 
    title: str, 
    version_data: dict
) -> Optional[Track]:
    """
    Deserialize a track version from cache data into Track object.
    
    Args:
        artist: Artist name (from query)
        title: Track title (from query)
        version_data: Version data from cache
        
    Returns:
        Track object or None if track was not found
    """
    if not version_data.get('found', True):
        # This is a negative cache entry (track not found)
        return None
    
    return Track(
        artist=artist,
        title=title,
        album=version_data.get('album'),
        duration=timedelta(seconds=version_data['duration_seconds']),
        link=version_data.get('link')
    )


def get_cached_track(
    artist: str,
    title: str,
    album: Optional[str],
    service_name: str,
    cache_data: dict
) -> Optional[Track]:
    """
    Retrieve track from cache with album awareness.
    
    If album is specified, searches for exact album match.
    If album is None, returns the default version (is_default=True).
    
    Args:
        artist: Artist name
        title: Track title  
        album: Optional album name for specific version
        service_name: Name of music service (e.g., "spotify")
        cache_data: Track cache data dictionary
        
    Returns:
        Track object if found in cache, None otherwise
        Note: Returns None (not a Track with None) for "not found" results
    """
    track_key = normalize_track_key(artist, title)
    track_entry = cache_data['tracks'].get(track_key)
    
    if not track_entry:
        return None  # Track not in cache at all
    
    # Update access statistics
    track_entry['last_accessed'] = datetime.now(timezone.utc).isoformat()
    track_entry['access_count'] = track_entry.get('access_count', 0) + 1
    
    versions = track_entry.get('versions', {}).get(service_name, [])
    
    if not versions:
        return None  # No versions for this service
    
    if album is None:
        # No album specified - use default version
        for version in versions:
            if version.get('is_default', False):
                LOG.debug("Track cache hit (default): %s - %s", artist, title)
                return _deserialize_track_version(artist, title, version)
        return None  # No default version cached
    else:
        # Album specified - find exact match
        normalized_album = album.strip().lower()
        for version in versions:
            if version.get('normalized_album') == normalized_album:
                LOG.debug("Track cache hit (album: %s): %s - %s", album, artist, title)
                return _deserialize_track_version(artist, title, version)
        return None  # Specific album not cached


def update_track_cache(
    artist: str,
    title: str,
    album: Optional[str],
    service_name: str,
    track: Optional[Track],
    cache_data: dict,
    is_default: bool = False
) -> None:
    """
    Update track cache with new version.
    Handles both found and not-found tracks.
    
    Args:
        artist: Artist name
        title: Track title
        album: Optional album name
        service_name: Name of music service
        track: Track object if found, None if not found
        cache_data: Track cache data dictionary (modified in place)
        is_default: Mark this version as the default (no album specified)
    """
    track_key = normalize_track_key(artist, title)
    
    # Initialize track entry if needed
    if track_key not in cache_data['tracks']:
        cache_data['tracks'][track_key] = {
            'query': {'artist': artist, 'title': title},
            'versions': {},
            'first_seen': datetime.now(timezone.utc).isoformat(),
            'last_accessed': datetime.now(timezone.utc).isoformat(),
            'access_count': 1
        }
    
    track_entry = cache_data['tracks'][track_key]
    track_entry['last_accessed'] = datetime.now(timezone.utc).isoformat()
    track_entry['access_count'] = track_entry.get('access_count', 0) + 1
    
    # Initialize service versions if needed
    if service_name not in track_entry['versions']:
        track_entry['versions'][service_name] = []
    
    versions = track_entry['versions'][service_name]
    
    # Create version entry
    if track:
        # Track found - cache it
        version_data = {
            'found': True,
            'artist': track.artist,  # Store actual result (may differ from query)
            'title': track.title,
            'album': track.album,
            'normalized_album': (track.album or '').strip().lower(),
            'duration_seconds': int(track.duration.total_seconds()),
            'link': track.link,
            'is_default': is_default,
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Add service-specific data if available
        if hasattr(track, '__dict__'):
            service_specific = {}
            for key, value in track.__dict__.items():
                if key not in ['artist', 'title', 'album', 'duration', 'link']:
                    service_specific[key] = value
            if service_specific:
                version_data['service_specific'] = service_specific
        
        # Check if this version already exists (by album)
        normalized_album = (track.album or '').strip().lower()
        existing_idx = None
        for idx, v in enumerate(versions):
            if v.get('normalized_album') == normalized_album:
                existing_idx = idx
                break
        
        if existing_idx is not None:
            # Update existing version
            versions[existing_idx] = version_data
            LOG.debug("Updated cached track version: %s - %s (album: %s)", 
                     artist, title, track.album or "default")
        else:
            # Add new version
            versions.append(version_data)
            LOG.debug("Added new cached track version: %s - %s (album: %s)", 
                     artist, title, track.album or "default")
    else:
        # Track not found - store negative cache
        version_data = {
            'found': False,
            'album': album,
            'normalized_album': (album or '').strip().lower(),
            'is_default': is_default,
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Check if this negative result already exists
        normalized_album = (album or '').strip().lower()
        existing_idx = None
        for idx, v in enumerate(versions):
            if not v.get('found', True) and v.get('normalized_album') == normalized_album:
                existing_idx = idx
                break
        
        if existing_idx is not None:
            # Update existing negative cache
            versions[existing_idx] = version_data
        else:
            # Add new negative cache
            versions.append(version_data)
        
        LOG.debug("Cached 'not found' result: %s - %s (album: %s)", 
                 artist, title, album or "default")


def get_track_cache_stats(cache_data: dict) -> dict:
    """
    Return statistics about track cache.
    
    Args:
        cache_data: Track cache data dictionary
        
    Returns:
        Dictionary with cache statistics
    """
    stats = {
        'total_tracks': len(cache_data.get('tracks', {})),
        'services': {},
        'not_found_tracks': 0,
        'total_versions': 0,
        'most_accessed': []
    }
    
    service_counts = {}
    access_counts = []
    
    for track_key, track_data in cache_data.get('tracks', {}).items():
        versions = track_data.get('versions', {})
        
        for service_name, service_versions in versions.items():
            if service_name not in service_counts:
                service_counts[service_name] = {'cached': 0, 'not_found': 0}
            
            for version in service_versions:
                stats['total_versions'] += 1
                if version.get('found', True):
                    service_counts[service_name]['cached'] += 1
                else:
                    service_counts[service_name]['not_found'] += 1
                    stats['not_found_tracks'] += 1
        
        access_counts.append((
            track_key,
            track_data.get('access_count', 0)
        ))
    
    stats['services'] = service_counts
    stats['most_accessed'] = sorted(access_counts, key=lambda x: x[1], reverse=True)[:10]
    
    return stats


def cleanup_stale_tracks(
    cache_data: dict,
    current_tracks: set[str],
    max_age_days: int = 90
) -> int:
    """
    Remove tracks not used in any current playlist or too old.
    
    Args:
        cache_data: Track cache data dictionary (modified in place)
        current_tracks: Set of track keys currently in use across all playlists
        max_age_days: Remove tracks not accessed in this many days
        
    Returns:
        Count of removed tracks
    """
    tracks_to_remove = []
    now = datetime.now(timezone.utc)
    
    for track_key, track_data in cache_data.get('tracks', {}).items():
        # Check if track is still in use
        if track_key in current_tracks:
            continue
        
        # Check if track is too old
        last_accessed = datetime.fromisoformat(track_data.get('last_accessed'))
        age_days = (now - last_accessed).days
        
        if age_days > max_age_days:
            tracks_to_remove.append(track_key)
            LOG.info("Removing stale track cache entry: %s (age: %d days)", track_key, age_days)
    
    for track_key in tracks_to_remove:
        del cache_data['tracks'][track_key]
    
    return len(tracks_to_remove)
