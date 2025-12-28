import logging

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from mixdiscer.configuration import (
    load_config,
    MIXDISC_DIRECTORY_CONFIG,
    PLAYLIST_DURATION_THRESHOLD_CONFIG,
    TEMPLATE_DIR_CONFIG,
    OUTPUT_DIR_CONFIG,
    CACHE_FILE_CONFIG,
    TRACK_CACHE_FILE_CONFIG,
)
from mixdiscer.playlists import get_playlists, get_playlists_from_paths, check_playlist_uniqueness
from mixdiscer.music_service import (
    Track,
    MusicService,
    MusicServicePlaylist,
    MusicServiceError,
    ProcessedPlaylist,
    ValidationWarning,
)
from mixdiscer.music_service.spotify import SpotifyMusicService
from mixdiscer.output.render import render_output
from mixdiscer.validation import ValidationResult
from mixdiscer.cache import (
    get_cache_key,
    load_cache,
    save_cache,
    is_cache_valid,
    get_cached_music_service_playlist,
    update_cache_entry,
    cleanup_stale_cache_entries,
)
from mixdiscer.track_cache import (
    load_track_cache,
    save_track_cache,
)

LOG = logging.getLogger(__name__)


@dataclass
class RemotePlaylistCheckResult:
    """Result of checking a remote playlist for updates"""
    music_service_playlist: MusicServicePlaylist
    validation_warning: Optional[ValidationWarning]
    should_update_cache: bool
    cache_updates: dict
    snapshot_id: Optional[str]


def calculate_duration(tracks: list[Optional[Track]]) -> timedelta:

    total_duration = timedelta()

    for track in tracks:
        if track is None:
            continue

        total_duration += track.duration

    return total_duration


def _build_frozen_warning(cache_entry: dict, service_name: str) -> ValidationWarning:
    """Build ValidationWarning from cached frozen state"""
    frozen_reason = cache_entry.get('remote_frozen_reason', {})
    return ValidationWarning(
        warning_type=frozen_reason.get('type', 'unknown'),
        message=(
            f'This remote playlist exceeds the 80-minute limit on {service_name}. '
            f'Showing last valid version.'
        ),
        details=frozen_reason,
        frozen_at=datetime.fromisoformat(cache_entry['remote_frozen_at']),
        frozen_version_date=datetime.fromisoformat(
            cache_entry['music_services'][service_name]['cached_at']
        )
    )


