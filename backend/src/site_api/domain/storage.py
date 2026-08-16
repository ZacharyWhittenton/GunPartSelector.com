from typing import Protocol


class UnsupportedFileTypeError(Exception):
    """Raised when an uploaded file's content type is not an allowed image type."""


class FileTooLargeError(Exception):
    """Raised when an uploaded file exceeds the maximum allowed size."""


class FileStorage(Protocol):
    async def save_image(self, content: bytes, content_type: str) -> str:
        """Persist image bytes and return a URL the frontend can load it from."""
        ...
