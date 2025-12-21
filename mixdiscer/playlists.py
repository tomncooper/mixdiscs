""" Module for loading playlists from YAML files """
import logging

from pathlib import Path
from dataclasses import dataclass
from typing import List, Generator, Tuple, Optional
import re

import yaml

LOG = logging.getLogger(__name__)


class PlaylistValidationError(Exception):
    """ Exception raised when a playlist fails validation """
    pass


@dataclass
class Playlist:
    """ Dataclass representing a Playlist and its metadata"""
    user: str
    title: str
    description: str
    genre: str
    tracks: List[Tuple[str, str, Optional[str]]]  # (artist, title, album)
    filepath: Optional[Path] = None


def validate_username_format(username: str) -> None:
    """
    Validate that username follows format rules.
    
    Rules:
    - 3-30 characters
    - Alphanumeric, underscore, or hyphen only
    - No spaces
    
    Args:
        username: The username to validate
        
    Raises:
        PlaylistValidationError: If username format is invalid
    """
    if len(username) < 3:
        raise PlaylistValidationError(
            f"Invalid username '{username}': username must be at least 3 characters"
        )
    
    if len(username) > 30:
        raise PlaylistValidationError(
            f"Invalid username '{username}': username must be at most 30 characters"
        )
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        raise PlaylistValidationError(
            f"Invalid username '{username}': username can only contain letters, numbers, "
            f"underscores, and hyphens (no spaces or special characters)"
        )


def check_playlist_uniqueness(playlists: List[Playlist]) -> List[Tuple[Playlist, Playlist]]:
    """
    Check for duplicate username-playlist title combinations.
    
    Args:
        playlists: List of Playlist objects to check
        
    Returns:
        List of tuples of duplicate pairs (first occurrence, duplicate)
    """
    seen = {}  # key: (user, title) -> Playlist
    duplicates = []
    
    for playlist in playlists:
        key = (playlist.user, playlist.title)
        
        if key in seen:
            duplicates.append((seen[key], playlist))
        else:
            seen[key] = playlist
    
    return duplicates


def validate_username_matches_folder(filepath: Path, user: str, base_directory: Path) -> None:
    """
    Validate that the username in YAML matches the parent folder name.
    
    Expected structure: <base_directory>/<username>/<playlist>.yaml
    
    Args:
        filepath: Path to the playlist file
        user: Username from the YAML file
        base_directory: Base directory containing user folders (e.g., mixdiscs/)
        
    Raises:
        PlaylistValidationError: If structure is invalid or username doesn't match
    """
    try:
        # Get path relative to base directory
        relative_path = filepath.relative_to(base_directory)
        parts = relative_path.parts
        
        # Should be exactly 2 parts: username/playlist.yaml
        if len(parts) != 2:
            raise PlaylistValidationError(
                f"Playlist file must be in format: {base_directory.name}/<username>/<playlist>.yaml. "
                f"Found: {relative_path}"
            )
        
        folder_username = parts[0]
        
        # Check username matches folder (case-sensitive)
        if user != folder_username:
            raise PlaylistValidationError(
                f"Username '{user}' in YAML does not match folder name '{folder_username}'. "
                f"They must match exactly (case-sensitive)."
            )
            
    except ValueError:
        # filepath is not relative to base_directory
        raise PlaylistValidationError(
            f"Playlist file must be inside {base_directory}/<username>/ directory"
        )


def get_playlists(directory: str) -> Generator[Playlist]:
    """ Generator that yields all the playlists in a directory """

    LOG.debug("Loading playlists from directory: %s", directory)

    path = Path(directory)

    if not path.exists():
        LOG.error("Directory %s does not exist", directory)
        raise FileNotFoundError(f"Directory {directory} does not exist")

    for playlist_filepath in path.glob('*/*.yaml'):
        try:
            yield load_playlist(playlist_filepath, path)
        except (yaml.YAMLError, IOError, PlaylistValidationError) as e:
            LOG.error("Error loading playlist %s: %s", playlist_filepath, e)
            continue


