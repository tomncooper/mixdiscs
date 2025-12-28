# AGENTS.md

## Project Overview

**MixDiscs** is a nerdy playlist sharing platform where users submit playlists via pull requests. The system validates that playlists are under 80 minutes (the length of a MiniDisc or CD-R) and automatically creates playlists on music streaming services.

## Project Structure

### Code (`mixdiscer/`)
The main application code that processes playlists and interacts with music services:

- **`main.py`** - Entry point containing the core playlist processing logic
  - Loads configuration
  - Processes user playlists from YAML files
  - Validates playlist duration against 80-minute threshold
  - Integrates with music services (currently Spotify)
  - Generates output using templates
  - **Remote Playlist Update Logic:**
    - `check_remote_playlist_update()` - Checks for remote playlist changes using snapshots
    - Returns `RemotePlaylistCheckResult` with playlist data and cache update instructions
    - Raises `MusicServiceError` on API failures (graceful error handling)
    - `_build_frozen_warning()` - Constructs frozen playlist warnings from cache

- **`configuration.py`** - Configuration management

- **`playlists.py`** - Playlist parsing and handling

- **`music_service/`** - Music service integrations
  - `music_service.py` - Base classes and interfaces
    - `Track` - Individual song metadata
    - `MusicService` - Abstract base for service implementations
    - `MusicServicePlaylist` - Processed playlist with tracks
    - `ProcessedPlaylist` - User playlist + service playlist(s) + warnings
    - `ValidationWarning` - Frozen playlist warning metadata
    - `MusicServiceError` - Service-specific exceptions
  - `spotify.py` - Spotify-specific implementation using Spotipy library
    - `extract_playlist_id()` - Parses Spotify URLs/URIs
    - `get_playlist_snapshot()` - Gets current snapshot (lightweight check)
    - `fetch_remote_playlist()` - Fetches full playlist with pagination
    - `process_user_playlist()` - Processes both manual and remote playlists

- **`cache.py`** - Playlist cache management
  - Stores processed playlists to reduce API calls
  - Tracks remote playlist snapshots for change detection
  - Manages frozen playlist metadata (validation status, freeze timestamp, reason)
  - `update_cache_entry()` - Updates cache with snapshot and frozen state
  - **Cache Persistence:** Immediately saved after frozen/unfrozen state changes
  
- **`track_cache.py`** - Individual track cache
  - Caches track search results
  - Reduces redundant Spotify API calls

- **`output/`** - Output generation and rendering

### Playlists (`mixdiscs/`)
User-submitted playlists in username-based folder structure:
- Structure: `mixdiscs/<username>/<playlist-title>.yaml`
- Each user has their own folder
- Username in YAML must match folder name (case-sensitive)
- Username-playlist combinations must be globally unique

Each playlist file contains:
- `user` - Playlist creator (must match folder name)
- `title` - Playlist name
- `description` - Playlist description
- `genre` - Music genre
- **Either:**
  - `playlist` - List of tracks in "Artist - Song Title" format (manual playlist)
  - `remote_playlist` - Spotify URL/URI linking to an existing playlist (remote playlist)

**Manual Playlist Example:** `mixdiscs/MixMasterTest/Testy McTest List.yaml`
```yaml
user: MixMasterTest
title: Testy McTest List
description: A test playlist
genre: rock
playlist:
  - The Beatles - Hey Jude
  - Queen - Bohemian Rhapsody
```

**Remote Playlist Example:** `mixdiscs/MixMasterTest/My Spotify Playlist.yaml`
```yaml
user: MixMasterTest
title: My Spotify Playlist
description: My curated Spotify playlist
genre: electronic
remote_playlist: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
```

## Running the Application

### Prerequisites
Export Spotify API credentials:
```bash
export SPOTIPY_CLIENT_ID='<client-id>'
export SPOTIPY_CLIENT_SECRET='<client-secret>'
```

### Execution
```bash
uv run python app.py config.yaml
```

## Key Concepts

