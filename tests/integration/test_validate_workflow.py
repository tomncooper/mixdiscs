""" Integration tests for playlist validation workflow """

import pytest
from pathlib import Path
from datetime import timedelta
from unittest.mock import Mock, patch

from mixdiscer.main import validate_playlists_from_files
from mixdiscer.playlists import Playlist
from mixdiscer.music_service import MusicServicePlaylist, Track


@pytest.mark.integration
def test_validate_workflow_end_to_end(tmp_path, test_config):
    """Test complete validation workflow from file to result"""
    
    # Create a test playlist file
    mixdisc_dir = tmp_path / "mixdiscs"
    user_dir = mixdisc_dir / "TestUser"
    user_dir.mkdir(parents=True)
    
    playlist_file = user_dir / "test_playlist.yaml"
    playlist_content = """
user: TestUser
title: Test Playlist
description: A test playlist for integration testing
genre: Rock
playlist:
  - The Beatles - Hey Jude
  - Queen - Bohemian Rhapsody
  - Led Zeppelin - Stairway to Heaven
"""
    playlist_file.write_text(playlist_content)
    
    # Mock the music service
    with patch('mixdiscer.main._get_music_service') as mock_get_service:
        mock_service = Mock()
        mock_service.name = "spotify"
        
        # Create mock response with reasonable durations
        mock_tracks = [
            Track("The Beatles", "Hey Jude", "Past Masters", timedelta(minutes=7, seconds=11), "link1"),
            Track("Queen", "Bohemian Rhapsody", "A Night at the Opera", timedelta(minutes=5, seconds=55), "link2"),
            Track("Led Zeppelin", "Stairway to Heaven", "Led Zeppelin IV", timedelta(minutes=8, seconds=2), "link3"),
        ]
        
        total_duration = sum((t.duration for t in mock_tracks), timedelta())
        
        mock_service_playlist = MusicServicePlaylist(
            service_name="spotify",
            tracks=mock_tracks,
            total_duration=total_duration
        )
        mock_service.process_user_playlist.return_value = mock_service_playlist
        mock_get_service.return_value = mock_service
        
        # Run validation
        results = validate_playlists_from_files(
            str(test_config),
            [playlist_file],
            update_cache=False
        )
        
        # Assertions
        assert len(results) == 1
        result = results[0]
        
        assert result.is_valid
        assert result.user == "TestUser"
        assert result.title == "Test Playlist"
        assert result.total_duration < timedelta(minutes=80)
        assert len(result.missing_tracks) == 0


@pytest.mark.integration
def test_validate_workflow_invalid_playlist(tmp_path, test_config):
    """Test validation workflow with invalid playlist"""
    
    # Create a playlist that exceeds duration
    mixdisc_dir = tmp_path / "mixdiscs"
    user_dir = mixdisc_dir / "TestUser"
    user_dir.mkdir(parents=True)
    
    playlist_file = user_dir / "long_playlist.yaml"
    playlist_content = """
user: TestUser
title: Long Playlist
description: This will be too long
genre: Progressive Rock
playlist:
  - Long Song 1 - Track 1
  - Long Song 2 - Track 2
  - Long Song 3 - Track 3
"""
    playlist_file.write_text(playlist_content)
    
    # Mock music service with long durations
    with patch('mixdiscer.main._get_music_service') as mock_get_service:
        mock_service = Mock()
        mock_service.name = "spotify"
        
        mock_tracks = [
            Track("Artist", "Track 1", "Album", timedelta(minutes=30), "link1"),
            Track("Artist", "Track 2", "Album", timedelta(minutes=30), "link2"),
            Track("Artist", "Track 3", "Album", timedelta(minutes=30), "link3"),
        ]
        
        total_duration = sum((t.duration for t in mock_tracks), timedelta())
        
        mock_service_playlist = MusicServicePlaylist(
            service_name="spotify",
            tracks=mock_tracks,
            total_duration=total_duration
        )
        mock_service.process_user_playlist.return_value = mock_service_playlist
        mock_get_service.return_value = mock_service
        
        # Run validation
        results = validate_playlists_from_files(
            str(test_config),
            [playlist_file],
            update_cache=False
        )
        
        # Assertions
        assert len(results) == 1
        result = results[0]
        
        assert not result.is_valid
        assert result.duration_exceeded
        assert result.total_duration == timedelta(minutes=90)


@pytest.mark.integration
def test_validate_workflow_duplicate_detection(tmp_path, test_config):
    """Test that duplicate playlists are detected"""
    
    mixdisc_dir = tmp_path / "mixdiscs"
    user_dir = mixdisc_dir / "TestUser"
    user_dir.mkdir(parents=True)
    
    # Create original playlist
    original_file = user_dir / "original.yaml"
    original_content = """
user: TestUser
title: My Playlist
description: Original
genre: Rock
playlist:
  - Artist - Song
"""
    original_file.write_text(original_content)
    
    # Create duplicate with same user/title
    duplicate_file = user_dir / "duplicate.yaml"
    duplicate_content = """
user: TestUser
title: My Playlist
description: Duplicate with same title
genre: Pop
playlist:
  - Different Artist - Different Song
"""
    duplicate_file.write_text(duplicate_content)
    
    # Mock music service
    with patch('mixdiscer.main._get_music_service') as mock_get_service:
        mock_service = Mock()
        mock_service.name = "spotify"
        mock_get_service.return_value = mock_service
        
        # Validate only the duplicate file (original already exists)
        results = validate_playlists_from_files(
            str(test_config),
            [duplicate_file],
            update_cache=False
        )
        
        assert len(results) == 1
        result = results[0]
        
        assert not result.is_valid
        assert result.duplicate_of == original_file


@pytest.mark.integration
def test_validate_workflow_with_missing_tracks(tmp_path, test_config):
    """Test validation when some tracks cannot be found"""
    
    mixdisc_dir = tmp_path / "mixdiscs"
    user_dir = mixdisc_dir / "TestUser"
    user_dir.mkdir(parents=True)
    
    playlist_file = user_dir / "playlist_with_missing.yaml"
    playlist_content = """
user: TestUser
title: Playlist With Missing Tracks
description: Some tracks won't be found
genre: Electronic
playlist:
  - The Beatles - Hey Jude
  - Nonexistent Artist - Fake Song
  - Queen - Bohemian Rhapsody
"""
    playlist_file.write_text(playlist_content)
    
    # Mock music service
    with patch('mixdiscer.main._get_music_service') as mock_get_service:
        mock_service = Mock()
        mock_service.name = "spotify"
        
        # Second track is None (not found)
        mock_tracks = [
            Track("The Beatles", "Hey Jude", "Album", timedelta(minutes=7), "link1"),
            None,  # Missing track
            Track("Queen", "Bohemian Rhapsody", "Album", timedelta(minutes=6), "link3"),
        ]
        
        total_duration = timedelta(minutes=13)  # Only found tracks
        
        mock_service_playlist = MusicServicePlaylist(
            service_name="spotify",
            tracks=mock_tracks,
            total_duration=total_duration
        )
        mock_service.process_user_playlist.return_value = mock_service_playlist
        mock_get_service.return_value = mock_service
        
        # Run validation
        results = validate_playlists_from_files(
            str(test_config),
            [playlist_file],
            update_cache=False
        )
        
        assert len(results) == 1
        result = results[0]
        
        # Should still be valid if under duration
        assert result.is_valid
        assert len(result.missing_tracks) == 1
        # missing_tracks is a list of tuples (artist, title, album)
        assert result.missing_tracks[0] == ("Nonexistent Artist", "Fake Song", None)
