"""YAML generation functions for playlists"""

from typing import Optional


def generate_manual_yaml(
    user: str,
    title: str,
    description: str,
    genre: str,
    num_tracks: int = 10
) -> str:
    """
    Generate a manual playlist YAML with placeholder tracks.
    
    Args:
        user: Username
        title: Playlist title
        description: Playlist description
        genre: Music genre
        num_tracks: Number of placeholder tracks to create
    
    Returns:
        YAML content as string
    """
    # Generate placeholder tracks
    track_lines = []
    for i in range(1, num_tracks + 1):
        track_lines.append(f"  - Artist Name {i} - Song Title {i}")
    
    tracks = "\n".join(track_lines)
    
    return f"""user: {user}
title: {title}
description: {description}
genre: {genre}
playlist:
{tracks}
"""


def generate_remote_yaml(
    user: str,
    title: str,
    description: str,
    genre: str,
    spotify_url: str
) -> str:
    """
    Generate a remote playlist YAML with Spotify URL.
    
    Args:
        user: Username
        title: Playlist title
        description: Playlist description
        genre: Music genre
        spotify_url: Spotify playlist URL or URI
    
    Returns:
        YAML content as string
    """
    return f"""user: {user}
title: {title}
description: {description}
genre: {genre}
remote_playlist: {spotify_url}
"""


def generate_yaml(
    user: str,
    title: str,
    description: str,
    genre: str,
    playlist_type: str,
    num_tracks: Optional[int] = None,
    spotify_url: Optional[str] = None
) -> str:
    """
    Generate playlist YAML based on type.
    
    Args:
        user: Username
        title: Playlist title
        description: Playlist description
        genre: Music genre
        playlist_type: 'manual' or 'remote'
        num_tracks: Number of placeholder tracks (manual only)
        spotify_url: Spotify URL (remote only)
    
    Returns:
        YAML content as string
    
    Raises:
        ValueError: If invalid playlist type or missing required args
    """
    if playlist_type == "manual":
        if num_tracks is None:
            num_tracks = 10
        return generate_manual_yaml(user, title, description, genre, num_tracks)
    elif playlist_type == "remote":
        if not spotify_url:
            raise ValueError("spotify_url required for remote playlists")
        return generate_remote_yaml(user, title, description, genre, spotify_url)
    else:
        raise ValueError(f"Invalid playlist type: {playlist_type}")
