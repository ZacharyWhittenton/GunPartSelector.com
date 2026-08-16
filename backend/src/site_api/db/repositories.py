from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import (
    AccountNoteRecord,
    AppointmentRecord,
    BlogPostRecord,
    BuildItemRecord,
    BuildRecord,
    ClickEventRecord,
    CommentRecord,
    ContactRequestRecord,
    DiscountCodeRecord,
    LeadNoteRecord,
    MarketplaceItemRecord,
    OrderItemRecord,
    OrderRecord,
    PageViewRecord,
    PartCategoryRecord,
    ProductRecord,
    TagSubscriptionRecord,
    TestimonialRecord,
    UserRecord,
    WishlistItemRecord,
)
from site_api.domain.account_notes import AccountNote
from site_api.domain.analytics import ClickEvent, PageViewEvent, PageViewSummary
from site_api.domain.blog import (
    BlogPost,
    Comment,
    CommentNotFoundError,
    PostNotFoundError,
    PostStatus,
    TagSubscription,
)
from site_api.domain.builds import Build, BuildItem
from site_api.domain.catalog import (
    CategoryWithCount,
    PartCategory,
    Product,
    ProductFacets,
    ProductFilter,
    ProductSort,
    StockStatus,
)
from site_api.domain.contacts import (
    ContactRequest,
    ContactRequestNotFoundError,
    ContactRequestStatus,
)
from site_api.domain.discount_codes import DiscountCode, DiscountCodeNotFoundError, DiscountType
from site_api.domain.lead_notes import LeadNote
from site_api.domain.marketplace import (
    ItemNotFoundError,
    MarketplaceItem,
    Order,
    OrderItem,
    OrderNotFoundError,
    OrderStatus,
    WishlistItem,
)
from site_api.domain.scheduling import Appointment, AppointmentStatus, SlotNotFoundError
from site_api.domain.testimonials import (
    Testimonial,
    TestimonialNotFoundError,
    TestimonialStatus,
)
from site_api.domain.users import AccountStatus, User, UserNotFoundError, UserRole


def _to_domain_user(record: UserRecord) -> User:
    return User(
        id=record.id,
        email_address=record.email_address,
        full_name=record.full_name,
        hashed_password=record.hashed_password,
        role=UserRole(record.role),
        status=AccountStatus(record.status),
        created_at=record.created_at,
        last_login_at=record.last_login_at,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        self._session.add(
            UserRecord(
                id=user.id,
                email_address=user.email_address,
                full_name=user.full_name,
                hashed_password=user.hashed_password,
                role=user.role.value,
                status=user.status.value,
                created_at=user.created_at,
                last_login_at=user.last_login_at,
            )
        )
        await self._session.flush()
        return user

    async def get_by_email(self, email_address: str) -> User | None:
        result = await self._session.execute(
            select(UserRecord).where(UserRecord.email_address == email_address)
        )
        record = result.scalar_one_or_none()
        return None if record is None else _to_domain_user(record)

    async def get_by_id(self, user_id: UUID) -> User | None:
        record = await self._session.get(UserRecord, user_id)
        return None if record is None else _to_domain_user(record)

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(UserRecord).order_by(UserRecord.created_at))
        return [_to_domain_user(record) for record in result.scalars().all()]

    async def update_role(self, user_id: UUID, role: UserRole) -> User:
        record = await self._session.get(UserRecord, user_id)
        if record is None:
            raise UserNotFoundError
        record.role = role.value
        await self._session.flush()
        return _to_domain_user(record)

    async def update_status(self, user_id: UUID, status: AccountStatus) -> User:
        record = await self._session.get(UserRecord, user_id)
        if record is None:
            raise UserNotFoundError
        record.status = status.value
        await self._session.flush()
        return _to_domain_user(record)

    async def update_last_login(self, user_id: UUID, when: datetime) -> None:
        record = await self._session.get(UserRecord, user_id)
        if record is None:
            raise UserNotFoundError
        record.last_login_at = when
        await self._session.flush()


class SqlAlchemyAccountNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, note: AccountNote) -> AccountNote:
        self._session.add(
            AccountNoteRecord(
                id=note.id,
                user_id=note.user_id,
                author_id=note.author_id,
                author_name=note.author_name,
                body=note.body,
                created_at=note.created_at,
            )
        )
        await self._session.flush()
        return note

    async def list_for_user(self, user_id: UUID) -> list[AccountNote]:
        result = await self._session.execute(
            select(AccountNoteRecord)
            .where(AccountNoteRecord.user_id == user_id)
            .order_by(AccountNoteRecord.created_at.desc())
        )
        return [
            AccountNote(
                id=record.id,
                user_id=record.user_id,
                author_id=record.author_id,
                author_name=record.author_name,
                body=record.body,
                created_at=record.created_at,
            )
            for record in result.scalars().all()
        ]


