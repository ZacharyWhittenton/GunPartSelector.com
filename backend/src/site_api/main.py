from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import boto3
import stripe
from anthropic import AsyncAnthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from site_api.api.dependencies import (
    get_admin_service,
    get_analytics_service,
    get_auth_service,
    get_blog_service,
    get_build_service,
    get_catalog_service,
    get_chat_service,
    get_contact_request_service,
    get_dashboard_service,
    get_discount_code_service,
    get_email_service,
    get_file_storage,
    get_marketplace_service,
    get_scheduling_service,
    get_testimonial_service,
)
from site_api.api.routes import (
    admin,
    analytics,
    analytics_admin,
    auth,
    blog,
    blog_admin,
    builds,
    catalog,
    chat,
    contact_requests,
    contact_requests_admin,
    dashboard_admin,
    discount_codes_admin,
    health,
    marketplace,
    marketplace_admin,
    scheduling,
    scheduling_admin,
    testimonials,
    testimonials_admin,
)
from site_api.core.config import Settings
from site_api.core.logging import configure_logging
from site_api.db.database import Database
from site_api.domain.storage import FileStorage
from site_api.services.admin import AdminService
from site_api.services.analytics import AnalyticsService
from site_api.services.auth import AuthService
from site_api.services.blog import BlogService
from site_api.services.builds import BuildService
from site_api.services.catalog import CatalogService
from site_api.services.chat import ChatService
from site_api.services.contact_requests import ContactRequestService
from site_api.services.dashboard import DashboardService
from site_api.services.discount_codes import DiscountCodeService
from site_api.services.email import EmailService
from site_api.services.marketplace import MarketplaceService
from site_api.services.scheduling import SchedulingService
from site_api.services.testimonials import TestimonialService

ContactServiceProvider = Callable[[], ContactRequestService]
AuthServiceProvider = Callable[[], AuthService]
AdminServiceProvider = Callable[[], AdminService]
BlogServiceProvider = Callable[[], BlogService]
FileStorageProvider = Callable[[], FileStorage]
SchedulingServiceProvider = Callable[[], SchedulingService]
ChatServiceProvider = Callable[[], ChatService]
MarketplaceServiceProvider = Callable[[], MarketplaceService]
TestimonialServiceProvider = Callable[[], TestimonialService]
EmailServiceProvider = Callable[[], EmailService]
DashboardServiceProvider = Callable[[], DashboardService]
DiscountCodeServiceProvider = Callable[[], DiscountCodeService]
AnalyticsServiceProvider = Callable[[], AnalyticsService]
CatalogServiceProvider = Callable[[], CatalogService]
BuildServiceProvider = Callable[[], BuildService]


