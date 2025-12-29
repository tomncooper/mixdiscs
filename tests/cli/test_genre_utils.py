"""Tests for genre utilities"""

import pytest
from pathlib import Path

from mixdiscer.cli.genre_utils import (
    get_genres_from_playlists,
    get_suggested_genres,
)


class TestGetGenresFromPlaylists:
    """Test extracting genres from playlist files"""
    
    def test_empty_directory(self, tmp_path):
        """Test with no playlists"""
        genres = get_genres_from_playlists(tmp_path)
        assert genres == {}
    
    def test_single_playlist(self, tmp_path):
        """Test with one playlist"""
        user_dir = tmp_path / "TestUser"
        user_dir.mkdir()
        
        (user_dir / "playlist1.yaml").write_text(
            "user: TestUser\ntitle: Test\ngenre: rock\n"
        )
        
        genres = get_genres_from_playlists(tmp_path)
        assert genres == {"rock": 1}
    
    def test_multiple_playlists_same_genre(self, tmp_path):
        """Test multiple playlists with same genre"""
        user_dir = tmp_path / "TestUser"
        user_dir.mkdir()
        
        (user_dir / "playlist1.yaml").write_text(
            "user: TestUser\ntitle: Test1\ngenre: rock\n"
        )
        (user_dir / "playlist2.yaml").write_text(
            "user: TestUser\ntitle: Test2\ngenre: rock\n"
        )
        
        genres = get_genres_from_playlists(tmp_path)
        assert genres == {"rock": 2}
    
    def test_multiple_genres(self, tmp_path):
        """Test multiple different genres"""
        user_dir = tmp_path / "TestUser"
        user_dir.mkdir()
        
        (user_dir / "playlist1.yaml").write_text(
            "user: TestUser\ntitle: Test1\ngenre: rock\n"
        )
        (user_dir / "playlist2.yaml").write_text(
            "user: TestUser\ntitle: Test2\ngenre: jazz\n"
        )
        (user_dir / "playlist3.yaml").write_text(
            "user: TestUser\ntitle: Test3\ngenre: rock\n"
        )
        
        genres = get_genres_from_playlists(tmp_path)
        assert genres == {"rock": 2, "jazz": 1}
    
    def test_case_insensitive(self, tmp_path):
        """Test that genres are normalized to lowercase"""
        user_dir = tmp_path / "TestUser"
        user_dir.mkdir()
        
        (user_dir / "playlist1.yaml").write_text(
            "genre: Rock\n"
        )
        (user_dir / "playlist2.yaml").write_text(
            "genre: ROCK\n"
        )
        (user_dir / "playlist3.yaml").write_text(
            "genre: rock\n"
        )
        
        genres = get_genres_from_playlists(tmp_path)
        assert genres == {"rock": 3}
    
    def test_whitespace_trimmed(self, tmp_path):
        """Test that whitespace is trimmed"""
        user_dir = tmp_path / "TestUser"
        user_dir.mkdir()
        
        (user_dir / "playlist.yaml").write_text(
            "genre:   rock  \n"
        )
        
        genres = get_genres_from_playlists(tmp_path)
        assert genres == {"rock": 1}
    
    def test_nested_directories(self, tmp_path):
        """Test scanning nested user directories"""
        user1_dir = tmp_path / "User1"
        user1_dir.mkdir()
        user2_dir = tmp_path / "User2"
        user2_dir.mkdir()
        
        (user1_dir / "playlist1.yaml").write_text("genre: rock\n")
        (user2_dir / "playlist2.yaml").write_text("genre: jazz\n")
        
        genres = get_genres_from_playlists(tmp_path)
        assert genres == {"rock": 1, "jazz": 1}
    
    def test_invalid_yaml_skipped(self, tmp_path):
        """Test that invalid YAML files are skipped"""
        user_dir = tmp_path / "TestUser"
        user_dir.mkdir()
        
        # Valid file
        (user_dir / "valid.yaml").write_text("genre: rock\n")
        
        # Invalid YAML
        (user_dir / "invalid.yaml").write_text("}{invalid yaml][")
        
        genres = get_genres_from_playlists(tmp_path)
        assert genres == {"rock": 1}
    
    def test_missing_genre_field_skipped(self, tmp_path):
        """Test that files without genre field are skipped"""
        user_dir = tmp_path / "TestUser"
        user_dir.mkdir()
        
        (user_dir / "no_genre.yaml").write_text(
            "user: TestUser\ntitle: Test\n"
        )
        (user_dir / "has_genre.yaml").write_text(
            "genre: rock\n"
        )
        
        genres = get_genres_from_playlists(tmp_path)
        assert genres == {"rock": 1}


