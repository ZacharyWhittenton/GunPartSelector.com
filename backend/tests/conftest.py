from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from site_api.core.config import Settings
from site_api.domain.account_notes import AccountNote
from site_api.domain.analytics import ClickEvent, PageViewEvent, PageViewSummary
from site_api.domain.blog import (
    BlogPost,
    Comment,
    CommentNotFoundError,
    PostNotFoundError,
    TagSubscription,
)
from site_api.domain.contacts import (
    ContactRequest,
    ContactRequestNotFoundError,
    ContactRequestStatus,
)
from site_api.domain.discount_codes import DiscountCode, DiscountCodeNotFoundError
from site_api.domain.lead_notes import LeadNote
from site_api.domain.marketplace import (
    ItemNotFoundError,
    MarketplaceItem,
    Order,
    OrderItem,
    OrderStatus,
    WishlistItem,
)
from site_api.domain.scheduling import Appointment, AppointmentStatus, SlotNotFoundError
from site_api.domain.testimonials import Testimonial, TestimonialNotFoundError, TestimonialStatus
from site_api.domain.users import AccountStatus, User, UserNotFoundError, UserRole
from site_api.main import create_app
from site_api.services.admin import AdminService
from site_api.services.analytics import AnalyticsService
from site_api.services.auth import AuthService
from site_api.services.blog import BlogService
from site_api.services.chat import ChatService
from site_api.services.contact_requests import ContactRequestService
from site_api.services.dashboard import DashboardService
from site_api.services.discount_codes import DiscountCodeService
from site_api.services.email import EmailService
from site_api.services.marketplace import MarketplaceService
from site_api.services.scheduling import SchedulingService
from site_api.services.testimonials import TestimonialService


class InMemoryContactRequestRepository:
    def __init__(self) -> None:
        self.contact_requests: list[ContactRequest] = []

    async def add(self, contact_request: ContactRequest) -> ContactRequest:
        self.contact_requests.append(contact_request)
        return contact_request

    async def update(self, contact_request: ContactRequest) -> ContactRequest:
        for index, existing in enumerate(self.contact_requests):
            if existing.id == contact_request.id:
                self.contact_requests[index] = contact_request
                return contact_request
        raise ContactRequestNotFoundError

    async def get_by_id(self, contact_request_id: UUID) -> ContactRequest | None:
        for contact_request in self.contact_requests:
            if contact_request.id == contact_request_id:
                return contact_request
        return None

    async def list_all(self, status: ContactRequestStatus | None = None) -> list[ContactRequest]:
        results = self.contact_requests
        if status is not None:
            results = [request for request in results if request.status is status]
        return sorted(results, key=lambda request: request.created_at, reverse=True)


class InMemoryLeadNoteRepository:
    def __init__(self) -> None:
        self.notes: list[LeadNote] = []

    async def add(self, note: LeadNote) -> LeadNote:
        self.notes.append(note)
        return note

    async def list_for_lead(self, lead_id: UUID) -> list[LeadNote]:
        results = [note for note in self.notes if note.lead_id == lead_id]
        return sorted(results, key=lambda note: note.created_at, reverse=True)


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: list[User] = []

    async def add(self, user: User) -> User:
        self.users.append(user)
        return user

    async def get_by_email(self, email_address: str) -> User | None:
        for user in self.users:
            if user.email_address == email_address:
                return user
        return None

    async def get_by_id(self, user_id: UUID) -> User | None:
        for user in self.users:
            if user.id == user_id:
                return user
        return None

    async def list_all(self) -> list[User]:
        return list(self.users)

    async def update_role(self, user_id: UUID, role: UserRole) -> User:
        return self._replace(user_id, role=role)

    async def update_status(self, user_id: UUID, status: AccountStatus) -> User:
        return self._replace(user_id, status=status)

    async def update_last_login(self, user_id: UUID, when: datetime) -> None:
        self._replace(user_id, last_login_at=when)

    def _replace(self, user_id: UUID, **changes: object) -> User:
        for index, user in enumerate(self.users):
            if user.id == user_id:
                updated = replace(user, **changes)
                self.users[index] = updated
                return updated
        raise UserNotFoundError


