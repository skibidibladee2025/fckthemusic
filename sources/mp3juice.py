"""
MP3Juice Music Client - Search and download from mp3juice.sc
"""
import copy
import time
import base64
from urllib.parse import quote, urlencode
from contextlib import suppress
from itertools import zip_longest
from typing_extensions import Unpack
from rich.progress import Progress

from .base import BaseMusicClient, BaseMusicClientKwargs, SongInfo, SongInfoUtils, AudioLinkTester
from .base import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict


class MP3JuiceMusicClient(BaseMusicClient):
    """MP3Juice music client for searching and downloading from mp3juice.sc"""
    source = 'MP3JuiceMusicClient'
    API_KEY = None

    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        # Double the search size as in original
        kwargs['search_size_per_source'] = kwargs.get('search_size_per_source', 30) * 2
        super(MP3JuiceMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mp3juice.sc/",
            "Origin": "https://mp3juice.sc"
        }
        self.default_download_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mp3juice.sc/",
            "Origin": "https://mp3juice.sc"
        }
        self.default_headers = self.default_search_headers
        self._initsession()

    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None) -> list:
        """Construct search URLs for a keyword."""
        rule = rule or {}
        request_overrides = request_overrides or {}

        # Merge default search headers into request_overrides
        headers = request_overrides.pop('headers', {})
        headers.update(self.default_search_headers)
        request_overrides['headers'] = headers

        # Fetch and decode API key from the main page
        try:
            resp = self.get('https://mp3juice.sc/', **request_overrides)
            resp.raise_for_status()
            # Extract obfuscated API key from JavaScript
            import re
            import base64

            # Pattern: var apiKey=decodeKey('...')
            match = re.search(r"var apiKey=decodeKey\('([^']+)'\)", resp.text)
            if match:
                obfuscated = match.group(1)
                # Decode: reverse string then base64 decode
                MP3JuiceMusicClient.API_KEY = base64.b64decode(obfuscated[::-1]).decode()
            else:
                # Fallback: try direct var apiKey='...'
                match = re.search(r"var apiKey='([^']+)'", resp.text)
                if match:
                    MP3JuiceMusicClient.API_KEY = match.group(1)
        except Exception as e:
            self.logger_handle.warning(f"Could not fetch/decode API key: {e}")
            MP3JuiceMusicClient.API_KEY = "default_key"

        default_rule = {
            'api_key': MP3JuiceMusicClient.API_KEY,
            'y': 's',
            'q': base64.b64encode(quote(keyword, safe="").encode("utf-8")).decode("utf-8"),
            '_': str(int(time.time() * 1000))
        }
        default_rule.update(rule)

        base_url = 'https://mp3juice.sc/api/v1/search?'
        page_rule = copy.deepcopy(default_rule)
        search_urls = [base_url + urlencode(page_rule)]
        self.search_size_per_page = self.search_size_per_source

        return search_urls

    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = None, request_overrides: dict = None,
                song_infos: list = None, progress: Progress = None) -> list:
        """Search for songs."""
        request_overrides = request_overrides or {}
        song_infos = song_infos or []
        page_no = 1
        search_result_idx = -1

        # Merge default search headers into request_overrides
        headers = request_overrides.pop('headers', {})
        headers.update(self.default_search_headers)
        request_overrides['headers'] = headers

        task_id = progress.add_task(
            f"{self.source}._search >>> Start to process the 0th search result on page {page_no}",
            total=None, completed=0
        )

        # Ensure API key is available
        if not MP3JuiceMusicClient.API_KEY:
            try:
                resp = self.get('https://mp3juice.sc/', **request_overrides)
                resp.raise_for_status()
                import re
                import base64
                match = re.search(r"var apiKey=decodeKey\('([^']+)'\)", resp.text)
                if match:
                    obfuscated = match.group(1)
                    MP3JuiceMusicClient.API_KEY = base64.b64decode(obfuscated[::-1]).decode()
                else:
                    match = re.search(r"var apiKey='([^']+)'", resp.text)
                    if match:
                        MP3JuiceMusicClient.API_KEY = match.group(1)
            except Exception:
                MP3JuiceMusicClient.API_KEY = "default_key"

        try:
            # Fetch search results
            resp = self.get(search_url, allow_redirects=True, **request_overrides)
            resp.raise_for_status()

            data = resp2json(resp)
            search_results_yt = [{**item, "root_source": "YouTube"} for item in data.get("yt", [])]
            search_results_sc = [{**item, "root_source": "SoundCloud"} for item in data.get("sc", [])]

            # Interleave YouTube and SoundCloud results
            combined_results = [
                x for ab in zip_longest(search_results_yt, search_results_sc)
                for x in ab if x is not None
            ]

            for search_result_idx, search_result in enumerate(combined_results):
                # Check search size limit
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page:
                    search_result_idx -= 1
                    break

                # Update progress
                progress.update(
                    task_id,
                    description=f"{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}",
                    completed=search_result_idx+1,
                    total=search_result_idx+1
                )

                # Validate search result
                if not isinstance(search_result, dict) or not (song_id := search_result.get('id')):
                    continue

                # SoundCloud needs extra fields - extract from 'stream' field
                if search_result['root_source'] in ['SoundCloud']:
                    if 'stream' not in search_result:
                        continue
                    # Decode stream to get id_base64 and title_base64
                    try:
                        import base64
                        stream_decoded = base64.b64decode(search_result['stream']).decode()
                        # Format: {id}/{uuid}/stream/hls?client_id=...
                        parts = stream_decoded.split('/')
                        if len(parts) >= 2:
                            search_result['id_base64'] = parts[0]
                            search_result['title_base64'] = parts[1]
                        else:
                            continue
                    except Exception:
                        continue

                download_result = {}

                # Build download URL based on source
                if search_result['root_source'] in ['SoundCloud']:
                    download_url = f"https://thetacloud.org/s/{search_result['id_base64']}/{search_result['title_base64']}/"
                else:
                    # YouTube flow - multiple API calls
                    try:
                        auth_resp = self.get(
                            "https://theta.thetacloud.org/api/v1/auth?",
                            params={"api_key": MP3JuiceMusicClient.API_KEY, "_": str(int(time.time() * 1000))},
                            **request_overrides
                        )
                        auth_resp.raise_for_status()
                        download_result['auth'] = resp2json(auth_resp)
                    except Exception:
                        continue

                    auth_key = safeextractfromdict(download_result['auth'], ['key'], None)
                    if not auth_key:
                        continue

                    # Merge auth header with request_overrides headers
                    yt_headers = request_overrides.get('headers', {}).copy()
                    yt_headers["Authorization"] = f"Bearer {auth_key}"

                    try:
                        init_resp = self.get(
                            'https://theta.thetacloud.org/api/v1/init?',
                            headers=yt_headers,
                            params={'_': str(int(time.time() * 1000))},
                            **{k: v for k, v in request_overrides.items() if k != 'headers'}
                        )
                        init_resp.raise_for_status()
                        download_result['init'] = resp2json(init_resp)
                    except Exception:
                        continue

                    convert_url = download_result['init'].get('convertURL', '')
                    if not convert_url:
                        continue

                    try:
                        convert_resp = self.get(
                            f'{convert_url}&v={search_result["id"]}&f=mp3&_={str(int(time.time()))}',
                            **{k: v for k, v in request_overrides.items() if k != 'headers'},
                            headers=yt_headers
                        )
                        convert_resp.raise_for_status()
                        download_result['convert'] = resp2json(convert_resp)
                    except Exception:
                        continue

                    redirect_url = download_result['convert'].get('redirectURL', '')
                    if not redirect_url:
                        continue

                    try:
                        redirect_resp = self.get(
                            redirect_url,
                            **{k: v for k, v in request_overrides.items() if k != 'headers'},
                            headers=yt_headers
                        )
                        redirect_resp.raise_for_status()
                        download_result['redirect'] = resp2json(redirect_resp)
                    except Exception:
                        continue

                    download_url = download_result['redirect'].get('downloadURL', '')
                    if not download_url:
                        continue

                    download_url += f'&v={song_id}&f=mp3&r=mp3juice.sc'

                # Test download URL
                download_url_status = self.audio_link_tester.test(
                    url=download_url,
                    request_overrides=request_overrides,
                    renew_session=True
                )

                # Create song info
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}},
                    source=self.source,
                    song_name=legalizestring(search_result.get('title', 'Unknown')),
                    singers='NULL',
                    album='NULL',
                    ext=download_url_status['ext'],
                    file_size_bytes=download_url_status['file_size_bytes'],
                    file_size=download_url_status['file_size'],
                    identifier=song_id,
                    duration_s=None,
                    duration='-:-:-',
                    lyric='NULL',
                    cover_url=None,
                    download_url=download_url_status['download_url'],
                    download_url_status=download_url_status,
                    root_source=search_result['root_source'],
                )

                # Validate
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS:
                    continue

                # Download the actual content
                try:
                    content_resp = self.get(download_url, **request_overrides)
                    content_resp.raise_for_status()
                    song_info.downloaded_contents = content_resp.content
                    song_info.file_size_bytes = len(song_info.downloaded_contents)
                    song_info.file_size = SongInfoUtils.byte2mb(song_info.file_size_bytes)
                    song_info.duration_s = SongInfoUtils.naiveguessdurationfromaudiobytes(song_info.downloaded_contents)
                    song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
                except Exception as e:
                    self.logger_handle.warning(f"Failed to download content: {e}")
                    continue

                if song_info.with_valid_download_url:
                    song_infos.append(song_info)

            progress.update(
                task_id,
                description=f'{self.source}._search >>> {search_result_idx+1} search results processed on page {page_no}'
            )

        except Exception as err:
            progress.update(
                task_id,
                description=f'{self.source}._search >>> {keyword} on page {page_no} (Error: {err})'
            )
            self.logger_handle.error(f'{self.source}._search >>> {keyword} on page {page_no} (Error: {err})')

        return song_infos