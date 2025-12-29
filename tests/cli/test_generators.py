"""Tests for YAML generators"""

from mixdiscer.cli.generators import (
    generate_manual_yaml,
    generate_remote_yaml,
    generate_yaml,
)


class TestGenerateManualYAML:
    """Test manual playlist YAML generation"""
    
    def test_basic_generation(self):
        """Test basic manual playlist generation"""
        yaml = generate_manual_yaml(
            user="TestUser",
            title="Test Playlist",
            description="A test playlist",
            genre="rock",
            num_tracks=3
        )
        
        assert "user: TestUser" in yaml
        assert "title: Test Playlist" in yaml
        assert "description: A test playlist" in yaml
        assert "genre: rock" in yaml
        assert "playlist:" in yaml
        assert "Artist Name 1 - Song Title 1" in yaml
        assert "Artist Name 3 - Song Title 3" in yaml
    
    def test_default_track_count(self):
        """Test default number of tracks"""
        yaml = generate_manual_yaml(
            user="User",
            title="Title",
            description="Desc",
            genre="pop"
        )
        
        # Count track placeholders
        track_count = yaml.count("Artist Name")
        assert track_count == 10


class TestGenerateRemoteYAML:
    """Test remote playlist YAML generation"""
    
    def test_basic_generation(self):
        """Test basic remote playlist generation"""
        yaml = generate_remote_yaml(
            user="TestUser",
            title="Test Playlist",
            description="A test playlist",
            genre="rock",
            spotify_url="https://open.spotify.com/playlist/123"
        )
        
        assert "user: TestUser" in yaml
        assert "title: Test Playlist" in yaml
        assert "description: A test playlist" in yaml
        assert "genre: rock" in yaml
        assert "remote_playlist: https://open.spotify.com/playlist/123" in yaml
        assert "\nplaylist:" not in yaml  # Check for "\nplaylist:" specifically


class TestGenerateYAML:
    """Test unified YAML generation function"""
    
    def test_manual_type(self):
        """Test generating manual playlist"""
        yaml = generate_yaml(
            user="User",
            title="Title",
            description="Desc",
            genre="pop",
            playlist_type="manual",
            num_tracks=5
        )
        
        assert "playlist:" in yaml
        assert yaml.count("Artist Name") == 5
    
    def test_remote_type(self):
        """Test generating remote playlist"""
        yaml = generate_yaml(
            user="User",
            title="Title",
            description="Desc",
            genre="pop",
            playlist_type="remote",
            spotify_url="https://open.spotify.com/playlist/123"
        )
        
        assert "remote_playlist:" in yaml
        assert "\nplaylist:" not in yaml  # Check for "\nplaylist:" specifically
    
    def test_invalid_type(self):
        """Test invalid playlist type"""
        try:
            generate_yaml(
                user="User",
                title="Title",
                description="Desc",
                genre="pop",
                playlist_type="invalid"
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid playlist type" in str(e)
    
    def test_remote_missing_url(self):
        """Test remote type without URL"""
        try:
            generate_yaml(
                user="User",
                title="Title",
                description="Desc",
                genre="pop",
                playlist_type="remote"
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "spotify_url required" in str(e)
