""" Module containing the MusicService abstract class and associated dataclasses """

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Sequence

from mixdiscer.playlists import Playlist


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
class ProcessedPlaylist:
    """ Dataclass representing a processed playlist with its total duration """
    user_playlist: Playlist
    music_service_playlists: list[MusicServicePlaylist]


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
    def find_track(self, artist: str, track: str) -> Optional[Track]:
        """ Returns a Track object for the given artist and track.
        If the track is not found, returns None """

    @abstractmethod
    def process_user_playlist(self, playlist: Playlist) -> MusicServicePlaylist:
        """ Returns a MusicServicePlaylist containing that music services version
        of the supplied user playlist """