def _to_domain_post(record: BlogPostRecord) -> BlogPost:
    return BlogPost(
        id=record.id,
        title=record.title,
        slug=record.slug,
        excerpt=record.excerpt,
        body=record.body,
        cover_image_url=record.cover_image_url,
        tags=tuple(record.tags),
        author_id=record.author_id,
        author_name=record.author_name,
        status=PostStatus(record.status),
        published_at=record.published_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyBlogPostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, post: BlogPost) -> BlogPost:
        self._session.add(
            BlogPostRecord(
                id=post.id,
                title=post.title,
                slug=post.slug,
                excerpt=post.excerpt,
                body=post.body,
                cover_image_url=post.cover_image_url,
                tags=list(post.tags),
                author_id=post.author_id,
                author_name=post.author_name,
                status=post.status.value,
                published_at=post.published_at,
                created_at=post.created_at,
                updated_at=post.updated_at,
            )
        )
        await self._session.flush()
        return post

    async def update(self, post: BlogPost) -> BlogPost:
        record = await self._session.get(BlogPostRecord, post.id)
        if record is None:
            raise PostNotFoundError
        record.title = post.title
        record.slug = post.slug
        record.excerpt = post.excerpt
        record.body = post.body
        record.cover_image_url = post.cover_image_url
        record.tags = list(post.tags)
        record.status = post.status.value
        record.published_at = post.published_at
        record.updated_at = post.updated_at
        await self._session.flush()
        return _to_domain_post(record)

    async def delete(self, post_id: UUID) -> None:
        record = await self._session.get(BlogPostRecord, post_id)
        if record is None:
            raise PostNotFoundError
        await self._session.delete(record)
        await self._session.flush()

    async def get_by_id(self, post_id: UUID) -> BlogPost | None:
        record = await self._session.get(BlogPostRecord, post_id)
        return None if record is None else _to_domain_post(record)

    async def get_by_slug(self, slug: str) -> BlogPost | None:
        result = await self._session.execute(
            select(BlogPostRecord).where(BlogPostRecord.slug == slug)
        )
        record = result.scalar_one_or_none()
        return None if record is None else _to_domain_post(record)

    async def slug_exists(self, slug: str) -> bool:
        result = await self._session.execute(
            select(BlogPostRecord.id).where(BlogPostRecord.slug == slug)
        )
        return result.scalar_one_or_none() is not None

    async def list_published(self, tag: str | None = None) -> list[BlogPost]:
        query = select(BlogPostRecord).where(BlogPostRecord.status == PostStatus.PUBLISHED.value)
        if tag is not None:
            query = query.where(BlogPostRecord.tags.any(tag))
        query = query.order_by(BlogPostRecord.published_at.desc())
        result = await self._session.execute(query)
        return [_to_domain_post(record) for record in result.scalars().all()]

    async def list_all(self) -> list[BlogPost]:
        result = await self._session.execute(
            select(BlogPostRecord).order_by(BlogPostRecord.created_at.desc())
        )
        return [_to_domain_post(record) for record in result.scalars().all()]

    async def list_distinct_published_tags(self) -> list[str]:
        result = await self._session.execute(
            select(BlogPostRecord.tags).where(BlogPostRecord.status == PostStatus.PUBLISHED.value)
        )
        tags: set[str] = set()
        for row in result.scalars().all():
            tags.update(row)
        return sorted(tags)


class SqlAlchemyCommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, comment: Comment) -> Comment:
        self._session.add(
            CommentRecord(
                id=comment.id,
                post_id=comment.post_id,
                author_id=comment.author_id,
                author_name=comment.author_name,
                body=comment.body,
                created_at=comment.created_at,
            )
        )
        await self._session.flush()
        return comment

    async def get_by_id(self, comment_id: UUID) -> Comment | None:
        record = await self._session.get(CommentRecord, comment_id)
        return None if record is None else self._to_domain(record)

    async def list_for_post(self, post_id: UUID) -> list[Comment]:
        result = await self._session.execute(
            select(CommentRecord)
            .where(CommentRecord.post_id == post_id)
            .order_by(CommentRecord.created_at)
        )
        return [self._to_domain(record) for record in result.scalars().all()]

    async def delete(self, comment_id: UUID) -> None:
        record = await self._session.get(CommentRecord, comment_id)
        if record is None:
            raise CommentNotFoundError
        await self._session.delete(record)
        await self._session.flush()

    @staticmethod
    def _to_domain(record: CommentRecord) -> Comment:
        return Comment(
            id=record.id,
            post_id=record.post_id,
            author_id=record.author_id,
            author_name=record.author_name,
            body=record.body,
            created_at=record.created_at,
        )


class SqlAlchemyTagSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, subscription: TagSubscription) -> TagSubscription:
        self._session.add(
            TagSubscriptionRecord(
                id=subscription.id,
                user_id=subscription.user_id,
                tag_name=subscription.tag_name,
                created_at=subscription.created_at,
            )
        )
        await self._session.flush()
        return subscription

    async def remove(self, user_id: UUID, tag_name: str) -> None:
        result = await self._session.execute(
            select(TagSubscriptionRecord).where(
                TagSubscriptionRecord.user_id == user_id,
                TagSubscriptionRecord.tag_name == tag_name,
            )
        )
        record = result.scalar_one_or_none()
        if record is not None:
            await self._session.delete(record)
            await self._session.flush()

    async def get(self, user_id: UUID, tag_name: str) -> TagSubscription | None:
        result = await self._session.execute(
            select(TagSubscriptionRecord).where(
                TagSubscriptionRecord.user_id == user_id,
                TagSubscriptionRecord.tag_name == tag_name,
            )
        )
        record = result.scalar_one_or_none()
        return None if record is None else self._to_domain(record)

    async def list_for_user(self, user_id: UUID) -> list[TagSubscription]:
        result = await self._session.execute(
            select(TagSubscriptionRecord)
            .where(TagSubscriptionRecord.user_id == user_id)
            .order_by(TagSubscriptionRecord.created_at)
        )
        return [self._to_domain(record) for record in result.scalars().all()]

    @staticmethod
    def _to_domain(record: TagSubscriptionRecord) -> TagSubscription:
        return TagSubscription(
            id=record.id,
            user_id=record.user_id,
            tag_name=record.tag_name,
            created_at=record.created_at,
        )


def _to_domain_contact_request(record: ContactRequestRecord) -> ContactRequest:
    return ContactRequest(
        id=record.id,
        name=record.name,
        email_address=record.email_address,
        company=record.company,
        phone=record.phone,
        service=record.service,
        message=record.message,
        status=ContactRequestStatus(record.status),
        created_at=record.created_at,
        updated_at=record.updated_at,
        follow_up_at=record.follow_up_at,
    )


class SqlAlchemyContactRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, contact_request: ContactRequest) -> ContactRequest:
        self._session.add(
            ContactRequestRecord(
                id=contact_request.id,
                name=contact_request.name,
                email_address=contact_request.email_address,
                company=contact_request.company,
                phone=contact_request.phone,
                service=contact_request.service,
                message=contact_request.message,
                status=contact_request.status.value,
                created_at=contact_request.created_at,
                updated_at=contact_request.updated_at,
                follow_up_at=contact_request.follow_up_at,
            )
        )
        await self._session.flush()
        return contact_request

    async def update(self, contact_request: ContactRequest) -> ContactRequest:
        record = await self._session.get(ContactRequestRecord, contact_request.id)
        if record is None:
            raise ContactRequestNotFoundError
        record.status = contact_request.status.value
        record.updated_at = contact_request.updated_at
        record.follow_up_at = contact_request.follow_up_at
        await self._session.flush()
        return _to_domain_contact_request(record)

    async def get_by_id(self, contact_request_id: UUID) -> ContactRequest | None:
        record = await self._session.get(ContactRequestRecord, contact_request_id)
        return None if record is None else _to_domain_contact_request(record)

    async def list_all(self, status: ContactRequestStatus | None = None) -> list[ContactRequest]:
        query = select(ContactRequestRecord).order_by(ContactRequestRecord.created_at.desc())
        if status is not None:
            query = query.where(ContactRequestRecord.status == status.value)
        result = await self._session.execute(query)
        return [_to_domain_contact_request(record) for record in result.scalars().all()]


class SqlAlchemyLeadNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, note: LeadNote) -> LeadNote:
        self._session.add(
            LeadNoteRecord(
                id=note.id,
                lead_id=note.lead_id,
                author_id=note.author_id,
                author_name=note.author_name,
                body=note.body,
                created_at=note.created_at,
            )
        )
        await self._session.flush()
        return note

    async def list_for_lead(self, lead_id: UUID) -> list[LeadNote]:
        result = await self._session.execute(
            select(LeadNoteRecord)
            .where(LeadNoteRecord.lead_id == lead_id)
            .order_by(LeadNoteRecord.created_at.desc())
        )
        return [
            LeadNote(
                id=record.id,
                lead_id=record.lead_id,
                author_id=record.author_id,
                author_name=record.author_name,
                body=record.body,
                created_at=record.created_at,
            )
            for record in result.scalars().all()
        ]


