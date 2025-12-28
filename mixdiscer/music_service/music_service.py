""" Module containing the MusicService abstract class and associated dataclasses """

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Sequence

from mixdiscer.playlists import Playlist


class MusicServiceError(Exception):
    """ Exception raised for unrecoverable errors in music service operations.

    Attributes:
        message: explanation of the error
        service_name: name of the music service raising the error
        original_exception: the original exception that caused this error, if any
    """

    def __init__(
            self,
            message: str,
            service_name: str,
            original_exception: Optional[Exception] = None,
    ) -> None:
        self.message = message
        self.service_name = service_name
        self.original_exception = original_exception
        super().__init__(f"[{service_name}] {message}")


@dataclass
class Track:
    """ Dataclass representing a Track and its metadata """
    artist: str
    title: str
    album: Optional[str]
    duration: timedelta
    link: Optional[str]


@dataclass
class MusicServicePlaylist:
    """ Dataclass representing a processed playlist from a music service """
    service_name: str
    tracks: Sequence[Optional[Track]]
    total_duration: timedelta


@dataclass
class ValidationWarning:
    """Warning about remote playlist validation failure"""
    warning_type: str
    message: str
    details: dict
    frozen_at: Optional[datetime] = None
    frozen_version_date: Optional[datetime] = None


@dataclass
class ProcessedPlaylist:
    """ Dataclass representing a processed playlist with its total duration """
    user_playlist: Playlist
    music_service_playlists: list[MusicServicePlaylist]
    validation_warning: Optional[ValidationWarning] = None


def calculate_total_duration(tracks: Sequence[Optional[Track]]) -> timedelta:
    """ Calculate the total duration of a list of tracks """
    total_duration = timedelta()

    for track in tracks:
        if track is None:
            continue

        total_duration += track.duration

    return total_duration


class MusicService(ABC):
    """ Abstract class representing a music service """

    @property
    @abstractmethod
    def name(self) -> str:
        """ Returns the name of the music service.
        This name is ued to identify the service in logs and output """

    @abstractmethod
    def find_track(self, artist: str, track: str, album: Optional[str] = None) -> Optional[Track]:
        """ Returns a Track object for the given artist and track.
        If the track is not found because it is not present on the music
        service then this method should return None. If there is any
        other error which prevents finding the track then the method
        should raise a MusicServiceError.

        Arguments:
            artist: The name of the performing artist
            track: The title of the track
            album: Optional album name to find a specific version of the track.
                   If not provided, the service should return the first/default match.
                   If provided but not found, the service should fall back to default.

        Returns:
            A Track object representing the track or None if the track
            is not found.
        """

    @abstractmethod
    def process_user_playlist(self, playlist: Playlist) -> MusicServicePlaylist:
        """ Returns a MusicServicePlaylist containing that music services version
        of the supplied user playlist 

        Arguments:
            playlist: A user Playlist object containing the tracks to process

        Returns:
            A MusicServicePlaylist object containing the tracks and
            other metadata for the playlist.
        """
