""" Unit tests for main.py """

import pytest
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from mixdiscer.main import (
    calculate_duration,
    _load_rendering_config,
    _get_music_service,
    _process_single_playlist,
    validate_playlist,
)
from mixdiscer.music_service import Track, MusicServicePlaylist
from mixdiscer.playlists import Playlist
from mixdiscer.validation import ValidationResult


def test_calculate_duration():
    """Test calculating total duration from tracks"""
    tracks = [
        Track("A", "B", "C", timedelta(minutes=3, seconds=30), "link"),
        Track("D", "E", "F", timedelta(minutes=4, seconds=15), "link"),
        Track("G", "H", "I", timedelta(minutes=2, seconds=45), "link"),
    ]
    
    total = calculate_duration(tracks)
    
    assert total == timedelta(minutes=10, seconds=30)


def test_calculate_duration_with_none():
    """Test calculating duration with missing tracks"""
    tracks = [
        Track("A", "B", "C", timedelta(minutes=3), "link"),
        None,
        Track("D", "E", "F", timedelta(minutes=4), "link"),
        None,
    ]
    
    total = calculate_duration(tracks)
    
    assert total == timedelta(minutes=7)


def test_calculate_duration_empty():
    """Test calculating duration with empty list"""
    total = calculate_duration([])
    
    assert total == timedelta()


def test_calculate_duration_all_none():
    """Test calculating duration with all None"""
    total = calculate_duration([None, None, None])
    
    assert total == timedelta()


def test_load_rendering_config(test_config):
    """Test loading rendering configuration"""
    mixdisc_dir, template_dir, output_dir, duration_threshold, cache_path, track_cache_path = \
        _load_rendering_config(str(test_config))
    
    assert mixdisc_dir is not None
    assert template_dir.name == "templates"
    assert output_dir.name == "output"
    assert duration_threshold == timedelta(minutes=80)
    assert cache_path.name == "playlists_cache.json"
    assert track_cache_path.name == "tracks_cache.json"


def test_get_music_service():
    """Test music service initialization"""
    with patch.dict('os.environ', {
        'SPOTIPY_CLIENT_ID': 'test_id',
        'SPOTIPY_CLIENT_SECRET': 'test_secret'
    }):
        service = _get_music_service()
        
        assert service is not None
        assert service.name == "spotify"


def test_process_single_playlist_no_cache(sample_playlist):
    """Test processing playlist without cache"""
    mock_service = Mock()
    mock_service.name = "spotify"
    mock_service_playlist = MusicServicePlaylist(
        service_name="spotify",
        tracks=[
            Track("Artist", "Song", "Album", timedelta(minutes=3), "link"),
        ],
        total_duration=timedelta(minutes=3)
    )
    mock_service.process_user_playlist.return_value = mock_service_playlist
    
    result = _process_single_playlist(sample_playlist, mock_service)
    
    assert result is not None
    assert len(result.music_service_playlists) == 1
    assert result.music_service_playlists[0] == mock_service_playlist
    assert result.user_playlist == sample_playlist


def test_process_single_playlist_cache_hit(sample_playlist, empty_cache):
    """Test processing playlist with cache hit"""
    mock_service = Mock()
    mock_service.name = "spotify"
    
    # Setup cache with playlist data
    cache_key = "TestUser/Test Playlist"
    empty_cache['playlists'][cache_key] = {
        'user': 'TestUser',
        'title': 'Test Playlist',
        'content_hash': 'dummy_hash',
        'music_services': {
            'spotify': {
                'total_duration_seconds': 180,
                'tracks': [
                    {
                        'artist': 'Cached Artist',
                        'title': 'Cached Song',
                        'album': 'Cached Album',
                        'duration_seconds': 180,
                        'link': 'https://cached.link'
                    }
                ]
            }
        }
    }
    
    # Mock cache validity check to return True
    with patch('mixdiscer.cache.is_cache_valid', return_value=True):
        with patch('mixdiscer.cache.compute_playlist_hash', return_value='dummy_hash'):
            result = _process_single_playlist(
                sample_playlist, 
                mock_service,
                cache_key=cache_key,
                cache_data=empty_cache
            )
    
    assert result is not None
    # Should use cached data - process_user_playlist should not be called
    assert not mock_service.process_user_playlist.called
    assert len(result.music_service_playlists) == 1
    assert result.music_service_playlists[0].tracks[0].artist == 'Cached Artist'


def test_validate_playlist_valid(sample_playlist):
    """Test validating a playlist under duration threshold"""
    mock_service = Mock()
    mock_service.name = "spotify"
    mock_service_playlist = MusicServicePlaylist(
        service_name="spotify",
        tracks=[
            Track("Artist", "Song", "Album", timedelta(minutes=3), "link"),
        ],
        total_duration=timedelta(minutes=70)  # Under 80
    )
    mock_service.process_user_playlist.return_value = mock_service_playlist
    
    result = validate_playlist(
        sample_playlist.filepath,
        sample_playlist,
        mock_service,
        timedelta(minutes=80)
    )
    
    assert result.is_valid
    assert result.total_duration == timedelta(minutes=70)
    assert result.user == "TestUser"
    assert result.title == "Test Playlist"


