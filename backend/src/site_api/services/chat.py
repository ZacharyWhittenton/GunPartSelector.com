from collections.abc import Callable
from datetime import UTC, datetime

from anthropic import AsyncAnthropic

from site_api.db.repositories import (
    SqlAlchemyAppointmentRepository,
    SqlAlchemyBlogPostRepository,
    SqlAlchemyUserRepository,
)
from site_api.domain.blog import PostStatus
from site_api.domain.chat import ChatNotConfiguredError, ChatTurn
from site_api.domain.scheduling import AppointmentStatus
from site_api.domain.users import AuthenticatedUser, UserRole

MAX_RESPONSE_TOKENS = 1024

SITE_MAP = """
Pages available on the site:
- Home (/) — overview and hero
- About (/about) — company story
- Services (/services) — service listings, each with a detail page at /services/:slug
- Gallery (/gallery) — portfolio/project examples
- Resources (/resources) — articles and guides
- Blog (/blog) — blog posts, each at /blog/:slug
- Contact (/contact) — contact form for project inquiries
- Schedule (/schedule) — book a meeting time
- Login (/login) and Register (/register) — account access
- Admin dashboard (/admin), Admin blog (/admin/blog), Admin schedule (/admin/schedule) — admin-only
""".strip()

BASE_INSTRUCTIONS = """
You are the site assistant for WD Web Solutions, a web design and development agency.
Answer questions about the business and help visitors find their way around the site.
Be concise and friendly. Only state facts you were given in this prompt or the
conversation — if you don't know something, say so and point the person to the
Contact page rather than guessing.
""".strip()


class ChatService:
    def __init__(
        self,
        client: AsyncAnthropic | None,
        blog_repository: SqlAlchemyBlogPostRepository,
        appointment_repository: SqlAlchemyAppointmentRepository,
        user_repository: SqlAlchemyUserRepository,
        model: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._client = client
        self._blog_repository = blog_repository
        self._appointment_repository = appointment_repository
        self._user_repository = user_repository
        self._model = model
        self._clock = clock

    async def send_message(
        self,
        turns: list[ChatTurn],
        current_user: AuthenticatedUser | None,
        page_context: str | None,
    ) -> str:
        if self._client is None:
            raise ChatNotConfiguredError

        system_prompt = await self._build_system_prompt(current_user, page_context)

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=MAX_RESPONSE_TOKENS,
            system=system_prompt,
            messages=[{"role": turn.role, "content": turn.content} for turn in turns],
        )

        return "".join(block.text for block in response.content if block.type == "text")

    async def _build_system_prompt(
        self,
        current_user: AuthenticatedUser | None,
        page_context: str | None,
    ) -> str:
        sections = [BASE_INSTRUCTIONS, SITE_MAP]

        posts = await self._blog_repository.list_published()
        if posts:
            titles = "\n".join(f"- {post.title} (/blog/{post.slug})" for post in posts[:8])
            sections.append(f"Recently published blog posts:\n{titles}")

        if current_user is None:
            sections.append(await self._visitor_context())
        elif current_user.role is UserRole.ADMIN:
            sections.append(await self._admin_context(current_user))
        else:
            sections.append(await self._customer_context(current_user))

        if page_context:
            sections.append(f"The person is currently viewing: {page_context}")

        return "\n\n".join(sections)

    async def _visitor_context(self) -> str:
        open_slots = await self._appointment_repository.list_open_upcoming(self._clock())
        availability = (
            f"There are currently {len(open_slots)} open meeting time(s) at /schedule."
            if open_slots
            else "There are no open meeting times right now — check back soon."
        )
        return (
            "You are speaking with a visitor who has not registered or logged in.\n"
            "They must register (/register) or log in (/login) before they can book a "
            f"meeting on the Schedule page.\n{availability}"
        )

    async def _customer_context(self, current_user: AuthenticatedUser) -> str:
        open_slots = await self._appointment_repository.list_open_upcoming(self._clock())
        my_appointments = await self._appointment_repository.list_for_client(current_user.id)
        upcoming = [
            appointment
            for appointment in my_appointments
            if appointment.status is AppointmentStatus.BOOKED
        ]
        upcoming_text = (
            "\n".join(f"- {a.starts_at.isoformat()} UTC" for a in upcoming[:5])
            if upcoming
            else "none"
        )
        return (
            f"You are speaking with a logged-in client named {current_user.full_name}.\n"
            f"There are {len(open_slots)} open meeting time(s) at /schedule.\n"
            f"Their upcoming booked appointments (UTC):\n{upcoming_text}"
        )

    async def _admin_context(self, current_user: AuthenticatedUser) -> str:
        users = await self._user_repository.list_all()
        all_appointments = await self._appointment_repository.list_all(status=None)
        open_count = sum(
            1 for a in all_appointments if a.status is AppointmentStatus.OPEN
        )
        booked_count = sum(
            1 for a in all_appointments if a.status is AppointmentStatus.BOOKED
        )
        all_posts = await self._blog_repository.list_all()
        draft_count = sum(1 for p in all_posts if p.status is PostStatus.DRAFT)
        return (
            f"You are speaking with an admin named {current_user.full_name}. They can "
            "manage accounts at /admin, blog posts at /admin/blog, and scheduling at "
            "/admin/schedule.\n"
            f"Current stats: {len(users)} registered account(s), {open_count} open "
            f"meeting slot(s), {booked_count} booked appointment(s), {draft_count} "
            "draft blog post(s)."
        )
