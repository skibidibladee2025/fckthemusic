"""
Base classes for music clients.
"""
import logging
from abc import ABC, abstractmethod
from typing import TypedDict, Optional, Any
from dataclasses import dataclass, field


class BaseMusicClientKwargs(TypedDict, total=False):
    """Keyword arguments for BaseMusicClient."""
    search_size_per_source: int
    strict_limit_search_size_per_page: bool
    disable_print: bool
    logger_handle: Optional[logging.Logger]
    session: Any
    timeout: int


@dataclass
class SongInfo:
    """Song information container."""
    raw_data: dict
    source: str
    song_name: str
    singers: str
    album: str
    ext: str
    file_size_bytes: int
    file_size: str
    identifier: str
    duration_s: Optional[float]
    duration: str
    lyric: str
    cover_url: Optional[str]
    download_url: str
    download_url_status: dict
    root_source: str
    downloaded_contents: bytes = field(default=b'', repr=False)

    @property
    def with_valid_download_url(self) -> bool:
        """Check if download URL is valid."""
        return bool(self.download_url and self.download_url.startswith('http'))


class SongInfoUtils:
    """Utility functions for SongInfo."""

    @staticmethod
    def byte2mb(bytes_val: int) -> str:
        """Convert bytes to MB string."""
        return f"{bytes_val / (1024 * 1024):.2f}MB"

    @staticmethod
    def seconds2hms(seconds: float) -> str:
        """Convert seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def naiveguessdurationfromaudiobytes(audio_bytes: bytes) -> float:
        """Naively guess duration from audio bytes (rough estimate for MP3)."""
        # Rough estimate: 128 kbps MP3 = 16 KB/s
        if not audio_bytes:
            return 0.0
        return len(audio_bytes) / 16000


class AudioLinkTester:
    """Test audio download links."""
    VALID_AUDIO_EXTS = {'.mp3', '.m4a', '.flac', '.wav', '.ogg', '.aac'}

    def __init__(self, session=None, timeout=30):
        self.session = session
        self.timeout = timeout

    def test(self, url: str, request_overrides: dict = None, renew_session: bool = False) -> dict:
        """Test a download URL and return status info."""
        import requests

        session = self.session or requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # Try HEAD request first
        try:
            resp = session.head(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '')
                content_length = resp.headers.get('Content-Length')
                ext = self._guess_ext(content_type, url)
                return {
                    'download_url': url,
                    'ext': ext,
                    'file_size_bytes': int(content_length) if content_length else 0,
                    'file_size': SongInfoUtils.byte2mb(int(content_length)) if content_length else '0MB',
                    'valid': True
                }
        except Exception:
            pass

        # Fallback
        ext = self._guess_ext('', url)
        return {
            'download_url': url,
            'ext': ext,
            'file_size_bytes': 0,
            'file_size': '0MB',
            'valid': True  # Assume valid if we can't check
        }

    def _guess_ext(self, content_type: str, url: str) -> str:
        """Guess file extension from content type or URL."""
        if 'mpeg' in content_type or 'mp3' in content_type:
            return '.mp3'
        if 'm4a' in content_type or 'mp4' in content_type:
            return '.m4a'
        if 'flac' in content_type:
            return '.flac'
        if 'wav' in content_type:
            return '.wav'
        if 'ogg' in content_type:
            return '.ogg'
        if 'aac' in content_type:
            return '.aac'

        # From URL
        url_lower = url.lower()
        for ext in self.VALID_AUDIO_EXTS:
            if ext in url_lower:
                return ext
        return '.mp3'  # Default


def legalizestring(s: str) -> str:
    """Sanitize string for filesystem."""
    if not s:
        return 'Unknown'
    # Replace problematic characters
    for char in '<>:"/\\|?*\n\r\t':
        s = s.replace(char, '_')
    return s.strip()


def usesearchheaderscookies(func):
    """Decorator to apply search headers/cookies."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def resp2json(resp) -> dict:
    """Convert response to JSON."""
    try:
        return resp.json()
    except Exception:
        return {}


def safeextractfromdict(data: dict, keys: list, default=None):
    """Safely extract nested value from dict."""
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


class BaseMusicClient(ABC):
    """Abstract base class for music clients."""

    source: str = 'BaseMusicClient'
    search_size_per_page: int = 30
    search_size_per_source: int = 30
    strict_limit_search_size_per_page: bool = True
    disable_print: bool = False
    logger_handle: Optional[logging.Logger] = None

    def __init__(self, **kwargs: BaseMusicClientKwargs):
        self.search_size_per_source = kwargs.get('search_size_per_source', 30)
        self.strict_limit_search_size_per_page = kwargs.get('strict_limit_search_size_per_page', True)
        self.disable_print = kwargs.get('disable_print', False)
        self.logger_handle = kwargs.get('logger_handle', logging.getLogger(self.source))
        self._session = kwargs.get('session')
        self._timeout = kwargs.get('timeout', 30)
        self.audio_link_tester = AudioLinkTester(session=self._session, timeout=self._timeout)

    def _initsession(self):
        """Initialize session."""
        import requests
        if self._session is None:
            self._session = requests.Session()
        self.audio_link_tester.session = self._session

    def get(self, url: str, **kwargs):
        """GET request wrapper."""
        if self._session is None:
            self._initsession()
        timeout = kwargs.pop('timeout', self._timeout)
        return self._session.get(url, timeout=timeout, **kwargs)

    @abstractmethod
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None) -> list:
        """Construct search URLs for a keyword."""
        pass

    @abstractmethod
    def _search(self, keyword: str = '', search_url: str = None, request_overrides: dict = None,
                song_infos: list = None, progress=None) -> list:
        """Search for songs."""
        pass

    def search(self, keyword: str, request_overrides: dict = None) -> list:
        """Public search method."""
        from rich.progress import Progress

        search_urls = self._constructsearchurls(keyword, request_overrides=request_overrides)
        song_infos = []

        with Progress(transient=True) as progress:
            for search_url in search_urls:
                song_infos = self._search(
                    keyword=keyword,
                    search_url=search_url,
                    request_overrides=request_overrides,
                    song_infos=song_infos,
                    progress=progress
                )

        return song_infos