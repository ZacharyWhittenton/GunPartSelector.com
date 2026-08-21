"""Bootstrap a local admin account.

There's no API path to create an admin (POST /api/auth/register always
creates a CUSTOMER) and no admin account is seeded anywhere else in this
repo -- seed_demo_data.py and seed_merch_data.py both expect one to already
exist and skip their admin-only steps otherwise. This creates it.

Local development only. Run from backend/ with:
    uv run python ../data/seeds/seed_admin_account.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "src"))

from site_api.core.config import Settings
from site_api.core.security import hash_password
from site_api.db.database import Database
from site_api.db.models import UserRecord
from site_api.db.repositories import SqlAlchemyUserRepository
from site_api.domain.users import UserRole
from site_api.services.auth import AuthService, RegisterUser

ADMIN_EMAIL = "admin@example.com"
ADMIN_NAME = "Admin Account"
ADMIN_PASSWORD = "AdminPass123!"


async def main() -> None:
    settings = Settings()
    database = Database(settings.database_url)

    async with database.session() as session:
        user_repository = SqlAlchemyUserRepository(session)
        auth_service = AuthService(user_repository)

        existing = await user_repository.get_by_email(ADMIN_EMAIL)
        if existing is not None:
            if existing.role is not UserRole.ADMIN:
                await user_repository.update_role(existing.id, UserRole.ADMIN)
                print(f"Promoted {ADMIN_EMAIL} to admin.")
            # Reset the password to the known local-dev value regardless, so a
            # quick-login button using ADMIN_PASSWORD always works even if this
            # account's real password has since been changed. Local dev only.
            record = await session.get(UserRecord, existing.id)
            if record is not None:
                record.hashed_password = hash_password(ADMIN_PASSWORD)
            print(f"{ADMIN_EMAIL} ready ({ADMIN_EMAIL} / {ADMIN_PASSWORD}).")
        else:
            user = await auth_service.register(
                RegisterUser(
                    email_address=ADMIN_EMAIL, full_name=ADMIN_NAME, password=ADMIN_PASSWORD
                )
            )
            await user_repository.update_role(user.id, UserRole.ADMIN)
            print(f"Created admin account: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")

        await session.flush()

    await database.dispose()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
