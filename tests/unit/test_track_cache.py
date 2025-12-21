""" Unit tests for track_cache.py """

import pytest
import json
from pathlib import Path
from datetime import timedelta, datetime, timezone
from freezegun import freeze_time

from mixdiscer.track_cache import (
    normalize_track_key,
    load_track_cache,
    save_track_cache,
    get_cached_track,
    update_track_cache,
    get_track_cache_stats,
    cleanup_stale_tracks,
)
from mixdiscer.music_service import Track


def test_normalize_track_key():
    """Test track key normalization"""
    key1 = normalize_track_key("The Beatles", "Hey Jude")
    key2 = normalize_track_key("THE BEATLES", "HEY JUDE")
    key3 = normalize_track_key("  The Beatles  ", "  Hey Jude  ")
    
    assert key1 == "the beatles - hey jude"
    assert key1 == key2  # Case insensitive
    assert key1 == key3  # Trimmed


def test_load_track_cache_existing(tmp_path):
    """Test loading existing track cache"""
    cache_path = tmp_path / "tracks.json"
    cache_data = {
        'version': '2.0',
        'last_updated': '2024-01-01T00:00:00+00:00',
        'tracks': {
            'artist - title': {
                'query': {'artist': 'Artist', 'title': 'Title'},
                'versions': {}
            }
        }
    }
    cache_path.write_text(json.dumps(cache_data))
    
    loaded = load_track_cache(cache_path)
    
    assert loaded['version'] == '2.0'
    assert 'artist - title' in loaded['tracks']


def test_load_track_cache_missing(tmp_path):
    """Test loading non-existent cache creates empty structure"""
    cache_path = tmp_path / "nonexistent.json"
    
    cache = load_track_cache(cache_path)
    
    assert cache['version'] == '2.0'
    assert cache['tracks'] == {}
    assert 'last_updated' in cache


def test_load_track_cache_invalid_json(tmp_path):
    """Test handling corrupted track cache"""
    cache_path = tmp_path / "corrupt.json"
    cache_path.write_text("{ invalid json")
    
    cache = load_track_cache(cache_path)
    
    assert cache['version'] == '2.0'
    assert cache['tracks'] == {}


@freeze_time("2024-01-15 12:00:00")
def test_save_track_cache(tmp_path):
    """Test saving track cache with timestamp"""
    cache_path = tmp_path / "tracks.json"
    cache_data = {
        'version': '2.0',
        'last_updated': '2024-01-01T00:00:00+00:00',
        'tracks': {}
    }
    
    save_track_cache(cache_data, cache_path)
    
    assert cache_path.exists()
    
    with open(cache_path, 'r') as f:
        saved = json.load(f)
    
    assert saved['version'] == '2.0'
    assert '2024-01-15' in saved['last_updated']


def test_get_cached_track_hit_default():
    """Test cache hit for default version (no album)"""
    cache_data = {
        'tracks': {
            'artist - title': {
                'query': {'artist': 'Artist', 'title': 'Title'},
                'versions': {
                    'spotify': [
                        {
                            'found': True,
                            'album': 'Album',
                            'normalized_album': 'album',
                            'duration_seconds': 180,
                            'link': 'https://example.com/track',
                            'is_default': True
                        }
                    ]
                }
            }
        }
    }
    
    track = get_cached_track('Artist', 'Title', None, 'spotify', cache_data)
    
    assert track is not None
    assert track.artist == 'Artist'
    assert track.title == 'Title'
    assert track.duration == timedelta(seconds=180)


def test_get_cached_track_hit_with_album():
    """Test cache hit with specific album"""
    cache_data = {
        'tracks': {
            'artist - title': {
                'query': {'artist': 'Artist', 'title': 'Title'},
                'versions': {
                    'spotify': [
                        {
                            'found': True,
                            'album': 'Album One',
                            'normalized_album': 'album one',
                            'duration_seconds': 180,
                            'link': 'https://example.com/track',
                            'is_default': False
                        }
                    ]
                }
            }
        }
    }
    
    track = get_cached_track('Artist', 'Title', 'Album One', 'spotify', cache_data)
    
    assert track is not None
    assert track.album == 'Album One'


def test_get_cached_track_miss():
    """Test cache miss"""
    cache_data = {'tracks': {}}
    
    track = get_cached_track('Artist', 'Title', None, 'spotify', cache_data)
    
    assert track is None


