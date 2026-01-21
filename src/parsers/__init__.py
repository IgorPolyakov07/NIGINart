from src.parsers.base import BaseParser, PlatformMetrics
from src.parsers.factory import ParserFactory
from src.parsers.telegram_parser import TelegramParser
from src.parsers.youtube_parser import YouTubeParser
from src.parsers.vk_parser import VKParser
from src.parsers.tiktok_parser import TikTokParser
from src.parsers.instagram_parser import InstagramParser
from src.parsers.pinterest_parser import PinterestParser
from src.parsers.dzen_parser import DzenParser
from src.parsers.wibes_parser import WibesParser
ParserFactory.register('telegram', TelegramParser)
ParserFactory.register('youtube', YouTubeParser)
ParserFactory.register('vk', VKParser)
ParserFactory.register('tiktok', TikTokParser)
ParserFactory.register('instagram', InstagramParser)
ParserFactory.register('pinterest', PinterestParser)
ParserFactory.register('dzen', DzenParser)
ParserFactory.register('wibes', WibesParser)
__all__ = [
    "BaseParser",
    "PlatformMetrics",
    "ParserFactory",
    "TelegramParser",
    "YouTubeParser",
    "VKParser",
    "TikTokParser",
    "InstagramParser",
    "PinterestParser",
    "DzenParser",
    "WibesParser",
]
