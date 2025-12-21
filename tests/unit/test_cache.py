""" Unit tests for cache.py """

import pytest
import json
from pathlib import Path
from datetime import timedelta, datetime, timezone
from freezegun import freeze_time

from mixdiscer.cache import (
    get_cache_key,
    compute_playlist_hash,
    load_cache,
    save_cache,
    is_cache_valid,
    get_cached_music_service_playlist,
    update_cache_entry,
    cleanup_stale_cache_entries,
)
from mixdiscer.playlists import Playlist
from mixdiscer.music_service import Track, MusicServicePlaylist


def test_get_cache_key(sample_playlist):
    """Test cache key generation"""
    key = get_cache_key(sample_playlist)
    
    assert key == "TestUser/Test Playlist"
    assert "/" in key
    assert sample_playlist.user in key
    assert sample_playlist.title in key


def test_compute_playlist_hash(tmp_path):
    """Test computing hash of playlist file"""
    playlist_path = tmp_path / "test.yaml"
    content = "user: Test\ntitle: Test Playlist\n"
    playlist_path.write_text(content)
    
    hash1 = compute_playlist_hash(playlist_path)
    
    assert hash1 is not None
    assert len(hash1) == 64  # SHA256 produces 64-char hex string
    
    # Same content should produce same hash
    hash2 = compute_playlist_hash(playlist_path)
    assert hash1 == hash2


def test_compute_playlist_hash_different_files(tmp_path):
    """Test that different files produce different hashes"""
    file1 = tmp_path / "file1.yaml"
    file2 = tmp_path / "file2.yaml"
    
    file1.write_text("content1")
    file2.write_text("content2")
    
    hash1 = compute_playlist_hash(file1)
    hash2 = compute_playlist_hash(file2)
    
    assert hash1 != hash2


def test_compute_playlist_hash_identical_files(tmp_path):
    """Test that identical files produce same hash"""
    file1 = tmp_path / "file1.yaml"
    file2 = tmp_path / "file2.yaml"
    
    content = "user: Test\ntitle: Test\n"
    file1.write_text(content)
    file2.write_text(content)
    
    hash1 = compute_playlist_hash(file1)
    hash2 = compute_playlist_hash(file2)
    
    assert hash1 == hash2


def test_load_cache_existing(tmp_path):
    """Test loading existing cache file"""
    cache_path = tmp_path / "cache.json"
    cache_data = {
        'version': '1.0',
        'last_updated': '2024-01-01T00:00:00+00:00',
        'playlists': {
            'User/Title': {
                'user': 'User',
                'title': 'Title'
            }
        }
    }
    cache_path.write_text(json.dumps(cache_data))
    
    loaded = load_cache(cache_path)
    
    assert loaded['version'] == '1.0'
    assert 'User/Title' in loaded['playlists']


def test_load_cache_missing(tmp_path):
    """Test loading non-existent cache creates empty structure"""
    cache_path = tmp_path / "nonexistent.json"
    
    cache = load_cache(cache_path)
    
    assert cache['version'] == '1.0'
    assert cache['playlists'] == {}
    assert 'last_updated' in cache


def test_load_cache_invalid_json(tmp_path):
    """Test handling corrupted cache file"""
    cache_path = tmp_path / "corrupt.json"
    cache_path.write_text("{ invalid json")
    
    cache = load_cache(cache_path)
    
    # Should return empty cache structure
    assert cache['version'] == '1.0'
    assert cache['playlists'] == {}


@freeze_time("2024-01-15 12:00:00")
def test_save_cache(tmp_path):
    """Test saving cache with timestamp update"""
    cache_path = tmp_path / ".cache" / "test.json"
    cache_data = {
        'version': '1.0',
        'last_updated': '2024-01-01T00:00:00+00:00',
        'playlists': {}
    }
    
    save_cache(cache_data, cache_path)
    
    assert cache_path.exists()
    
    with open(cache_path, 'r') as f:
        saved = json.load(f)
    
    assert saved['version'] == '1.0'
    assert '2024-01-15' in saved['last_updated']


def test_save_cache_creates_directory(tmp_path):
    """Test that save_cache creates parent directory"""
    cache_path = tmp_path / "nested" / "dir" / "cache.json"
    cache_data = {
        'version': '1.0',
        'playlists': {}
    }
    
    save_cache(cache_data, cache_path)
    
    assert cache_path.exists()
    assert cache_path.parent.is_dir()


def test_is_cache_valid_unchanged(sample_playlist):
    """Test that unchanged playlist is valid"""
    current_hash = compute_playlist_hash(sample_playlist.filepath)
    cache_entry = {
        'content_hash': current_hash,
        'user': sample_playlist.user,
        'title': sample_playlist.title
    }
    
    assert is_cache_valid(sample_playlist, cache_entry)


def test_is_cache_valid_changed(sample_playlist):
    """Test that changed playlist is invalid"""
    cache_entry = {
        'content_hash': 'old_hash_value_different',
        'user': sample_playlist.user,
        'title': sample_playlist.title
    }
    
    assert not is_cache_valid(sample_playlist, cache_entry)