class TestGetSuggestedGenres:
    """Test getting suggested genres"""
    
    def test_empty_config_no_playlists(self):
        """Test with no config and no playlists"""
        genres, metadata = get_suggested_genres({})
        assert genres == []
        assert metadata == {}
    
    def test_config_genres_only(self):
        """Test with only config genres"""
        config = {"suggested_genres": ["rock", "pop", "jazz"]}
        genres, metadata = get_suggested_genres(config)
        
        assert genres == ["jazz", "pop", "rock"]  # Alphabetical
        assert all(metadata[g] == "Suggested genre" for g in genres)
    
    def test_playlist_genres_only(self, tmp_path):
        """Test with only playlist genres"""
        user_dir = tmp_path / "User"
        user_dir.mkdir()
        
        (user_dir / "p1.yaml").write_text("genre: rock\n")
        (user_dir / "p2.yaml").write_text("genre: rock\n")
        (user_dir / "p3.yaml").write_text("genre: jazz\n")
        
        genres, metadata = get_suggested_genres({}, tmp_path)
        
        # Rock first (2 uses), then jazz (1 use)
        assert genres == ["rock", "jazz"]
        assert metadata["rock"] == "Used in 2 playlists"
        assert metadata["jazz"] == "Used in 1 playlist"
    
    def test_combined_genres(self, tmp_path):
        """Test combining config and playlist genres"""
        user_dir = tmp_path / "User"
        user_dir.mkdir()
        
        (user_dir / "p1.yaml").write_text("genre: electronic\n")
        (user_dir / "p2.yaml").write_text("genre: electronic\n")
        
        config = {"suggested_genres": ["rock", "pop", "electronic"]}
        genres, metadata = get_suggested_genres(config, tmp_path)
        
        # Electronic first (2 uses), then pop, rock (unused, alphabetical)
        assert genres == ["electronic", "pop", "rock"]
        assert metadata["electronic"] == "Used in 2 playlists"
        assert metadata["pop"] == "Suggested genre"
        assert metadata["rock"] == "Suggested genre"
    
    def test_sort_by_usage_count(self, tmp_path):
        """Test that genres are sorted by usage count"""
        user_dir = tmp_path / "User"
        user_dir.mkdir()
        
        # rock: 3, jazz: 2, pop: 1
        (user_dir / "p1.yaml").write_text("genre: rock\n")
        (user_dir / "p2.yaml").write_text("genre: rock\n")
        (user_dir / "p3.yaml").write_text("genre: rock\n")
        (user_dir / "p4.yaml").write_text("genre: jazz\n")
        (user_dir / "p5.yaml").write_text("genre: jazz\n")
        (user_dir / "p6.yaml").write_text("genre: pop\n")
        
        genres, metadata = get_suggested_genres({}, tmp_path)
        
        assert genres == ["rock", "jazz", "pop"]
        assert metadata["rock"] == "Used in 3 playlists"
        assert metadata["jazz"] == "Used in 2 playlists"
        assert metadata["pop"] == "Used in 1 playlist"
    
    def test_no_duplicates(self, tmp_path):
        """Test that genres appear only once"""
        user_dir = tmp_path / "User"
        user_dir.mkdir()
        
        (user_dir / "p1.yaml").write_text("genre: rock\n")
        
        config = {"suggested_genres": ["rock", "pop"]}
        genres, metadata = get_suggested_genres(config, tmp_path)
        
        # Rock should appear once (from playlist, not config)
        assert genres == ["rock", "pop"]
        assert metadata["rock"] == "Used in 1 playlist"
        assert metadata["pop"] == "Suggested genre"
    
    def test_case_normalization(self, tmp_path):
        """Test that case is normalized"""
        user_dir = tmp_path / "User"
        user_dir.mkdir()
        
        (user_dir / "p1.yaml").write_text("genre: Rock\n")
        
        config = {"suggested_genres": ["POP", "Jazz"]}
        genres, metadata = get_suggested_genres(config, tmp_path)
        
        # All lowercase
        assert genres == ["rock", "jazz", "pop"]
    
    def test_alphabetical_within_same_usage(self, tmp_path):
        """Test alphabetical sorting for genres with same usage count"""
        user_dir = tmp_path / "User"
        user_dir.mkdir()
        
        # All have 1 use
        (user_dir / "p1.yaml").write_text("genre: jazz\n")
        (user_dir / "p2.yaml").write_text("genre: rock\n")
        (user_dir / "p3.yaml").write_text("genre: blues\n")
        
        genres, metadata = get_suggested_genres({}, tmp_path)
        
        # Alphabetical when same count
        assert genres == ["blues", "jazz", "rock"]
    
    def test_nonexistent_directory(self, tmp_path):
        """Test with non-existent playlist directory"""
        nonexistent = tmp_path / "does_not_exist"
        config = {"suggested_genres": ["rock"]}
        
        genres, metadata = get_suggested_genres(config, nonexistent)
        
        assert genres == ["rock"]
        assert metadata["rock"] == "Suggested genre"
