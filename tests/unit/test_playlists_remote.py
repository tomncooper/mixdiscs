"""Unit tests for remote playlist loading functionality"""

import pytest
from pathlib import Path

from mixdiscer.playlists import (
    Playlist,
    load_playlist,
    PlaylistValidationError
)


class TestRemotePlaylistLoading:
    """Test loading playlists with remote_playlist field"""

    def test_load_remote_playlist_valid(self, tmp_path):
        """Test loading a valid remote playlist"""
        playlist_dir = tmp_path / "TestUser"
        playlist_dir.mkdir()
        
        playlist_file = playlist_dir / "remote_playlist.yaml"
        playlist_file.write_text("""
user: TestUser
title: My Remote Playlist
description: A playlist from Spotify
genre: electronic
remote_playlist: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
""")
        
        playlist = load_playlist(playlist_file, tmp_path)
        
        assert playlist.user == "TestUser"
        assert playlist.title == "My Remote Playlist"
        assert playlist.description == "A playlist from Spotify"
        assert playlist.genre == "electronic"
        assert playlist.remote_playlist == "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        assert playlist.remote_service == "spotify"
        assert playlist.tracks is None  # Remote playlists don't have manual tracks

    def test_load_remote_playlist_spotify_uri_format(self, tmp_path):
        """Test loading remote playlist with spotify:playlist: URI format"""
        playlist_dir = tmp_path / "TestUser"
        playlist_dir.mkdir()
        
        playlist_file = playlist_dir / "remote_playlist.yaml"
        playlist_file.write_text("""
user: TestUser
title: My Remote Playlist
description: A playlist from Spotify
genre: rock
remote_playlist: spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
""")
        
        playlist = load_playlist(playlist_file, tmp_path)
        
        assert playlist.remote_playlist == "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
        assert playlist.tracks is None

    def test_load_remote_playlist_with_query_params(self, tmp_path):
        """Test loading remote playlist with query parameters in URL"""
        playlist_dir = tmp_path / "TestUser"
        playlist_dir.mkdir()
        
        playlist_file = playlist_dir / "remote_playlist.yaml"
        playlist_file.write_text("""
user: TestUser
title: My Remote Playlist
description: A playlist from Spotify
genre: pop
remote_playlist: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=abc123
""")
        
        playlist = load_playlist(playlist_file, tmp_path)
        
        assert "open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M" in playlist.remote_playlist

    def test_load_manual_playlist_still_works(self, tmp_path):
        """Test that manual playlists still work as before"""
        playlist_dir = tmp_path / "TestUser"
        playlist_dir.mkdir()
        
        playlist_file = playlist_dir / "manual_playlist.yaml"
        playlist_file.write_text("""
user: TestUser
title: My Manual Playlist
description: A manually curated playlist
genre: rock
playlist:
  - Artist One - Song One
  - Artist Two - Song Two
""")
        
        playlist = load_playlist(playlist_file, tmp_path)
        
        assert playlist.user == "TestUser"
        assert playlist.title == "My Manual Playlist"
        assert playlist.remote_playlist is None
        assert playlist.tracks is not None
        assert len(playlist.tracks) == 2
        assert playlist.tracks[0] == ("Artist One", "Song One", None)