1. **80-Minute Limit** - Playlists must be ≤80 minutes (MiniDisc/CD-R capacity)
2. **YAML-Based Playlists** - Simple text format for playlist submission
3. **Manual vs Remote Playlists**:
   - **Manual**: Users list tracks directly in YAML
   - **Remote**: Users link to existing Spotify playlist
4. **Pull Request Workflow** - CI validates and processes playlists automatically
5. **Multi-Service Support** - Architecture supports multiple music services (currently Spotify)
6. **Template-Based Output** - Generates formatted output from processed playlists
7. **Snapshot-Based Caching** - Remote playlists use Spotify snapshots to detect changes efficiently
8. **Frozen Playlists** - Remote playlists that exceed 80 minutes are frozen at last valid version

## Remote Playlist Architecture

### Overview

Remote playlists allow users to link to existing Spotify playlists instead of manually listing tracks. The system automatically fetches tracks from Spotify and uses a snapshot-based caching strategy to minimize API calls.

### How It Works

#### 1. Initial Submission (PR)
```
User creates YAML with remote_playlist URL
    ↓
CI validates:
  - URL format (Spotify domain)
  - Playlist accessibility
  - Duration ≤ 80 minutes
    ↓
PR merged if valid
```

#### 2. First Render (Post-Merge)
```
System detects remote playlist
    ↓
Fetch full playlist from Spotify API
    ↓
Get snapshot_id (unique version identifier)
    ↓
Cache: tracks + snapshot_id + metadata
    ↓
Render to HTML with "🔗 Remote" badge
```

#### 3. Subsequent Renders (Updates)
```
System checks snapshot_id (1 API call)
    ↓
Compare with cached snapshot
    ├─ Same → Use cached tracks (0 additional API calls)
    └─ Different → Fetch full playlist (1 API call)
                   ↓
                   Validate duration
                   ├─ ≤ 80min → Update cache, render
                   └─ > 80min → FREEZE (see below)
```

**API Efficiency:** 
- Unchanged playlist: 1 API call (snapshot check only)
- Changed playlist: 2 API calls (snapshot + full fetch)
- **50% reduction** in API calls for stable playlists

### Frozen Playlist Logic

When a remote playlist exceeds 80 minutes:

#### Freeze Behavior
```
Remote playlist changed (snapshot differs)
    ↓
check_remote_playlist_update() called
    ↓
Fetch new version from Spotify
    ↓
Duration > 80 minutes?
    ↓
YES - FREEZE:
  - Returns RemotePlaylistCheckResult with:
    - music_service_playlist: cached (valid) version
    - validation_warning: frozen warning details
    - should_update_cache: True
    - cache_updates: {
        remote_validation_status: 'frozen',
        frozen_at: timestamp,
        frozen_reason: {duration, track counts, etc.}
        // NOTE: snapshot_id NOT updated - keep checking
      }
    ↓
Caller applies cache_updates to cache entry
    ↓
Immediately persist with save_cache() (atomic)
    ↓
Render with 🧊 frozen badge and ⚠️ warning
    ↓
Display frozen playlists page with:
  - Freeze information
  - What changed
  - How to fix
```

#### Unfreeze Behavior
```
Next render:
  Snapshot still different (keep checking)
    ↓
  check_remote_playlist_update() called
    ↓
  Fetch new version
    ↓
  Duration ≤ 80 minutes?
    ↓
  YES - UNFREEZE:
    - Returns RemotePlaylistCheckResult with:
      - music_service_playlist: new (valid) version
      - validation_warning: None
      - should_update_cache: True
      - cache_updates: {
          remote_snapshot_id: current_snapshot,
          remote_validation_status: 'valid',
          frozen_at: None,
          frozen_reason: None
        }
    ↓
  Caller applies updates and save_cache()
    ↓
  Render normally (no warnings)
```

#### Error Handling (Robust Design)
```
check_remote_playlist_update() encounters error
    ↓
MusicServiceError raised (API failures)
    ↓
Caller catches exception
    ↓
Two options:
  1. Use cached version (graceful degradation)
  2. Skip playlist and log (unexpected errors)
    ↓
Rendering continues for other playlists
    ↓
No crashes, partial failures handled
```

### Data Structures

