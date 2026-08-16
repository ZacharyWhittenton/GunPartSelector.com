from pathlib import Path
from uuid import uuid4

from site_api.domain.storage import FileTooLargeError, UnsupportedFileTypeError

MAX_IMAGE_BYTES = 5 * 1024 * 1024

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


class LocalFileStorage:
    """Stores uploaded images on local disk. A future S3-backed implementation can
    satisfy the same FileStorage protocol without changing any calling code."""

    def __init__(self, base_dir: Path, base_url: str) -> None:
        self._base_dir = base_dir
        self._base_url = base_url.rstrip("/")
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def save_image(self, content: bytes, content_type: str) -> str:
        extension = _ALLOWED_CONTENT_TYPES.get(content_type)
        if extension is None:
            raise UnsupportedFileTypeError

        if len(content) > MAX_IMAGE_BYTES:
            raise FileTooLargeError

        filename = f"{uuid4()}.{extension}"
        (self._base_dir / filename).write_bytes(content)
        return f"{self._base_url}/{filename}"