def check_remote_playlist_update(
    playlist,
    music_service: MusicService,
    cache_entry: dict,
    duration_threshold: timedelta
) -> RemotePlaylistCheckResult:
    """
    Check if remote playlist has been updated and validate it.
    
    Returns RemotePlaylistCheckResult with:
    - Playlist to use (cached or new)
    - Warning if frozen
    - Cache update instructions (but doesn't modify cache itself)
    
    Args:
        playlist: User playlist object
        music_service: Music service instance
        cache_entry: Cache entry for this playlist
        duration_threshold: Maximum allowed duration
        
    Returns:
        RemotePlaylistCheckResult with playlist and cache update info
        
    Raises:
        MusicServiceError: If critical music service operations fail
        ValueError: If cache data is corrupted/invalid
    """
    # Validate cache entry has required fields
    if not cache_entry.get('music_services'):
        raise ValueError(f"Cache entry missing 'music_services' for {playlist.title}")
    
    cached_snapshot = cache_entry.get('remote_snapshot_id')
    
    # Get current snapshot from Spotify
    try:
        current_snapshot = music_service.get_playlist_snapshot(playlist.remote_playlist)
    except MusicServiceError:
        # Re-raise music service errors for caller to handle
        raise
    except Exception as e:
        LOG.error("Unexpected error getting snapshot for %s: %s", playlist.title, e)
        # Wrap in MusicServiceError for consistent error handling
        raise MusicServiceError(
            message=f"Failed to get snapshot: {e}",
            service_name=music_service.name,
            original_exception=e
        ) from e
    
    # No change detected
    if current_snapshot == cached_snapshot:
        LOG.info("✓ Remote playlist unchanged: %s", playlist.title)
        
        # Check if this is a frozen playlist
        warning = None
        if cache_entry.get('remote_validation_status') == 'frozen':
            warning = _build_frozen_warning(cache_entry, music_service.name)
        
        cached_playlist = get_cached_music_service_playlist(
            get_cache_key(playlist),
            music_service.name,
            {'playlists': {get_cache_key(playlist): cache_entry}}
        )
        
        return RemotePlaylistCheckResult(
            music_service_playlist=cached_playlist,
            validation_warning=warning,
            should_update_cache=False,
            cache_updates={},
            snapshot_id=current_snapshot
        )
    
    # Snapshot changed - fetch new version
    LOG.info("⟳ Remote playlist changed: %s (snapshot: %s → %s)", 
             playlist.title, 
             cached_snapshot[:8] if cached_snapshot else 'none', 
             current_snapshot[:8])
    
    try:
        new_playlist = music_service.fetch_remote_playlist(playlist.remote_playlist)
    except MusicServiceError:
        # Re-raise music service errors
        raise
    except Exception as e:
        LOG.error("Unexpected error fetching playlist %s: %s", playlist.title, e)
        raise MusicServiceError(
            message=f"Failed to fetch remote playlist: {e}",
            service_name=music_service.name,
            original_exception=e
        ) from e
    
    current_track_count = len([t for t in new_playlist.tracks if t is not None])
    
    # Validate duration
    if new_playlist.total_duration > duration_threshold:
        # FREEZE - prepare cache updates but don't apply them
        exceeded_by = new_playlist.total_duration - duration_threshold
        
        LOG.warning(
            "⚠️  FROZEN: Remote playlist %s exceeds duration (using cached version)",
            playlist.title
        )
        
        # Get cached version for comparison
        cached_playlist = get_cached_music_service_playlist(
            get_cache_key(playlist),
            music_service.name,
            {'playlists': {get_cache_key(playlist): cache_entry}}
        )
        cached_track_count = len([t for t in cached_playlist.tracks if t is not None])
        cached_at = datetime.fromisoformat(
            cache_entry['music_services'][music_service.name]['cached_at']
        )
        frozen_at = datetime.now(timezone.utc)
        
        # Prepare cache updates (but don't modify cache_entry)
        frozen_reason = {
            'type': 'duration_exceeded',
            'current_duration': str(new_playlist.total_duration),
            'current_track_count': current_track_count,
            'cached_track_count': cached_track_count,
            'limit': str(duration_threshold),
            'exceeded_by': str(exceeded_by),
            'last_checked': frozen_at.isoformat()
        }
        
        cache_updates = {
            'remote_validation_status': 'frozen',
            'remote_frozen_at': frozen_at.isoformat(),
            'remote_frozen_reason': frozen_reason
            # NOTE: Do NOT update remote_snapshot_id - keep checking on next render
        }
        
        # Create warning
        warning = ValidationWarning(
            warning_type='duration_exceeded',
            message=(
                f'This remote playlist now exceeds the 80-minute limit on {music_service.name}. '
                f'Showing last valid version.'
            ),
            details=frozen_reason,
            frozen_at=frozen_at,
            frozen_version_date=cached_at
        )
        
        return RemotePlaylistCheckResult(
            music_service_playlist=cached_playlist,
            validation_warning=warning,
            should_update_cache=True,
            cache_updates=cache_updates,
            snapshot_id=current_snapshot  # Don't update snapshot in cache
        )
    
    # Valid update - unfrozen
    LOG.info("✓ Remote playlist %s updated successfully", playlist.title)
    
    cache_updates = {
        'remote_snapshot_id': current_snapshot,
        'remote_validation_status': 'valid',
        'remote_frozen_at': None,
        'remote_frozen_reason': None
    }
    
    return RemotePlaylistCheckResult(
        music_service_playlist=new_playlist,
        validation_warning=None,
        should_update_cache=True,
        cache_updates=cache_updates,
        snapshot_id=current_snapshot
    )


