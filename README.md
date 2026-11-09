# MP3Juice Music Client

A Python client for searching and downloading music from [mp3juice.sc](https://mp3juice.sc/).

## Features

- Search music from YouTube and SoundCloud
- Download MP3 files directly
- Progress tracking with rich console output
- Automatic API key extraction from mp3juice.sc

## Installation

```bash
pip install -r requirements.txt
```

Required packages:
- `requests>=2.31.0`
- `rich>=13.7.0`
- `typing_extensions>=4.5.0`

## Usage

### Command Line

```bash
# Search for songs
python demo.py "song name" --max-results 5

# Search and download the first result
python demo.py "song name" --max-results 5 --download --output-dir ./downloads
```

### As a Library

```python
from sources import MP3JuiceMusicClient

# Create client
client = MP3JuiceMusicClient(
    search_size_per_source=10,  # results per source (YouTube + SoundCloud)
    disable_print=False
)

# Search for songs
results = client.search("never gonna give you up")

for song in results:
    print(f"{song.song_name} - {song.root_source}")
    print(f"  Size: {song.file_size}")
    print(f"  Duration: {song.duration}")
    print(f"  Download URL: {song.download_url}")

# Access downloaded content (already downloaded during search)
if results:
    first_song = results[0]
    with open(f"{first_song.song_name}{first_song.ext}", "wb") as f:
        f.write(first_song.downloaded_contents)
```

## How It Works

1. **API Key Extraction**: Fetches and decodes the obfuscated API key from mp3juice.sc's homepage
2. **Search**: Queries the mp3juice.sc API with the search term
3. **YouTube Flow**: 
   - Gets auth token from theta.thetacloud.org
   - Initializes conversion
   - Converts video to MP3
   - Gets download URL
4. **SoundCloud Flow**: Uses direct stream URLs (currently has issues)
5. **Download**: Fetches the actual audio content

## Project Structure

```
mp3juice_client/
├── sources/
│   ├── __init__.py       # Exports
│   ├── base.py           # Base classes (BaseMusicClient, SongInfo, etc.)
│   └── mp3juice.py       # MP3JuiceMusicClient implementation
├── demo.py               # CLI demo script
├── requirements.txt      # Dependencies
└── README.md             # This file
```

## Notes

- The SoundCloud download flow currently returns 404 errors (thetacloud.org endpoint may have changed)
- YouTube downloads work reliably
- The client automatically handles rate limiting and retries
- Downloaded content is stored in memory during search (use `downloaded_contents` attribute)

## Legal Disclaimer

This tool is for educational purposes only. Downloading copyrighted music may violate terms of service and copyright laws. Please respect artists' rights and use legitimate music services.