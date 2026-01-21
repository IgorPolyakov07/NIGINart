from typing import Type
from src.parsers.base import BaseParser
class ParserFactory:
    _parsers: dict[str, Type[BaseParser]] = {}
    @classmethod
    def register(cls, platform: str, parser_class: Type[BaseParser]) -> None:
        cls._parsers[platform.lower()] = parser_class
    @classmethod
    def create(cls, platform: str, account_id: str, account_url: str) -> BaseParser:
        parser_class = cls._parsers.get(platform.lower())
        if not parser_class:
            raise ValueError(
                f"Unsupported platform: {platform}. "
                f"Supported platforms: {cls.get_supported_platforms()}"
            )
        return parser_class(account_id, account_url)
    @classmethod
    def get_supported_platforms(cls) -> list[str]:
        return list(cls._parsers.keys())
