#!/usr/bin/env python3
"""
MixDiscs Playlist Generator CLI

Interactive tool to create playlist YAML files for MixDiscs.
"""

import sys
from pathlib import Path

from mixdiscer.configuration import load_config
from mixdiscer.cli.prompts import (
    prompt_username,
    prompt_playlist_type,
    prompt_title,
    prompt_description,
    prompt_genre,
    prompt_num_tracks,
    prompt_spotify_url,
    prompt_confirmation,
)
from mixdiscer.cli.generators import generate_yaml
from mixdiscer.cli.validators import sanitize_filename
from mixdiscer.cli.genre_utils import get_suggested_genres


def find_mixdiscs_directory() -> Path:
    """
    Find the mixdiscs directory.
    
    Searches from current directory upwards for mixdiscs/ directory.
    
    Returns:
        Path to mixdiscs directory
    
    Raises:
        FileNotFoundError: If mixdiscs directory not found
    """
    current = Path.cwd()
    
    # Check current directory
    if (current / "mixdiscs").is_dir():
        return current / "mixdiscs"
    
    # Check parent directories
    for parent in current.parents:
        if (parent / "mixdiscs").is_dir():
            return parent / "mixdiscs"
    
    raise FileNotFoundError(
        "Could not find 'mixdiscs' directory. "
        "Please run this command from the MixDiscs repository."
    )


def print_header():
    """Print CLI header"""
    print()
    print("=" * 52)
    print("🎵  MixDiscs Playlist Generator")
    print("=" * 52)
    print()


def print_success(filepath: Path, is_new_user: bool):
    """Print success message with next steps"""
    print()
    print("=" * 52)
    print("✅  Playlist created successfully!")
    print("=" * 52)
    print()
    print(f"📁 File: {filepath.relative_to(Path.cwd()).as_posix()}")
    print()
    print("Next steps:")
    print("  1. Edit the file and customize your playlist")
    print("  2. Review the track list (manual) or verify Spotify URL (remote)")
    print("  3. Commit your changes:")
    if is_new_user:
        print(f"       git add mixdiscs/{filepath.parent.name}/")
    else:
        print(f"       git add {filepath.relative_to(Path.cwd()).as_posix()}")
    print(f"       git commit -m 'Add playlist: {filepath.stem}'")
    print("  4. Push to your branch and open a pull request")
    print("  5. CI will validate your playlist automatically")
    print()
    print("💡 Tips:")
    print("  • Keep total duration under 80 minutes (MiniDisc/CD-R limit)")
    print("  • For manual playlists: use 'Artist - Song Title' format")
    print("  • For remote playlists: ensure playlist is public on Spotify")
    print()
    print("Happy mixing! 🎵")
    print()


def main():
    """Main CLI entry point"""
    try:
        print_header()
        
        # Find mixdiscs directory
        try:
            mixdiscs_dir = find_mixdiscs_directory()
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            print()
            print("Make sure you're running this from the MixDiscs repository.")
            sys.exit(1)
        
        # Load configuration for genre suggestions
        config_path = mixdiscs_dir.parent / "config.yaml"
        config = {}
        try:
            config = load_config(str(config_path))
        except Exception:
            # Use empty config if file doesn't exist or can't be loaded
            pass
        
        # Get genre suggestions (sorted by usage)
        suggested_genres, genre_metadata = get_suggested_genres(config, mixdiscs_dir)
        
        # Prompt for username
        username, is_new_user = prompt_username(mixdiscs_dir)
        
        if is_new_user:
            print(f"✨ Creating new user: {username}")
        else:
            print(f"📁 Using existing user: {username}")
        print()
        
        user_dir = mixdiscs_dir / username
        
        # Prompt for playlist type
        playlist_type = prompt_playlist_type()
        print()
        
        # Prompt for common fields
        title = prompt_title(user_dir)
        description = prompt_description()
        genre = prompt_genre(suggested_genres, genre_metadata)
        print()
        
        # Type-specific prompts
        num_tracks = None
        spotify_url = None
        
        if playlist_type == "manual":
            num_tracks = prompt_num_tracks()
            print()
        else:  # remote
            spotify_url = prompt_spotify_url()
            print()
        
        # Generate filename
        safe_title = sanitize_filename(title)
        filename = f"{safe_title}.yaml"
        filepath = user_dir / filename
        
        # Show file preview and confirm
        print("📝 Preview:")
        print(f"   User: {username}")
        print(f"   Title: {title}")
        print(f"   Description: {description}")
        print(f"   Genre: {genre}")
        print(f"   Type: {playlist_type}")
        if playlist_type == "manual":
            print(f"   Tracks: {num_tracks} placeholders")
        else:
            print(f"   Spotify URL: {spotify_url}")
        print()
        print(f"   File: {filepath.relative_to(Path.cwd()).as_posix()}")
        print()
        
        # Confirm creation
        if not prompt_confirmation("Create this playlist?"):
            print()
            print("❌ Cancelled. No files were created.")
            print()
            sys.exit(0)
        
        # Create directory if needed
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate YAML content
        yaml_content = generate_yaml(
            user=username,
            title=title,
            description=description,
            genre=genre,
            playlist_type=playlist_type,
            num_tracks=num_tracks,
            spotify_url=spotify_url
        )
        
        # Write file
        filepath.write_text(yaml_content, encoding="utf-8")
        
        # Show success message
        print_success(filepath, is_new_user)
        
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Cancelled by user.")
        print()
        sys.exit(130)
    except Exception as e:
        print()
        print(f"❌ Unexpected error: {e}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