class InMemoryAccountNoteRepository:
    def __init__(self) -> None:
        self.notes: list[AccountNote] = []

    async def add(self, note: AccountNote) -> AccountNote:
        self.notes.append(note)
        return note

    async def list_for_user(self, user_id: UUID) -> list[AccountNote]:
        return [note for note in self.notes if note.user_id == user_id]


class InMemoryBlogPostRepository:
    def __init__(self) -> None:
        self.posts: list[BlogPost] = []

    async def add(self, post: BlogPost) -> BlogPost:
        self.posts.append(post)
        return post

    async def update(self, post: BlogPost) -> BlogPost:
        for index, existing in enumerate(self.posts):
            if existing.id == post.id:
                self.posts[index] = post
                return post
        raise PostNotFoundError

    async def delete(self, post_id: UUID) -> None:
        for index, post in enumerate(self.posts):
            if post.id == post_id:
                del self.posts[index]
                return
        raise PostNotFoundError

    async def get_by_id(self, post_id: UUID) -> BlogPost | None:
        for post in self.posts:
            if post.id == post_id:
                return post
        return None

    async def get_by_slug(self, slug: str) -> BlogPost | None:
        for post in self.posts:
            if post.slug == slug:
                return post
        return None

    async def slug_exists(self, slug: str) -> bool:
        return any(post.slug == slug for post in self.posts)

    async def list_published(self, tag: str | None = None) -> list[BlogPost]:
        from site_api.domain.blog import PostStatus

        results = [post for post in self.posts if post.status is PostStatus.PUBLISHED]
        if tag is not None:
            results = [post for post in results if tag in post.tags]
        return sorted(results, key=lambda post: post.published_at or post.created_at, reverse=True)

    async def list_all(self) -> list[BlogPost]:
        return sorted(self.posts, key=lambda post: post.created_at, reverse=True)

    async def list_distinct_published_tags(self) -> list[str]:
        from site_api.domain.blog import PostStatus

        tags: set[str] = set()
        for post in self.posts:
            if post.status is PostStatus.PUBLISHED:
                tags.update(post.tags)
        return sorted(tags)


class InMemoryCommentRepository:
    def __init__(self) -> None:
        self.comments: list[Comment] = []

    async def add(self, comment: Comment) -> Comment:
        self.comments.append(comment)
        return comment

    async def get_by_id(self, comment_id: UUID) -> Comment | None:
        for comment in self.comments:
            if comment.id == comment_id:
                return comment
        return None

    async def list_for_post(self, post_id: UUID) -> list[Comment]:
        return [comment for comment in self.comments if comment.post_id == post_id]

    async def delete(self, comment_id: UUID) -> None:
        for index, comment in enumerate(self.comments):
            if comment.id == comment_id:
                del self.comments[index]
                return
        raise CommentNotFoundError


class InMemoryTagSubscriptionRepository:
    def __init__(self) -> None:
        self.subscriptions: list[TagSubscription] = []

    async def add(self, subscription: TagSubscription) -> TagSubscription:
        self.subscriptions.append(subscription)
        return subscription

    async def remove(self, user_id: UUID, tag_name: str) -> None:
        self.subscriptions = [
            sub
            for sub in self.subscriptions
            if not (sub.user_id == user_id and sub.tag_name == tag_name)
        ]

    async def get(self, user_id: UUID, tag_name: str) -> TagSubscription | None:
        for sub in self.subscriptions:
            if sub.user_id == user_id and sub.tag_name == tag_name:
                return sub
        return None

    async def list_for_user(self, user_id: UUID) -> list[TagSubscription]:
        return [sub for sub in self.subscriptions if sub.user_id == user_id]


