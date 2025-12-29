# Frequently Asked Questions

## Getting Started

**Q: How do I submit a playlist?**  
A: Fork the repo, create `mixdiscs/YourUsername/my_playlist_title.yaml`, add your tracks, submit a PR. See the [Home](Home) page for format examples.

**Q: Manual or remote playlist?**  
A: **Manual** = list tracks yourself. **Remote** = link to Spotify playlist that auto-syncs.

**Q: Can I submit multiple playlists?**  
A: Yes! Create multiple YAML files in your username folder with different titles.

## Common Issues

**Q: My PR failed — what now?**  
A: Check [Troubleshooting Common Errors](Troubleshooting-Common-Errors) for fixes.

**Q: Why can't Spotify find my track?**  
A: Check spelling, verify it exists on Spotify, or replace with a different track.

**Q: My playlist is exactly 80 minutes — is that OK?**  
A: Yes! ≤80:00 means 80:00 is valid.

## Usernames

**Q: Can I change my username later?**  
A: Yes, but you'll need to move all your playlists and update the YAML files. Easier to pick carefully upfront.

**Q: Are usernames case-sensitive?**  
A: Yes. `MusicLover` ≠ `musiclover`

**Q: Can my username have spaces?**  
A: No. Use underscores or hyphens: `Music_Lover` or `Music-Lover`

## Remote Playlists

**Q: What if I update my Spotify playlist?**  
A: Changes sync automatically! But if it goes over 80 minutes, it will [freeze](Fixing-Frozen-Playlists).

**Q: How do I unfreeze my playlist?**  
A: Remove tracks on Spotify to get under 80 minutes. It unfreezes automatically. See [Fixing Frozen Playlists](Fixing-Frozen-Playlists).

**Q: Can I use someone else's Spotify playlist?**  
A: Yes, if it's public. But they control updates, which could freeze your entry.

**Q: Can I use a private playlist?**  
A: No, it must be public for validation.

## Updates

**Q: Can I update my playlist after it's merged?**  
A: **Manual**: Submit a new PR with changes. **Remote**: Just update your Spotify playlist.

**Q: How long until my playlist appears on the site?**  
A: A few minutes after your PR is merged.

**Q: How often does the site update?**  
A: Automatically on merges, plus periodic re-renders.

## Technical

**Q: Where do I get Spotify API credentials?**  
A: [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) — only needed for local testing. CI has its own.

**Q: Which music services are supported?**  
A: Currently only Spotify. More coming soon.

**Q: Can I contribute code?**  
A: Yes! PRs welcome. See the [repository](https://github.com/tomncooper/mixdiscs).

## Still Have Questions?

- Check the [Validation Rules Reference](Validation-Rules-Reference) for detailed requirements
- [Open an issue](https://github.com/tomncooper/mixdiscs/issues) on GitHub
