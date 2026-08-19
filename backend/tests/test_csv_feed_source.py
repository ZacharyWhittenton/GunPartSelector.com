from pathlib import Path

import pytest

from site_api.services.feed_sources.csv_feed_source import CsvFeedSource, CsvFeedSourceError

HEADER = "category_hint,brand,name,sku,price_cents,weight_oz,description,affiliate_url,image_url,in_stock,attribute_tags\n"


def _write_csv(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "feed.csv"
    path.write_text(HEADER + body, encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_fetch_items_parses_a_row(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "Barrels,BCM,16in Barrel,BCM-16,22900,28.5,A test barrel.,"
        "https://example.com/bcm-16,https://example.com/bcm-16.jpg,true,"
        "caliber:556;platform:ar15\n",
    )

    items = await CsvFeedSource(path).fetch_items()

    assert len(items) == 1
    item = items[0]
    assert item.category_hint == "Barrels"
    assert item.brand == "BCM"
    assert item.name == "16in Barrel"
    assert item.sku == "BCM-16"
    assert item.price_cents == 22900
    assert item.weight_oz == 28.5
    assert item.affiliate_url == "https://example.com/bcm-16"
    assert item.image_url == "https://example.com/bcm-16.jpg"
    assert item.in_stock is True
    assert item.attribute_tags == ["caliber:556", "platform:ar15"]


@pytest.mark.asyncio
async def test_fetch_items_defaults_missing_optional_fields(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "Barrels,BCM,16in Barrel,BCM-16,22900,28.5,A test barrel.,"
        "https://example.com/bcm-16,,,\n",
    )

    items = await CsvFeedSource(path).fetch_items()

    assert items[0].image_url is None
    assert items[0].in_stock is True
    assert items[0].attribute_tags == []


@pytest.mark.asyncio
async def test_fetch_items_parses_out_of_stock(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "Barrels,BCM,16in Barrel,BCM-16,22900,28.5,A test barrel.,"
        "https://example.com/bcm-16,,false,\n",
    )

    items = await CsvFeedSource(path).fetch_items()

    assert items[0].in_stock is False


@pytest.mark.asyncio
async def test_fetch_items_raises_on_missing_required_column(tmp_path: Path) -> None:
    path = tmp_path / "feed.csv"
    path.write_text("brand,name\nBCM,16in Barrel\n", encoding="utf-8")

    with pytest.raises(CsvFeedSourceError, match="missing required column"):
        await CsvFeedSource(path).fetch_items()


@pytest.mark.asyncio
async def test_fetch_items_raises_on_unparseable_price(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "Barrels,BCM,16in Barrel,BCM-16,not-a-number,28.5,A test barrel.,"
        "https://example.com/bcm-16,,,\n",
    )

    with pytest.raises(CsvFeedSourceError, match="Row 2"):
        await CsvFeedSource(path).fetch_items()