class InMemoryAppointmentRepository:
    def __init__(self) -> None:
        self.appointments: list[Appointment] = []

    async def add(self, appointment: Appointment) -> Appointment:
        self.appointments.append(appointment)
        return appointment

    async def update(self, appointment: Appointment) -> Appointment:
        for index, existing in enumerate(self.appointments):
            if existing.id == appointment.id:
                self.appointments[index] = appointment
                return appointment
        raise SlotNotFoundError

    async def delete(self, appointment_id: UUID) -> None:
        for index, appointment in enumerate(self.appointments):
            if appointment.id == appointment_id:
                del self.appointments[index]
                return
        raise SlotNotFoundError

    async def get_by_id(self, appointment_id: UUID) -> Appointment | None:
        for appointment in self.appointments:
            if appointment.id == appointment_id:
                return appointment
        return None

    async def list_open_upcoming(self, now: datetime) -> list[Appointment]:
        results = [
            appointment
            for appointment in self.appointments
            if appointment.status is AppointmentStatus.OPEN and appointment.starts_at >= now
        ]
        return sorted(results, key=lambda appointment: appointment.starts_at)

    async def list_for_client(self, client_id: UUID) -> list[Appointment]:
        results = [
            appointment for appointment in self.appointments if appointment.client_id == client_id
        ]
        return sorted(results, key=lambda appointment: appointment.starts_at, reverse=True)

    async def list_all(self, status: AppointmentStatus | None = None) -> list[Appointment]:
        results = self.appointments
        if status is not None:
            results = [appointment for appointment in results if appointment.status is status]
        return sorted(results, key=lambda appointment: appointment.starts_at, reverse=True)


class InMemoryMarketplaceItemRepository:
    def __init__(self) -> None:
        self.items: list[MarketplaceItem] = []

    async def add(self, item: MarketplaceItem) -> MarketplaceItem:
        self.items.append(item)
        return item

    async def update(self, item: MarketplaceItem) -> MarketplaceItem:
        for index, existing in enumerate(self.items):
            if existing.id == item.id:
                self.items[index] = item
                return item
        raise ItemNotFoundError

    async def delete(self, item_id: UUID) -> None:
        for index, item in enumerate(self.items):
            if item.id == item_id:
                del self.items[index]
                return
        raise ItemNotFoundError

    async def get_by_id(self, item_id: UUID) -> MarketplaceItem | None:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    async def get_by_slug(self, slug: str) -> MarketplaceItem | None:
        for item in self.items:
            if item.slug == slug:
                return item
        return None

    async def slug_exists(self, slug: str) -> bool:
        return any(item.slug == slug for item in self.items)

    async def list_active(self) -> list[MarketplaceItem]:
        return [item for item in self.items if item.is_active]

    async def list_all(self) -> list[MarketplaceItem]:
        return list(self.items)


class InMemoryOrderRepository:
    def __init__(self) -> None:
        self.orders: list[Order] = []
        self.order_items: list[OrderItem] = []

    async def add(self, order: Order, items: list[OrderItem]) -> Order:
        self.orders.append(order)
        self.order_items.extend(items)
        return order

    async def update_status(
        self,
        order_id: UUID,
        status: OrderStatus,
        stripe_payment_intent_id: str | None,
        customer_email: str | None,
    ) -> Order:
        for index, order in enumerate(self.orders):
            if order.id == order_id:
                updated = replace(
                    order,
                    status=status,
                    stripe_payment_intent_id=stripe_payment_intent_id
                    or order.stripe_payment_intent_id,
                    customer_email=customer_email or order.customer_email,
                )
                self.orders[index] = updated
                return updated
        raise ValueError("order not found")

    async def get_by_id(self, order_id: UUID) -> Order | None:
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    async def get_by_session_id(self, stripe_checkout_session_id: str) -> Order | None:
        for order in self.orders:
            if order.stripe_checkout_session_id == stripe_checkout_session_id:
                return order
        return None

    async def list_items_for_order(self, order_id: UUID) -> list[OrderItem]:
        return [item for item in self.order_items if item.order_id == order_id]

    async def list_for_customer(self, customer_id: UUID) -> list[Order]:
        results = [order for order in self.orders if order.customer_id == customer_id]
        return sorted(results, key=lambda order: order.created_at, reverse=True)

    async def list_all(self, status: OrderStatus | None = None) -> list[Order]:
        results = self.orders
        if status is not None:
            results = [order for order in results if order.status is status]
        return sorted(results, key=lambda order: order.created_at, reverse=True)

    async def count_orders_for_item(self, item_id: UUID) -> int:
        return sum(1 for item in self.order_items if item.marketplace_item_id == item_id)


