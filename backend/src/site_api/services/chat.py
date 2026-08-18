from collections.abc import Callable
from datetime import UTC, datetime

from anthropic import AsyncAnthropic

from site_api.db.repositories import SqlAlchemyBlogPostRepository, SqlAlchemyUserRepository
from site_api.domain.blog import PostStatus
from site_api.domain.chat import ChatNotConfiguredError, ChatTurn
from site_api.domain.users import AuthenticatedUser, UserRole

MAX_RESPONSE_TOKENS = 1024

SITE_MAP = """
Pages available on the site:
- Home (/) — interactive 3D AR-15 build configurator
- Parts catalog (/parts) — browse parts by category, each category at /parts/:categorySlug
  and each product at /parts/:categorySlug/:productSlug
- Store (/merch) — apparel and merch, each item at /merch/:slug
- About (/about) — what GunPartSelector.com is and how it works
- Support (/services) — help topics
- Guides (/resources) — build guides and articles
- Blog (/blog) — blog posts, each at /blog/:slug
- Contact (/contact) — contact form
- Cart (/cart) and checkout
- Login (/login) and Register (/register) — account access
- Admin dashboard (/admin) and admin sections for the parts catalog, blog, and store
  orders — admin-only
""".strip()

BASE_INSTRUCTIONS = """
You are the site assistant for GunPartSelector.com, an AR-15 build configurator and
parts catalog. Visitors browse parts by category, add them to a build with live
compatibility checks, and can share their build with a link. GunPartSelector.com is
an affiliate site: "Add to Build" and product links send the visitor to a retailer to
complete the purchase — GunPartSelector.com does not hold inventory or ship parts.
Answer questions about the business and help visitors find their way around the site.
Be concise and friendly. Only state facts you were given in this prompt or the
conversation — if you don't know something, say so and point the person to the
Contact page rather than guessing. Never give legal advice about firearm regulations;
point those questions to the Contact page or a qualified professional instead.
""".strip()


class ChatService:
    def __init__(
        self,
        client: AsyncAnthropic | None,
        blog_repository: SqlAlchemyBlogPostRepository,
        user_repository: SqlAlchemyUserRepository,
        model: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._client = client
        self._blog_repository = blog_repository
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
            sections.append(self._visitor_context())
        elif current_user.role is UserRole.ADMIN:
            sections.append(await self._admin_context(current_user))
        else:
            sections.append(self._customer_context(current_user))

        if page_context:
            sections.append(f"The person is currently viewing: {page_context}")

        return "\n\n".join(sections)

    def _visitor_context(self) -> str:
        return (
            "You are speaking with a visitor who has not registered or logged in. "
            "Registering (/register) or logging in (/login) lets them save a build "
            "and view their order history, but browsing the catalog and using the "
            "builder does not require an account."
        )

    def _customer_context(self, current_user: AuthenticatedUser) -> str:
        return f"You are speaking with a logged-in customer named {current_user.full_name}."

    async def _admin_context(self, current_user: AuthenticatedUser) -> str:
        users = await self._user_repository.list_all()
        all_posts = await self._blog_repository.list_all()
        draft_count = sum(1 for p in all_posts if p.status is PostStatus.DRAFT)
        return (
            f"You are speaking with an admin named {current_user.full_name}. They can "
            "manage the parts catalog and store at /admin, blog posts at /admin/blog, "
            "and store orders at /admin/marketplace/orders.\n"
            f"Current stats: {len(users)} registered account(s), {draft_count} draft "
            "blog post(s)."
        )