def test_get_cached_music_service_playlist_exists(empty_cache, sample_playlist):
    """Test retrieving cached playlist"""
    cache_data = empty_cache
    cache_key = "TestUser/Test Playlist"
    
    cache_data['playlists'][cache_key] = {
        'user': 'TestUser',
        'title': 'Test Playlist',
        'music_services': {
            'spotify': {
                'total_duration_seconds': 450,
                'tracks': [
                    {
                        'artist': 'Test Artist',
                        'title': 'Test Song',
                        'album': 'Test Album',
                        'duration_seconds': 225,
                        'link': 'https://example.com/track'
                    },
                    None  # Missing track
                ]
            }
        }
    }
    
    playlist = get_cached_music_service_playlist(cache_key, 'spotify', cache_data)
    
    assert playlist is not None
    assert playlist.service_name == 'spotify'
    assert len(playlist.tracks) == 2
    assert playlist.tracks[0].artist == 'Test Artist'
    assert playlist.tracks[1] is None
    assert playlist.total_duration == timedelta(seconds=450)


def test_get_cached_music_service_playlist_missing(empty_cache):
    """Test that missing cache returns None"""
    playlist = get_cached_music_service_playlist('NonExistent/Playlist', 'spotify', empty_cache)
    
    assert playlist is None


def test_get_cached_music_service_playlist_different_service(empty_cache):
    """Test that wrong service returns None"""
    cache_data = empty_cache
    cache_key = "TestUser/Test"
    
    cache_data['playlists'][cache_key] = {
        'music_services': {
            'spotify': {
                'total_duration_seconds': 300,
                'tracks': []
            }
        }
    }
    
    # Request different service
    playlist = get_cached_music_service_playlist(cache_key, 'apple_music', cache_data)
    
    assert playlist is None


def test_update_cache_entry_new(empty_cache, sample_playlist, sample_music_service_playlist):
    """Test creating new cache entry"""
    cache_key = get_cache_key(sample_playlist)
    
    update_cache_entry(cache_key, sample_playlist, sample_music_service_playlist, empty_cache)
    
    assert cache_key in empty_cache['playlists']
    entry = empty_cache['playlists'][cache_key]
    assert entry['user'] == sample_playlist.user
    assert entry['title'] == sample_playlist.title
    assert 'content_hash' in entry
    assert 'spotify' in entry['music_services']


def test_update_cache_entry_existing(empty_cache, sample_playlist, sample_music_service_playlist):
    """Test updating existing cache entry"""
    cache_key = get_cache_key(sample_playlist)
    
    # Create initial entry
    empty_cache['playlists'][cache_key] = {
        'user': sample_playlist.user,
        'title': sample_playlist.title,
        'content_hash': 'old_hash',
        'music_services': {}
    }
    
    update_cache_entry(cache_key, sample_playlist, sample_music_service_playlist, empty_cache)
    
    entry = empty_cache['playlists'][cache_key]
    # Hash should be updated
    assert entry['content_hash'] != 'old_hash'
    assert 'spotify' in entry['music_services']


def test_update_cache_entry_serialization(empty_cache, sample_playlist):
    """Test that tracks are serialized correctly"""
    cache_key = get_cache_key(sample_playlist)
    
    tracks = [
        Track("Artist", "Title", "Album", timedelta(minutes=3, seconds=30), "https://link"),
        None  # Missing track
    ]
    music_service_playlist = MusicServicePlaylist(
        service_name="spotify",
        tracks=tracks,
        total_duration=timedelta(minutes=3, seconds=30)
    )
    
    update_cache_entry(cache_key, sample_playlist, music_service_playlist, empty_cache)
    
    entry = empty_cache['playlists'][cache_key]
    spotify_data = entry['music_services']['spotify']
    
    assert len(spotify_data['tracks']) == 2
    assert spotify_data['tracks'][0]['artist'] == "Artist"
    assert spotify_data['tracks'][0]['duration_seconds'] == 210
    assert spotify_data['tracks'][1] is None


def test_cleanup_stale_cache_entries(empty_cache):
    """Test removing cache entries for deleted playlists"""
    # Add cache entries
    empty_cache['playlists']['User1/Playlist1'] = {'user': 'User1', 'title': 'Playlist1'}
    empty_cache['playlists']['User2/Playlist2'] = {'user': 'User2', 'title': 'Playlist2'}
    empty_cache['playlists']['User3/Playlist3'] = {'user': 'User3', 'title': 'Playlist3'}
    
    # Only keep Playlist1 and Playlist2
    current_playlists = [
        Playlist('User1', 'Playlist1', 'Desc', 'Genre', [], None),
        Playlist('User2', 'Playlist2', 'Desc', 'Genre', [], None),
    ]
    
    removed = cleanup_stale_cache_entries(empty_cache, current_playlists)
    
    assert removed == 1
    assert 'User1/Playlist1' in empty_cache['playlists']
    assert 'User2/Playlist2' in empty_cache['playlists']
    assert 'User3/Playlist3' not in empty_cache['playlists']


def test_cleanup_stale_cache_entries_nothing_to_remove(empty_cache):
    """Test cleanup when cache is already clean"""
    empty_cache['playlists']['User1/Playlist1'] = {'user': 'User1', 'title': 'Playlist1'}
    
    current_playlists = [
        Playlist('User1', 'Playlist1', 'Desc', 'Genre', [], None),
    ]
    
    removed = cleanup_stale_cache_entries(empty_cache, current_playlists)
    
    assert removed == 0
    assert 'User1/Playlist1' in empty_cache['playlists']


def test_cleanup_stale_cache_entries_empty_cache(empty_cache):
    """Test cleanup with empty cache"""
    current_playlists = [
        Playlist('User1', 'Playlist1', 'Desc', 'Genre', [], None),
    ]
    
    removed = cleanup_stale_cache_entries(empty_cache, current_playlists)
    
    assert removed == 0