**Playlist (dataclass):**
```python
@dataclass
class Playlist:
    user: str
    title: str
    description: str
    genre: str
    tracks: Optional[list[tuple[str, str, Optional[str]]]] = None  # Manual: (artist, title, album)
    remote_playlist: Optional[str] = None        # Remote: Spotify URL/URI
    remote_service: str = "spotify"              # Service identifier
    filepath: Optional[Path] = None              # Source file path
```

**RemotePlaylistCheckResult (dataclass):**
```python
@dataclass
class RemotePlaylistCheckResult:
    music_service_playlist: MusicServicePlaylist  # Playlist to use
    validation_warning: Optional[ValidationWarning]  # Frozen warning if applicable
    should_update_cache: bool                     # Whether cache needs updating
    cache_updates: dict                           # Fields to update in cache
    snapshot_id: Optional[str]                    # Current snapshot (for logging)
```

**Cache Entry (remote playlist):**
```json
{
  "user": "Username",
  "title": "Playlist Title",
  "filepath": "mixdiscs/Username/Playlist.yaml",
  "content_hash": "abc123...",
  "remote_playlist_url": "https://open.spotify.com/playlist/...",
  "remote_snapshot_id": "snapshot_xyz",
  "remote_validation_status": "valid|frozen",
  "remote_frozen_at": "2024-12-27T10:00:00Z",
  "remote_frozen_reason": {
    "type": "duration_exceeded",
    "current_duration": "85:23",
    "current_track_count": 25,
    "cached_track_count": 20,
    "limit": "80:00",
    "exceeded_by": "5:23",
    "last_checked": "2024-12-27T10:00:00Z"
  },
  "music_services": {
    "spotify": {
      "tracks": [...],
      "total_duration_seconds": 4500,
      "cached_at": "2024-12-27T10:00:00Z"
    }
  }
}
```

**ValidationWarning (dataclass):**
```python
@dataclass
class ValidationWarning:
    warning_type: str                        # "duration_exceeded", etc.
    message: str                             # User-facing message
    details: dict                            # Duration, track counts, exceeded_by, etc.
    frozen_at: Optional[datetime] = None     # When frozen (ISO format in cache)
    frozen_version_date: Optional[datetime] = None  # Cached version date
```

### UI Components

**Main Page (`index.html`):**
- 🔗 "Remote" badge next to title (links to Spotify)
- 🧊 "Frozen" badge (if frozen)
- ⚠️ Warning message below playlist (if frozen)
- Tooltip shows freeze details

**Frozen Playlists Page (`frozen-playlists.html`):**
- Always generated (even if empty)
- List of all frozen playlists
- Three-column layout:
  - **Frozen Information:** Frozen date, cached version date
  - **Duration Issue:** Remote duration, limit, exceeded amount
  - **Track Count:** Remote vs cached track counts, difference
- "How to fix" instructions
- Direct links to edit on Spotify

### Cache Strategy

**Why Snapshot-Based?**
- Spotify provides snapshot_id that changes when playlist is modified
- Single API call to check for changes
- Avoids fetching full playlist every time
- Efficient for unchanged playlists

**Cache Invalidation:**
- YAML file changes (content_hash) → Clear cache
- Snapshot changes → Refetch playlist
- Manual cache clear → Re-fetch on next render

**Cache Persistence (Critical for Frozen State):**
- **Atomic writes:** Cache saved immediately after frozen/unfrozen state changes
- **Separation of concerns:** `check_remote_playlist_update()` doesn't modify cache
- **Transaction pattern:** 
  1. Get cache update instructions from function
  2. Apply updates to cache entry
  3. Immediately call `save_cache()`
- **Error safety:** If error occurs after state change, cache is already persisted

**Cache Location:**
- `.playlist_cache/playlists_cache.json` - Playlist metadata and tracks
- `.playlist_cache/tracks_cache.json` - Individual track search results (manual playlists)

## Contributing Playlists

Users can contribute by:
1. Creating a YAML file in `mixdiscs/` directory
2. Listing tracks in "Artist - Song Title" format
3. Submitting a pull request
4. CI validates duration and creates the playlist on the music service

