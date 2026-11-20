"""URL shortener backed by the project's custom hash table."""

from collections.abc import Callable
from typing import Protocol
from urllib.parse import urlsplit

from src.base62 import decode, encode
from src.hash_table import HashTable


class _HashTable(Protocol):
    strategy: str

    @property
    def capacity(self) -> int: ...

    def set(self, key: str, value: str) -> None: ...

    def get(self, key: str) -> str | None: ...

    def inspect(self) -> tuple[tuple[tuple[str, str], ...], ...]: ...

    def hash_trace(self, key: str) -> tuple[tuple[int, ...], int]: ...

    def probe_trace(self, key: str) -> tuple[int, ...]: ...


class Shortener:
    """Map validated HTTP(S) URLs to stable, sequential base62 codes."""

    def __init__(
        self, table_class: Callable[[], _HashTable] = HashTable
    ) -> None:
        self._url_to_code = table_class()
        self._code_to_url = table_class()
        self._next_id = 0

    @staticmethod
    def _validate_url(url: str) -> None:
        if not isinstance(url, str):
            raise TypeError("url must be a string")
        if not url or any(character.isspace() for character in url):
            raise ValueError("url must not be empty or contain whitespace")

        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
            parsed.port
        except ValueError as error:
            raise ValueError("url is malformed") from error

        if parsed.scheme.lower() not in ("http", "https") or not hostname:
            raise ValueError("url must be an absolute HTTP or HTTPS URL with a host")

    def shorten(self, url: str) -> str:
        """Return the existing or newly assigned code for a valid URL."""
        self._validate_url(url)
        existing_code = self._url_to_code.get(url)
        if existing_code is not None:
            return existing_code

        code = encode(self._next_id)
        self._url_to_code.set(url, code)
        self._code_to_url.set(code, url)
        self._next_id += 1
        return code

    def expand(self, code: str) -> str:
        """Return the original URL for a previously issued canonical code."""
        if not isinstance(code, str):
            raise TypeError("code must be a string")

        value = decode(code)
        if encode(value) != code:
            raise ValueError("code must use its canonical base62 representation")

        url = self._code_to_url.get(code)
        if url is None:
            raise KeyError(code)
        return url

    @property
    def table_capacity(self) -> int:
        """Return the URL-to-code table's current capacity."""
        return self._url_to_code.capacity

    @property
    def table_strategy(self) -> str:
        """Return the collision strategy used by the URL-to-code table."""
        return self._url_to_code.strategy

    def inspect_table(self) -> tuple[tuple[tuple[str, str], ...], ...]:
        """Return an immutable snapshot of URL-to-code buckets or slots."""
        return self._url_to_code.inspect()

    def hash_trace(self, url: str) -> tuple[tuple[int, ...], int]:
        """Return Horner residues and the starting bucket or slot for a URL."""
        return self._url_to_code.hash_trace(url)

    def probe_trace(self, url: str) -> tuple[int, ...]:
        """Return the buckets or slots inspected while finding a URL."""
        return self._url_to_code.probe_trace(url)
