"""Tests for CLI validators"""

import pytest
from pathlib import Path

from mixdiscer.cli.validators import (
    validate_username,
    validate_title,
    validate_title_uniqueness,
    validate_spotify_url,
    sanitize_filename,
    validate_description,
    validate_genre,
)


class TestValidateUsername:
    """Test username validation"""
    
    def test_valid_usernames(self):
        """Test valid username formats"""
        valid_names = [
            "user123",
            "User_Name",
            "User-Name",
            "abc",
            "A1B",  # Changed from "A1" (too short)
            "user_123-test",
        ]
        for username in valid_names:
            is_valid, error = validate_username(username)
            assert is_valid, f"{username} should be valid, got: {error}"
            assert error is None
    
    def test_empty_username(self):
        """Test empty username"""
        is_valid, error = validate_username("")
        assert not is_valid
        assert "cannot be empty" in error.lower()
    
    def test_too_short(self):
        """Test username too short"""
        is_valid, error = validate_username("ab")
        assert not is_valid
        assert "at least 3" in error
    
    def test_too_long(self):
        """Test username too long"""
        is_valid, error = validate_username("a" * 31)
        assert not is_valid
        assert "at most 30" in error
    
    def test_invalid_characters(self):
        """Test invalid characters in username"""
        invalid_names = [
            "user name",  # space
            "user@name",  # special char
            "user.name",  # period
            "_username",  # starts with underscore
            "-username",  # starts with dash
        ]
        for username in invalid_names:
            is_valid, error = validate_username(username)
            assert not is_valid, f"{username} should be invalid"


class TestValidateTitle:
    """Test title validation"""
    
    def test_valid_titles(self):
        """Test valid titles"""
        valid_titles = [
            "My Playlist",
            "Summer Vibes 2024",
            "Rock & Roll",
            "A",
            "x" * 100,
        ]
        for title in valid_titles:
            is_valid, error = validate_title(title)
            assert is_valid, f"{title} should be valid, got: {error}"
    
    def test_empty_title(self):
        """Test empty title"""
        is_valid, error = validate_title("")
        assert not is_valid
        assert "cannot be empty" in error.lower()
    
    def test_whitespace_only(self):
        """Test whitespace-only title"""
        is_valid, error = validate_title("   ")
        assert not is_valid
    
    def test_too_long(self):
        """Test title too long"""
        is_valid, error = validate_title("x" * 101)
        assert not is_valid
        assert "at most 100" in error


class TestValidateTitleUniqueness:
    """Test title uniqueness validation"""
    
    def test_unique_title(self, tmp_path):
        """Test unique title for user"""
        user_dir = tmp_path / "TestUser"
        user_dir.mkdir()
        
        is_unique, error = validate_title_uniqueness("New Playlist", user_dir)
        assert is_unique
        assert error is None
    
    def test_duplicate_title(self, tmp_path):
        """Test duplicate title for user"""
        user_dir = tmp_path / "TestUser"
        user_dir.mkdir()
        
        # Create existing file
        (user_dir / "Existing Playlist.yaml").touch()
        
        is_unique, error = validate_title_uniqueness("Existing Playlist", user_dir)
        assert not is_unique
        assert "already have" in error
    
    def test_nonexistent_user_dir(self, tmp_path):
        """Test validation with non-existent user directory"""
        user_dir = tmp_path / "NonExistent"
        
        is_unique, error = validate_title_uniqueness("Any Title", user_dir)
        assert is_unique
        assert error is None


class TestValidateSpotifyURL:
    """Test Spotify URL validation"""
    
    def test_valid_urls(self):
        """Test valid Spotify URLs"""
        valid_urls = [
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
            "http://open.spotify.com/playlist/123abc",
            "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
        ]
        for url in valid_urls:
            is_valid, error = validate_spotify_url(url)
            assert is_valid, f"{url} should be valid, got: {error}"
    
    def test_empty_url(self):
        """Test empty URL"""
        is_valid, error = validate_spotify_url("")
        assert not is_valid
    
    def test_invalid_urls(self):
        """Test invalid URLs"""
        invalid_urls = [
            "https://google.com",
            "https://spotify.com/playlist/123",
            "not a url",
            "spotify:track:123",
        ]
        for url in invalid_urls:
            is_valid, error = validate_spotify_url(url)
            assert not is_valid, f"{url} should be invalid"


class TestSanitizeFilename:
    """Test filename sanitization"""
    
    def test_basic_sanitization(self):
        """Test basic filename sanitization"""
        assert sanitize_filename("Simple Name") == "Simple Name"
        assert sanitize_filename("  Spaces  ") == "Spaces"
    
    def test_special_characters(self):
        """Test removal of special characters"""
        assert sanitize_filename("Name/With\\Bad:Chars") == "Name-With-Bad-Chars"
        assert sanitize_filename("File*With?Bad\"Chars") == "File-With-Bad-Chars"
        assert sanitize_filename("Name<With>Pipes|") == "Name-With-Pipes-"
    
    def test_multiple_spaces_dashes(self):
        """Test collapsing multiple spaces and dashes"""
        assert sanitize_filename("Too   Many    Spaces") == "Too Many Spaces"
        assert sanitize_filename("Too---Many---Dashes") == "Too-Many-Dashes"


class TestValidateDescription:
    """Test description validation"""
    
    def test_valid_descriptions(self):
        """Test valid descriptions"""
        valid = ["Short desc", "A" * 500]
        for desc in valid:
            is_valid, error = validate_description(desc)
            assert is_valid
    
    def test_empty_description(self):
        """Test empty description"""
        is_valid, error = validate_description("")
        assert not is_valid
    
    def test_too_long(self):
        """Test description too long"""
        is_valid, error = validate_description("x" * 501)
        assert not is_valid
        assert "at most 500" in error


class TestValidateGenre:
    """Test genre validation"""
    
    def test_valid_genres(self):
        """Test valid genres"""
        valid = ["rock", "hip-hop", "Electronic Dance"]
        for genre in valid:
            is_valid, error = validate_genre(genre)
            assert is_valid, f"{genre} should be valid, got: {error}"
    
    def test_empty_genre(self):
        """Test empty genre"""
        is_valid, error = validate_genre("")
        assert not is_valid
    
    def test_invalid_characters(self):
        """Test invalid characters in genre"""
        is_valid, error = validate_genre("rock/pop")
        assert not is_valid
    
    def test_too_long(self):
        """Test genre too long"""
        is_valid, error = validate_genre("x" * 51)
        assert not is_valid
