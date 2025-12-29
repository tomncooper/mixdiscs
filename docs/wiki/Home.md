# Welcome to Mixdiscs! 🎵

There are plenty of playlist sharing sites but how many of them let you share playlists via pull requests. 
Every playlist must be **under 80 minutes** — the length of a [MiniDisc](https://www.minidisc.wiki/) or CD-R.

## Getting Started

**New here?** Follow these steps:

1. **Fork** [the repository](https://github.com/tomncooper/mixdiscs)
2. **Create** `mixdiscs/YourUsername/my_playlist_title.yaml`
3. **Add** your tracks or point to a playlist on a music service like Spotify (see formats below) 
4. **Submit** a pull request

The CI will validate your playlist automatically and update the Mixdisc site!

## Quick Format Reference

### Option A: Manual Playlist
```yaml
user: YourUsername
title: My Playlist
description: A short description
genre: rock
playlist:
  - Pink Floyd - Comfortably Numb
  - The Beatles - Come Together
```

### Option B: Remote Playlist (Spotify)
```yaml
user: YourUsername
title: My Playlist
description: A short description
genre: rock
remote_playlist: https://open.spotify.com/playlist/PLAYLIST_ID
```

## Need Help?

- 🚫 **CI Failed?** → [Troubleshooting Common Errors](Troubleshooting-Common-Errors)
- ⚠️ **Playlist Frozen?** → [Fixing Frozen Playlists](Fixing-Frozen-Playlists)
- 📋 **Detailed Rules?** → [Validation Rules Reference](Validation-Rules-Reference)
- ❓ **Questions?** → [FAQ](FAQ)

**Browse playlists**: [mixdiscs.com](https://mixdiscs.com/)
