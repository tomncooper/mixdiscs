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

- **`configuration.py`** - Configuration management

- **`playlists.py`** - Playlist parsing and handling

- **`music_service/`** - Music service integrations
  - `music_service.py` - Base classes and interfaces for Track, MusicService, MusicServicePlaylist, ProcessedPlaylist
  - `spotify.py` - Spotify-specific implementation using Spotipy library

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
- `playlist` - List of tracks in "Artist - Song Title" format

Example: `mixdiscs/MixMasterTest/Testy McTest List.yaml`

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
3. **Pull Request Workflow** - CI validates and processes playlists automatically
4. **Multi-Service Support** - Architecture supports multiple music services (currently Spotify)
5. **Template-Based Output** - Generates formatted output from processed playlists

## Contributing Playlists

Users can contribute by:
1. Creating a YAML file in `mixdiscs/` directory
2. Listing tracks in "Artist - Song Title" format
3. Submitting a pull request
4. CI validates duration and creates the playlist on the music service

## Agent Guidelines

When working with this codebase, AI agents should:

- **Use Context7 MCP Server** - For any questions about external libraries (especially `spotipy` for Spotify integration), use the Context7 MCP server to get accurate, up-to-date API documentation
- **Understand Dependencies** - Check `pyproject.toml` for Python dependencies and their versions
- **Test Duration Logic** - The 80-minute validation is core functionality; ensure changes don't break this
- **Respect YAML Format** - Maintain the simple "Artist - Song Title" format for user playlists
- **Preserve Multi-Service Architecture** - Keep the music service abstraction layer for future service additions
- **Validation Functions** - The codebase now has two modes:
  - `run` mode: Process all playlists in a directory (batch processing)
  - `validate` mode: Validate specific playlist files (used for PR validation)
- **Testing Validation** - Use the `validate` command with local test files before modifying validation logic
- **GitHub Action** - PR validation happens automatically via `.github/workflows/validate-playlists.yml`
- **Folder Structure** - Playlists are organized by username:
  - Structure: `mixdiscs/<username>/<playlist>.yaml`
  - Username validation enforced (format, folder match, uniqueness)
  - Use `scripts/migrate_to_folders.sh` to migrate flat structures