def _to_domain_appointment(record: AppointmentRecord) -> Appointment:
    return Appointment(
        id=record.id,
        starts_at=record.starts_at,
        ends_at=record.ends_at,
        status=AppointmentStatus(record.status),
        client_id=record.client_id,
        client_name=record.client_name,
        client_email=record.client_email,
        notes=record.notes,
        created_by_admin_id=record.created_by_admin_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyAppointmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, appointment: Appointment) -> Appointment:
        self._session.add(
            AppointmentRecord(
                id=appointment.id,
                starts_at=appointment.starts_at,
                ends_at=appointment.ends_at,
                status=appointment.status.value,
                client_id=appointment.client_id,
                client_name=appointment.client_name,
                client_email=appointment.client_email,
                notes=appointment.notes,
                created_by_admin_id=appointment.created_by_admin_id,
                created_at=appointment.created_at,
                updated_at=appointment.updated_at,
            )
        )
        await self._session.flush()
        return appointment

    async def update(self, appointment: Appointment) -> Appointment:
        record = await self._session.get(AppointmentRecord, appointment.id)
        if record is None:
            raise SlotNotFoundError
        record.starts_at = appointment.starts_at
        record.ends_at = appointment.ends_at
        record.status = appointment.status.value
        record.client_id = appointment.client_id
        record.client_name = appointment.client_name
        record.client_email = appointment.client_email
        record.notes = appointment.notes
        record.updated_at = appointment.updated_at
        await self._session.flush()
        return _to_domain_appointment(record)

    async def delete(self, appointment_id: UUID) -> None:
        record = await self._session.get(AppointmentRecord, appointment_id)
        if record is None:
            raise SlotNotFoundError
        await self._session.delete(record)
        await self._session.flush()

    async def get_by_id(self, appointment_id: UUID) -> Appointment | None:
        record = await self._session.get(AppointmentRecord, appointment_id)
        return None if record is None else _to_domain_appointment(record)

    async def list_open_upcoming(self, now: datetime) -> list[Appointment]:
        result = await self._session.execute(
            select(AppointmentRecord)
            .where(
                AppointmentRecord.status == AppointmentStatus.OPEN.value,
                AppointmentRecord.starts_at >= now,
            )
            .order_by(AppointmentRecord.starts_at)
        )
        return [_to_domain_appointment(record) for record in result.scalars().all()]

    async def list_for_client(self, client_id: UUID) -> list[Appointment]:
        result = await self._session.execute(
            select(AppointmentRecord)
            .where(AppointmentRecord.client_id == client_id)
            .order_by(AppointmentRecord.starts_at.desc())
        )
        return [_to_domain_appointment(record) for record in result.scalars().all()]

    async def list_all(self, status: AppointmentStatus | None = None) -> list[Appointment]:
        query = select(AppointmentRecord)
        if status is not None:
            query = query.where(AppointmentRecord.status == status.value)
        query = query.order_by(AppointmentRecord.starts_at.desc())
        result = await self._session.execute(query)
        return [_to_domain_appointment(record) for record in result.scalars().all()]


