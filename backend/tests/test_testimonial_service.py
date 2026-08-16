from datetime import UTC, datetime
from itertools import count
from uuid import UUID

import pytest

from site_api.domain.testimonials import (
    InvalidRatingError,
    TestimonialNotFoundError,
    TestimonialStatus,
)
from site_api.services.testimonials import SubmitTestimonial, TestimonialService
from tests.conftest import InMemoryTestimonialRepository

CUSTOMER_ID = UUID("22222222-2222-2222-2222-222222222222")
OTHER_CUSTOMER_ID = UUID("33333333-3333-3333-3333-333333333333")

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


@pytest.fixture
def service(testimonial_repository: InMemoryTestimonialRepository) -> TestimonialService:
    ids = iter(UUID(int=n) for n in count(1))
    return TestimonialService(
        testimonial_repository,
        id_factory=lambda: next(ids),
        clock=lambda: NOW,
    )


def _submit_command(**overrides: object) -> SubmitTestimonial:
    defaults: dict[str, object] = {
        "customer_id": CUSTOMER_ID,
        "customer_name": "Taylor Client",
        "rating": 5,
        "body": "Fantastic team, highly recommend.",
    }
    defaults.update(overrides)
    return SubmitTestimonial(**defaults)


@pytest.mark.asyncio
async def test_submit_new_testimonial_is_pending(service: TestimonialService) -> None:
    testimonial = await service.submit_testimonial(_submit_command())

    assert testimonial.status is TestimonialStatus.PENDING
    assert testimonial.customer_id == CUSTOMER_ID
    assert testimonial.rating == 5


@pytest.mark.asyncio
async def test_submit_rejects_rating_out_of_range(service: TestimonialService) -> None:
    with pytest.raises(InvalidRatingError):
        await service.submit_testimonial(_submit_command(rating=6))

    with pytest.raises(InvalidRatingError):
        await service.submit_testimonial(_submit_command(rating=0))


@pytest.mark.asyncio
async def test_resubmitting_updates_existing_and_resets_to_pending(
    service: TestimonialService,
) -> None:
    first = await service.submit_testimonial(_submit_command(rating=3, body="It was okay."))
    await service.approve_testimonial(first.id)

    updated = await service.submit_testimonial(
        _submit_command(rating=5, body="Actually it grew on me, love it now.")
    )

    assert updated.id == first.id
    assert updated.rating == 5
    assert updated.status is TestimonialStatus.PENDING
    all_testimonials = await service.list_all()
    assert len(all_testimonials) == 1


@pytest.mark.asyncio
async def test_get_my_testimonial_returns_none_when_absent(service: TestimonialService) -> None:
    assert await service.get_my_testimonial(CUSTOMER_ID) is None


@pytest.mark.asyncio
async def test_approve_testimonial(service: TestimonialService) -> None:
    testimonial = await service.submit_testimonial(_submit_command())

    approved = await service.approve_testimonial(testimonial.id)

    assert approved.status is TestimonialStatus.APPROVED


@pytest.mark.asyncio
async def test_reject_testimonial(service: TestimonialService) -> None:
    testimonial = await service.submit_testimonial(_submit_command())

    rejected = await service.reject_testimonial(testimonial.id)

    assert rejected.status is TestimonialStatus.REJECTED


@pytest.mark.asyncio
async def test_approve_raises_when_missing(service: TestimonialService) -> None:
    with pytest.raises(TestimonialNotFoundError):
        await service.approve_testimonial(UUID(int=999))


@pytest.mark.asyncio
async def test_delete_testimonial(service: TestimonialService) -> None:
    testimonial = await service.submit_testimonial(_submit_command())

    await service.delete_testimonial(testimonial.id)

    assert await service.list_all() == []


@pytest.mark.asyncio
async def test_delete_raises_when_missing(service: TestimonialService) -> None:
    with pytest.raises(TestimonialNotFoundError):
        await service.delete_testimonial(UUID(int=999))


@pytest.mark.asyncio
async def test_list_approved_excludes_pending_and_rejected(service: TestimonialService) -> None:
    approved = await service.submit_testimonial(_submit_command(customer_id=CUSTOMER_ID))
    await service.approve_testimonial(approved.id)

    pending = await service.submit_testimonial(_submit_command(customer_id=OTHER_CUSTOMER_ID))

    visible = await service.list_approved()

    assert [testimonial.id for testimonial in visible] == [approved.id]
    assert pending.status is TestimonialStatus.PENDING


@pytest.mark.asyncio
async def test_list_approved_respects_limit(service: TestimonialService) -> None:
    for index in range(3):
        submitted = await service.submit_testimonial(
            _submit_command(customer_id=UUID(int=100 + index))
        )
        await service.approve_testimonial(submitted.id)

    limited = await service.list_approved(limit=2)

    assert len(limited) == 2


@pytest.mark.asyncio
async def test_list_all_filters_by_status(service: TestimonialService) -> None:
    approved = await service.submit_testimonial(_submit_command(customer_id=CUSTOMER_ID))
    await service.approve_testimonial(approved.id)
    await service.submit_testimonial(_submit_command(customer_id=OTHER_CUSTOMER_ID))

    approved_only = await service.list_all(TestimonialStatus.APPROVED)
    pending_only = await service.list_all(TestimonialStatus.PENDING)

    assert len(approved_only) == 1
    assert len(pending_only) == 1
