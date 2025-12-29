"""Validation functions for CLI inputs"""

import re
from pathlib import Path
from typing import Optional


def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """
    Validate username format.
    
    Rules:
    - 3-30 characters
    - Alphanumeric, underscores, and hyphens only
    - Must start with alphanumeric
    
    Returns:
        (is_valid, error_message)
    """
    if not username:
        return False, "Username cannot be empty"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 30:
        return False, "Username must be at most 30 characters"
    
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", username):
        return (
            False,
            "Username must start with a letter or number and contain only "
            "alphanumeric characters, underscores, and hyphens"
        )
    
    return True, None


def validate_title(title: str) -> tuple[bool, Optional[str]]:
    """
    Validate playlist title.
    
    Rules:
    - Not empty
    - 1-100 characters
    - Safe for filenames (will be sanitized)
    
    Returns:
        (is_valid, error_message)
    """
    if not title or not title.strip():
        return False, "Title cannot be empty"
    
    if len(title) > 100:
        return False, "Title must be at most 100 characters"
    
    return True, None


def validate_title_uniqueness(
    title: str, user_dir: Path
) -> tuple[bool, Optional[str]]:
    """
    Check if playlist title is unique for the user.
    
    Returns:
        (is_unique, error_message)
    """
    if not user_dir.exists():
        return True, None
    
    # Sanitize title to match how it will be saved
    safe_filename = sanitize_filename(title)
    
    # Check for existing files with same title
    for yaml_file in user_dir.glob("*.yaml"):
        if yaml_file.stem == safe_filename:
            return False, f"You already have a playlist titled '{title}'"
    
    return True, None


def validate_spotify_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate Spotify playlist URL format.
    
    Accepts:
    - https://open.spotify.com/playlist/ID
    - spotify:playlist:ID
    
    Returns:
        (is_valid, error_message)
    """
    if not url or not url.strip():
        return False, "URL cannot be empty"
    
    url = url.strip()
    
    # Check for Spotify URL patterns
    url_pattern = r"https?://open\.spotify\.com/playlist/[a-zA-Z0-9]+"
    uri_pattern = r"spotify:playlist:[a-zA-Z0-9]+"
    
    if re.match(url_pattern, url) or re.match(uri_pattern, url):
        return True, None
    
    return (
        False,
        "Invalid Spotify URL. Expected format: "
        "https://open.spotify.com/playlist/ID or spotify:playlist:ID"
    )


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be safe for use as a filename.
    
    - Removes leading/trailing whitespace
    - Replaces problematic characters with safe alternatives
    - Preserves readable format
    """
    # Strip whitespace
    filename = filename.strip()
    
    # Replace problem characters but keep spaces and common punctuation
    # Remove: / \ : * ? " < > |
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        filename = filename.replace(char, '-')
    
    # Replace multiple spaces/dashes with single
    filename = re.sub(r'\s+', ' ', filename)
    filename = re.sub(r'-+', '-', filename)
    
    return filename


def validate_description(description: str) -> tuple[bool, Optional[str]]:
    """
    Validate playlist description.
    
    Rules:
    - Not empty
    - 1-500 characters
    
    Returns:
        (is_valid, error_message)
    """
    if not description or not description.strip():
        return False, "Description cannot be empty"
    
    if len(description) > 500:
        return False, "Description must be at most 500 characters"
    
    return True, None


def validate_genre(genre: str) -> tuple[bool, Optional[str]]:
    """
    Validate genre.
    
    Rules:
    - Not empty
    - 1-50 characters
    - Alphanumeric, spaces, hyphens
    
    Returns:
        (is_valid, error_message)
    """
    if not genre or not genre.strip():
        return False, "Genre cannot be empty"
    
    genre = genre.strip()
    
    if len(genre) > 50:
        return False, "Genre must be at most 50 characters"
    
    if not re.match(r"^[a-zA-Z0-9\s-]+$", genre):
        return (
            False,
            "Genre must contain only letters, numbers, spaces, and hyphens"
        )
    
    return True, None
