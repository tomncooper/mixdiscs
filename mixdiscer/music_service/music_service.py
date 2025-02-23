""" Module containing the MusicService abstract class and associated dataclasses """

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from mixdiscer.playlists import Playlist


@dataclass
class Track:
    """ Dataclass representing a Track and its metadata """
    artist: str
    title: str
    album: Optional[str]
    duration: timedelta


class MusicService(ABC):
    """ Abstract class representing a music service """

    @abstractmethod
    def find_track(self, artist: str, track: str) -> Optional[Track]:
        """ Returns a Track object for the given artist and track.
        If the track is not found, returns None """

    @abstractmethod
    def process_playlist(self, playlist: Playlist) -> list[Optional[Track]]:
        """ Returns a list of Track objects for the given playlist """
