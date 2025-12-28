"""Unit tests for cache functionality with remote playlists"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mixdiscer.cache import (
    update_cache_entry,
    get_cache_key
)
from mixdiscer.playlists import Playlist
from mixdiscer.music_service import MusicServicePlaylist, Track


class TestCacheWithRemotePlaylists:
    """Test cache operations with remote playlists"""

    def test_update_cache_entry_with_remote_playlist(self, tmp_path):
        """Test updating cache entry for a remote playlist"""
        # Create remote playlist
        playlist_file = tmp_path / "test.yaml"
        playlist_file.write_text("test")
        
        playlist = Playlist(
            user="TestUser",
            title="Remote Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        # Create music service playlist
        tracks = [
            Track(
                artist="Artist One",
                title="Song One",
                album="Album One",
                duration=timedelta(minutes=3),
                link="https://spotify.com/track1"
            )
        ]
        
        music_service_playlist = MusicServicePlaylist(
            service_name="spotify",
            tracks=tracks,
            total_duration=timedelta(minutes=3)
        )
        
        # Update cache
        cache_data = {
            'version': '1.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'playlists': {}
        }
        
        cache_key = get_cache_key(playlist)
        snapshot_id = "snapshot_abc123"
        
        update_cache_entry(cache_key, playlist, music_service_playlist, cache_data, snapshot_id)
        
        # Verify cache entry
        entry = cache_data['playlists'][cache_key]
        assert entry['user'] == "TestUser"
        assert entry['title'] == "Remote Playlist"
        assert entry['remote_playlist_url'] == "https://open.spotify.com/playlist/test123"
        assert entry['remote_snapshot_id'] == "snapshot_abc123"
        assert entry['remote_validation_status'] == 'valid'
        assert entry['remote_frozen_at'] is None
        assert entry['remote_frozen_reason'] is None

    def test_update_cache_entry_with_manual_playlist(self, tmp_path):
        """Test that manual playlists don't have remote fields set"""
        playlist_file = tmp_path / "test.yaml"
        playlist_file.write_text("test")
        
        playlist = Playlist(
            user="TestUser",
            title="Manual Playlist",
            description="Test",
            genre="rock",
            tracks=[("Artist", "Song", None)],
            filepath=playlist_file
        )
        
        tracks = [
            Track(
                artist="Artist",
                title="Song",
                album="Album",
                duration=timedelta(minutes=3),
                link="https://spotify.com/track1"
            )
        ]
        
        music_service_playlist = MusicServicePlaylist(
            service_name="spotify",
            tracks=tracks,
            total_duration=timedelta(minutes=3)
        )
        
        cache_data = {
            'version': '1.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'playlists': {}
        }
        
        cache_key = get_cache_key(playlist)
        update_cache_entry(cache_key, playlist, music_service_playlist, cache_data)
        
        # Verify remote fields are None
        entry = cache_data['playlists'][cache_key]
        assert entry['remote_playlist_url'] is None
        assert entry['remote_snapshot_id'] is None
        assert entry['remote_validation_status'] is None
        assert entry['remote_frozen_at'] is None
        assert entry['remote_frozen_reason'] is None

    def test_update_cache_entry_with_snapshot_update(self, tmp_path):
        """Test updating snapshot_id for existing remote playlist"""
        playlist_file = tmp_path / "test.yaml"
        playlist_file.write_text("test")
        
        playlist = Playlist(
            user="TestUser",
            title="Remote Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        tracks = [
            Track(
                artist="Artist",
                title="Song",
                album="Album",
                duration=timedelta(minutes=3),
                link="https://spotify.com/track1"
            )
        ]
        
        music_service_playlist = MusicServicePlaylist(
            service_name="spotify",
            tracks=tracks,
            total_duration=timedelta(minutes=3)
        )
        
        # Create cache with old snapshot
        cache_data = {
            'version': '1.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'playlists': {}
        }
        
        cache_key = get_cache_key(playlist)
        
        # First update with old snapshot
        update_cache_entry(cache_key, playlist, music_service_playlist, cache_data, "old_snapshot")
        assert cache_data['playlists'][cache_key]['remote_snapshot_id'] == "old_snapshot"
        
        # Update with new snapshot
        update_cache_entry(cache_key, playlist, music_service_playlist, cache_data, "new_snapshot")
        assert cache_data['playlists'][cache_key]['remote_snapshot_id'] == "new_snapshot"

    def test_cache_entry_clears_remote_fields_when_switching_to_manual(self, tmp_path):
        """Test that converting from remote to manual clears remote fields"""
        playlist_file = tmp_path / "test.yaml"
        playlist_file.write_text("test")
        
        # Start with remote playlist
        remote_playlist = Playlist(
            user="TestUser",
            title="Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        tracks = [
            Track(
                artist="Artist",
                title="Song",
                album="Album",
                duration=timedelta(minutes=3),
                link="https://spotify.com/track1"
            )
        ]
        
        music_service_playlist = MusicServicePlaylist(
            service_name="spotify",
            tracks=tracks,
            total_duration=timedelta(minutes=3)
        )
        
        cache_data = {
            'version': '1.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'playlists': {}
        }
        
        cache_key = get_cache_key(remote_playlist)
        
        # Cache as remote
        update_cache_entry(cache_key, remote_playlist, music_service_playlist, cache_data, "snapshot123")
        assert cache_data['playlists'][cache_key]['remote_snapshot_id'] == "snapshot123"
        
        # Now convert to manual
        manual_playlist = Playlist(
            user="TestUser",
            title="Playlist",
            description="Test",
            genre="rock",
            tracks=[("Artist", "Song", None)],
            filepath=playlist_file
        )
        
        update_cache_entry(cache_key, manual_playlist, music_service_playlist, cache_data)
        
        # Remote fields should be cleared
        assert cache_data['playlists'][cache_key]['remote_playlist_url'] is None
        assert cache_data['playlists'][cache_key]['remote_snapshot_id'] is None


