"""Utilities for genre management"""

from pathlib import Path
from typing import Optional
from collections import Counter
import yaml


def get_genres_from_playlists(mixdiscs_dir: Path) -> dict[str, int]:
    """
    Extract genres from existing playlist files with usage counts.
    
    Args:
        mixdiscs_dir: Path to mixdiscs directory
    
    Returns:
        Dictionary of {genre: count} for all genres found in playlists
    """
    genre_counts = Counter()
    
    # Scan all YAML files in mixdiscs directory
    for yaml_file in mixdiscs_dir.rglob("*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and 'genre' in data:
                    genre = data['genre'].strip().lower()
                    if genre:
                        genre_counts[genre] += 1
        except Exception:
            # Skip files that can't be parsed
            continue
    
    return dict(genre_counts)


def get_suggested_genres(
    config: dict,
    mixdiscs_dir: Optional[Path] = None
) -> tuple[list[str], dict[str, str]]:
    """
    Get suggested genres from config and existing playlists.
    
    Combines:
    1. Genres from config.yaml (suggested_genres)
    2. Genres from existing playlists (if mixdiscs_dir provided)
    
    Sorts by:
    - Genres from playlists first, ordered by usage count (most used first)
    - Then genres from config that aren't used yet (alphabetical)
    
    Args:
        config: Configuration dictionary
        mixdiscs_dir: Optional path to scan for existing genres
    
    Returns:
        Tuple of (sorted genre list, genre metadata dict)
        - genre list: Sorted list of unique genre suggestions
        - metadata: {genre: description} for display hints
    """
    # Get genres from existing playlists with counts
    playlist_genres = {}
    if mixdiscs_dir and mixdiscs_dir.exists():
        playlist_genres = get_genres_from_playlists(mixdiscs_dir)
    
    # Get genres from config
    config_genres = set(
        g.lower() for g in config.get('suggested_genres', [])
    )
    
    # Sort playlist genres by usage (most used first)
    sorted_playlist_genres = sorted(
        playlist_genres.items(),
        key=lambda x: (-x[1], x[0])  # Sort by count desc, then name asc
    )
    
    # Build final genre list and metadata
    genres = []
    metadata = {}
    
    # Add playlist genres first (with usage counts)
    for genre, count in sorted_playlist_genres:
        genres.append(genre)
        if count == 1:
            metadata[genre] = "Used in 1 playlist"
        else:
            metadata[genre] = f"Used in {count} playlists"
    
    # Add config genres that aren't already used (alphabetically)
    unused_config_genres = sorted(config_genres - set(playlist_genres.keys()))
    for genre in unused_config_genres:
        genres.append(genre)
        metadata[genre] = "Suggested genre"
    
    return genres, metadata