## Agent Guidelines

When working with this codebase, AI agents should:

### External Dependencies
- **Use Context7 MCP Server** - For any questions about external libraries (especially `spotipy` for Spotify integration), use the Context7 MCP server to get accurate, up-to-date API documentation
- **Understand Dependencies** - Check `pyproject.toml` for Python dependencies and their versions

### Core Functionality
- **Test Duration Logic** - The 80-minute validation is core functionality; ensure changes don't break this
- **Respect YAML Format** - Maintain the simple "Artist - Song Title" format for manual playlists
- **Preserve Multi-Service Architecture** - Keep the music service abstraction layer for future service additions

### Modes of Operation
- **Validation Functions** - The codebase has multiple modes:
  - `validate` mode: Validate specific playlist files (used for PR validation)
  - `render` mode: Render all playlists to HTML (post-merge)
  - `run` mode: End-to-end processing (validate + render)
- **Testing Validation** - Use the `validate` command with local test files before modifying validation logic
- **GitHub Action** - PR validation happens automatically via `.github/workflows/validate-playlists.yml`

### File Organization
- **Folder Structure** - Playlists are organized by username:
  - Structure: `mixdiscs/<username>/<playlist>.yaml`
  - Username validation enforced (format, folder match, uniqueness)
  - Use `scripts/migrate_to_folders.sh` to migrate flat structures

### Remote Playlists (Critical Patterns)
- **Snapshot-First Pattern**: Always check snapshot before fetching full playlist
- **Error Handling**: `check_remote_playlist_update()` raises `MusicServiceError` on failures
  - Caller must catch and handle gracefully
  - Use cached version for `MusicServiceError`
  - Skip playlist for unexpected errors
- **Return Value Pattern**: Function returns `RemotePlaylistCheckResult` dataclass
  - Contains: playlist, warning, cache_updates dict, flags
  - Does NOT modify cache directly
  - Caller applies cache updates and persists immediately
- **State Transitions**: 
  - valid → frozen: Cache saved immediately after detecting over-limit
  - frozen → valid: Cache saved immediately after detecting under-limit
  - Prevents state loss on errors

### Cache Management (Critical for Data Integrity)
- **Atomic Persistence**: 
  - Cache must be saved immediately after frozen/unfrozen state changes
  - Pattern: `apply updates → save_cache() → continue`
  - Do NOT batch cache saves across playlists
- **Playlist Cache**: Full playlist metadata and tracks
- **Track Cache**: Individual track lookup results (manual playlists)
- **Snapshot-Based Invalidation**: Remote playlists use snapshot comparison

### Frozen Playlist Handling
- **Freeze Logic**: When remote playlist exceeds 80 minutes:
  1. Return cached (valid) version
  2. Create `ValidationWarning` with details
  3. Return cache_updates with frozen state
  4. Caller persists immediately
- **Unfreeze Logic**: When remote playlist returns to ≤80 minutes:
  1. Return new (valid) version
  2. No warning
  3. Return cache_updates clearing frozen state
  4. Caller persists immediately
- **UI Display**: 
  - Show frozen badge and warning
  - Provide actionable fix instructions
  - Link to Spotify for editing
- **Testing**: Test both freeze and unfreeze workflows

### Testing Strategy
- **Unit Tests**: 162 tests covering all functionality
- **Remote Playlist Tests**: 
  - `test_check_remote_update.py` - Update checking logic
  - `test_spotify_remote.py` - Spotify integration
  - `test_render_remote.py` - Rendering with frozen playlists
  - `test_cache_remote.py` - Cache persistence
- **Integration Tests**: `test_remote_playlist_workflow.py` - End-to-end scenarios
- **Run Before Commit**: `uv run pytest tests/ -v`

### Common Pitfalls to Avoid
- ❌ Modifying cache inside `check_remote_playlist_update()` (breaks transaction pattern)
- ❌ Batching cache saves (loses frozen state on errors)
- ❌ Returning None on errors (use exceptions instead)
- ❌ Ignoring `should_update_cache` flag (causes stale cache)
- ❌ Not testing frozen → unfrozen transitions (common edge case)
