import logging

from datetime import timedelta
from pathlib import Path
from typing import Optional

from mixdiscer.configuration import (
    load_config,
    MIXDISC_DIRECTORY_CONFIG,
    PLAYLIST_DURATION_THRESHOLD_CONFIG,
    TEMPLATE_DIR_CONFIG,
    OUTPUT_DIR_CONFIG,
)
from mixdiscer.playlists import get_playlists, get_playlists_from_paths, check_playlist_uniqueness
from mixdiscer.music_service import (
    Track,
    MusicService,
    MusicServicePlaylist,
    ProcessedPlaylist,
)
from mixdiscer.music_service.spotify import SpotifyMusicService
from mixdiscer.output.render import render_output
from mixdiscer.validation import ValidationResult

LOG = logging.getLogger(__name__)


def calculate_duration(tracks: list[Optional[Track]]) -> timedelta:

    total_duration = timedelta()

    for track in tracks:
        if track is None:
            continue

        total_duration += track.duration

    return total_duration


def _load_rendering_config(config_path: str) -> tuple[str, Path, Path, timedelta]:
    """
    Load configuration for rendering operations.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        tuple: (mixdisc_directory, template_dir, output_dir, duration_threshold)
    """
    config = load_config(config_path)
    mixdisc_directory = config.get(MIXDISC_DIRECTORY_CONFIG)
    template_dir = Path(config.get(TEMPLATE_DIR_CONFIG))
    output_dir = Path(config.get(OUTPUT_DIR_CONFIG))
    duration_threshold = timedelta(
        minutes=config.get(PLAYLIST_DURATION_THRESHOLD_CONFIG)
    )
    return mixdisc_directory, template_dir, output_dir, duration_threshold


def _get_music_service() -> MusicService:
    """
    Initialize and return the music service to use.
    
    Currently returns Spotify, but could be extended to support
    multiple services based on configuration.
    
    Returns:
        MusicService instance
    """
    return SpotifyMusicService()


def _process_single_playlist(playlist, music_service: MusicService) -> ProcessedPlaylist:
    """
    Process a single playlist with a music service.
    
    Args:
        playlist: Playlist object to process
        music_service: Music service to use for processing
        
    Returns:
        ProcessedPlaylist with music service data populated
    """
    processed_playlist = ProcessedPlaylist(
        user_playlist=playlist,
        music_service_playlists=[]
    )
    
    music_service_playlist = music_service.process_user_playlist(playlist)
    processed_playlist.music_service_playlists.append(music_service_playlist)
    
    return processed_playlist


def _log_rendering_summary(
    total: int,
    successful: int,
    failed: list[tuple[str, Exception]],
    output_dir: Path
) -> None:
    """Log rendering summary statistics"""
    
    LOG.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    LOG.info("Rendering complete!")
    LOG.info("  Total playlists: %d", total)
    LOG.info("  Successfully rendered: %d", successful)
    LOG.info("  Failed: %d", len(failed))
    LOG.info("  Output: %s/index.html", output_dir)
    
    if failed:
        LOG.warning("Failed playlists:")
        for playlist_name, error in failed:
            LOG.warning("  - %s: %s", playlist_name, error)


def validate_playlist(
    playlist_path: Path,
    playlist,
    music_service: MusicService,
    duration_threshold: timedelta
) -> ValidationResult:
    """ Validate a single playlist and return validation result """

    try:
        music_service_playlist = music_service.process_user_playlist(playlist)

        missing_tracks = [
            playlist.tracks[i] for i, track in enumerate(music_service_playlist.tracks)
            if track is None
        ]

        is_valid = music_service_playlist.total_duration <= duration_threshold

        return ValidationResult(
            filepath=playlist_path,
            user=playlist.user,
            title=playlist.title,
            is_valid=is_valid,
            total_duration=music_service_playlist.total_duration,
            duration_threshold=duration_threshold,
            missing_tracks=missing_tracks
        )

    except Exception as e:
        LOG.error("Error validating playlist %s: %s", playlist_path, e)
        return ValidationResult(
            filepath=playlist_path,
            user=playlist.user if hasattr(playlist, 'user') else "Unknown",
            title=playlist.title if hasattr(playlist, 'title') else "Unknown",
            is_valid=False,
            total_duration=timedelta(),
            duration_threshold=duration_threshold,
            missing_tracks=[],
            error_message=str(e)
        )


def run(config_path: str):
    """ Main function for Mixdiscer """

    LOG.info("Running Mixdiscer with config %s", config_path)

    mixdisc_directory, template_dir, output_dir, playlist_duration_threshold = \
        _load_rendering_config(config_path)

    music_service = _get_music_service()

    output: list[ProcessedPlaylist] = []
    over_duration_playlists: list[ProcessedPlaylist] = []

    for playlist in get_playlists(mixdisc_directory):
        processed_playlist = _process_single_playlist(playlist, music_service)
        
        # Get the music service playlist (first one, as we only have Spotify now)
        music_service_playlist = processed_playlist.music_service_playlists[0]

        if music_service_playlist.total_duration > playlist_duration_threshold:
            LOG.warning(
                "Playlist %s by %s is above the duration threshold of %s by %s",
                playlist.title,
                playlist.user,
                playlist_duration_threshold,
                (music_service_playlist.total_duration - playlist_duration_threshold),
            )
            over_duration_playlists.append(processed_playlist)
        else:
            LOG.info(
                "Processed playlist %s by %s (total duration: %s)",
                playlist.title,
                playlist.user,
                music_service_playlist.total_duration
            )
            output.append(processed_playlist)

    LOG.info(
        "Mixdiscer processing complete. Processed %d playlists.",
        len(output) + len(over_duration_playlists)
    )
    if over_duration_playlists:
        LOG.warning(
            "There were %d playlists over the duration threshold.",
            len(over_duration_playlists)
        )

    render_output(output, output_dir, template_dir)