def test_validate_playlist_over_duration(sample_playlist):
    """Test validating a playlist over duration threshold"""
    mock_service = Mock()
    mock_service.name = "spotify"
    mock_service_playlist = MusicServicePlaylist(
        service_name="spotify",
        tracks=[
            Track("Artist", "Song", "Album", timedelta(minutes=3), "link"),
        ],
        total_duration=timedelta(minutes=90)  # Over 80
    )
    mock_service.process_user_playlist.return_value = mock_service_playlist
    
    result = validate_playlist(
        sample_playlist.filepath,
        sample_playlist,
        mock_service,
        timedelta(minutes=80)
    )
    
    assert not result.is_valid
    assert result.total_duration == timedelta(minutes=90)
    assert result.duration_exceeded


def test_validate_playlist_missing_tracks(sample_playlist):
    """Test validating playlist with missing tracks"""
    mock_service = Mock()
    mock_service.name = "spotify"
    mock_service_playlist = MusicServicePlaylist(
        service_name="spotify",
        tracks=[
            Track("Artist", "Song", "Album", timedelta(minutes=3), "link"),
            None,  # Missing track
        ],
        total_duration=timedelta(minutes=70)
    )
    mock_service.process_user_playlist.return_value = mock_service_playlist
    
    result = validate_playlist(
        sample_playlist.filepath,
        sample_playlist,
        mock_service,
        timedelta(minutes=80)
    )
    
    assert result.is_valid  # Still valid if under duration
    assert len(result.missing_tracks) == 1


def test_validate_playlist_error(sample_playlist):
    """Test validation with error"""
    mock_service = Mock()
    mock_service.name = "spotify"
    mock_service.process_user_playlist.side_effect = Exception("API Error")
    
    result = validate_playlist(
        sample_playlist.filepath,
        sample_playlist,
        mock_service,
        timedelta(minutes=80)
    )
    
    assert not result.is_valid
    assert result.error_message == "API Error"


def test_validate_playlist_with_cache_update(sample_playlist, tmp_path):
    """Test validation with cache update"""
    cache_path = tmp_path / "cache.json"
    
    mock_service = Mock()
    mock_service.name = "spotify"
    mock_service_playlist = MusicServicePlaylist(
        service_name="spotify",
        tracks=[
            Track("Artist", "Song", "Album", timedelta(minutes=3), "link"),
        ],
        total_duration=timedelta(minutes=70)
    )
    mock_service.process_user_playlist.return_value = mock_service_playlist
    
    result = validate_playlist(
        sample_playlist.filepath,
        sample_playlist,
        mock_service,
        timedelta(minutes=80),
        cache_path=cache_path
    )
    
    assert result.is_valid
    # Cache file should be created
    assert cache_path.exists()


@patch('mixdiscer.main.SpotifyMusicService')
@patch('mixdiscer.main.get_playlists')
def test_validate_playlist_uses_cache_when_unchanged(mock_get_playlists, mock_spotify, sample_playlist, tmp_path):
    """Test that unchanged playlists use cache during validation"""
    cache_path = tmp_path / "cache.json"
    
    # Setup mocks
    mock_service_instance = Mock()
    mock_service_instance.name = "spotify"
    mock_spotify.return_value = mock_service_instance
    
    mock_service_playlist = MusicServicePlaylist(
        service_name="spotify",
        tracks=[Track("A", "B", "C", timedelta(minutes=3), "link")],
        total_duration=timedelta(minutes=70)
    )
    mock_service_instance.process_user_playlist.return_value = mock_service_playlist
    
    # First validation - should call music service
    result1 = validate_playlist(
        sample_playlist.filepath,
        sample_playlist,
        mock_service_instance,
        timedelta(minutes=80),
        cache_path=cache_path
    )
    
    assert result1.is_valid
    assert mock_service_instance.process_user_playlist.call_count == 1
    
    # Second validation with skip_music_service_if_cached=True and unchanged file
    with patch('mixdiscer.main.load_cache') as mock_load_cache:
        with patch('mixdiscer.main.is_cache_valid', return_value=True):
            with patch('mixdiscer.main.get_cached_music_service_playlist', return_value=mock_service_playlist):
                result2 = validate_playlist(
                    sample_playlist.filepath,
                    sample_playlist,
                    mock_service_instance,
                    timedelta(minutes=80),
                    cache_path=cache_path,
                    skip_music_service_if_cached=True
                )
    
    assert result2.is_valid
    # Should not call music service again (still 1 call from first validation)
    assert mock_service_instance.process_user_playlist.call_count == 1
