""" Unit tests for playlists.py """

import pytest
from pathlib import Path
import yaml

from mixdiscer.playlists import (
    Playlist,
    PlaylistValidationError,
    load_playlist,
    validate_username_format,
    validate_username_matches_folder,
    check_playlist_uniqueness,
    get_artist_title_album_from_entry,
    get_playlists,
    get_playlists_from_paths,
)


# Username validation tests
def test_validate_username_format_valid():
    """Test that valid usernames pass validation"""
    valid_usernames = ["User123", "test_user", "user-name", "ABC", "a1b2c3"]
    
    for username in valid_usernames:
        validate_username_format(username)  # Should not raise


def test_validate_username_format_too_short():
    """Test that usernames under 3 characters are rejected"""
    with pytest.raises(PlaylistValidationError, match="at least 3 characters"):
        validate_username_format("ab")


def test_validate_username_format_too_long():
    """Test that usernames over 30 characters are rejected"""
    with pytest.raises(PlaylistValidationError, match="at most 30 characters"):
        validate_username_format("a" * 31)


def test_validate_username_format_invalid_chars():
    """Test that usernames with spaces or special characters are rejected"""
    invalid_usernames = ["user name", "user@name", "user.name", "user!name", "user#name"]
    
    for username in invalid_usernames:
        with pytest.raises(PlaylistValidationError, match="can only contain"):
            validate_username_format(username)


def test_validate_username_format_hyphen_underscore():
    """Test that hyphens and underscores are allowed"""
    validate_username_format("user-name")
    validate_username_format("user_name")
    validate_username_format("user-name_123")


# Folder structure validation tests
def test_validate_username_matches_folder(tmp_path):
    """Test that matching username and folder passes"""
    base_dir = tmp_path / "mixdiscs"
    base_dir.mkdir()
    user_dir = base_dir / "TestUser"
    user_dir.mkdir()
    filepath = user_dir / "playlist.yaml"
    filepath.touch()
    
    validate_username_matches_folder(filepath, "TestUser", base_dir)


def test_validate_username_folder_mismatch(tmp_path):
    """Test that mismatched username and folder raises error"""
    base_dir = tmp_path / "mixdiscs"
    base_dir.mkdir()
    user_dir = base_dir / "TestUser"
    user_dir.mkdir()
    filepath = user_dir / "playlist.yaml"
    filepath.touch()
    
    with pytest.raises(PlaylistValidationError, match="does not match folder name"):
        validate_username_matches_folder(filepath, "DifferentUser", base_dir)


def test_validate_username_wrong_depth(tmp_path):
    """Test that wrong directory depth is rejected"""
    base_dir = tmp_path / "mixdiscs"
    base_dir.mkdir()
    filepath = base_dir / "playlist.yaml"  # Missing user folder
    filepath.touch()
    
    with pytest.raises(PlaylistValidationError, match="must be in format"):
        validate_username_matches_folder(filepath, "TestUser", base_dir)


def test_validate_username_nested_too_deep(tmp_path):
    """Test that nested structure too deep is rejected"""
    base_dir = tmp_path / "mixdiscs"
    base_dir.mkdir()
    user_dir = base_dir / "TestUser" / "subfolder"
    user_dir.mkdir(parents=True)
    filepath = user_dir / "playlist.yaml"
    filepath.touch()
    
    with pytest.raises(PlaylistValidationError, match="must be in format"):
        validate_username_matches_folder(filepath, "TestUser", base_dir)


# Track parsing tests
def test_get_artist_title_album_basic():
    """Test parsing basic 'Artist - Title' format"""
    artist, title, album = get_artist_title_album_from_entry("The Beatles - Hey Jude")
    
    assert artist == "The Beatles"
    assert title == "Hey Jude"
    assert album is None


def test_get_artist_title_album_with_album():
    """Test parsing 'Artist - Title | Album' format"""
    artist, title, album = get_artist_title_album_from_entry("Queen - Bohemian Rhapsody | A Night at the Opera")
    
    assert artist == "Queen"
    assert title == "Bohemian Rhapsody"
    assert album == "A Night at the Opera"


def test_get_artist_title_album_with_dash_in_title():
    """Test parsing when title contains dash"""
    artist, title, album = get_artist_title_album_from_entry("Artist - Title - With - Dashes")
    
    assert artist == "Artist"
    assert title == "Title - With - Dashes"
    assert album is None


def test_get_artist_title_album_invalid_format():
    """Test that invalid format raises error"""
    with pytest.raises(PlaylistValidationError, match="Invalid playlist entry format"):
        get_artist_title_album_from_entry("The Beatles Hey Jude")


def test_get_artist_title_album_blank_artist():
    """Test that blank artist is rejected"""
    with pytest.raises(PlaylistValidationError, match="Artist name cannot be blank"):
        get_artist_title_album_from_entry(" - Hey Jude")