class TestFrozenPlaylistCache:
    """Test cache operations for frozen playlists"""

    def test_cache_frozen_playlist_metadata(self, tmp_path):
        """Test that frozen playlist metadata is stored correctly"""
        playlist_file = tmp_path / "test.yaml"
        playlist_file.write_text("test")
        
        playlist = Playlist(
            user="TestUser",
            title="Frozen Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        cache_data = {
            'version': '1.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'playlists': {}
        }
        
        cache_key = get_cache_key(playlist)
        
        # Manually simulate frozen state (would normally be set by check_remote_playlist_update)
        cache_data['playlists'][cache_key] = {
            'user': playlist.user,
            'title': playlist.title,
            'filepath': str(playlist.filepath),
            'content_hash': 'abc123',
            'remote_playlist_url': playlist.remote_playlist,
            'remote_snapshot_id': 'old_snapshot',
            'remote_validation_status': 'frozen',
            'remote_frozen_at': datetime.now(timezone.utc).isoformat(),
            'remote_frozen_reason': {
                'type': 'duration_exceeded',
                'current_duration': '85:00',
                'current_track_count': 25,
                'cached_track_count': 20,
                'limit': '80:00',
                'exceeded_by': '5:00',
                'last_checked': datetime.now(timezone.utc).isoformat()
            },
            'music_services': {},
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
        
        entry = cache_data['playlists'][cache_key]
        
        assert entry['remote_validation_status'] == 'frozen'
        assert entry['remote_frozen_at'] is not None
        assert entry['remote_frozen_reason'] is not None
        assert entry['remote_frozen_reason']['type'] == 'duration_exceeded'
        assert entry['remote_frozen_reason']['current_track_count'] == 25
        assert entry['remote_frozen_reason']['cached_track_count'] == 20

    def test_unfreezing_playlist_clears_frozen_metadata(self, tmp_path):
        """Test that unfreezing a playlist clears frozen metadata"""
        playlist_file = tmp_path / "test.yaml"
        playlist_file.write_text("test")
        
        playlist = Playlist(
            user="TestUser",
            title="Playlist",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/test123",
            filepath=playlist_file
        )
        
        tracks = [
            Track(
                artist="Artist",
                title="Song",
                album="Album",
                duration=timedelta(minutes=3),
                link="https://spotify.com/track1"
            )
        ]
        
        music_service_playlist = MusicServicePlaylist(
            service_name="spotify",
            tracks=tracks,
            total_duration=timedelta(minutes=3)
        )
        
        cache_data = {
            'version': '1.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'playlists': {}
        }
        
        cache_key = get_cache_key(playlist)
        
        # Start with frozen state
        cache_data['playlists'][cache_key] = {
            'user': playlist.user,
            'title': playlist.title,
            'filepath': str(playlist.filepath),
            'content_hash': 'abc123',
            'remote_playlist_url': playlist.remote_playlist,
            'remote_snapshot_id': 'old_snapshot',
            'remote_validation_status': 'frozen',
            'remote_frozen_at': datetime.now(timezone.utc).isoformat(),
            'remote_frozen_reason': {'type': 'duration_exceeded'},
            'music_services': {},
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Update with valid playlist (unfreeze)
        update_cache_entry(cache_key, playlist, music_service_playlist, cache_data, "new_snapshot")
        
        entry = cache_data['playlists'][cache_key]
        assert entry['remote_validation_status'] == 'valid'
        assert entry['remote_frozen_at'] is None
        assert entry['remote_frozen_reason'] is None
        assert entry['remote_snapshot_id'] == 'new_snapshot'