def render_all_playlists(config_path: str, skip_errors: bool = False) -> None:
    """
    Render all playlists to HTML without duration validation.
    
    This is intended for use after playlists have been validated
    (e.g., in main branch after PR merge). Unlike run(), this does
    not filter playlists by duration threshold.
    
    Args:
        config_path: Path to configuration file
        skip_errors: If True, continue rendering even if some playlists fail
    """
    
    LOG.info("Rendering all playlists from config %s", config_path)
    
    mixdisc_directory, template_dir, output_dir, _ = _load_rendering_config(config_path)
    music_service = _get_music_service()
    
    processed_playlists: list[ProcessedPlaylist] = []
    failed_playlists: list[tuple[str, Exception]] = []
    
    # Get all playlists
    playlists = list(get_playlists(mixdisc_directory))
    LOG.info("Found %d playlists to render", len(playlists))
    
    # Process each playlist
    for playlist in playlists:
        try:
            LOG.debug("Processing playlist: %s by %s", playlist.title, playlist.user)
            
            processed_playlist = _process_single_playlist(playlist, music_service)
            processed_playlists.append(processed_playlist)
            
            # Get the music service playlist (first one, as we only have Spotify now)
            music_service_playlist = processed_playlist.music_service_playlists[0]
            
            LOG.info(
                "✓ Rendered playlist: %s by %s (duration: %s, tracks: %d)",
                playlist.title,
                playlist.user,
                music_service_playlist.total_duration,
                len([t for t in music_service_playlist.tracks if t is not None])
            )
            
        except Exception as e:
            error_msg = f"Failed to process playlist {playlist.title} by {playlist.user}"
            LOG.error("%s: %s", error_msg, e)
            failed_playlists.append((f"{playlist.user}/{playlist.title}", e))
            
            if not skip_errors:
                raise Exception(f"{error_msg}: {e}") from e
    
    # Render to HTML
    LOG.info("Rendering HTML output to %s", output_dir)
    render_output(processed_playlists, output_dir, template_dir)
    
    # Summary
    _log_rendering_summary(len(playlists), len(processed_playlists), failed_playlists, output_dir)
    
    if failed_playlists and not skip_errors:
        raise Exception(f"Rendering completed with {len(failed_playlists)} errors")


def validate_playlists_from_files(config_path: str, playlist_files: list[Path]) -> list[ValidationResult]:
    """ Validate specific playlist files and return results """

    LOG.info("Validating %d playlist file(s)", len(playlist_files))

    mixdisc_directory, _, _, playlist_duration_threshold = _load_rendering_config(config_path)
    music_service = _get_music_service()

    results = []

    # Load all existing playlists for uniqueness checking
    existing_playlists = list(get_playlists(mixdisc_directory))
    LOG.debug("Loaded %d existing playlists for uniqueness checking", len(existing_playlists))

    # Create a mapping of successfully loaded playlists
    loaded_playlists = {}
    for playlist in get_playlists_from_paths(playlist_files, Path(mixdisc_directory)):
        # Find the matching file path by checking which file hasn't been processed yet
        for path in playlist_files:
            if path not in loaded_playlists:
                loaded_playlists[path] = playlist
                break

    # Check for duplicates between new playlists and existing ones
    all_playlists = existing_playlists + list(loaded_playlists.values())
    duplicate_pairs = check_playlist_uniqueness(all_playlists)
    
    # Create a map of new playlists that are duplicates
    duplicate_map = {}
    for original, duplicate in duplicate_pairs:
        # Only flag if the duplicate is one of the files being validated
        if duplicate.filepath in playlist_files:
            duplicate_map[duplicate.filepath] = original.filepath

    # Process each file
    for playlist_path in playlist_files:
        if playlist_path not in loaded_playlists:
            # File failed to load
            LOG.error("Failed to load playlist: %s", playlist_path)
            results.append(ValidationResult(
                filepath=playlist_path,
                user="Unknown",
                title="Unknown",
                is_valid=False,
                total_duration=timedelta(),
                duration_threshold=playlist_duration_threshold,
                missing_tracks=[],
                error_message="Failed to load playlist file"
            ))
            continue

        playlist = loaded_playlists[playlist_path]
        
        # Check if this is a duplicate
        if playlist_path in duplicate_map:
            LOG.error("✗ Playlist %s is a duplicate of %s", playlist.title, duplicate_map[playlist_path])
            results.append(ValidationResult(
                filepath=playlist_path,
                user=playlist.user,
                title=playlist.title,
                is_valid=False,
                total_duration=timedelta(),
                duration_threshold=playlist_duration_threshold,
                missing_tracks=[],
                duplicate_of=duplicate_map[playlist_path]
            ))
            continue

        LOG.info("Validating playlist: %s", playlist_path)
        result = validate_playlist(
            playlist_path,
            playlist,
            music_service,
            playlist_duration_threshold
        )
        results.append(result)

        if result.is_valid:
            LOG.info("✓ Playlist %s is valid (duration: %s)", playlist.title, result.total_duration)
        else:
            if result.error_message:
                LOG.error("✗ Playlist %s failed: %s", playlist.title, result.error_message)
            else:
                LOG.error(
                    "✗ Playlist %s exceeds duration limit by %s",
                    playlist.title,
                    result.duration_difference
                )

    valid_count = sum(1 for r in results if r.is_valid)
    LOG.info(
        "Validation complete: %d valid, %d invalid",
        valid_count,
        len(results) - valid_count
    )

    return results
