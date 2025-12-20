""" Module for validating playlists """

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Optional

from mixdiscer.music_service import Track


@dataclass
class ValidationResult:
    """ Dataclass representing the result of validating a playlist """
    filepath: Path
    user: str
    title: str
    is_valid: bool
    total_duration: timedelta
    duration_threshold: timedelta
    missing_tracks: list[tuple[str, str]]
    error_message: Optional[str] = None
    duplicate_of: Optional[Path] = None

    @property
    def duration_exceeded(self) -> bool:
        """ Returns True if the playlist duration exceeds the threshold """
        return self.total_duration > self.duration_threshold

    @property
    def duration_difference(self) -> timedelta:
        """ Returns the difference between total duration and threshold """
        return self.total_duration - self.duration_threshold


def format_validation_results(results: list[ValidationResult]) -> str:
    """ Format validation results as markdown """

    if not results:
        return "No playlists to validate."

    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count

    output = ["# Playlist Validation Results\n"]

    if invalid_count == 0:
        output.append(f"✅ All {valid_count} playlist(s) passed validation!\n")
    else:
        output.append(f"❌ {invalid_count} of {len(results)} playlist(s) failed validation.\n")

    # Show failed playlists first
    failed_results = [r for r in results if not r.is_valid]
    if failed_results:
        output.append("## Failed Playlists\n")
        for result in failed_results:
            output.append(f"### ❌ {result.title} by {result.user}\n")
            output.append(f"**File:** `{result.filepath}`\n")

            if result.error_message:
                output.append(f"**Error:** {result.error_message}\n")
            elif result.duplicate_of:
                output.append(f"**Duplicate:** This playlist already exists at `{result.duplicate_of}`\n")
                output.append(f"**Note:** Username-playlist combination must be globally unique\n")
            elif result.duration_exceeded:
                output.append(f"**Duration:** {format_duration(result.total_duration)} "
                            f"(exceeds limit by {format_duration(result.duration_difference)})\n")
                output.append(f"**Limit:** {format_duration(result.duration_threshold)}\n")

            if result.missing_tracks:
                output.append(f"\n**Missing tracks ({len(result.missing_tracks)}):**\n")
                for artist, track in result.missing_tracks:
                    output.append(f"- {artist} - {track}\n")
            output.append("\n")

    # Show passed playlists
    passed_results = [r for r in results if r.is_valid]
    if passed_results:
        output.append("## Passed Playlists\n")
        for result in passed_results:
            output.append(f"### ✅ {result.title} by {result.user}\n")
            output.append(f"**Duration:** {format_duration(result.total_duration)} / "
                        f"{format_duration(result.duration_threshold)}\n")
            if result.missing_tracks:
                output.append(f"**Note:** {len(result.missing_tracks)} track(s) not found on music service\n")
            output.append("\n")

    return "".join(output)


def format_duration(duration: timedelta) -> str:
    """ Format a timedelta as MM:SS """
    total_seconds = int(duration.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"
