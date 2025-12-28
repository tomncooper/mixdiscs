```
 __  __  _       ____   _               
|  \/  |(_)     |  _  \(_)              
| .  . | _ __  _| | | | _ ___  ___  ___ 
| |\/| || |\ \/ / | | || / __|/ __|/ __|
| |  | || | >  <| |/ / | \__ \ (__ \__ \
\_|  |_/|_|/_/\_\___/  |_|___/\___||___/
```

Playlist sharing....but nerdier!

You can add your playlist via a pull request, the CI will check the specified music service (currently ony Spotify but more are coming) to find the songs and, this is the crucial part, make sure it is less than 80 minuets long. Than's it, you have 80 mins, the length of a [MiniDisc](https://en.wikipedia.org/wiki/MiniDisc) (told you it was nerdy) or a CD-R (remember them).

Your playlists will be checked in CI to make sure the tracks exist and you have meet the length criteria then it will be rendered in all its glory on [mixdiscs.com](https://mixdiscs.com/). I am working on the auto-generated MiniDiscs... 

## Table of Contents

- [Contributing a Playlist](#contributing-a-playlist)
- [Understanding Frozen Playlists](#understanding-frozen-playlists)
- [Development](#development)
- [Testing](#testing)

## Contributing a Playlist

You can contribute playlists in two ways: **manual playlists** or **remote playlists**.

### Option 1: Manual Playlist

1. Create a folder with your username in the `mixdiscs/` directory: `mixdiscs/YourUsername/`
2. Create a YAML file for your playlist: `mixdiscs/YourUsername/Your Playlist Title.yaml`
3. Follow this structure:
```yaml
user: YourUsername
title: Your Playlist Title
description: A description of your playlist
genre: rock
playlist:
  - Artist Name - Song Title
  - Another Artist - Another Song
```

### Option 2: Remote Playlist

Instead of listing tracks manually, you can link to an existing Spotify playlist:

1. Create a folder with your username in the `mixdiscs/` directory: `mixdiscs/YourUsername/`
2. Create a YAML file for your playlist: `mixdiscs/YourUsername/Your Playlist Title.yaml`
3. Follow this structure:
```yaml
user: YourUsername
title: Your Playlist Title
description: A description of your playlist
genre: electronic
remote_playlist: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
```

**Remote Playlist Features:**
- 🔗 Automatically syncs from your Spotify playlist
- 🔄 Updates when you change your Spotify playlist
- ⚠️ **Frozen Playlists**: If you change your remote playlist and that results in it exceeding 80 minutes, it will be "frozen" at the last valid version and display a warning. Simply remove tracks until you are below the limit to unfreeze it.

**Spotify URL Formats Supported:**
- Web URL: `https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M`
- Spotify URI: `spotify:playlist:37i9dQZF1DXcBWIGoYBM5M`

**Note:** You cannot have both `playlist` and `remote_playlist` fields in the same YAML file. Choose one format per playlist.

### Validation Rules (Both Types)

4. **CI Checks:**
   - **Username format**: 3-30 characters, alphanumeric with underscores/hyphens only (no spaces).
   - **Folder structure**: The playlist file should be at `mixdiscs/<username>/<playlist>.yaml`.
   - **Username match**: The `user` field must match the folder name (case-sensitive)
   - **Global uniqueness**: No other playlist with the same username-title combination can exist. Baiscally, don't put the same title in two of your playlists.
   - **Required fields**: All fields (`user`, `title`, `description`, `genre`) are required and cannot be blank.
   - **Manual playlists**: Must contain at least one track in the `playlist` field.
   - **Remote playlists**: Must have a valid Spotify URL in the `remote_playlist` field.
   - **Track format** (manual only): Each track must be in the format: `Artist - Song Title` (with a space-dash-space separator).
   - Neither artist name nor song title can be blank (manual playlists).
5. Submit a pull request
6. The CI will automatically validate:
   - Folder structure is correct
   - Username matches folder name
   - No duplicate username-playlist combinations
   - All required fields are present and not blank
   - Track format is correct (manual playlists)
   - All tracks can be found on Spotify (manual playlists)
   - Spotify URL is valid (remote playlists)
   - Playlist is accessible and under 80 minutes (remote playlists)
   - Total duration is ≤80 minutes
7. If validation passes, your playlist will be merged!
8. After merge, playlists are automatically rendered to HTML and published to GitHub Pages

## Understanding Frozen Playlists

If you submit a **remote playlist** that later exceeds the 80-minute limit on Spotify:

- 🧊 **Your playlist will be "frozen"** at its last valid version
- ⚠️ **A warning icon** will appear next to your playlist
- 📌 **The cached version** from when it was valid will be displayed
- 🔗 **Direct link to Spotify** so you can edit it
- ✅ **Automatic unfreeze** once you remove tracks to get back under 80 minutes

**Why frozen?** This ensures the site always shows valid 80-minute playlists while giving you control over your Spotify playlist.

**How to unfreeze:** Simply remove tracks from your Spotify playlist to get under 80 minutes. The next time the site updates, it will automatically unfreeze and show the current version.

## Development

To run locally you will need to export envars containing your spotify credentials:

```bash
 export SPOTIPY_CLIENT_ID='<client-id>'
 export SPOTIPY_CLIENT_SECRET='<client-secret>'
```

### Process All Playlists

You can then run the app with:

```bash
uv run python app.py run config.yaml
```

### Validate Specific Playlists

To validate specific playlist files:

```bash
uv run python app.py validate config.yaml --files mixdiscs/file1.yaml mixdiscs/file2.yaml
```

This is useful for testing your playlist before submitting a PR.

### Render All Playlists to HTML

To render all playlists to HTML (used by CI after merge):

```bash
uv run python app.py render config.yaml
```

This will generate `site_files/index.html` with all playlists.

Options:
- `--skip-errors` - Continue rendering even if some playlists fail

### Validate Changed Playlists (Helper Script)

To quickly validate all playlists that have changed compared to the main branch:

```bash
./scripts/validate_changed.sh
```

This script:
1. Finds all modified/added playlist files compared to main
2. Validates them using the validate command
3. Requires Spotify credentials to be exported

## Testing

This project has comprehensive unit tests to ensure reliability and maintainability.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=mixdiscer --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_playlists.py

# Run tests matching a pattern
uv run pytest -k "test_validate"

# Run with verbose output
uv run pytest -v

# Run without capturing output (useful for debugging)
uv run pytest -s
```
