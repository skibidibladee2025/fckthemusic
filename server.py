#!/usr/bin/env python
"""
FastAPI server for MP3Juice Music Client - enables iPhone Shortcuts integration.

Run locally:     python server.py
Run with gunicorn: gunicorn server:app --workers 2 --bind 0.0.0.0:8000
"""
import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sources import MP3JuiceMusicClient, SongInfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mp3juice-api")

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4)

# Cache for search results (simple in-memory, expires after 5 min)
search_cache = {}
cache_ttl = 300  # seconds

app = FastAPI(
    title="MP3Juice API",
    description="Search and download music from mp3juice.sc",
    version="1.0.0",
)

# Enable CORS for iPhone Shortcuts
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Pydantic Models =====
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="Song/artist to search for")
    max_results: int = Field(5, ge=1, le=20, description="Max results per source")
    sources: List[str] = Field(["youtube"], description="Sources to search: youtube, soundcloud")


class SearchResult(BaseModel):
    index: int
    title: str
    source: str
    size_mb: str
    duration: str
    download_url: str
    video_id: str


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResult]


class DownloadRequest(BaseModel):
    download_url: str = Field(..., description="Direct download URL from search results")
    filename: Optional[str] = Field(None, description="Custom filename (without extension)")


# ===== Helper Functions =====
def run_in_thread(func, *args, **kwargs):
    """Run blocking function in thread pool."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, func, *args, **kwargs)


def get_client(max_results: int = 10) -> MP3JuiceMusicClient:
    """Create a new client instance."""
    return MP3JuiceMusicClient(
        search_size_per_source=max_results,
        disable_print=True
    )


def search_songs(query: str, max_results: int = 5) -> List[SongInfo]:
    """Blocking search function."""
    client = get_client(max_results)
    return client.search(query)


def download_song(download_url: str) -> bytes:
    """Blocking download function."""
    import requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://mp3juice.sc/',
        'Origin': 'https://mp3juice.sc'
    }
    resp = requests.get(download_url, headers=headers, timeout=60, stream=True, allow_redirects=True)
    resp.raise_for_status()
    return resp.content


# ===== API Endpoints =====
@app.get("/")
async def root():
    return {
        "name": "MP3Juice API",
        "version": "1.0.0",
        "description": "Search and download music from mp3juice.sc",
        "endpoints": {
            "search": "POST /search",
            "download": "POST /download",
            "health": "GET /health"
        },
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mp3juice-api"}


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search for songs.

    Returns list of results with download URLs ready for /download endpoint.
    """
    logger.info(f"Search: '{request.query}' (max={request.max_results})")

    try:
        results = await run_in_thread(search_songs, request.query, request.max_results)
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    if not results:
        return SearchResponse(query=request.query, total_results=0, results=[])

    # Filter by requested sources
    filtered = []
    for i, song in enumerate(results):
        if request.sources and song.root_source.lower() not in [s.lower() for s in request.sources]:
            continue
        filtered.append(SearchResult(
            index=i + 1,
            title=song.song_name,
            source=song.root_source,
            size_mb=song.file_size,
            duration=song.duration,
            download_url=song.download_url,
            video_id=song.identifier
        ))

    return SearchResponse(
        query=request.query,
        total_results=len(filtered),
        results=filtered
    )


@app.post("/download")
async def download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """
    Download a song by its download URL.

    Returns the MP3 file directly (streaming response).
    """
    logger.info(f"Download: {request.download_url[:80]}...")

    try:
        content = await run_in_thread(download_song, request.download_url)
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

    if not content:
        raise HTTPException(status_code=404, detail="No content downloaded")

    # Generate filename
    if request.filename:
        filename = f"{request.filename}.mp3"
    else:
        # Extract from URL or use generic
        filename = "song.mp3"

    # Save to temp file for FileResponse
    import tempfile
    temp_dir = Path(tempfile.gettempdir()) / "mp3juice_downloads"
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / filename

    with open(temp_file, 'wb') as f:
        f.write(content)

    # Schedule cleanup
    background_tasks.add_task(lambda: temp_file.unlink(missing_ok=True))

    return FileResponse(
        path=str(temp_file),
        media_type="audio/mpeg",
        filename=filename,
        headers={"Content-Length": str(len(content))}
    )


@app.get("/download")
async def download_get(request: Request, filename: Optional[str] = None):
    """
    GET version of download for iPhone Shortcuts.
    Usage: /download?url=<encoded_download_url>&filename=name
    """
    # Get the raw query string after /download?
    full_url = str(request.url)
    query_start = full_url.find('?')
    if query_start == -1:
        raise HTTPException(status_code=400, detail="Missing url parameter")

    query_string = full_url[query_start + 1:]
    # Parse manually to handle encoded URLs correctly
    params = {}
    for param in query_string.split('&'):
        if '=' in param:
            k, v = param.split('=', 1)
            params[k] = v

    url = params.get('url')
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")

    # Decode the URL (it was double-encoded)
    from urllib.parse import unquote
    url = unquote(url)

    download_request = DownloadRequest(download_url=url, filename=filename)
    return await download(download_request, BackgroundTasks())


# ===== Main =====
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)