class InMemoryWishlistRepository:
    def __init__(self) -> None:
        self.entries: list[WishlistItem] = []

    async def add(self, wishlist_item: WishlistItem) -> WishlistItem:
        self.entries.append(wishlist_item)
        return wishlist_item

    async def remove(self, user_id: UUID, marketplace_item_id: UUID) -> None:
        self.entries = [
            entry
            for entry in self.entries
            if not (entry.user_id == user_id and entry.marketplace_item_id == marketplace_item_id)
        ]

    async def get(self, user_id: UUID, marketplace_item_id: UUID) -> WishlistItem | None:
        for entry in self.entries:
            if entry.user_id == user_id and entry.marketplace_item_id == marketplace_item_id:
                return entry
        return None

    async def list_for_user(self, user_id: UUID) -> list[WishlistItem]:
        return [entry for entry in self.entries if entry.user_id == user_id]


class InMemoryTestimonialRepository:
    def __init__(self) -> None:
        self.testimonials: list[Testimonial] = []

    async def add(self, testimonial: Testimonial) -> Testimonial:
        self.testimonials.append(testimonial)
        return testimonial

    async def update(self, testimonial: Testimonial) -> Testimonial:
        for index, existing in enumerate(self.testimonials):
            if existing.id == testimonial.id:
                self.testimonials[index] = testimonial
                return testimonial
        raise TestimonialNotFoundError

    async def delete(self, testimonial_id: UUID) -> None:
        for index, testimonial in enumerate(self.testimonials):
            if testimonial.id == testimonial_id:
                del self.testimonials[index]
                return
        raise TestimonialNotFoundError

    async def get_by_id(self, testimonial_id: UUID) -> Testimonial | None:
        for testimonial in self.testimonials:
            if testimonial.id == testimonial_id:
                return testimonial
        return None

    async def get_by_customer_id(self, customer_id: UUID) -> Testimonial | None:
        for testimonial in self.testimonials:
            if testimonial.customer_id == customer_id:
                return testimonial
        return None

    async def list_approved(self, limit: int | None = None) -> list[Testimonial]:
        results = [
            testimonial
            for testimonial in self.testimonials
            if testimonial.status is TestimonialStatus.APPROVED
        ]
        results = sorted(results, key=lambda testimonial: testimonial.created_at, reverse=True)
        return results if limit is None else results[:limit]

    async def list_all(self, status: TestimonialStatus | None = None) -> list[Testimonial]:
        results = self.testimonials
        if status is not None:
            results = [testimonial for testimonial in results if testimonial.status is status]
        return sorted(results, key=lambda testimonial: testimonial.created_at, reverse=True)