def test_get_artist_title_album_blank_title():
    """Test that blank title is rejected"""
    with pytest.raises(PlaylistValidationError, match="Song title cannot be blank"):
        get_artist_title_album_from_entry("The Beatles - ")


def test_get_artist_title_album_blank_album():
    """Test that blank album specification is rejected"""
    with pytest.raises(PlaylistValidationError, match="Album cannot be blank"):
        get_artist_title_album_from_entry("The Beatles - Hey Jude | ")


def test_get_artist_title_album_pipe_without_spaces():
    """Test that pipe without spaces raises error"""
    with pytest.raises(PlaylistValidationError, match="with spaces"):
        get_artist_title_album_from_entry("The Beatles - Hey Jude|Album")


def test_get_artist_title_album_blank_entry():
    """Test that blank entry is rejected"""
    with pytest.raises(PlaylistValidationError, match="cannot be blank"):
        get_artist_title_album_from_entry("")


def test_get_artist_title_album_whitespace():
    """Test parsing with extra whitespace"""
    artist, title, album = get_artist_title_album_from_entry("  The Beatles  -  Hey Jude  ")
    
    assert artist == "The Beatles"
    assert title == "Hey Jude"
    assert album is None


# Uniqueness check tests
def test_check_playlist_uniqueness_no_duplicates():
    """Test that unique playlists pass"""
    playlists = [
        Playlist("User1", "Title1", "Desc", "Genre", [], None),
        Playlist("User1", "Title2", "Desc", "Genre", [], None),
        Playlist("User2", "Title1", "Desc", "Genre", [], None),
    ]
    
    duplicates = check_playlist_uniqueness(playlists)
    assert len(duplicates) == 0


def test_check_playlist_uniqueness_with_duplicates():
    """Test detection of duplicate user/title combinations"""
    playlist1 = Playlist("User1", "Title1", "Desc", "Genre", [], None)
    playlist2 = Playlist("User1", "Title1", "Different Desc", "Different Genre", [], None)
    playlists = [playlist1, playlist2]
    
    duplicates = check_playlist_uniqueness(playlists)
    
    assert len(duplicates) == 1
    assert duplicates[0] == (playlist1, playlist2)


def test_check_playlist_uniqueness_same_title_different_users():
    """Test that same title for different users is allowed"""
    playlists = [
        Playlist("User1", "Title1", "Desc", "Genre", [], None),
        Playlist("User2", "Title1", "Desc", "Genre", [], None),
    ]
    
    duplicates = check_playlist_uniqueness(playlists)
    assert len(duplicates) == 0


def test_check_playlist_uniqueness_multiple_duplicates():
    """Test detection of multiple duplicate sets"""
    p1 = Playlist("User1", "Title1", "Desc", "Genre", [], None)
    p2 = Playlist("User1", "Title1", "Desc", "Genre", [], None)
    p3 = Playlist("User2", "Title2", "Desc", "Genre", [], None)
    p4 = Playlist("User2", "Title2", "Desc", "Genre", [], None)
    
    playlists = [p1, p2, p3, p4]
    duplicates = check_playlist_uniqueness(playlists)
    
    assert len(duplicates) == 2


# Playlist loading tests
def test_load_playlist_valid(tmp_path):
    """Test loading a well-formed playlist"""
    base_dir = tmp_path / "mixdiscs"
    base_dir.mkdir()
    user_dir = base_dir / "TestUser"
    user_dir.mkdir()
    
    playlist_path = user_dir / "test.yaml"
    playlist_content = """
user: TestUser
title: Test Playlist
description: A test playlist
genre: Rock
playlist:
  - The Beatles - Hey Jude
  - Queen - Bohemian Rhapsody
"""
    playlist_path.write_text(playlist_content)
    
    playlist = load_playlist(playlist_path, base_dir)
    
    assert playlist.user == "TestUser"
    assert playlist.title == "Test Playlist"
    assert playlist.description == "A test playlist"
    assert playlist.genre == "Rock"
    assert len(playlist.tracks) == 2
    assert playlist.tracks[0] == ("The Beatles", "Hey Jude", None)
    assert playlist.filepath == playlist_path


def test_load_playlist_missing_required_fields(tmp_path):
    """Test that missing required fields raises error"""
    playlist_path = tmp_path / "TestUser" / "test.yaml"
    playlist_path.parent.mkdir(parents=True)
    
    # Missing 'title' field
    playlist_path.write_text("""
user: TestUser
description: A test playlist
genre: Rock
playlist:
  - The Beatles - Hey Jude
""")
    
    with pytest.raises(PlaylistValidationError, match="Missing required field"):
        load_playlist(playlist_path)


def test_load_playlist_blank_user(tmp_path):
    """Test that blank user field is rejected"""
    playlist_path = tmp_path / "TestUser" / "test.yaml"
    playlist_path.parent.mkdir(parents=True)
    
    playlist_path.write_text("""
user: 
title: Test
description: Test
genre: Rock
playlist:
  - Artist - Song
""")
    
    with pytest.raises(PlaylistValidationError, match="'user' cannot be blank"):
        load_playlist(playlist_path)


