""" Unit tests for music_service.py """

import pytest
from datetime import timedelta

from mixdiscer.music_service import (
    Track,
    MusicServicePlaylist,
    ProcessedPlaylist,
    MusicServiceError,
)
from mixdiscer.playlists import Playlist


def test_track_dataclass():
    """Test creating Track instance"""
    track = Track(
        artist="The Beatles",
        title="Hey Jude",
        album="Past Masters",
        duration=timedelta(minutes=7, seconds=11),
        link="https://open.spotify.com/track/0aym2LBJBk9DAYuHHutrIl"
    )
    
    assert track.artist == "The Beatles"
    assert track.title == "Hey Jude"
    assert track.album == "Past Masters"
    assert track.duration == timedelta(minutes=7, seconds=11)
    assert track.link == "https://open.spotify.com/track/0aym2LBJBk9DAYuHHutrIl"


def test_track_without_album():
    """Test creating Track without album"""
    track = Track(
        artist="Artist",
        title="Song",
        album=None,
        duration=timedelta(minutes=3),
        link="https://example.com"
    )
    
    assert track.album is None


def test_track_without_link():
    """Test creating Track without link"""
    track = Track(
        artist="Artist",
        title="Song",
        album="Album",
        duration=timedelta(minutes=3),
        link=None
    )
    
    assert track.link is None


def test_music_service_playlist_dataclass(sample_tracks):
    """Test creating MusicServicePlaylist instance"""
    total_duration = sum((t.duration for t in sample_tracks), timedelta())
    
    playlist = MusicServicePlaylist(
        service_name="spotify",
        tracks=sample_tracks,
        total_duration=total_duration
    )
    
    assert playlist.service_name == "spotify"
    assert len(playlist.tracks) == 3
    assert playlist.total_duration == total_duration


def test_music_service_playlist_with_missing_tracks():
    """Test MusicServicePlaylist with None tracks"""
    tracks = [
        Track("Artist", "Song", "Album", timedelta(minutes=3), "https://link"),
        None,  # Missing track
        Track("Artist2", "Song2", "Album2", timedelta(minutes=4), "https://link2"),
    ]
    
    playlist = MusicServicePlaylist(
        service_name="spotify",
        tracks=tracks,
        total_duration=timedelta(minutes=7)
    )
    
    assert len(playlist.tracks) == 3
    assert playlist.tracks[1] is None


def test_processed_playlist_dataclass(sample_playlist, sample_music_service_playlist):
    """Test creating ProcessedPlaylist instance"""
    processed = ProcessedPlaylist(
        user_playlist=sample_playlist,
        music_service_playlists=[sample_music_service_playlist]
    )
    
    assert processed.user_playlist == sample_playlist
    assert len(processed.music_service_playlists) == 1
    assert processed.music_service_playlists[0] == sample_music_service_playlist


def test_processed_playlist_multiple_services(sample_playlist):
    """Test ProcessedPlaylist with multiple music services"""
    spotify_playlist = MusicServicePlaylist(
        service_name="spotify",
        tracks=[],
        total_duration=timedelta()
    )
    
    apple_music_playlist = MusicServicePlaylist(
        service_name="apple_music",
        tracks=[],
        total_duration=timedelta()
    )
    
    processed = ProcessedPlaylist(
        user_playlist=sample_playlist,
        music_service_playlists=[spotify_playlist, apple_music_playlist]
    )
    
    assert len(processed.music_service_playlists) == 2


def test_music_service_error():
    """Test MusicServiceError exception"""
    error = MusicServiceError(
        message="Connection failed",
        service_name="spotify",
        original_exception=None
    )
    
    assert error.message == "Connection failed"
    assert error.service_name == "spotify"
    assert error.original_exception is None
    assert "[spotify]" in str(error)
    assert "Connection failed" in str(error)


def test_music_service_error_with_original_exception():
    """Test MusicServiceError with wrapped exception"""
    original = ValueError("Invalid token")
    
    error = MusicServiceError(
        message="Authentication failed",
        service_name="spotify",
        original_exception=original
    )
    
    assert error.original_exception == original
    assert isinstance(error.original_exception, ValueError)


def test_music_service_error_inheritance():
    """Test that MusicServiceError is an Exception"""
    error = MusicServiceError("Test", "spotify")
    
    assert isinstance(error, Exception)
    
    # Should be catchable as Exception
    with pytest.raises(Exception):
        raise error
