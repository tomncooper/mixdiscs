# Remote Playlists User Guide

## What are Remote Playlists?

Remote playlists let you link directly to your existing Spotify playlists instead of manually typing out all your tracks. It's faster, easier, and your playlist will automatically sync when you make changes on Spotify!

## Quick Start

### 1. Create Your YAML File

Instead of listing tracks manually:
```yaml
user: YourUsername
title: My Summer Vibes
description: Chill tracks for summer
genre: electronic
remote_playlist: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
```

### 2. Get Your Spotify Playlist URL

**Option A - From Spotify Web:**
1. Open your playlist on [open.spotify.com](https://open.spotify.com)
2. Click the "Share" button (•••)
3. Choose "Copy link to playlist"
4. Paste into your YAML file

**Option B - From Spotify App:**
1. Open your playlist in the Spotify app
2. Click the "Share" button (•••)
3. Choose "Copy Spotify URI"
4. Paste into your YAML file (works with both URLs and URIs!)

### 3. Submit Your Pull Request

That's it! The system will:
- ✅ Validate your playlist is under 80 minutes
- ✅ Fetch all tracks from Spotify
- ✅ Display it on the site with a 🔗 badge

## Features

### 🔄 Automatic Updates

When you update your Spotify playlist:
- Changes are detected automatically
- Your MixDiscs playlist updates on the next site build
- As long as it stays under 80 minutes, you're good!

### 🧊 Frozen Playlists

If your Spotify playlist grows beyond 80 minutes:
- ⚠️ Your playlist gets "frozen" at the last valid version
- You'll see a warning icon with details
- The site shows the cached (under 80 min) version
- Your Spotify link is still there so you can edit it

**To unfreeze:** Simply remove tracks on Spotify to get back under 80 minutes. Next update, it unfreezes automatically!

### 📊 What You'll See

**On the main playlist page:**
- 🔗 **"Remote" badge** - Shows it's linked to Spotify
- **Your playlist tracks** - Automatically fetched
- **⚠️ Warning icon** (if frozen) - Hover for details

**If frozen, the warning shows:**
- When it was frozen
- What the cached version date is
- How much over 80 minutes the current Spotify version is
- How many tracks were added
- A direct link to edit on Spotify

## Rules & Limitations

### ✅ You Can:
- Link to any public Spotify playlist
- Update your Spotify playlist anytime
- Have multiple remote playlists
- Mix remote and manual playlists

### ❌ You Cannot:
- Link to private Spotify playlists (they must be public)
- Have both `playlist` and `remote_playlist` in the same YAML
- Exceed 80 minutes (playlist gets frozen)
- Link to non-Spotify URLs (yet - more services coming!)

## Troubleshooting

### "Playlist not found" Error
- Make sure your playlist is **public** on Spotify
- Check the URL is correct (no extra characters)
- Try the Spotify URI format instead: `spotify:playlist:37i9dQZF1DX...`

### "Playlist exceeds duration limit"
- Your playlist is over 80 minutes
- Either remove tracks on Spotify, or
- Submit it as a manual playlist with only your favorite 80 minutes

### "Frozen" Warning on Site
1. Click the Spotify link on your playlist
2. Remove enough tracks to get under 80 minutes
3. Wait for the next site update (automatic)
4. Your playlist will unfreeze and show the current version

## FAQ

**Q: Can I edit my remote playlist after submitting?**
A: Yes! Edit it on Spotify and it will update automatically (as long as it stays under 80 minutes).

**Q: What happens if I delete my Spotify playlist?**
A: The site will show an error and your playlist won't render. Submit a PR to remove the YAML file.

**Q: Can I convert a manual playlist to remote?**
A: Yes! Just edit your YAML file to replace the `playlist` field with `remote_playlist` and submit a PR.

**Q: Can I convert a remote playlist to manual?**
A: Yes! Replace the `remote_playlist` field with `playlist` and list all tracks manually.

**Q: How often does it check for updates?**
A: Every time the site rebuilds (when a PR is merged or manually triggered).

**Q: Does it use my Spotify account?**
A: No! It uses public API access. Your personal Spotify account isn't involved.

## Examples

### Remote Playlist (Electronic)
```yaml
user: DJSpinMaster
title: Deep House Sessions
description: Smooth deep house for late nights
genre: electronic
remote_playlist: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
```

### Remote Playlist (Rock)
```yaml
user: RockFan92
title: 90s Alternative Classics
description: Best alternative rock from the 90s
genre: rock
remote_playlist: spotify:playlist:37i9dQZEVXbMDoHDwVN2tF
```

### Manual Playlist (for comparison)
```yaml
user: ClassicVibes
title: Jazz Standards
description: Essential jazz standards
genre: jazz
playlist:
  - Miles Davis - So What
  - John Coltrane - Giant Steps
  - Bill Evans - Waltz for Debby
```

## Need Help?

- 🐛 Found a bug? Open an issue on GitHub
- 💡 Have a suggestion? Start a discussion
- ❓ Questions? Check existing issues or ask in discussions

Happy playlist sharing! 🎵