def test_load_playlist_blank_title(tmp_path):
    """Test that blank title is rejected"""
    playlist_path = tmp_path / "TestUser" / "test.yaml"
    playlist_path.parent.mkdir(parents=True)
    
    playlist_path.write_text("""
user: TestUser
title: 
description: Test
genre: Rock
playlist:
  - Artist - Song
""")
    
    with pytest.raises(PlaylistValidationError, match="'title' cannot be blank"):
        load_playlist(playlist_path)


def test_load_playlist_empty_tracks(tmp_path):
    """Test that empty playlist is rejected"""
    playlist_path = tmp_path / "TestUser" / "test.yaml"
    playlist_path.parent.mkdir(parents=True)
    
    playlist_path.write_text("""
user: TestUser
title: Test
description: Test
genre: Rock
playlist: []
""")
    
    with pytest.raises(PlaylistValidationError, match="Must specify either 'playlist' or 'remote_playlist'"):
        load_playlist(playlist_path)


def test_load_playlist_with_album_filter(tmp_path):
    """Test loading playlist with album specifications"""
    base_dir = tmp_path / "mixdiscs"
    base_dir.mkdir()
    user_dir = base_dir / "TestUser"
    user_dir.mkdir()
    
    playlist_path = user_dir / "test.yaml"
    playlist_path.write_text("""
user: TestUser
title: Test
description: Test
genre: Rock
playlist:
  - The Beatles - Hey Jude | Past Masters
  - Queen - Bohemian Rhapsody
""")
    
    playlist = load_playlist(playlist_path, base_dir)
    
    assert len(playlist.tracks) == 2
    assert playlist.tracks[0] == ("The Beatles", "Hey Jude", "Past Masters")
    assert playlist.tracks[1] == ("Queen", "Bohemian Rhapsody", None)


def test_load_playlist_invalid_yaml(tmp_path):
    """Test that invalid YAML raises error"""
    playlist_path = tmp_path / "test.yaml"
    playlist_path.write_text("{ invalid yaml: [")
    
    with pytest.raises(yaml.YAMLError):
        load_playlist(playlist_path)


# Generator tests
def test_get_playlists(temp_mixdisc_dir):
    """Test getting all playlists from directory"""
    # Create valid playlists
    user1_dir = temp_mixdisc_dir / "TestUser"
    user1_playlist = user1_dir / "playlist1.yaml"
    user1_playlist.write_text("""
user: TestUser
title: Playlist 1
description: Test
genre: Rock
playlist:
  - Artist - Song
""")
    
    user2_dir = temp_mixdisc_dir / "AnotherUser"
    user2_playlist = user2_dir / "playlist2.yaml"
    user2_playlist.write_text("""
user: AnotherUser
title: Playlist 2
description: Test
genre: Pop
playlist:
  - Artist - Song
""")
    
    playlists = list(get_playlists(str(temp_mixdisc_dir)))
    
    assert len(playlists) == 2
    assert any(p.user == "TestUser" for p in playlists)
    assert any(p.user == "AnotherUser" for p in playlists)


def test_get_playlists_skip_invalid(temp_mixdisc_dir):
    """Test that invalid playlists are skipped"""
    user_dir = temp_mixdisc_dir / "TestUser"
    
    # Valid playlist
    valid_playlist = user_dir / "valid.yaml"
    valid_playlist.write_text("""
user: TestUser
title: Valid
description: Test
genre: Rock
playlist:
  - Artist - Song
""")
    
    # Invalid playlist (missing fields)
    invalid_playlist = user_dir / "invalid.yaml"
    invalid_playlist.write_text("""
user: TestUser
title: Invalid
""")
    
    playlists = list(get_playlists(str(temp_mixdisc_dir)))
    
    # Should only return valid playlist
    assert len(playlists) == 1
    assert playlists[0].title == "Valid"


def test_get_playlists_from_paths(tmp_path):
    """Test loading playlists from specific paths"""
    base_dir = tmp_path / "mixdiscs"
    base_dir.mkdir()
    user_dir = base_dir / "TestUser"
    user_dir.mkdir()
    
    path1 = user_dir / "playlist1.yaml"
    path1.write_text("""
user: TestUser
title: Playlist 1
description: Test
genre: Rock
playlist:
  - Artist - Song
""")
    
    path2 = user_dir / "playlist2.yaml"
    path2.write_text("""
user: TestUser
title: Playlist 2
description: Test
genre: Pop
playlist:
  - Artist - Song
""")
    
    playlists = list(get_playlists_from_paths([path1, path2], base_dir))
    
    assert len(playlists) == 2


def test_get_playlists_missing_directory():
    """Test that missing directory raises error"""
    with pytest.raises(FileNotFoundError):
        list(get_playlists("/nonexistent/directory"))