class InMemoryDiscountCodeRepository:
    def __init__(self) -> None:
        self.discount_codes: list[DiscountCode] = []

    async def add(self, discount_code: DiscountCode) -> DiscountCode:
        self.discount_codes.append(discount_code)
        return discount_code

    async def update(self, discount_code: DiscountCode) -> DiscountCode:
        for index, existing in enumerate(self.discount_codes):
            if existing.id == discount_code.id:
                self.discount_codes[index] = discount_code
                return discount_code
        raise DiscountCodeNotFoundError

    async def delete(self, discount_code_id: UUID) -> None:
        for index, discount_code in enumerate(self.discount_codes):
            if discount_code.id == discount_code_id:
                del self.discount_codes[index]
                return
        raise DiscountCodeNotFoundError

    async def get_by_id(self, discount_code_id: UUID) -> DiscountCode | None:
        for discount_code in self.discount_codes:
            if discount_code.id == discount_code_id:
                return discount_code
        return None

    async def get_by_code(self, code: str) -> DiscountCode | None:
        for discount_code in self.discount_codes:
            if discount_code.code == code:
                return discount_code
        return None

    async def list_all(self) -> list[DiscountCode]:
        return sorted(self.discount_codes, key=lambda code: code.created_at, reverse=True)


class InMemoryAnalyticsRepository:
    def __init__(self) -> None:
        self.page_views: list[PageViewEvent] = []
        self.clicks: list[ClickEvent] = []

    async def record_page_view(self, event: PageViewEvent) -> PageViewEvent:
        self.page_views.append(event)
        return event

    async def record_click(self, event: ClickEvent) -> ClickEvent:
        self.clicks.append(event)
        return event

    async def top_pages(self, since: datetime, limit: int) -> list[PageViewSummary]:
        by_path: dict[str, list[PageViewEvent]] = {}
        for view in self.page_views:
            if view.created_at >= since:
                by_path.setdefault(view.path, []).append(view)

        summaries = [
            PageViewSummary(
                path=path,
                view_count=len(views),
                unique_sessions=len({view.session_id for view in views}),
            )
            for path, views in by_path.items()
        ]
        summaries.sort(key=lambda summary: summary.view_count, reverse=True)
        return summaries[:limit]

    async def click_points(self, path: str, since: datetime) -> list[ClickEvent]:
        return [click for click in self.clicks if click.path == path and click.created_at >= since]


class FakeStripeCheckoutSession:
    def __init__(self, session_id: str, url: str) -> None:
        self.id = session_id
        self.url = url


class FakeStripeCheckoutSessions:
    def __init__(self) -> None:
        self.created_params: list[dict] = []
        self.next_session_id = "cs_test_1"

    async def create_async(self, params: dict) -> FakeStripeCheckoutSession:
        self.created_params.append(params)
        session_id = self.next_session_id
        return FakeStripeCheckoutSession(
            session_id, f"https://checkout.stripe.com/pay/{session_id}"
        )


class FakeStripeCheckout:
    def __init__(self) -> None:
        self.sessions = FakeStripeCheckoutSessions()


class FakeStripeCoupon:
    def __init__(self, coupon_id: str) -> None:
        self.id = coupon_id


class FakeStripeCoupons:
    def __init__(self) -> None:
        self.created_params: list[dict] = []
        self.next_coupon_id = "coupon_test_1"

    async def create_async(self, params: dict) -> FakeStripeCoupon:
        self.created_params.append(params)
        return FakeStripeCoupon(self.next_coupon_id)


class FakeStripeV1:
    def __init__(self) -> None:
        self.checkout = FakeStripeCheckout()
        self.coupons = FakeStripeCoupons()


class FakeStripeClient:
    def __init__(self) -> None:
        self.v1 = FakeStripeV1()


class FakeSesClient:
    def __init__(self, should_raise: bool = False) -> None:
        self.sent: list[dict] = []
        self.should_raise = should_raise

    def send_email(self, **kwargs: object) -> dict:
        if self.should_raise:
            raise RuntimeError("SES failure")
        self.sent.append(kwargs)
        return {"MessageId": "fake-message-id"}


class FakeAnthropicTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class FakeAnthropicMessage:
    def __init__(self, text: str) -> None:
        self.content = [FakeAnthropicTextBlock(text)]