class TestRemotePlaylistValidation:
    """Test validation errors for remote playlists"""

    def test_both_playlist_and_remote_playlist_error(self, tmp_path):
        """Test that having both playlist and remote_playlist raises error"""
        playlist_dir = tmp_path / "TestUser"
        playlist_dir.mkdir()
        
        playlist_file = playlist_dir / "invalid_playlist.yaml"
        playlist_file.write_text("""
user: TestUser
title: Invalid Playlist
description: Has both formats
genre: rock
playlist:
  - Artist - Song
remote_playlist: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
""")
        
        with pytest.raises(PlaylistValidationError) as exc_info:
            load_playlist(playlist_file, tmp_path)
        
        assert "both 'playlist' and 'remote_playlist'" in str(exc_info.value).lower()

    def test_neither_playlist_nor_remote_playlist_error(self, tmp_path):
        """Test that having neither playlist nor remote_playlist raises error"""
        playlist_dir = tmp_path / "TestUser"
        playlist_dir.mkdir()
        
        playlist_file = playlist_dir / "invalid_playlist.yaml"
        playlist_file.write_text("""
user: TestUser
title: Invalid Playlist
description: Has neither format
genre: rock
""")
        
        with pytest.raises(PlaylistValidationError) as exc_info:
            load_playlist(playlist_file, tmp_path)
        
        assert "must specify either 'playlist' or 'remote_playlist'" in str(exc_info.value).lower()

    def test_invalid_spotify_url_format(self, tmp_path):
        """Test that invalid Spotify URL format raises error"""
        playlist_dir = tmp_path / "TestUser"
        playlist_dir.mkdir()
        
        playlist_file = playlist_dir / "invalid_playlist.yaml"
        playlist_file.write_text("""
user: TestUser
title: Invalid Playlist
description: Invalid URL
genre: rock
remote_playlist: https://example.com/not-a-spotify-url
""")
        
        with pytest.raises(PlaylistValidationError) as exc_info:
            load_playlist(playlist_file, tmp_path)
        
        assert "invalid spotify playlist url" in str(exc_info.value).lower()

    def test_empty_remote_playlist_field(self, tmp_path):
        """Test that empty remote_playlist field is treated as not having it"""
        playlist_dir = tmp_path / "TestUser"
        playlist_dir.mkdir()
        
        playlist_file = playlist_dir / "invalid_playlist.yaml"
        playlist_file.write_text("""
user: TestUser
title: Invalid Playlist
description: Empty remote field
genre: rock
remote_playlist:
""")
        
        with pytest.raises(PlaylistValidationError) as exc_info:
            load_playlist(playlist_file, tmp_path)
        
        # Should fail because neither playlist nor remote_playlist is provided
        assert "must specify either" in str(exc_info.value).lower()

    def test_blank_remote_playlist_url(self, tmp_path):
        """Test that blank remote_playlist URL raises error"""
        playlist_dir = tmp_path / "TestUser"
        playlist_dir.mkdir()
        
        playlist_file = playlist_dir / "invalid_playlist.yaml"
        playlist_file.write_text("""
user: TestUser
title: Invalid Playlist
description: Blank URL
genre: rock
remote_playlist: "   "
""")
        
        with pytest.raises(PlaylistValidationError) as exc_info:
            load_playlist(playlist_file, tmp_path)
        
        assert "invalid spotify playlist url" in str(exc_info.value).lower()


class TestRemotePlaylistDataclass:
    """Test Playlist dataclass with remote fields"""

    def test_create_remote_playlist_object(self):
        """Test creating a Playlist object with remote fields"""
        playlist = Playlist(
            user="TestUser",
            title="Test Remote",
            description="Test description",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/123",
            remote_service="spotify",
            filepath=Path("/tmp/test.yaml")
        )
        
        assert playlist.user == "TestUser"
        assert playlist.tracks is None
        assert playlist.remote_playlist == "https://open.spotify.com/playlist/123"
        assert playlist.remote_service == "spotify"

    def test_create_manual_playlist_object(self):
        """Test creating a manual Playlist object still works"""
        playlist = Playlist(
            user="TestUser",
            title="Test Manual",
            description="Test description",
            genre="rock",
            tracks=[("Artist", "Song", None)],
            filepath=Path("/tmp/test.yaml")
        )
        
        assert playlist.tracks is not None
        assert playlist.remote_playlist is None
        assert playlist.remote_service == "spotify"  # Default value

    def test_remote_service_defaults_to_spotify(self):
        """Test that remote_service defaults to 'spotify'"""
        playlist = Playlist(
            user="TestUser",
            title="Test",
            description="Test",
            genre="rock",
            tracks=None,
            remote_playlist="https://open.spotify.com/playlist/123"
        )
        
        assert playlist.remote_service == "spotify"
