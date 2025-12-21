""" Shared pytest fixtures for all tests """

import pytest
from pathlib import Path
from datetime import timedelta
from typing import Optional

from mixdiscer.playlists import Playlist
from mixdiscer.music_service import Track, MusicServicePlaylist


@pytest.fixture
def temp_mixdisc_dir(tmp_path):
    """Create temporary mixdisc directory structure with user folders"""
    mixdisc_dir = tmp_path / "mixdiscs"
    mixdisc_dir.mkdir()
    
    # Create sample user directories
    (mixdisc_dir / "TestUser").mkdir()
    (mixdisc_dir / "AnotherUser").mkdir()
    
    return mixdisc_dir


@pytest.fixture
def sample_playlist(tmp_path):
    """Return a sample Playlist object with filepath"""
    playlist_path = tmp_path / "TestUser" / "test_playlist.yaml"
    playlist_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a dummy YAML file so filepath exists
    playlist_path.write_text("""
user: TestUser
title: Test Playlist
description: A test playlist
genre: Rock
playlist:
  - Artist One - Song One
  - Artist Two - Song Two
""")
    
    return Playlist(
        user="TestUser",
        title="Test Playlist",
        description="A test playlist",
        genre="Rock",
        tracks=[
            ("Artist One", "Song One", None),
            ("Artist Two", "Song Two", None),
        ],
        filepath=playlist_path
    )


@pytest.fixture
def sample_track():
    """Return a sample Track object"""
    return Track(
        artist="Test Artist",
        title="Test Song",
        album="Test Album",
        duration=timedelta(minutes=3, seconds=45),
        link="https://example.com/track"
    )


@pytest.fixture
def sample_tracks():
    """Return a list of sample Track objects"""
    return [
        Track(
            artist="Artist One",
            title="Song One",
            album="Album One",
            duration=timedelta(minutes=3, seconds=30),
            link="https://example.com/track1"
        ),
        Track(
            artist="Artist Two",
            title="Song Two",
            album="Album Two",
            duration=timedelta(minutes=4, seconds=15),
            link="https://example.com/track2"
        ),
        Track(
            artist="Artist Three",
            title="Song Three",
            album=None,
            duration=timedelta(minutes=2, seconds=45),
            link="https://example.com/track3"
        ),
    ]


@pytest.fixture
def sample_music_service_playlist(sample_tracks):
    """Return a sample MusicServicePlaylist"""
    total_duration = sum((t.duration for t in sample_tracks), timedelta())
    return MusicServicePlaylist(
        service_name="spotify",
        tracks=sample_tracks,
        total_duration=total_duration
    )


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration file"""
    config_path = tmp_path / "test_config.yaml"
    mixdisc_dir = tmp_path / "mixdiscs"
    mixdisc_dir.mkdir()
    
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    
    config_content = f"""
mixdisc_directory: {mixdisc_dir}
playlist_duration_threshold_mins: 80
template_directory: {template_dir}
output_directory: {output_dir}
cache_file: {cache_dir / "playlists_cache.json"}
track_cache_file: {cache_dir / "tracks_cache.json"}
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def empty_cache():
    """Return empty cache structure"""
    return {
        'version': '1.0',
        'last_updated': '2024-01-01T00:00:00+00:00',
        'playlists': {}
    }


@pytest.fixture
def mock_spotify_search_result():
    """Return a mock Spotify search result"""
    return {
        'tracks': {
            'items': [
                {
                    'id': 'track123',
                    'name': 'Test Song',
                    'uri': 'spotify:track:track123',
                    'external_urls': {'spotify': 'https://open.spotify.com/track/track123'},
                    'duration_ms': 225000,  # 3:45
                    'artists': [{'name': 'Test Artist'}],
                    'album': {'name': 'Test Album'}
                }
            ]
        }
    }


@pytest.fixture
def mock_spotify_no_results():
    """Return a mock Spotify search with no results"""
    return {
        'tracks': {
            'items': []
        }
    }
