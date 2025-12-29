# Validation Rules Reference

Complete reference for all validation rules. Most users won't need this — check [Troubleshooting Common Errors](Troubleshooting-Common-Errors) first.

## File Structure

**Required structure**:
```
mixdiscs/
└── YourUsername/
    └── Playlist Name.yaml
```

**Username requirements**:
- 3-30 characters
- Letters, numbers, underscores, hyphens only
- No spaces
- Must match `user` field exactly (case-sensitive)

## Required YAML Fields

All playlists need:
```yaml
user: YourUsername        # Must match folder name
title: Playlist Title     # Must be unique for your username
description: Some text    # Cannot be empty
genre: rock              # Any genre name
```

Plus ONE of:
```yaml
playlist:                 # Manual: list of tracks
  - Artist - Song
  
# OR

remote_playlist: URL      # Remote: Spotify playlist URL
```

❌ Cannot have both `playlist` and `remote_playlist`

## Manual Playlist Rules

**Track format**: `Artist - Song Title`
- Must have space-dash-space (` - `)
- Both artist and song must be non-empty
- Each track must exist on Spotify

**Valid examples**:
```yaml
✅ - The Beatles - Let It Be
✅ - Pink Floyd - Comfortably Numb
```

**Invalid examples**:
```yaml
❌ - The Beatles: Let It Be        # Wrong separator
❌ - Let It Be                      # Missing artist
❌ - The Beatles -                  # Missing song
```

## Remote Playlist Rules

**Supported URL formats**:
```yaml
✅ remote_playlist: https://open.spotify.com/playlist/PLAYLIST_ID
✅ remote_playlist: spotify:playlist:PLAYLIST_ID
```

**Requirements**:
- Playlist must exist on Spotify
- Playlist must be **public**
- Must be a playlist URL (not track/album)

## Duration Rules

**The big rule**: Total duration ≤ 80:00 (4800 seconds)

```
✅ 79:59 - Valid
✅ 80:00 - Valid (exactly at limit)
❌ 80:01 - Invalid
```

**Manual playlists**: Sum of all track durations  
**Remote playlists**: Total duration from Spotify

## Username Rules

**Valid characters**: `a-z A-Z 0-9 _ -`

**Valid usernames**:
```
✅ MusicLover
✅ DJ_Cool
✅ indie-fan-99
```

**Invalid usernames**:
```
❌ Music Lover    # No spaces
❌ dj.cool        # No dots
❌ ab             # Too short (min 3)
```

## Title Rules

- Cannot be empty or whitespace-only
- Must be unique for your username
- Can contain any characters (spaces, punctuation OK)

**Uniqueness**: The combination of `user` + `title` must be globally unique
```
✅ Alice / Rock Classics
✅ Bob / Rock Classics      # Different user, OK
❌ Alice / Rock Classics    # Duplicate, not OK
```

## Genre Rules

- Cannot be empty
- Can be any string (free-form)
- Case-sensitive (lowercase recommended)

**Common genres**: rock, electronic, hip-hop, jazz, classical, pop, indie, metal, folk, country

## Local Testing

Test before submitting:

```bash
# Set Spotify credentials (get from developer.spotify.com)
export SPOTIPY_CLIENT_ID='your-client-id'
export SPOTIPY_CLIENT_SECRET='your-client-secret'

# Validate your playlist
uv run python app.py validate config.yaml --files mixdiscs/YourUsername/playlist.yaml
```

## Quick Checklist

Before submitting your PR:

- [ ] Folder structure: `mixdiscs/YourUsername/`
- [ ] Username is 3-30 chars, alphanumeric with `-` or `_`
- [ ] `user` field matches folder name (case-sensitive)
- [ ] `title` is unique for your username
- [ ] `description` and `genre` are not empty
- [ ] Manual: tracks in `Artist - Song` format
- [ ] Remote: valid public Spotify URL
- [ ] Total duration ≤ 80:00
- [ ] All tracks found on Spotify

## See Also

- [Troubleshooting Common Errors](Troubleshooting-Common-Errors) - Fix specific error messages
- [FAQ](FAQ) - Common questions
