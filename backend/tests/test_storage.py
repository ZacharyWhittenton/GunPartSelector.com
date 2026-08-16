from pathlib import Path

import pytest

from site_api.core.storage import LocalFileStorage
from site_api.domain.storage import FileTooLargeError, UnsupportedFileTypeError


@pytest.mark.asyncio
async def test_save_image_writes_file_and_returns_url(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path / "blog", base_url="/api/uploads/blog")

    url = await storage.save_image(b"fake-image-bytes", "image/png")

    assert url.startswith("/api/uploads/blog/")
    assert url.endswith(".png")
    saved_files = list((tmp_path / "blog").iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == b"fake-image-bytes"


@pytest.mark.asyncio
async def test_save_image_rejects_unsupported_type(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path / "blog", base_url="/api/uploads/blog")

    with pytest.raises(UnsupportedFileTypeError):
        await storage.save_image(b"not-an-image", "application/pdf")


@pytest.mark.asyncio
async def test_save_image_rejects_oversized_file(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path / "blog", base_url="/api/uploads/blog")
    oversized_content = b"x" * (5 * 1024 * 1024 + 1)

    with pytest.raises(FileTooLargeError):
        await storage.save_image(oversized_content, "image/jpeg")


def test_constructor_creates_base_directory(tmp_path: Path) -> None:
    base_dir = tmp_path / "does-not-exist-yet"

    LocalFileStorage(base_dir=base_dir, base_url="/api/uploads/blog")

    assert base_dir.is_dir()
