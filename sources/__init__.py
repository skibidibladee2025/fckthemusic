"""
Sources package - music client implementations.
"""
from .base import BaseMusicClient, BaseMusicClientKwargs, SongInfo, SongInfoUtils, AudioLinkTester
from .mp3juice import MP3JuiceMusicClient

__all__ = [
    'BaseMusicClient',
    'BaseMusicClientKwargs',
    'SongInfo',
    'SongInfoUtils',
    'AudioLinkTester',
    'MP3JuiceMusicClient',
]