def _load_rendering_config(config_path: str) -> tuple[str, Path, Path, timedelta, Path, Path]:
    """
    Load configuration for rendering operations.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        tuple: (mixdisc_directory, template_dir, output_dir, duration_threshold, 
                cache_path, track_cache_path)
    """
    config = load_config(config_path)
    mixdisc_directory = config.get(MIXDISC_DIRECTORY_CONFIG)
    template_dir = Path(config.get(TEMPLATE_DIR_CONFIG))
    output_dir = Path(config.get(OUTPUT_DIR_CONFIG))
    duration_threshold = timedelta(
        minutes=config.get(PLAYLIST_DURATION_THRESHOLD_CONFIG)
    )
    cache_path = Path(config.get(CACHE_FILE_CONFIG, '.playlist_cache/playlists_cache.json'))
    track_cache_path = Path(config.get(TRACK_CACHE_FILE_CONFIG, '.playlist_cache/tracks_cache.json'))
    return mixdisc_directory, template_dir, output_dir, duration_threshold, cache_path, track_cache_path


def _get_music_service() -> MusicService:
    """
    Initialize and return the music service to use.
    
    Currently returns Spotify, but could be extended to support
    multiple services based on configuration.
    
    Returns:
        MusicService instance
    """
    return SpotifyMusicService()


def _process_single_playlist(
    playlist,
    music_service: MusicService,
    cache_key: Optional[str] = None,
    cache_data: Optional[dict] = None
) -> ProcessedPlaylist:
    """
    Process a single playlist with a music service.
    Uses cache if available and valid.
    
    Args:
        playlist: Playlist object to process
        music_service: Music service to use for processing
        cache_key: Optional cache key for lookup
        cache_data: Optional cache data dictionary
        
    Returns:
        ProcessedPlaylist with music service data populated
    """
    processed_playlist = ProcessedPlaylist(
        user_playlist=playlist,
        music_service_playlists=[]
    )
    
    # Try cache first
    if cache_key and cache_data:
        cached_playlist = get_cached_music_service_playlist(
            cache_key,
            music_service.name,
            cache_data
        )
        if cached_playlist:
            LOG.debug("Using cached data for %s (%s)", playlist.title, music_service.name)
            processed_playlist.music_service_playlists.append(cached_playlist)
            return processed_playlist
    
    # Cache miss - process normally
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
    duration_threshold: timedelta,
    cache_path: Optional[Path] = None,
    track_cache_path: Optional[Path] = None,
    skip_music_service_if_cached: bool = False
) -> ValidationResult:
    """ 
    Validate a single playlist and optionally update cache.
    
    Args:
        playlist_path: Path to playlist file
        playlist: Loaded Playlist object
        music_service: Music service to use for validation
        duration_threshold: Maximum allowed duration
        cache_path: Path to playlist cache file (for updates)
        track_cache_path: Path to track cache file (for incremental updates)
        skip_music_service_if_cached: If True, use cached data if unchanged
    """

    try:
        # Load track cache if available
        track_cache_data = load_track_cache(track_cache_path) if track_cache_path else None
        
        # Check if we can use cache to skip music service calls
        music_service_playlist = None
        used_cache = False
        
        if skip_music_service_if_cached and cache_path:
            cache_data = load_cache(cache_path)
            cache_key = get_cache_key(playlist)
            cache_entry = cache_data['playlists'].get(cache_key)
            
            if cache_entry and is_cache_valid(playlist, cache_entry):
                # Playlist unchanged - use cached data
                cached_playlist = get_cached_music_service_playlist(
                    cache_key,
                    music_service.name,
                    cache_data
                )
                if cached_playlist:
                    music_service_playlist = cached_playlist
                    used_cache = True
                    LOG.info("✓ [CACHE HIT] Using cached validation for %s", playlist.title)
            else:
                if cache_entry:
                    LOG.info("⟳ [CACHE INVALID] Playlist changed, reprocessing %s", playlist.title)
                else:
                    LOG.info("⟳ [CACHE MISS] Processing %s with music service", playlist.title)
        
        # If not using cache, process with music service (with track cache if available)
        if not music_service_playlist:
            if track_cache_data and hasattr(music_service, 'process_user_playlist_incremental'):
                # Use incremental processing with track cache
                music_service_playlist = music_service.process_user_playlist_incremental(
                    playlist,
                    track_cache_data
                )
            else:
                # Use standard processing
                music_service_playlist = music_service.process_user_playlist(playlist)

        # Calculate missing tracks (only for manual playlists)
        missing_tracks = []
        if playlist.tracks:  # Only check for manual playlists
            missing_tracks = [
                playlist.tracks[i] for i, track in enumerate(music_service_playlist.tracks)
                if track is None
            ]

        is_valid = music_service_playlist.total_duration <= duration_threshold

        # Update playlist cache if cache_path provided and validation passed
        if cache_path and is_valid and not used_cache:
            cache_data = load_cache(cache_path)
            cache_key = get_cache_key(playlist)
            # Get snapshot for remote playlists
            snapshot_id = None
            if playlist.remote_playlist:
                try:
                    snapshot_id = music_service.get_playlist_snapshot(playlist.remote_playlist)
                except Exception as e:
                    LOG.warning("Failed to get snapshot for %s: %s", playlist.title, e)
            update_cache_entry(cache_key, playlist, music_service_playlist, cache_data, snapshot_id)
            save_cache(cache_data, cache_path)
            LOG.debug("Updated playlist cache for %s", playlist.title)
        
        # Save track cache if it was used
        if track_cache_data and track_cache_path:
            save_track_cache(track_cache_data, track_cache_path)
            LOG.debug("Saved track cache")

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

    mixdisc_directory, template_dir, output_dir, playlist_duration_threshold, _, _ = \
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


