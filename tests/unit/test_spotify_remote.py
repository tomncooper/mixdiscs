"""Unit tests for Spotify remote playlist functionality"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta

from mixdiscer.music_service.spotify import SpotifyMusicService, SpotifyTrack
from mixdiscer.music_service import MusicServiceError


@pytest.fixture
def mock_spotify_service():
    """Create a mocked SpotifyMusicService without requiring credentials"""
    with patch.dict(os.environ, {
        'SPOTIPY_CLIENT_ID': 'test_client_id',
        'SPOTIPY_CLIENT_SECRET': 'test_client_secret'
    }):
        service = SpotifyMusicService()
        # Mock the spotify client to avoid actual API calls
        service.spotify = Mock()
        return service


class TestExtractPlaylistId:
    """Test extracting playlist ID from various Spotify URL formats"""

    def test_extract_from_web_url(self, mock_spotify_service):
        """Test extracting ID from standard web URL"""
        url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        
        playlist_id = mock_spotify_service.extract_playlist_id(url)
        
        assert playlist_id == "37i9dQZF1DXcBWIGoYBM5M"

    def test_extract_from_web_url_with_query_params(self, mock_spotify_service):
        """Test extracting ID from URL with query parameters"""
        url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=abc123def456"
        
        playlist_id = mock_spotify_service.extract_playlist_id(url)
        
        assert playlist_id == "37i9dQZF1DXcBWIGoYBM5M"

    def test_extract_from_spotify_uri(self, mock_spotify_service):
        """Test extracting ID from Spotify URI format"""
        uri = "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
        
        playlist_id = mock_spotify_service.extract_playlist_id(uri)
        
        assert playlist_id == "37i9dQZF1DXcBWIGoYBM5M"

    def test_extract_from_invalid_url_raises_error(self, mock_spotify_service):
        """Test that invalid URL format raises ValueError"""
        invalid_url = "https://example.com/not-a-spotify-url"
        
        with pytest.raises(ValueError) as exc_info:
            mock_spotify_service.extract_playlist_id(invalid_url)
        
        assert "Invalid Spotify playlist" in str(exc_info.value)

    def test_extract_from_empty_string_raises_error(self, mock_spotify_service):
        """Test that empty string raises ValueError"""
        with pytest.raises(ValueError):
            mock_spotify_service.extract_playlist_id("")


class TestGetPlaylistSnapshot:
    """Test getting playlist snapshot ID"""

    def test_get_snapshot_success(self, mock_spotify_service):
        """Test successfully getting snapshot ID"""
        with patch.object(mock_spotify_service, 'extract_playlist_id', return_value='test_playlist_id'):
            mock_spotify_service.spotify.playlist = Mock(return_value={'snapshot_id': 'snapshot123'})
            
            snapshot_id = mock_spotify_service.get_playlist_snapshot("https://open.spotify.com/playlist/test")
            
            assert snapshot_id == 'snapshot123'
            mock_spotify_service.spotify.playlist.assert_called_once_with('test_playlist_id', fields='snapshot_id')

    def test_get_snapshot_error_raises_music_service_error(self, mock_spotify_service):
        """Test that errors are wrapped in MusicServiceError"""
        with patch.object(mock_spotify_service, 'extract_playlist_id', return_value='test_playlist_id'):
            mock_spotify_service.spotify.playlist = Mock(side_effect=Exception("API Error"))
            
            with pytest.raises(MusicServiceError) as exc_info:
                mock_spotify_service.get_playlist_snapshot("https://open.spotify.com/playlist/test")
            
            assert "Failed to get snapshot" in str(exc_info.value)
            assert exc_info.value.service_name == "spotify"


class TestFetchRemotePlaylist:
    """Test fetching tracks from remote Spotify playlist"""

    def test_fetch_small_playlist(self, mock_spotify_service):
        """Test fetching a playlist with less than 100 tracks"""
        with patch.object(mock_spotify_service, 'extract_playlist_id', return_value='test_playlist_id'):
            mock_spotify_service.spotify.playlist = Mock(return_value={
                'name': 'Test Playlist',
                'snapshot_id': 'snapshot123',
                'tracks': {'total': 3}
            })
            
            mock_spotify_service.spotify.playlist_items = Mock(return_value={
                'items': [
                    {
                        'track': {
                            'id': 'track1',
                            'name': 'Song One',
                            'uri': 'spotify:track:track1',
                            'duration_ms': 180000,
                            'artists': [{'name': 'Artist One'}],
                            'album': {'name': 'Album One'},
                            'external_urls': {'spotify': 'https://open.spotify.com/track/track1'}
                        }
                    },
                    {
                        'track': {
                            'id': 'track2',
                            'name': 'Song Two',
                            'uri': 'spotify:track:track2',
                            'duration_ms': 240000,
                            'artists': [{'name': 'Artist Two'}],
                            'album': {'name': 'Album Two'},
                            'external_urls': {'spotify': 'https://open.spotify.com/track/track2'}
                        }
                    }
                ],
                'next': None
            })
            
            result = mock_spotify_service.fetch_remote_playlist("https://open.spotify.com/playlist/test")
            
            assert result.service_name == "spotify"
            assert len(result.tracks) == 2
            assert result.tracks[0].title == "Song One"
            assert result.total_duration == timedelta(minutes=7)


class TestProcessUserPlaylistWithRemote:
    """Test process_user_playlist with remote playlists"""

    def test_process_remote_playlist(self, mock_spotify_service):
        """Test that remote playlists use fetch_remote_playlist"""
        from mixdiscer.playlists import Playlist
        from mixdiscer.music_service import MusicServicePlaylist
        from pathlib import Path
        
        remote_playlist = Playlist(
            user="TestUser",
            title="Remote Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=Path("/tmp/test.yaml")
        )
        
        mock_result = MusicServicePlaylist(
            service_name="spotify",
            tracks=[],
            total_duration=timedelta(minutes=30)
        )
        
        with patch.object(mock_spotify_service, 'fetch_remote_playlist', return_value=mock_result) as mock_fetch:
            result = mock_spotify_service.process_user_playlist(remote_playlist)
            
            mock_fetch.assert_called_once_with("https://open.spotify.com/playlist/test123")
            assert result == mock_result

    def test_process_manual_playlist_still_works(self, mock_spotify_service):
        """Test that manual playlists still use the original logic"""
        from mixdiscer.playlists import Playlist
        from pathlib import Path
        
        manual_playlist = Playlist(
            user="TestUser",
            title="Manual Playlist",
            description="Test",
            genre="rock",
            tracks=[("Artist", "Song", None)],
            filepath=Path("/tmp/test.yaml")
        )
        
        mock_spotify_service.spotify.search = Mock(return_value={
            'tracks': {
                'total': 1,
                'items': [{
                    'id': 'track1',
                    'name': 'Song',
                    'uri': 'spotify:track:track1',
                    'duration_ms': 180000,
                    'artists': [{'name': 'Artist'}],
                    'album': {'name': 'Album'},
                    'external_urls': {'spotify': 'https://open.spotify.com/track/track1'}
                }]
            }
        })
        
        result = mock_spotify_service.process_user_playlist(manual_playlist)
        
        assert result.service_name == "spotify"
        assert len(result.tracks) == 1
        mock_spotify_service.spotify.search.assert_called_once()