def get_playlists_from_paths(filepaths: List[Path], base_directory: Optional[Path] = None) -> Generator[Playlist]:
    """ Generator that yields playlists from a list of file paths 
    
    Args:
        filepaths: List of paths to playlist files
        base_directory: Base directory for validation (e.g., mixdiscs/). 
                       If None, will try to infer from file paths.
    """

    LOG.debug("Loading playlists from %d file paths", len(filepaths))

    for filepath in filepaths:
        if not filepath.exists():
            LOG.error("File %s does not exist", filepath)
            continue

        if not filepath.suffix == '.yaml':
            LOG.warning("File %s is not a YAML file, skipping", filepath)
            continue

        # Infer base directory if not provided (assume parent's parent is base)
        inferred_base = base_directory
        if inferred_base is None and len(filepath.parts) >= 2:
            inferred_base = filepath.parent.parent

        try:
            yield load_playlist(filepath, inferred_base)
        except (yaml.YAMLError, IOError, KeyError, PlaylistValidationError) as e:
            LOG.error("Error loading playlist %s: %s", filepath, e)
            continue


def load_playlist(filepath: Path, base_directory: Optional[Path] = None) -> Playlist:
    """ Load a Playlist from a Playlist YAML file 
    
    Args:
        filepath: Path to the playlist YAML file
        base_directory: Base directory for structure validation (e.g., mixdiscs/)
                       If None, validation for folder structure is skipped.
    """

    LOG.debug("Loading playlist from %s", filepath)

    with open(filepath, 'r', encoding="utf8") as playlist_file:
        data = yaml.load(playlist_file, Loader=yaml.FullLoader)

    # Validate required fields exist
    required_fields = ['user', 'title', 'description', 'genre', 'playlist']
    for field in required_fields:
        if field not in data:
            raise PlaylistValidationError(f"Missing required field: {field}")
    
    # Validate fields are not blank
    if not data['user'] or not str(data['user']).strip():
        raise PlaylistValidationError("Field 'user' cannot be blank")
    
    if not data['title'] or not str(data['title']).strip():
        raise PlaylistValidationError("Field 'title' cannot be blank")
    
    if not data['description'] or not str(data['description']).strip():
        raise PlaylistValidationError("Field 'description' cannot be blank")
    
    if not data['genre'] or not str(data['genre']).strip():
        raise PlaylistValidationError("Field 'genre' cannot be blank")
    
    if not data['playlist'] or len(data['playlist']) == 0:
        raise PlaylistValidationError("Field 'playlist' cannot be blank or empty")

    user = data['user'].strip()
    
    # Validate username format
    validate_username_format(user)
    
    # Validate folder structure if base_directory is provided
    if base_directory is not None:
        validate_username_matches_folder(filepath, user, base_directory)

    return Playlist(
        user=user,
        title=data['title'].strip(),
        description=data['description'].strip(),
        genre=data['genre'].strip(),
        tracks=[get_artist_title_album_from_entry(entry) for entry in data['playlist']],
        filepath=filepath
    )


def get_artist_title_album_from_entry(entry: str) -> tuple[str, str, Optional[str]]:
    """ 
    Extract artist, title, and optional album from a playlist entry.
    
    Supports two formats:
    - "Artist - Title" (album is None)
    - "Artist - Title | Album" (album is specified)
    
    Args:
        entry: Playlist entry string
        
    Returns:
        Tuple of (artist, title, album)
        
    Raises:
        PlaylistValidationError: If format is invalid
    """
    if not entry or not entry.strip():
        raise PlaylistValidationError("Playlist entry cannot be blank")
    
    # Check for album specification (pipe separator)
    if ' | ' in entry:
        track_part, album = entry.split(' | ', 1)
        album = album.strip()
        if not album:
            raise PlaylistValidationError(
                f"Album cannot be blank in entry: '{entry}'"
            )
    elif '|' in entry:
        # Pipe without proper spacing - this is likely a mistake
        raise PlaylistValidationError(
            f"Invalid format: '{entry}'. Use ' | ' (with spaces) to separate album"
        )
    else:
        track_part = entry
        album = None
    
    # Parse artist and title
    if ' - ' not in track_part:
        raise PlaylistValidationError(
            f"Invalid playlist entry format: '{entry}'. "
            f"Expected 'Artist - Title' or 'Artist - Title | Album'"
        )
    
    artist, title = track_part.split(' - ', 1)  # Split only on first ' - ' occurrence
    
    if not artist.strip():
        raise PlaylistValidationError(f"Artist name cannot be blank in entry: '{entry}'")
    
    if not title.strip():
        raise PlaylistValidationError(f"Song title cannot be blank in entry: '{entry}'")
    
    return artist.strip(), title.strip(), album