def _to_domain_item(record: MarketplaceItemRecord) -> MarketplaceItem:
    return MarketplaceItem(
        id=record.id,
        name=record.name,
        slug=record.slug,
        description=record.description,
        price_cents=record.price_cents,
        image_url=record.image_url,
        is_active=record.is_active,
        created_by_admin_id=record.created_by_admin_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyMarketplaceItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, item: MarketplaceItem) -> MarketplaceItem:
        self._session.add(
            MarketplaceItemRecord(
                id=item.id,
                name=item.name,
                slug=item.slug,
                description=item.description,
                price_cents=item.price_cents,
                image_url=item.image_url,
                is_active=item.is_active,
                created_by_admin_id=item.created_by_admin_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
        await self._session.flush()
        return item

    async def update(self, item: MarketplaceItem) -> MarketplaceItem:
        record = await self._session.get(MarketplaceItemRecord, item.id)
        if record is None:
            raise ItemNotFoundError
        record.name = item.name
        record.description = item.description
        record.price_cents = item.price_cents
        record.image_url = item.image_url
        record.is_active = item.is_active
        record.updated_at = item.updated_at
        await self._session.flush()
        return _to_domain_item(record)

    async def delete(self, item_id: UUID) -> None:
        record = await self._session.get(MarketplaceItemRecord, item_id)
        if record is None:
            raise ItemNotFoundError
        await self._session.delete(record)
        await self._session.flush()

    async def get_by_id(self, item_id: UUID) -> MarketplaceItem | None:
        record = await self._session.get(MarketplaceItemRecord, item_id)
        return None if record is None else _to_domain_item(record)

    async def get_by_slug(self, slug: str) -> MarketplaceItem | None:
        result = await self._session.execute(
            select(MarketplaceItemRecord).where(MarketplaceItemRecord.slug == slug)
        )
        record = result.scalar_one_or_none()
        return None if record is None else _to_domain_item(record)

    async def slug_exists(self, slug: str) -> bool:
        result = await self._session.execute(
            select(MarketplaceItemRecord.id).where(MarketplaceItemRecord.slug == slug)
        )
        return result.scalar_one_or_none() is not None

    async def list_active(self) -> list[MarketplaceItem]:
        result = await self._session.execute(
            select(MarketplaceItemRecord)
            .where(MarketplaceItemRecord.is_active.is_(True))
            .order_by(MarketplaceItemRecord.created_at.desc())
        )
        return [_to_domain_item(record) for record in result.scalars().all()]

    async def list_all(self) -> list[MarketplaceItem]:
        result = await self._session.execute(
            select(MarketplaceItemRecord).order_by(MarketplaceItemRecord.created_at.desc())
        )
        return [_to_domain_item(record) for record in result.scalars().all()]


def _to_domain_order(record: OrderRecord) -> Order:
    return Order(
        id=record.id,
        stripe_checkout_session_id=record.stripe_checkout_session_id,
        stripe_payment_intent_id=record.stripe_payment_intent_id,
        customer_id=record.customer_id,
        customer_email=record.customer_email,
        status=OrderStatus(record.status),
        total_cents=record.total_cents,
        discount_code=record.discount_code,
        discount_cents=record.discount_cents,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _to_domain_order_item(record: OrderItemRecord) -> OrderItem:
    return OrderItem(
        id=record.id,
        order_id=record.order_id,
        marketplace_item_id=record.marketplace_item_id,
        item_name=record.item_name,
        unit_price_cents=record.unit_price_cents,
        quantity=record.quantity,
        line_total_cents=record.line_total_cents,
    )


class SqlAlchemyOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, order: Order, items: list[OrderItem]) -> Order:
        self._session.add(
            OrderRecord(
                id=order.id,
                stripe_checkout_session_id=order.stripe_checkout_session_id,
                stripe_payment_intent_id=order.stripe_payment_intent_id,
                customer_id=order.customer_id,
                customer_email=order.customer_email,
                status=order.status.value,
                total_cents=order.total_cents,
                discount_code=order.discount_code,
                discount_cents=order.discount_cents,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )
        )
        for item in items:
            self._session.add(
                OrderItemRecord(
                    id=item.id,
                    order_id=item.order_id,
                    marketplace_item_id=item.marketplace_item_id,
                    item_name=item.item_name,
                    unit_price_cents=item.unit_price_cents,
                    quantity=item.quantity,
                    line_total_cents=item.line_total_cents,
                )
            )
        await self._session.flush()
        return order

    async def update_status(
        self,
        order_id: UUID,
        status: OrderStatus,
        stripe_payment_intent_id: str | None,
        customer_email: str | None,
    ) -> Order:
        record = await self._session.get(OrderRecord, order_id)
        if record is None:
            raise OrderNotFoundError
        record.status = status.value
        if stripe_payment_intent_id is not None:
            record.stripe_payment_intent_id = stripe_payment_intent_id
        if customer_email is not None:
            record.customer_email = customer_email
        await self._session.flush()
        return _to_domain_order(record)

    async def get_by_id(self, order_id: UUID) -> Order | None:
        record = await self._session.get(OrderRecord, order_id)
        return None if record is None else _to_domain_order(record)

    async def get_by_session_id(self, stripe_checkout_session_id: str) -> Order | None:
        result = await self._session.execute(
            select(OrderRecord).where(
                OrderRecord.stripe_checkout_session_id == stripe_checkout_session_id
            )
        )
        record = result.scalar_one_or_none()
        return None if record is None else _to_domain_order(record)

    async def list_items_for_order(self, order_id: UUID) -> list[OrderItem]:
        result = await self._session.execute(
            select(OrderItemRecord).where(OrderItemRecord.order_id == order_id)
        )
        return [_to_domain_order_item(record) for record in result.scalars().all()]

    async def list_for_customer(self, customer_id: UUID) -> list[Order]:
        result = await self._session.execute(
            select(OrderRecord)
            .where(OrderRecord.customer_id == customer_id)
            .order_by(OrderRecord.created_at.desc())
        )
        return [_to_domain_order(record) for record in result.scalars().all()]

    async def list_all(self, status: OrderStatus | None = None) -> list[Order]:
        query = select(OrderRecord)
        if status is not None:
            query = query.where(OrderRecord.status == status.value)
        query = query.order_by(OrderRecord.created_at.desc())
        result = await self._session.execute(query)
        return [_to_domain_order(record) for record in result.scalars().all()]

    async def count_orders_for_item(self, item_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(OrderItemRecord)
            .where(OrderItemRecord.marketplace_item_id == item_id)
        )
        return result.scalar_one()


class SqlAlchemyWishlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, wishlist_item: WishlistItem) -> WishlistItem:
        self._session.add(
            WishlistItemRecord(
                id=wishlist_item.id,
                user_id=wishlist_item.user_id,
                marketplace_item_id=wishlist_item.marketplace_item_id,
                created_at=wishlist_item.created_at,
            )
        )
        await self._session.flush()
        return wishlist_item

    async def remove(self, user_id: UUID, marketplace_item_id: UUID) -> None:
        result = await self._session.execute(
            select(WishlistItemRecord).where(
                WishlistItemRecord.user_id == user_id,
                WishlistItemRecord.marketplace_item_id == marketplace_item_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is not None:
            await self._session.delete(record)
            await self._session.flush()

    async def get(self, user_id: UUID, marketplace_item_id: UUID) -> WishlistItem | None:
        result = await self._session.execute(
            select(WishlistItemRecord).where(
                WishlistItemRecord.user_id == user_id,
                WishlistItemRecord.marketplace_item_id == marketplace_item_id,
            )
        )
        record = result.scalar_one_or_none()
        return None if record is None else self._to_domain(record)

    async def list_for_user(self, user_id: UUID) -> list[WishlistItem]:
        result = await self._session.execute(
            select(WishlistItemRecord)
            .where(WishlistItemRecord.user_id == user_id)
            .order_by(WishlistItemRecord.created_at.desc())
        )
        return [self._to_domain(record) for record in result.scalars().all()]

    @staticmethod
    def _to_domain(record: WishlistItemRecord) -> WishlistItem:
        return WishlistItem(
            id=record.id,
            user_id=record.user_id,
            marketplace_item_id=record.marketplace_item_id,
            created_at=record.created_at,
        )


def _to_domain_testimonial(record: TestimonialRecord) -> Testimonial:
    return Testimonial(
        id=record.id,
        customer_id=record.customer_id,
        customer_name=record.customer_name,
        rating=record.rating,
        body=record.body,
        status=TestimonialStatus(record.status),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyTestimonialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, testimonial: Testimonial) -> Testimonial:
        self._session.add(
            TestimonialRecord(
                id=testimonial.id,
                customer_id=testimonial.customer_id,
                customer_name=testimonial.customer_name,
                rating=testimonial.rating,
                body=testimonial.body,
                status=testimonial.status.value,
                created_at=testimonial.created_at,
                updated_at=testimonial.updated_at,
            )
        )
        await self._session.flush()
        return testimonial

    async def update(self, testimonial: Testimonial) -> Testimonial:
        record = await self._session.get(TestimonialRecord, testimonial.id)
        if record is None:
            raise TestimonialNotFoundError
        record.customer_name = testimonial.customer_name
        record.rating = testimonial.rating
        record.body = testimonial.body
        record.status = testimonial.status.value
        record.updated_at = testimonial.updated_at
        await self._session.flush()
        return _to_domain_testimonial(record)

    async def delete(self, testimonial_id: UUID) -> None:
        record = await self._session.get(TestimonialRecord, testimonial_id)
        if record is None:
            raise TestimonialNotFoundError
        await self._session.delete(record)
        await self._session.flush()

    async def get_by_id(self, testimonial_id: UUID) -> Testimonial | None:
        record = await self._session.get(TestimonialRecord, testimonial_id)
        return None if record is None else _to_domain_testimonial(record)

    async def get_by_customer_id(self, customer_id: UUID) -> Testimonial | None:
        result = await self._session.execute(
            select(TestimonialRecord).where(TestimonialRecord.customer_id == customer_id)
        )
        record = result.scalar_one_or_none()
        return None if record is None else _to_domain_testimonial(record)

    async def list_approved(self, limit: int | None = None) -> list[Testimonial]:
        query = (
            select(TestimonialRecord)
            .where(TestimonialRecord.status == TestimonialStatus.APPROVED.value)
            .order_by(TestimonialRecord.created_at.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self._session.execute(query)
        return [_to_domain_testimonial(record) for record in result.scalars().all()]

    async def list_all(self, status: TestimonialStatus | None = None) -> list[Testimonial]:
        query = select(TestimonialRecord).order_by(TestimonialRecord.created_at.desc())
        if status is not None:
            query = query.where(TestimonialRecord.status == status.value)
        result = await self._session.execute(query)
        return [_to_domain_testimonial(record) for record in result.scalars().all()]


def _to_domain_discount_code(record: DiscountCodeRecord) -> DiscountCode:
    return DiscountCode(
        id=record.id,
        code=record.code,
        discount_type=DiscountType(record.discount_type),
        value=record.value,
        is_active=record.is_active,
        expires_at=record.expires_at,
        max_redemptions=record.max_redemptions,
        redemption_count=record.redemption_count,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyDiscountCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, discount_code: DiscountCode) -> DiscountCode:
        self._session.add(
            DiscountCodeRecord(
                id=discount_code.id,
                code=discount_code.code,
                discount_type=discount_code.discount_type.value,
                value=discount_code.value,
                is_active=discount_code.is_active,
                expires_at=discount_code.expires_at,
                max_redemptions=discount_code.max_redemptions,
                redemption_count=discount_code.redemption_count,
                created_at=discount_code.created_at,
                updated_at=discount_code.updated_at,
            )
        )
        await self._session.flush()
        return discount_code

    async def update(self, discount_code: DiscountCode) -> DiscountCode:
        record = await self._session.get(DiscountCodeRecord, discount_code.id)
        if record is None:
            raise DiscountCodeNotFoundError
        record.discount_type = discount_code.discount_type.value
        record.value = discount_code.value
        record.is_active = discount_code.is_active
        record.expires_at = discount_code.expires_at
        record.max_redemptions = discount_code.max_redemptions
        record.redemption_count = discount_code.redemption_count
        record.updated_at = discount_code.updated_at
        await self._session.flush()
        return _to_domain_discount_code(record)

    async def delete(self, discount_code_id: UUID) -> None:
        record = await self._session.get(DiscountCodeRecord, discount_code_id)
        if record is None:
            raise DiscountCodeNotFoundError
        await self._session.delete(record)
        await self._session.flush()

    async def get_by_id(self, discount_code_id: UUID) -> DiscountCode | None:
        record = await self._session.get(DiscountCodeRecord, discount_code_id)
        return None if record is None else _to_domain_discount_code(record)

    async def get_by_code(self, code: str) -> DiscountCode | None:
        result = await self._session.execute(
            select(DiscountCodeRecord).where(DiscountCodeRecord.code == code)
        )
        record = result.scalar_one_or_none()
        return None if record is None else _to_domain_discount_code(record)

    async def list_all(self) -> list[DiscountCode]:
        result = await self._session.execute(
            select(DiscountCodeRecord).order_by(DiscountCodeRecord.created_at.desc())
        )
        return [_to_domain_discount_code(record) for record in result.scalars().all()]


def _to_domain_click(record: ClickEventRecord) -> ClickEvent:
    return ClickEvent(
        id=record.id,
        path=record.path,
        x_percent=record.x_percent,
        y_percent=record.y_percent,
        element_label=record.element_label,
        session_id=record.session_id,
        created_at=record.created_at,
    )


class SqlAlchemyAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_page_view(self, event: PageViewEvent) -> PageViewEvent:
        self._session.add(
            PageViewRecord(
                id=event.id,
                path=event.path,
                referrer=event.referrer,
                session_id=event.session_id,
                created_at=event.created_at,
            )
        )
        await self._session.flush()
        return event

    async def record_click(self, event: ClickEvent) -> ClickEvent:
        self._session.add(
            ClickEventRecord(
                id=event.id,
                path=event.path,
                x_percent=event.x_percent,
                y_percent=event.y_percent,
                element_label=event.element_label,
                session_id=event.session_id,
                created_at=event.created_at,
            )
        )
        await self._session.flush()
        return event

    async def top_pages(self, since: datetime, limit: int) -> list[PageViewSummary]:
        result = await self._session.execute(
            select(
                PageViewRecord.path,
                func.count().label("view_count"),
                func.count(func.distinct(PageViewRecord.session_id)).label("unique_sessions"),
            )
            .where(PageViewRecord.created_at >= since)
            .group_by(PageViewRecord.path)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [
            PageViewSummary(
                path=row.path, view_count=row.view_count, unique_sessions=row.unique_sessions
            )
            for row in result.all()
        ]

    async def click_points(self, path: str, since: datetime) -> list[ClickEvent]:
        result = await self._session.execute(
            select(ClickEventRecord).where(
                ClickEventRecord.path == path, ClickEventRecord.created_at >= since
            )
        )
        return [_to_domain_click(record) for record in result.scalars().all()]


def _to_domain_category(record: PartCategoryRecord) -> PartCategory:
    return PartCategory(
        id=record.id,
        slug=record.slug,
        name=record.name,
        section=record.section,
        sort_order=record.sort_order,
        created_at=record.created_at,
    )


class SqlAlchemyPartCategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_with_counts(self) -> list[CategoryWithCount]:
        result = await self._session.execute(
            select(
                PartCategoryRecord,
                func.count(ProductRecord.id).label("product_count"),
            )
            .outerjoin(
                ProductRecord,
                (ProductRecord.category_id == PartCategoryRecord.id)
                & (ProductRecord.is_active.is_(True)),
            )
            .group_by(PartCategoryRecord.id)
            .order_by(PartCategoryRecord.sort_order)
        )
        return [
            CategoryWithCount(category=_to_domain_category(record), product_count=count)
            for record, count in result.all()
        ]

    async def get_by_slug(self, slug: str) -> PartCategory | None:
        result = await self._session.execute(
            select(PartCategoryRecord).where(PartCategoryRecord.slug == slug)
        )
        record = result.scalar_one_or_none()
        return None if record is None else _to_domain_category(record)


def _to_domain_product(record: ProductRecord) -> Product:
    return Product(
        id=record.id,
        category_id=record.category_id,
        brand=record.brand,
        name=record.name,
        slug=record.slug,
        sku=record.sku,
        description=record.description,
        price_cents=record.price_cents,
        weight_oz=record.weight_oz,
        image_url=record.image_url,
        affiliate_url=record.affiliate_url,
        affiliate_retailer_name=record.affiliate_retailer_name,
        stock_status=StockStatus(record.stock_status),
        attribute_tags=list(record.attribute_tags),
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_filtered(self, product_filter: ProductFilter) -> tuple[list[Product], int]:
        query = select(ProductRecord).where(ProductRecord.is_active.is_(True))

        if product_filter.category_slug is not None:
            query = query.join(
                PartCategoryRecord, ProductRecord.category_id == PartCategoryRecord.id
            ).where(PartCategoryRecord.slug == product_filter.category_slug)
        if product_filter.brand:
            query = query.where(ProductRecord.brand.in_(product_filter.brand))
        if product_filter.price_min_cents is not None:
            query = query.where(ProductRecord.price_cents >= product_filter.price_min_cents)
        if product_filter.price_max_cents is not None:
            query = query.where(ProductRecord.price_cents <= product_filter.price_max_cents)
        if product_filter.stock_status is not None:
            query = query.where(ProductRecord.stock_status == product_filter.stock_status.value)
        if product_filter.attribute_tags:
            query = query.where(
                ProductRecord.attribute_tags.contains(product_filter.attribute_tags)
            )
        if product_filter.search:
            like = f"%{product_filter.search.lower()}%"
            query = query.where(func.lower(ProductRecord.name).like(like))

        count_result = await self._session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        if product_filter.sort is ProductSort.PRICE_ASC:
            query = query.order_by(ProductRecord.price_cents.asc())
        elif product_filter.sort is ProductSort.PRICE_DESC:
            query = query.order_by(ProductRecord.price_cents.desc())
        elif product_filter.sort is ProductSort.NAME_ASC:
            query = query.order_by(ProductRecord.name.asc())
        else:
            query = query.order_by(ProductRecord.created_at.desc())

        query = query.limit(product_filter.limit).offset(product_filter.offset)
        result = await self._session.execute(query)
        products = [_to_domain_product(record) for record in result.scalars().all()]
        return products, total

    async def get_by_slug(self, slug: str) -> Product | None:
        result = await self._session.execute(
            select(ProductRecord).where(ProductRecord.slug == slug)
        )
        record = result.scalar_one_or_none()
        return None if record is None else _to_domain_product(record)

    async def get_by_id(self, product_id: UUID) -> Product | None:
        record = await self._session.get(ProductRecord, product_id)
        return None if record is None else _to_domain_product(record)

    async def list_distinct_facets(self, category_id: UUID) -> ProductFacets:
        result = await self._session.execute(
            select(
                ProductRecord.brand, ProductRecord.price_cents, ProductRecord.attribute_tags
            ).where(ProductRecord.category_id == category_id, ProductRecord.is_active.is_(True))
        )
        rows = result.all()

        brands: set[str] = set()
        tag_groups: dict[str, set[str]] = {}
        prices: list[int] = []
        for brand, price_cents, attribute_tags in rows:
            brands.add(brand)
            prices.append(price_cents)
            for tag in attribute_tags:
                prefix, _, value = tag.partition(":")
                if not value:
                    continue
                tag_groups.setdefault(prefix, set()).add(value)

        return ProductFacets(
            brands=sorted(brands),
            attribute_tag_groups={
                prefix: sorted(values) for prefix, values in sorted(tag_groups.items())
            },
            price_min_cents=min(prices) if prices else 0,
            price_max_cents=max(prices) if prices else 0,
        )


class SqlAlchemyBuildRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, build: Build) -> None:
        self._session.add(BuildRecord(id=build.id, slug=build.slug, name=build.name))
        for item in build.items:
            self._session.add(
                BuildItemRecord(
                    id=item.id,
                    build_id=build.id,
                    product_id=item.product.id,
                    quantity=item.quantity,
                )
            )
        await self._session.flush()

    async def slug_exists(self, slug: str) -> bool:
        result = await self._session.execute(select(BuildRecord.id).where(BuildRecord.slug == slug))
        return result.scalar_one_or_none() is not None

    async def get_by_slug(self, slug: str) -> Build | None:
        build_result = await self._session.execute(
            select(BuildRecord).where(BuildRecord.slug == slug)
        )
        build_record = build_result.scalar_one_or_none()
        if build_record is None:
            return None

        items_result = await self._session.execute(
            select(BuildItemRecord, ProductRecord)
            .join(ProductRecord, BuildItemRecord.product_id == ProductRecord.id)
            .where(BuildItemRecord.build_id == build_record.id)
        )
        items = [
            BuildItem(
                id=item_record.id,
                build_id=item_record.build_id,
                product=_to_domain_product(product_record),
                quantity=item_record.quantity,
            )
            for item_record, product_record in items_result.all()
        ]

        return Build(
            id=build_record.id,
            slug=build_record.slug,
            name=build_record.name,
            created_at=build_record.created_at,
            items=items,
        )
