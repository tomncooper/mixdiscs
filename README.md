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

## Contributing a Playlist

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
4. **CI Checks:**
   - **Username format**: 3-30 characters, alphanumeric with underscores/hyphens only (no spaces).
   - **Folder structure**: The playlist file should be at `mixdiscs/<username>/<playlist>.yaml`.
   - **Username match**: The `user` field must match the folder name (case-sensitive)
   - **Global uniqueness**: No other playlist with the same username-title combination can exist. Baiscally, don't put the same title in two of your playlists.
   - **Required fields**: All fields (`user`, `title`, `description`, `genre`) are required and cannot be blank.
   - **Playlist tracks**: Must contain at least one track.
   - **Track format**: Each track must be in the format: `Artist - Song Title` (with a space-dash-space separator).
   - Neither artist name nor song title can be blank.
5. Submit a pull request
6. The CI will automatically validate:
   - Folder structure is correct
   - Username matches folder name
   - No duplicate username-playlist combinations
   - All required fields are present and not blank
   - Track format is correct
   - All tracks can be found on Spotify
   - Total duration is ≤80 minutes
7. If validation passes, your playlist will be merged!
8. After merge, playlists are automatically rendered to HTML and published to GitHub Pages

## How It Works

### Pull Request Flow
1. You submit a PR with your playlist
2. GitHub Action validates the playlist
3. If valid, PR can be merged

### Merge to Main Flow
1. PR is merged to main
2. GitHub Action automatically renders all playlists to HTML
3. HTML is deployed to GitHub Pages
4. Your playlist appears on the live site!

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

### Test Structure

```
tests/
├── unit/                    # Unit tests for individual modules
│   ├── test_configuration.py
│   ├── test_playlists.py
│   ├── test_validation.py
│   ├── test_cache.py
│   ├── test_track_cache.py
│   ├── test_main.py
│   └── music_service/
│       └── test_music_service.py
├── integration/             # Integration tests (future)
├── fixtures/                # Test data files
│   ├── playlists/
│   └── configs/
└── conftest.py             # Shared test fixtures
```

### Coverage Goals

- **Overall:** ≥65%
- **Critical modules:** ≥90%
  - `playlists.py` - 91%
  - `validation.py` - 95%
  - `cache.py` - 95%
  - `track_cache.py` - 89%

### Continuous Integration

Tests automatically run on every pull request that modifies code. The GitHub Actions workflow:
1. Installs dependencies
2. Runs linter (optional)
3. Runs type checker (optional)
4. Executes all tests with coverage
5. Fails if coverage drops below 65%
6. Uploads coverage reports as artifacts

See `.github/workflows/test.yml` for details.