def render_all_playlists(config_path: str, skip_errors: bool = False, use_cache: bool = True) -> None:
    """
    Render all playlists to HTML without duration validation.
    
    This is intended for use after playlists have been validated
    (e.g., in main branch after PR merge). Unlike run(), this does
    not filter playlists by duration threshold.
    
    Args:
        config_path: Path to configuration file
        skip_errors: If True, continue rendering even if some playlists fail
        use_cache: If True, use cached playlist data when available
    """
    
    LOG.info("Rendering all playlists from config %s", config_path)
    
    mixdisc_directory, template_dir, output_dir, duration_threshold, cache_path, track_cache_path = \
        _load_rendering_config(config_path)
    music_service = _get_music_service()
    
    # Load caches from configured paths
    cache_data = load_cache(cache_path) if use_cache else None
    track_cache_data = load_track_cache(track_cache_path) if use_cache else None
    
    processed_playlists: list[ProcessedPlaylist] = []
    failed_playlists: list[tuple[str, Exception]] = []
    
    # Statistics
    cache_hits = 0
    cache_misses = 0
    remote_snapshot_checks = 0
    remote_frozen = 0
    remote_unfrozen = 0
    
    # Get all playlists
    playlists = list(get_playlists(mixdisc_directory))
    LOG.info("Found %d playlists to render", len(playlists))
    
    # Process each playlist
    cache_updated = False
    for playlist in playlists:
        try:
            cache_key = get_cache_key(playlist) if use_cache else None
            is_cache_hit = False
            validation_warning = None
            
            # Handle remote playlists
            if playlist.remote_playlist:
                if cache_data and cache_key:
                    cache_entry = cache_data['playlists'].get(cache_key, {})
                    
                    if cache_entry:
                        # Check snapshot for remote playlist with error handling
                        remote_snapshot_checks += 1
                        try:
                            result = check_remote_playlist_update(
                                playlist,
                                music_service,
                                cache_entry,
                                duration_threshold
                            )
                            
                            # Extract results
                            music_service_playlist = result.music_service_playlist
                            validation_warning = result.validation_warning
                            
                            # Apply cache updates if needed
                            if result.should_update_cache:
                                # Track if this is a state transition
                                old_status = cache_entry.get('remote_validation_status')
                                new_status = result.cache_updates.get('remote_validation_status')
                                
                                for key, value in result.cache_updates.items():
                                    cache_entry[key] = value
                                
                                # CRITICAL: Persist cache immediately after state change
                                save_cache(cache_data, cache_path)
                                LOG.debug("Persisted cache updates for %s", playlist.title)
                                cache_updated = False  # Already saved
                                
                                # Log state transitions
                                if new_status and new_status != old_status:
                                    if new_status == 'frozen':
                                        remote_frozen += 1
                                        LOG.warning("⚠️  Remote playlist frozen: %s by %s", 
                                                  playlist.title, playlist.user)
                                    elif new_status == 'valid' and old_status == 'frozen':
                                        remote_unfrozen += 1
                                        LOG.info("✓ Remote playlist unfrozen: %s by %s", 
                                               playlist.title, playlist.user)
                            
                        except MusicServiceError as e:
                            # Music service errors - use cached version
                            LOG.error(
                                "Failed to check remote playlist update for '%s': %s. Using cached version.",
                                playlist.title, e
                            )
                            music_service_playlist = get_cached_music_service_playlist(
                                cache_key,
                                music_service.name,
                                cache_data
                            )
                            validation_warning = None
                            
                        except Exception as e:
                            # Unexpected errors - log and skip playlist
                            LOG.error(
                                "Unexpected error processing remote playlist '%s': %s. Skipping.",
                                playlist.title, e, exc_info=True
                            )
                            failed_playlists.append((playlist.title, e))
                            continue
                            
                    else:
                        # New remote playlist - fetch
                        LOG.info("⟳ [NEW REMOTE] Processing %s by %s", playlist.title, playlist.user)
                        cache_misses += 1
                        try:
                            music_service_playlist = music_service.fetch_remote_playlist(playlist.remote_playlist)
                            
                            # Get snapshot for cache
                            try:
                                snapshot_id = music_service.get_playlist_snapshot(playlist.remote_playlist)
                                update_cache_entry(cache_key, playlist, music_service_playlist, cache_data, snapshot_id)
                            except Exception as e:
                                LOG.warning("Failed to get snapshot for %s: %s", playlist.title, e)
                                update_cache_entry(cache_key, playlist, music_service_playlist, cache_data)
                            
                            save_cache(cache_data, cache_path)
                            cache_updated = False  # Already saved
                            validation_warning = None
                            
                        except MusicServiceError as e:
                            LOG.error("Failed to fetch new remote playlist '%s': %s. Skipping.", 
                                    playlist.title, e)
                            failed_playlists.append((playlist.title, e))
                            continue
                        except Exception as e:
                            LOG.error("Unexpected error fetching remote playlist '%s': %s. Skipping.",
                                    playlist.title, e, exc_info=True)
                            failed_playlists.append((playlist.title, e))
                            continue
                else:
                    # No cache - fetch remote playlist
                    try:
                        music_service_playlist = music_service.fetch_remote_playlist(playlist.remote_playlist)
                        validation_warning = None
                    except MusicServiceError as e:
                        LOG.error("Failed to fetch remote playlist '%s': %s. Skipping.", 
                                playlist.title, e)
                        failed_playlists.append((playlist.title, e))
                        continue
                    except Exception as e:
                        LOG.error("Unexpected error fetching remote playlist '%s': %s. Skipping.",
                                playlist.title, e, exc_info=True)
                        failed_playlists.append((playlist.title, e))
                        continue
                
                processed_playlist = ProcessedPlaylist(
                    user_playlist=playlist,
                    music_service_playlists=[music_service_playlist],
                    validation_warning=validation_warning
                )
                
            # Handle manual playlists (existing logic with track cache)
            else:
                validation_warning = None
                if cache_data and cache_key:
                    cache_entry = cache_data['playlists'].get(cache_key)
                    if cache_entry and is_cache_valid(playlist, cache_entry):
                        cache_hits += 1
                        is_cache_hit = True
                        LOG.info("✓ [CACHE HIT] %s by %s", playlist.title, playlist.user)
                    else:
                        cache_misses += 1
                        LOG.info("⟳ [CACHE MISS] Processing %s by %s", playlist.title, playlist.user)
                
                # Process with track cache if available
                if track_cache_data and hasattr(music_service, 'process_user_playlist_incremental'):
                    music_service_playlist = music_service.process_user_playlist_incremental(
                        playlist,
                        track_cache_data
                    )
                else:
                    music_service_playlist = music_service.process_user_playlist(playlist)
                
                processed_playlist = ProcessedPlaylist(
                    user_playlist=playlist,
                    music_service_playlists=[music_service_playlist],
                    validation_warning=validation_warning
                )
                
                # Update cache if miss
                if cache_data and cache_key and not is_cache_hit:
                    update_cache_entry(cache_key, playlist, music_service_playlist, cache_data)
                    cache_updated = True
            
            processed_playlists.append(processed_playlist)
            
            LOG.debug(
                "Rendered: %s (duration: %s, tracks: %d)%s",
                playlist.title,
                processed_playlist.music_service_playlists[0].total_duration,
                len([t for t in processed_playlist.music_service_playlists[0].tracks if t is not None]),
                " [FROZEN]" if validation_warning else ""
            )
            
        except Exception as e:
            error_msg = f"Failed to process playlist {playlist.title} by {playlist.user}"
            LOG.error("%s: %s", error_msg, e)
            failed_playlists.append((f"{playlist.user}/{playlist.title}", e))
            
            if not skip_errors:
                raise Exception(f"{error_msg}: {e}") from e
    
    # Save caches if updated or clean up stale entries
    if cache_data and use_cache:
        removed = cleanup_stale_cache_entries(cache_data, playlists)
        if removed > 0:
            LOG.info("Cleaned up %d stale cache entries", removed)
            cache_updated = True
        
        if cache_updated:
            save_cache(cache_data, cache_path)
            LOG.debug("Cache saved to %s", cache_path)
    
    # Save track cache
    if track_cache_data and use_cache:
        save_track_cache(track_cache_data, track_cache_path)
        LOG.debug("Track cache saved to %s", track_cache_path)
    
    # Render to HTML
    LOG.info("Rendering HTML output to %s", output_dir)
    render_output(processed_playlists, output_dir, template_dir)
    
    # Summary with cache stats
    LOG.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    LOG.info("Rendering complete!")
    LOG.info("  Total playlists: %d", len(playlists))
    LOG.info("  Successfully rendered: %d", len(processed_playlists))
    LOG.info("  Failed: %d", len(failed_playlists))
    if use_cache:
        LOG.info("  Cache hits: %d", cache_hits)
        LOG.info("  Cache misses: %d", cache_misses)
        LOG.info("  Cache efficiency: %.1f%%", (cache_hits / len(playlists) * 100) if playlists else 0)
    if remote_snapshot_checks > 0:
        LOG.info("  Remote playlists checked: %d", remote_snapshot_checks)
        if remote_frozen > 0:
            LOG.warning("  Remote playlists frozen: %d", remote_frozen)
        if remote_unfrozen > 0:
            LOG.info("  Remote playlists unfrozen: %d", remote_unfrozen)
    LOG.info("  Output: %s/index.html", output_dir)
    
    if failed_playlists:
        LOG.warning("Failed playlists:")
        for playlist_name, error in failed_playlists:
            LOG.warning("  - %s: %s", playlist_name, error)
    
    if failed_playlists and not skip_errors:
        raise Exception(f"Rendering completed with {len(failed_playlists)} errors")


def validate_playlists_from_files(
    config_path: str,
    playlist_files: list[Path],
    update_cache: bool = False
) -> list[ValidationResult]:
    """ Validate specific playlist files and optionally update cache """

    LOG.info("Validating %d playlist file(s)", len(playlist_files))

    mixdisc_directory, _, _, playlist_duration_threshold, cache_path, track_cache_path = _load_rendering_config(config_path)
    music_service = _get_music_service()

    results = []

    # Load all existing playlists for uniqueness checking, EXCLUDING files being validated
    # (to avoid detecting a file as duplicate of itself)
    existing_playlists = []
    for playlist in get_playlists(mixdisc_directory):
        # Only include if this playlist file is NOT being validated
        if playlist.filepath not in playlist_files:
            existing_playlists.append(playlist)
    LOG.debug("Loaded %d existing playlists for uniqueness checking (excluding files being validated)", len(existing_playlists))

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
            playlist_duration_threshold,
            cache_path=cache_path if update_cache else None,
            track_cache_path=track_cache_path if update_cache else None,
            skip_music_service_if_cached=update_cache  # Use cache during validation if updating cache
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