def test_get_cached_track_not_found_result():
    """Test cached 'not found' result"""
    cache_data = {
        'tracks': {
            'artist - title': {
                'query': {'artist': 'Artist', 'title': 'Title'},
                'versions': {
                    'spotify': [
                        {
                            'found': False,
                            'album': None,
                            'normalized_album': '',
                            'is_default': True
                        }
                    ]
                }
            }
        }
    }
    
    track = get_cached_track('Artist', 'Title', None, 'spotify', cache_data)
    
    # Should return None for not found
    assert track is None


def test_update_track_cache_new_track():
    """Test adding new track to cache"""
    cache_data = {'tracks': {}}
    
    track = Track(
        artist='Artist',
        title='Title',
        album='Album',
        duration=timedelta(minutes=3),
        link='https://example.com/track'
    )
    
    update_track_cache('Artist', 'Title', 'Album', 'spotify', track, cache_data, is_default=True)
    
    track_key = 'artist - title'
    assert track_key in cache_data['tracks']
    
    entry = cache_data['tracks'][track_key]
    assert 'spotify' in entry['versions']
    assert len(entry['versions']['spotify']) == 1
    assert entry['versions']['spotify'][0]['is_default'] is True


def test_update_track_cache_not_found():
    """Test caching 'not found' result"""
    cache_data = {'tracks': {}}
    
    update_track_cache('Artist', 'Title', None, 'spotify', None, cache_data, is_default=True)
    
    track_key = 'artist - title'
    assert track_key in cache_data['tracks']
    
    entry = cache_data['tracks'][track_key]
    assert entry['versions']['spotify'][0]['found'] is False


def test_update_track_cache_multiple_versions():
    """Test caching multiple album versions"""
    cache_data = {'tracks': {}}
    
    track1 = Track('Artist', 'Title', 'Album One', timedelta(minutes=3), 'https://link1')
    track2 = Track('Artist', 'Title', 'Album Two', timedelta(minutes=3, seconds=15), 'https://link2')
    
    update_track_cache('Artist', 'Title', 'Album One', 'spotify', track1, cache_data)
    update_track_cache('Artist', 'Title', 'Album Two', 'spotify', track2, cache_data)
    
    track_key = 'artist - title'
    versions = cache_data['tracks'][track_key]['versions']['spotify']
    
    assert len(versions) == 2


def test_get_track_cache_stats():
    """Test cache statistics generation"""
    cache_data = {
        'tracks': {
            'artist1 - title1': {
                'access_count': 10,
                'versions': {
                    'spotify': [
                        {'found': True}
                    ]
                }
            },
            'artist2 - title2': {
                'access_count': 5,
                'versions': {
                    'spotify': [
                        {'found': False}
                    ]
                }
            },
        }
    }
    
    stats = get_track_cache_stats(cache_data)
    
    assert stats['total_tracks'] == 2
    assert stats['total_versions'] == 2
    assert stats['not_found_tracks'] == 1
    assert 'spotify' in stats['services']
    assert stats['services']['spotify']['cached'] == 1
    assert stats['services']['spotify']['not_found'] == 1


@freeze_time("2024-06-01 12:00:00")
def test_cleanup_stale_tracks():
    """Test cleanup of stale tracks"""
    cache_data = {
        'tracks': {
            'current - track': {
                'last_accessed': '2024-05-30T00:00:00+00:00',  # 2 days old
                'versions': {}
            },
            'old - track': {
                'last_accessed': '2024-01-01T00:00:00+00:00',  # 151 days old
                'versions': {}
            },
        }
    }
    
    current_tracks = {'current - track'}
    
    removed = cleanup_stale_tracks(cache_data, current_tracks, max_age_days=90)
    
    assert removed == 1
    assert 'current - track' in cache_data['tracks']
    assert 'old - track' not in cache_data['tracks']


def test_cleanup_stale_tracks_keep_current():
    """Test that tracks in use are kept regardless of age"""
    cache_data = {
        'tracks': {
            'current - old': {
                'last_accessed': '2020-01-01T00:00:00+00:00',  # Very old
                'versions': {}
            },
        }
    }
    
    # Track is in use, should be kept
    current_tracks = {'current - old'}
    
    removed = cleanup_stale_tracks(cache_data, current_tracks, max_age_days=90)
    
    assert removed == 0
    assert 'current - old' in cache_data['tracks']
