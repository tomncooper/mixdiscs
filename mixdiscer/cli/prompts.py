"""Interactive prompts for playlist creation"""

from pathlib import Path
from typing import Optional

import questionary
from questionary import Validator, ValidationError

from mixdiscer.cli.validators import (
    validate_username,
    validate_title,
    validate_title_uniqueness,
    validate_description,
    validate_genre,
    validate_spotify_url,
)


class UsernameValidator(Validator):
    """Validator for username input"""
    
    def validate(self, document):
        is_valid, error_msg = validate_username(document.text)
        if not is_valid:
            raise ValidationError(
                message=error_msg,
                cursor_position=len(document.text)
            )


class ExistingUsernameValidator(Validator):
    """Validator for existing username selection"""
    
    def __init__(self, valid_usernames: list[str]):
        self.valid_usernames = valid_usernames
    
    def validate(self, document):
        if document.text not in self.valid_usernames:
            raise ValidationError(
                message=(
                    "Please select from existing users. " +
                    "Type to search, use arrow keys to navigate options " +
                    "and press Enter when highlighted."
                ),
                cursor_position=len(document.text)
            )


class TitleValidator(Validator):
    """Validator for title input"""
    
    def __init__(self, user_dir: Optional[Path] = None):
        self.user_dir = user_dir
    
    def validate(self, document):
        is_valid, error_msg = validate_title(document.text)
        if not is_valid:
            raise ValidationError(
                message=error_msg,
                cursor_position=len(document.text)
            )
        
        # Check uniqueness if user_dir provided
        if self.user_dir:
            is_unique, error_msg = validate_title_uniqueness(
                document.text, self.user_dir
            )
            if not is_unique:
                raise ValidationError(
                    message=error_msg,
                    cursor_position=len(document.text)
                )


class DescriptionValidator(Validator):
    """Validator for description input"""
    
    def validate(self, document):
        is_valid, error_msg = validate_description(document.text)
        if not is_valid:
            raise ValidationError(
                message=error_msg,
                cursor_position=len(document.text)
            )


class GenreValidator(Validator):
    """Validator for genre input"""
    
    def validate(self, document):
        is_valid, error_msg = validate_genre(document.text)
        if not is_valid:
            raise ValidationError(
                message=error_msg,
                cursor_position=len(document.text)
            )


class SpotifyURLValidator(Validator):
    """Validator for Spotify URL input"""
    
    def validate(self, document):
        is_valid, error_msg = validate_spotify_url(document.text)
        if not is_valid:
            raise ValidationError(
                message=error_msg,
                cursor_position=len(document.text)
            )


def prompt_username(mixdiscs_dir: Path) -> tuple[str, bool]:
    """
    Prompt for username selection (existing or new).
    
    First asks if user is new or existing, then:
    - Existing: Shows autocomplete search
    - New: Prompts for username creation
    
    Args:
        mixdiscs_dir: Path to mixdiscs directory
    
    Returns:
        (username, is_new) - username and whether it's a new user
    """
    # Get existing usernames
    existing = sorted([
        d.name for d in mixdiscs_dir.iterdir() 
        if d.is_dir() and not d.name.startswith('.')
    ])
    
    # Ask if new or existing user
    user_type = questionary.select(
        "Are you a new or existing user?",
        choices=[
            questionary.Choice(
                title="📁 Existing user (I already have playlists)",
                value="existing"
            ),
            questionary.Choice(
                title="✨ New user (This is my first playlist)",
                value="new"
            )
        ]
    ).ask()
    
    if user_type is None:  # User cancelled
        raise KeyboardInterrupt()
    
    if user_type == "existing":
        if not existing:
            print("⚠️  No existing users found. Creating new user instead.")
            print()
        else:
            # Show autocomplete search for existing users
            result = questionary.autocomplete(
                "Select your username (type to search, use arrows to navigate):",
                choices=existing,
                validate=ExistingUsernameValidator(existing),
                meta_information={u: "📁 Existing user" for u in existing}
            ).ask()
            
            if result is None:  # User cancelled
                raise KeyboardInterrupt()
            
            return result, False
    
    # Create new username
    new_username = questionary.text(
        "Enter new username (3-30 chars: letters, numbers, _ or -):",
        validate=UsernameValidator()
    ).ask()
    
    if new_username is None:  # User cancelled
        raise KeyboardInterrupt()
    
    return new_username, True


