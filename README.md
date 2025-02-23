# MixDiscs

Playlist sharing....but nerdier!

You can add your playlist via a pull request, the CI will check `<music service>` to find the songs and, this is the crucial part, make sure it is less than 80 minuets long. Than's it, you have 80 mins, the length of a [MiniDisc](https://en.wikipedia.org/wiki/MiniDisc) (told you it was nerdy) or a CD-R (remember them).

If your playlist passes the checks then the CI will create a playlist on `<music service>` and share it with the world. I am working on the auto-generated MiniDisc... 

## Development

To run locally you will need to export envars containing your spotify credentials:

```bash
 export SPOTIPY_CLIENT_ID='<client-id>'
 export SPOTIPY_CLIENT_SECRET='<client-secret>'
```