from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import BuildItemRecord, BuildRecord, ContactRequestRecord
from site_api.db.repositories import SqlAlchemyBuildRepository, SqlAlchemyContactRequestRepository
from site_api.domain.builds import Build, BuildItem
from site_api.domain.catalog import Product, StockStatus
from site_api.domain.contacts import ContactRequest, ContactRequestStatus


class RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = False

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        self.flushed = True


class OrderedRecordingSession:
    """Tracks add/flush calls in order, so tests can assert a parent row is
    flushed before dependent child rows are added -- catching FK-ordering bugs
    that a plain add-then-flush-once fake can't distinguish."""

    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def add(self, record: object) -> None:
        self.events.append(("add", record))

    async def flush(self) -> None:
        self.events.append(("flush", None))


@pytest.mark.asyncio
async def test_repository_maps_and_flushes_contact_request() -> None:
    session = RecordingSession()
    repository = SqlAlchemyContactRequestRepository(cast(AsyncSession, session))
    contact_request = ContactRequest(
        id=UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"),
        name="Taylor Client",
        email_address="taylor@example.com",
        company=None,
        phone=None,
        service="Asphalt Repair",
        message="Please call me.",
        status=ContactRequestStatus.RECEIVED,
        created_at=datetime(2026, 8, 4, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 4, 12, 0, tzinfo=UTC),
        follow_up_at=None,
    )

    result = await repository.add(contact_request)

    assert result is contact_request
    assert session.flushed is True
    assert len(session.added) == 1
    record = session.added[0]
    assert isinstance(record, ContactRequestRecord)
    assert record.email_address == contact_request.email_address


def _make_product(**overrides: object) -> Product:
    now = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
    defaults: dict[str, object] = {
        "id": UUID(int=10),
        "category_id": UUID(int=1),
        "brand": "BCM",
        "name": "Standard 16in Barrel",
        "slug": "bcm-standard-16in-barrel",
        "sku": "BCM-BBL-16",
        "description": "A test barrel.",
        "price_cents": 22900,
        "weight_oz": 28.5,
        "image_url": None,
        "affiliate_url": "#",
        "affiliate_retailer_name": None,
        "stock_status": StockStatus.IN_STOCK,
        "attribute_tags": ["caliber:556"],
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Product(**defaults)


@pytest.mark.asyncio
async def test_build_repository_flushes_build_before_adding_items() -> None:
    session = OrderedRecordingSession()
    repository = SqlAlchemyBuildRepository(cast(AsyncSession, session))
    build = Build(
        id=UUID(int=1),
        slug="abc123defg",
        name="My Carbine",
        created_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
        items=[
            BuildItem(id=UUID(int=2), build_id=UUID(int=1), product=_make_product(), quantity=1)
        ],
    )

    await repository.add(build)

    kinds = [
        (kind, type(record).__name__ if record is not None else None)
        for kind, record in session.events
    ]
    assert kinds == [
        ("add", "BuildRecord"),
        ("flush", None),
        ("add", "BuildItemRecord"),
        ("flush", None),
    ]
    build_record = session.events[0][1]
    assert isinstance(build_record, BuildRecord)
    assert build_record.slug == "abc123defg"
    item_record = session.events[2][1]
    assert isinstance(item_record, BuildItemRecord)
    assert item_record.build_id == build.id
    assert item_record.product_id == UUID(int=10)
