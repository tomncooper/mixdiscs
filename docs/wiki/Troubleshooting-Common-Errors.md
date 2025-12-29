# Troubleshooting Common Errors

Your PR failed CI validation? Here's how to fix the most common issues.

## "Duration exceeds limit"

**Problem**: Your playlist is over 80 minutes.

**Fix**: Remove tracks until you're under 80:00.

```bash
# Check locally before submitting - but you will need a Spotify API key
uv run python app.py validate config.yaml --files mixdiscs/YourUsername/playlist.yaml
```

## "Track not found: Artist - Song"

**Problem**: Spotify can't find one of your tracks.

**Fix**:
- Check spelling of artist and song name
- Try the track on [Spotify](https://open.spotify.com/) to verify it exists
- Replace with a different track if it's been removed

## Mixdisc chose the wrong track!?

There can be many different versions of a track on a given music service. 
For example there can be the original album track, remixes or live versions.
To really narrow down the search you can add an optional album to the tracks. 
Use the format:

```yaml
playlist:
    - track_name - artist_name | album_name
```

## "Username mismatch"

**Problem**: Your `user` field doesn't match your folder name.

**Fix**: Make them match exactly (case-sensitive)
```yaml
# Folder: mixdiscs/MusicLover/
✅ user: MusicLover
❌ user: musiclover
```

## "Duplicate username-title combination"

**Problem**: You already have a playlist with that title.

**Fix**: Choose a different, unique title.

## "Invalid track format"

**Problem**: Track doesn't follow `Artist - Song` format.

**Fix**: Use space-dash-space separator
```yaml
✅ - The Beatles - Let It Be
❌ - The Beatles: Let It Be
❌ - Let It Be
```

## "Remote playlist not accessible"

**Problem**: Your Spotify playlist is private or doesn't exist.

**Fix**:
- Make your playlist **public** on Spotify
- Verify the URL is correct
- Check you're using a playlist URL, not a track/album URL

## "Required field missing"

**Problem**: Your YAML is missing a required field.

**Fix**: Ensure all these fields exist and aren't empty:
```yaml
user: YourUsername        # Required, 3-30 chars
title: Playlist Title     # Required, unique for you
description: Some text    # Required, any text
genre: rock               # Required, any genre
```

## Still Stuck?

1. Check the [Validation Rules Reference](Validation-Rules-Reference) for detailed requirements
2. Look at existing playlists in the `mixdiscs/` folder for examples
3. [Open an issue](https://github.com/tomncooper/mixdiscs/issues) with your error message
