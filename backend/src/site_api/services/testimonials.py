from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger

from site_api.domain.testimonials import (
    InvalidRatingError,
    Testimonial,
    TestimonialNotFoundError,
    TestimonialRepository,
    TestimonialStatus,
)

MIN_RATING = 1
MAX_RATING = 5


@dataclass(frozen=True, slots=True)
class SubmitTestimonial:
    customer_id: UUID
    customer_name: str
    rating: int
    body: str


class TestimonialService:
    def __init__(
        self,
        repository: TestimonialRepository,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory
        self._clock = clock

    async def submit_testimonial(self, command: SubmitTestimonial) -> Testimonial:
        if not (MIN_RATING <= command.rating <= MAX_RATING):
            raise InvalidRatingError

        now = self._clock()
        existing = await self._repository.get_by_customer_id(command.customer_id)

        if existing is None:
            testimonial = Testimonial(
                id=self._id_factory(),
                customer_id=command.customer_id,
                customer_name=command.customer_name,
                rating=command.rating,
                body=command.body,
                status=TestimonialStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            saved = await self._repository.add(testimonial)
            logger.bind(testimonial_id=str(saved.id)).info("Testimonial submitted")
            return saved

        updated = Testimonial(
            id=existing.id,
            customer_id=existing.customer_id,
            customer_name=command.customer_name,
            rating=command.rating,
            body=command.body,
            status=TestimonialStatus.PENDING,
            created_at=existing.created_at,
            updated_at=now,
        )
        saved = await self._repository.update(updated)
        logger.bind(testimonial_id=str(saved.id)).info("Testimonial resubmitted for approval")
        return saved

    async def get_my_testimonial(self, customer_id: UUID) -> Testimonial | None:
        return await self._repository.get_by_customer_id(customer_id)

    async def approve_testimonial(self, testimonial_id: UUID) -> Testimonial:
        return await self._set_status(testimonial_id, TestimonialStatus.APPROVED)

    async def reject_testimonial(self, testimonial_id: UUID) -> Testimonial:
        return await self._set_status(testimonial_id, TestimonialStatus.REJECTED)

    async def delete_testimonial(self, testimonial_id: UUID) -> None:
        testimonial = await self._repository.get_by_id(testimonial_id)
        if testimonial is None:
            raise TestimonialNotFoundError
        await self._repository.delete(testimonial_id)

    async def list_approved(self, limit: int | None = None) -> list[Testimonial]:
        return await self._repository.list_approved(limit)

    async def list_all(self, status: TestimonialStatus | None = None) -> list[Testimonial]:
        return await self._repository.list_all(status)

    async def _set_status(self, testimonial_id: UUID, status: TestimonialStatus) -> Testimonial:
        testimonial = await self._repository.get_by_id(testimonial_id)
        if testimonial is None:
            raise TestimonialNotFoundError

        updated = Testimonial(
            id=testimonial.id,
            customer_id=testimonial.customer_id,
            customer_name=testimonial.customer_name,
            rating=testimonial.rating,
            body=testimonial.body,
            status=status,
            created_at=testimonial.created_at,
            updated_at=self._clock(),
        )
        saved = await self._repository.update(updated)
        logger.bind(testimonial_id=str(saved.id), status=status.value).info(
            "Testimonial status updated"
        )
        return saved