class FakeAnthropicMessages:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.last_kwargs: dict[str, object] | None = None

    async def create(self, **kwargs: object) -> FakeAnthropicMessage:
        self.last_kwargs = kwargs
        return FakeAnthropicMessage(self.reply)


class FakeAnthropicClient:
    def __init__(self, reply: str = "Hello! How can I help?") -> None:
        self.messages = FakeAnthropicMessages(reply)


class FakeFileStorage:
    def __init__(self) -> None:
        self.saved: list[tuple[bytes, str]] = []

    async def save_image(self, content: bytes, content_type: str) -> str:
        from site_api.domain.storage import (
            FileTooLargeError,
            UnsupportedFileTypeError,
        )

        if content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            raise UnsupportedFileTypeError
        if len(content) > 5 * 1024 * 1024:
            raise FileTooLargeError

        self.saved.append((content, content_type))
        return f"/api/uploads/blog/fake-{len(self.saved)}.jpg"


@pytest.fixture
def repository() -> InMemoryContactRequestRepository:
    return InMemoryContactRequestRepository()


@pytest.fixture
def fake_ses_client() -> FakeSesClient:
    return FakeSesClient()


@pytest.fixture
def email_service(fake_ses_client: FakeSesClient) -> EmailService:
    return EmailService(fake_ses_client, "sender@example.com", "admin@example.com")


@pytest.fixture
def lead_note_repository() -> InMemoryLeadNoteRepository:
    return InMemoryLeadNoteRepository()


@pytest.fixture
def contact_service(
    repository: InMemoryContactRequestRepository,
    lead_note_repository: InMemoryLeadNoteRepository,
    email_service: EmailService,
) -> ContactRequestService:
    return ContactRequestService(repository, lead_note_repository, email_service)


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def note_repository() -> InMemoryAccountNoteRepository:
    return InMemoryAccountNoteRepository()


@pytest.fixture
def auth_service(user_repository: InMemoryUserRepository) -> AuthService:
    return AuthService(user_repository)


@pytest.fixture
def admin_service(
    user_repository: InMemoryUserRepository,
    note_repository: InMemoryAccountNoteRepository,
) -> AdminService:
    return AdminService(user_repository, note_repository)


@pytest.fixture
def blog_post_repository() -> InMemoryBlogPostRepository:
    return InMemoryBlogPostRepository()


@pytest.fixture
def comment_repository() -> InMemoryCommentRepository:
    return InMemoryCommentRepository()


@pytest.fixture
def tag_subscription_repository() -> InMemoryTagSubscriptionRepository:
    return InMemoryTagSubscriptionRepository()


@pytest.fixture
def file_storage() -> FakeFileStorage:
    return FakeFileStorage()


@pytest.fixture
def appointment_repository() -> InMemoryAppointmentRepository:
    return InMemoryAppointmentRepository()


@pytest.fixture
def scheduling_service(
    appointment_repository: InMemoryAppointmentRepository,
    email_service: EmailService,
) -> SchedulingService:
    return SchedulingService(appointment_repository, email_service)


@pytest.fixture
def blog_service(
    blog_post_repository: InMemoryBlogPostRepository,
    comment_repository: InMemoryCommentRepository,
    tag_subscription_repository: InMemoryTagSubscriptionRepository,
) -> BlogService:
    return BlogService(blog_post_repository, comment_repository, tag_subscription_repository)


@pytest.fixture
def fake_anthropic_client() -> FakeAnthropicClient:
    return FakeAnthropicClient()


@pytest.fixture
def chat_service(
    fake_anthropic_client: FakeAnthropicClient,
    blog_post_repository: InMemoryBlogPostRepository,
    appointment_repository: InMemoryAppointmentRepository,
    user_repository: InMemoryUserRepository,
) -> ChatService:
    return ChatService(
        fake_anthropic_client,  # type: ignore[arg-type]
        blog_post_repository,
        appointment_repository,
        user_repository,
        "claude-opus-5",
    )


