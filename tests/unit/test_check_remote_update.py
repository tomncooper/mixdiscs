"""Unit tests for remote playlist update checking logic"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mixdiscer.main import check_remote_playlist_update, RemotePlaylistCheckResult
from mixdiscer.playlists import Playlist
from mixdiscer.music_service import MusicServicePlaylist, MusicServiceError, Track, ValidationWarning


class TestCheckRemotePlaylistUpdate:
    """Test check_remote_playlist_update function"""

    def test_unchanged_remote_playlist(self):
        """Test that unchanged snapshot returns cached playlist"""
        playlist_file = Path("/tmp/test.yaml")
        playlist = Playlist(
            user="TestUser",
            title="Remote Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        # Mock music service
        music_service = Mock()
        music_service.name = "spotify"
        music_service.get_playlist_snapshot = Mock(return_value="snapshot123")
        
        # Create cache entry with same snapshot
        cached_tracks = [
            Track(
                artist="Cached Artist",
                title="Cached Song",
                album="Cached Album",
                duration=timedelta(minutes=3),
                link="https://spotify.com/track"
            )
        ]
        
        cache_entry = {
            'user': 'TestUser',
            'title': 'Remote Playlist',
            'remote_playlist_url': 'https://open.spotify.com/playlist/test123',
            'remote_snapshot_id': 'snapshot123',  # Same snapshot
            'remote_validation_status': 'valid',
            'music_services': {
                'spotify': {
                    'tracks': [{
                        'artist': 'Cached Artist',
                        'title': 'Cached Song',
                        'album': 'Cached Album',
                        'duration_seconds': 180,
                        'link': 'https://spotify.com/track'
                    }],
                    'total_duration_seconds': 180,
                    'cached_at': datetime.now(timezone.utc).isoformat()
                }
            }
        }
        
        result = check_remote_playlist_update(
            playlist,
            music_service,
            cache_entry,
            timedelta(minutes=80)
        )
        
        assert result is not None
        assert isinstance(result, RemotePlaylistCheckResult)
        assert result.music_service_playlist is not None
        assert result.validation_warning is None
        assert result.should_update_cache is False
        assert len(result.music_service_playlist.tracks) == 1
        music_service.get_playlist_snapshot.assert_called_once()
        music_service.fetch_remote_playlist.assert_not_called()

    def test_changed_valid_remote_playlist(self):
        """Test that changed snapshot with valid duration fetches new tracks"""
        playlist_file = Path("/tmp/test.yaml")
        playlist = Playlist(
            user="TestUser",
            title="Remote Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        # Mock music service
        music_service = Mock()
        music_service.name = "spotify"
        music_service.get_playlist_snapshot = Mock(return_value="new_snapshot")
        
        new_tracks = [
            Track(
                artist="New Artist",
                title="New Song",
                album="New Album",
                duration=timedelta(minutes=3),
                link="https://spotify.com/new_track"
            )
        ]
        
        new_playlist = MusicServicePlaylist(
            service_name="spotify",
            tracks=new_tracks,
            total_duration=timedelta(minutes=3)
        )
        
        music_service.fetch_remote_playlist = Mock(return_value=new_playlist)
        
        cache_entry = {
            'user': 'TestUser',
            'title': 'Remote Playlist',
            'remote_playlist_url': 'https://open.spotify.com/playlist/test123',
            'remote_snapshot_id': 'old_snapshot',  # Different snapshot
            'remote_validation_status': 'valid',
            'music_services': {
                'spotify': {
                    'tracks': [],
                    'total_duration_seconds': 0,
                    'cached_at': datetime.now(timezone.utc).isoformat()
                }
            }
        }
        
        result = check_remote_playlist_update(
            playlist,
            music_service,
            cache_entry,
            timedelta(minutes=80)
        )
        
        assert result is not None
        assert isinstance(result, RemotePlaylistCheckResult)
        assert result.validation_warning is None
        assert result.should_update_cache is True
        assert result.music_service_playlist.total_duration == timedelta(minutes=3)
        assert result.cache_updates['remote_snapshot_id'] == 'new_snapshot'
        assert result.cache_updates['remote_validation_status'] == 'valid'
        music_service.fetch_remote_playlist.assert_called_once()

    def test_changed_exceeds_duration_freezes_playlist(self):
        """Test that exceeding duration freezes playlist at cached version"""
        playlist_file = Path("/tmp/test.yaml")
        playlist = Playlist(
            user="TestUser",
            title="Remote Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        # Mock music service
        music_service = Mock()
        music_service.name = "spotify"
        music_service.get_playlist_snapshot = Mock(return_value="new_snapshot")
        
        # New playlist exceeds duration
        new_tracks = [
            Track(
                artist=f"Artist {i}",
                title=f"Song {i}",
                album="Album",
                duration=timedelta(minutes=4),
                link=f"https://spotify.com/track{i}"
            )
            for i in range(25)  # 25 * 4 = 100 minutes
        ]
        
        new_playlist = MusicServicePlaylist(
            service_name="spotify",
            tracks=new_tracks,
            total_duration=timedelta(minutes=100)
        )
        
        music_service.fetch_remote_playlist = Mock(return_value=new_playlist)
        
        # Cached version is valid (20 tracks, 60 minutes)
        cached_tracks_data = [
            {
                'artist': f'Cached Artist {i}',
                'title': f'Cached Song {i}',
                'album': 'Album',
                'duration_seconds': 180,
                'link': f'https://spotify.com/cached{i}'
            }
            for i in range(20)
        ]
        
        cache_entry = {
            'user': 'TestUser',
            'title': 'Remote Playlist',
            'remote_playlist_url': 'https://open.spotify.com/playlist/test123',
            'remote_snapshot_id': 'old_snapshot',
            'remote_validation_status': 'valid',
            'music_services': {
                'spotify': {
                    'tracks': cached_tracks_data,
                    'total_duration_seconds': 3600,  # 60 minutes
                    'cached_at': '2024-12-01T10:00:00+00:00'
                }
            }
        }
        
        result = check_remote_playlist_update(
            playlist,
            music_service,
            cache_entry,
            timedelta(minutes=80)
        )
        
        # Should return cached playlist
        assert result is not None
        assert isinstance(result, RemotePlaylistCheckResult)
        assert len(result.music_service_playlist.tracks) == 20  # Cached version
        
        # Should have warning
        assert result.validation_warning is not None
        assert result.validation_warning.warning_type == 'duration_exceeded'
        assert 'exceeds the 80-minute limit' in result.validation_warning.message
        assert result.validation_warning.frozen_at is not None
        assert result.validation_warning.frozen_version_date is not None
        
        # Should update cache
        assert result.should_update_cache is True
        assert result.cache_updates['remote_validation_status'] == 'frozen'
        assert result.cache_updates['remote_frozen_at'] is not None
        assert result.cache_updates['remote_frozen_reason'] is not None
        assert result.cache_updates['remote_frozen_reason']['type'] == 'duration_exceeded'
        assert result.cache_updates['remote_frozen_reason']['current_track_count'] == 25
        assert result.cache_updates['remote_frozen_reason']['cached_track_count'] == 20
        
        # Snapshot should NOT be updated (keep checking)
        assert 'remote_snapshot_id' not in result.cache_updates

    def test_frozen_playlist_remains_frozen_with_same_snapshot(self):
        """Test that frozen playlist shows warning even with unchanged snapshot"""
        playlist_file = Path("/tmp/test.yaml")
        playlist = Playlist(
            user="TestUser",
            title="Frozen Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        music_service = Mock()
        music_service.name = "spotify"
        music_service.get_playlist_snapshot = Mock(return_value="old_snapshot")
        
        cache_entry = {
            'user': 'TestUser',
            'title': 'Frozen Playlist',
            'remote_playlist_url': 'https://open.spotify.com/playlist/test123',
            'remote_snapshot_id': 'old_snapshot',  # Same snapshot
            'remote_validation_status': 'frozen',
            'remote_frozen_at': '2024-12-20T10:00:00+00:00',
            'remote_frozen_reason': {
                'type': 'duration_exceeded',
                'current_duration': '85:00',
                'current_track_count': 25,
                'cached_track_count': 20,
                'limit': '80:00',
                'exceeded_by': '5:00',
                'last_checked': '2024-12-20T10:00:00+00:00'
            },
            'music_services': {
                'spotify': {
                    'tracks': [{
                        'artist': 'Artist',
                        'title': 'Song',
                        'album': 'Album',
                        'duration_seconds': 180,
                        'link': 'https://spotify.com/track'
                    }],
                    'total_duration_seconds': 180,
                    'cached_at': '2024-12-01T10:00:00+00:00'
                }
            }
        }
        
        result = check_remote_playlist_update(
            playlist,
            music_service,
            cache_entry,
            timedelta(minutes=80)
        )
        
        assert result is not None
        assert isinstance(result, RemotePlaylistCheckResult)
        assert result.validation_warning is not None
        assert result.validation_warning.warning_type == 'duration_exceeded'
        assert result.should_update_cache is False

    def test_error_getting_snapshot_raises_exception(self):
        """Test that errors getting snapshot raise MusicServiceError"""
        playlist_file = Path("/tmp/test.yaml")
        playlist = Playlist(
            user="TestUser",
            title="Remote Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        music_service = Mock()
        music_service.name = "spotify"
        music_service.get_playlist_snapshot = Mock(side_effect=Exception("API Error"))
        
        cache_entry = {
            'user': 'TestUser',
            'title': 'Remote Playlist',
            'remote_playlist_url': 'https://open.spotify.com/playlist/test123',
            'remote_snapshot_id': 'snapshot123',
            'remote_validation_status': 'valid',
            'music_services': {
                'spotify': {
                    'tracks': [{
                        'artist': 'Artist',
                        'title': 'Song',
                        'album': 'Album',
                        'duration_seconds': 180,
                        'link': 'https://spotify.com/track'
                    }],
                    'total_duration_seconds': 180,
                    'cached_at': datetime.now(timezone.utc).isoformat()
                }
            }
        }
        
        with pytest.raises(MusicServiceError) as exc_info:
            check_remote_playlist_update(
                playlist,
                music_service,
                cache_entry,
                timedelta(minutes=80)
            )
        
        assert "Failed to get snapshot" in str(exc_info.value)

    def test_error_fetching_updated_playlist_raises_exception(self):
        """Test that errors fetching updated playlist raise MusicServiceError"""
        playlist_file = Path("/tmp/test.yaml")
        playlist = Playlist(
            user="TestUser",
            title="Remote Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        music_service = Mock()
        music_service.name = "spotify"
        music_service.get_playlist_snapshot = Mock(return_value="new_snapshot")
        music_service.fetch_remote_playlist = Mock(side_effect=Exception("Fetch Error"))
        
        cache_entry = {
            'user': 'TestUser',
            'title': 'Remote Playlist',
            'remote_playlist_url': 'https://open.spotify.com/playlist/test123',
            'remote_snapshot_id': 'old_snapshot',
            'remote_validation_status': 'valid',
            'music_services': {
                'spotify': {
                    'tracks': [{
                        'artist': 'Artist',
                        'title': 'Song',
                        'album': 'Album',
                        'duration_seconds': 180,
                        'link': 'https://spotify.com/track'
                    }],
                    'total_duration_seconds': 180,
                    'cached_at': datetime.now(timezone.utc).isoformat()
                }
            }
        }
        
        with pytest.raises(MusicServiceError) as exc_info:
            check_remote_playlist_update(
                playlist,
                music_service,
                cache_entry,
                timedelta(minutes=80)
            )
        
        assert "Failed to fetch remote playlist" in str(exc_info.value)