def prompt_playlist_type() -> str:
    """
    Prompt for playlist type selection.
    
    Returns:
        'manual' or 'remote'
    """
    result = questionary.select(
        "Select playlist type:",
        choices=[
            questionary.Choice(
                title="📝 Manual (list tracks yourself)",
                value="manual"
            ),
            questionary.Choice(
                title="🔗 Remote (link to Spotify playlist)",
                value="remote"
            )
        ]
    ).ask()
    
    if result is None:  # User cancelled
        raise KeyboardInterrupt()
    
    return result


def prompt_title(user_dir: Path) -> str:
    """
    Prompt for playlist title with validation.
    
    Args:
        user_dir: Path to user's directory (for uniqueness check)
    
    Returns:
        Playlist title
    """
    result = questionary.text(
        "Playlist title (1-100 chars):",
        validate=TitleValidator(user_dir)
    ).ask()
    
    if result is None:  # User cancelled
        raise KeyboardInterrupt()
    
    return result.strip()


def prompt_description() -> str:
    """
    Prompt for playlist description.
    
    Returns:
        Description text
    """
    result = questionary.text(
        "Description:",
        validate=DescriptionValidator()
    ).ask()
    
    if result is None:  # User cancelled
        raise KeyboardInterrupt()
    
    return result.strip()


def prompt_genre(suggested_genres: list[str], genre_metadata: dict[str, str]) -> str:
    """
    Prompt for genre with suggestions and metadata.
    
    Args:
        suggested_genres: List of suggested genres (sorted by usage)
        genre_metadata: Dictionary of {genre: description} for display hints
    
    Returns:
        Genre string
    """
    result = questionary.autocomplete(
        "Genre (type to filter or enter custom):",
        choices=suggested_genres,
        validate=GenreValidator(),
        meta_information=genre_metadata
    ).ask()
    
    if result is None:  # User cancelled
        raise KeyboardInterrupt()
    
    return result.strip().lower()


def prompt_num_tracks() -> int:
    """
    Prompt for number of placeholder tracks (manual playlists).
    
    Returns:
        Number of tracks
    """
    result = questionary.text(
        "Number of placeholder tracks (default 10):",
        default="10"
    ).ask()
    
    if result is None:  # User cancelled
        raise KeyboardInterrupt()
    
    try:
        num_tracks = int(result)
        if num_tracks < 1:
            print("⚠️  Must be at least 1, using default of 10")
            return 10
        if num_tracks > 100:
            print("⚠️  Maximum 100 tracks, using 100")
            return 100
        return num_tracks
    except ValueError:
        print("⚠️  Invalid number, using default of 10")
        return 10


def prompt_spotify_url() -> str:
    """
    Prompt for Spotify playlist URL.
    
    Returns:
        Spotify URL
    """
    result = questionary.text(
        "Spotify playlist URL:",
        validate=SpotifyURLValidator()
    ).ask()
    
    if result is None:  # User cancelled
        raise KeyboardInterrupt()
    
    return result.strip()


def prompt_confirmation(message: str, default: bool = True) -> bool:
    """
    Prompt for yes/no confirmation.
    
    Args:
        message: Question to ask
        default: Default value
    
    Returns:
        True for yes, False for no
    """
    result = questionary.confirm(
        message,
        default=default
    ).ask()
    
    if result is None:  # User cancelled
        raise KeyboardInterrupt()
    
    return result