@pytest.fixture
def marketplace_item_repository() -> InMemoryMarketplaceItemRepository:
    return InMemoryMarketplaceItemRepository()


@pytest.fixture
def order_repository() -> InMemoryOrderRepository:
    return InMemoryOrderRepository()


@pytest.fixture
def wishlist_repository() -> InMemoryWishlistRepository:
    return InMemoryWishlistRepository()


@pytest.fixture
def fake_stripe_client() -> FakeStripeClient:
    return FakeStripeClient()


@pytest.fixture
def discount_code_repository() -> InMemoryDiscountCodeRepository:
    return InMemoryDiscountCodeRepository()


@pytest.fixture
def discount_code_service(
    discount_code_repository: InMemoryDiscountCodeRepository,
) -> DiscountCodeService:
    return DiscountCodeService(discount_code_repository)


@pytest.fixture
def analytics_repository() -> InMemoryAnalyticsRepository:
    return InMemoryAnalyticsRepository()


@pytest.fixture
def analytics_service(
    analytics_repository: InMemoryAnalyticsRepository,
) -> AnalyticsService:
    return AnalyticsService(analytics_repository)


@pytest.fixture
def marketplace_service(
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
    order_repository: InMemoryOrderRepository,
    wishlist_repository: InMemoryWishlistRepository,
    fake_stripe_client: FakeStripeClient,
    email_service: EmailService,
    discount_code_repository: InMemoryDiscountCodeRepository,
) -> MarketplaceService:
    return MarketplaceService(
        marketplace_item_repository,
        order_repository,
        wishlist_repository,
        fake_stripe_client,  # type: ignore[arg-type]
        "whsec_test_secret",
        "usd",
        "http://localhost:4200/marketplace/success?session_id={CHECKOUT_SESSION_ID}",
        "http://localhost:4200/cart",
        email_service,
        discount_code_repository,
    )


@pytest.fixture
def testimonial_repository() -> InMemoryTestimonialRepository:
    return InMemoryTestimonialRepository()


@pytest.fixture
def testimonial_service(
    testimonial_repository: InMemoryTestimonialRepository,
) -> TestimonialService:
    return TestimonialService(testimonial_repository)


@pytest.fixture
def dashboard_service(
    repository: InMemoryContactRequestRepository,
    appointment_repository: InMemoryAppointmentRepository,
    order_repository: InMemoryOrderRepository,
    testimonial_repository: InMemoryTestimonialRepository,
) -> DashboardService:
    return DashboardService(
        repository,
        appointment_repository,
        order_repository,
        testimonial_repository,
    )


@pytest.fixture
def app(
    contact_service: ContactRequestService,
    auth_service: AuthService,
    admin_service: AdminService,
    blog_service: BlogService,
    file_storage: FakeFileStorage,
    scheduling_service: SchedulingService,
    chat_service: ChatService,
    marketplace_service: MarketplaceService,
    testimonial_service: TestimonialService,
    dashboard_service: DashboardService,
    discount_code_service: DiscountCodeService,
    analytics_service: AnalyticsService,
) -> FastAPI:
    settings = Settings(environment="test", cors_origins=[], database_url=None)
    return create_app(
        settings,
        contact_service_provider=lambda: contact_service,
        auth_service_provider=lambda: auth_service,
        admin_service_provider=lambda: admin_service,
        blog_service_provider=lambda: blog_service,
        file_storage_provider=lambda: file_storage,
        scheduling_service_provider=lambda: scheduling_service,
        chat_service_provider=lambda: chat_service,
        marketplace_service_provider=lambda: marketplace_service,
        testimonial_service_provider=lambda: testimonial_service,
        dashboard_service_provider=lambda: dashboard_service,
        discount_code_service_provider=lambda: discount_code_service,
        analytics_service_provider=lambda: analytics_service,
    )


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