def create_app(
    settings: Settings | None = None,
    contact_service_provider: ContactServiceProvider | None = None,
    auth_service_provider: AuthServiceProvider | None = None,
    admin_service_provider: AdminServiceProvider | None = None,
    blog_service_provider: BlogServiceProvider | None = None,
    file_storage_provider: FileStorageProvider | None = None,
    scheduling_service_provider: SchedulingServiceProvider | None = None,
    chat_service_provider: ChatServiceProvider | None = None,
    marketplace_service_provider: MarketplaceServiceProvider | None = None,
    testimonial_service_provider: TestimonialServiceProvider | None = None,
    email_service_provider: EmailServiceProvider | None = None,
    dashboard_service_provider: DashboardServiceProvider | None = None,
    discount_code_service_provider: DiscountCodeServiceProvider | None = None,
    analytics_service_provider: AnalyticsServiceProvider | None = None,
    catalog_service_provider: CatalogServiceProvider | None = None,
    build_service_provider: BuildServiceProvider | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    configure_logging(resolved_settings.log_level)
    database = Database(resolved_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await database.dispose()

    application = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.database = database
    application.state.settings = resolved_settings
    application.state.anthropic_client = (
        AsyncAnthropic(api_key=resolved_settings.anthropic_api_key)
        if resolved_settings.anthropic_api_key
        else None
    )
    application.state.stripe_client = (
        stripe.StripeClient(api_key=resolved_settings.stripe_secret_key)
        if resolved_settings.stripe_secret_key
        else None
    )
    application.state.ses_client = (
        boto3.client("ses", region_name=resolved_settings.aws_ses_region)
        if resolved_settings.email_sender_address
        else None
    )

    if resolved_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )

    application.mount(
        f"{resolved_settings.api_prefix}/uploads/blog",
        StaticFiles(directory=str(Path(resolved_settings.blog_uploads_dir)), check_dir=False),
        name="blog-uploads",
    )
    application.mount(
        f"{resolved_settings.api_prefix}/uploads/marketplace",
        StaticFiles(
            directory=str(Path(resolved_settings.marketplace_uploads_dir)), check_dir=False
        ),
        name="marketplace-uploads",
    )

    application.include_router(health.router, prefix=resolved_settings.api_prefix)
    application.include_router(contact_requests.router, prefix=resolved_settings.api_prefix)
    application.include_router(contact_requests_admin.router, prefix=resolved_settings.api_prefix)
    application.include_router(auth.router, prefix=resolved_settings.api_prefix)
    application.include_router(admin.router, prefix=resolved_settings.api_prefix)
    application.include_router(blog.router, prefix=resolved_settings.api_prefix)
    application.include_router(blog_admin.router, prefix=resolved_settings.api_prefix)
    application.include_router(scheduling.router, prefix=resolved_settings.api_prefix)
    application.include_router(scheduling_admin.router, prefix=resolved_settings.api_prefix)
    application.include_router(chat.router, prefix=resolved_settings.api_prefix)
    application.include_router(marketplace.router, prefix=resolved_settings.api_prefix)
    application.include_router(marketplace_admin.router, prefix=resolved_settings.api_prefix)
    application.include_router(testimonials.router, prefix=resolved_settings.api_prefix)
    application.include_router(testimonials_admin.router, prefix=resolved_settings.api_prefix)
    application.include_router(dashboard_admin.router, prefix=resolved_settings.api_prefix)
    application.include_router(discount_codes_admin.router, prefix=resolved_settings.api_prefix)
    application.include_router(analytics.router, prefix=resolved_settings.api_prefix)
    application.include_router(analytics_admin.router, prefix=resolved_settings.api_prefix)
    application.include_router(catalog.router, prefix=resolved_settings.api_prefix)
    application.include_router(builds.router, prefix=resolved_settings.api_prefix)

    if contact_service_provider is not None:
        application.dependency_overrides[get_contact_request_service] = contact_service_provider

    if auth_service_provider is not None:
        application.dependency_overrides[get_auth_service] = auth_service_provider

    if admin_service_provider is not None:
        application.dependency_overrides[get_admin_service] = admin_service_provider

    if blog_service_provider is not None:
        application.dependency_overrides[get_blog_service] = blog_service_provider

    if file_storage_provider is not None:
        application.dependency_overrides[get_file_storage] = file_storage_provider

    if scheduling_service_provider is not None:
        application.dependency_overrides[get_scheduling_service] = scheduling_service_provider

    if chat_service_provider is not None:
        application.dependency_overrides[get_chat_service] = chat_service_provider

    if marketplace_service_provider is not None:
        application.dependency_overrides[get_marketplace_service] = marketplace_service_provider

    if testimonial_service_provider is not None:
        application.dependency_overrides[get_testimonial_service] = testimonial_service_provider

    if email_service_provider is not None:
        application.dependency_overrides[get_email_service] = email_service_provider

    if dashboard_service_provider is not None:
        application.dependency_overrides[get_dashboard_service] = dashboard_service_provider

    if discount_code_service_provider is not None:
        application.dependency_overrides[get_discount_code_service] = discount_code_service_provider

    if analytics_service_provider is not None:
        application.dependency_overrides[get_analytics_service] = analytics_service_provider

    if catalog_service_provider is not None:
        application.dependency_overrides[get_catalog_service] = catalog_service_provider

    if build_service_provider is not None:
        application.dependency_overrides[get_build_service] = build_service_provider

    return application


app = create_app()
