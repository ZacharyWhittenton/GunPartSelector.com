from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import (
    get_auth_service,
    get_current_user,
    get_settings,
)
from site_api.core.config import Settings
from site_api.core.security import create_access_token
from site_api.domain.users import (
    AccountSuspendedError,
    AuthenticatedUser,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    User,
    UserRole,
)
from site_api.services.auth import AuthenticateUser, AuthService, RegisterUser

router = APIRouter(prefix="/auth", tags=["auth"])

# Fixed seed accounts (see data/seeds/seed_admin_account.py and seed_demo_data.py) that
# the login page's dev-only "quick login" buttons sign in as. Deliberately not a
# password-based flow -- see the /dev-login route below for why.
DEV_LOGIN_ACCOUNTS: dict[UserRole, str] = {
    UserRole.ADMIN: "admin@example.com",
    UserRole.CUSTOMER: "morgan.rivera@example.com",
}


class RegisterRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    email_address: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    email_address: EmailStr
    password: str = Field(min_length=1, max_length=200)


class DevLoginRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    role: UserRole


class UserPublic(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    email_address: str
    full_name: str
    role: UserRole


class AuthResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    access_token: str
    token_type: str = "bearer"
    user: UserPublic


def _issue_token(user: User, settings: Settings) -> AuthResponse:
    access_token = create_access_token(
        user_id=str(user.id),
        email_address=user.email_address,
        full_name=user.full_name,
        role=user.role.value,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expires_minutes),
    )
    return AuthResponse(
        access_token=access_token,
        user=UserPublic(
            id=user.id,
            email_address=user.email_address,
            full_name=user.full_name,
            role=user.role,
        ),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    try:
        user = await service.register(
            RegisterUser(
                email_address=str(payload.email_address),
                full_name=payload.full_name,
                password=payload.password,
            )
        )
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists",
        ) from error

    return _issue_token(user, settings)


@router.post(
    "/login",
    response_model=AuthResponse,
    response_model_by_alias=True,
)
async def login(
    payload: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    try:
        user = await service.authenticate(
            AuthenticateUser(
                email_address=str(payload.email_address),
                password=payload.password,
            )
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email address or password",
        ) from error
    except AccountSuspendedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been suspended",
        ) from error

    return _issue_token(user, settings)


@router.post(
    "/dev-login",
    response_model=AuthResponse,
    response_model_by_alias=True,
)
async def dev_login(
    payload: DevLoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    # No password check by design -- this exists purely so the frontend's dev-only
    # quick-login buttons never need a real credential embedded in shipped JS (which
    # a build's isDevMode() check does NOT prevent -- it only gates whether the UI
    # renders, not whether literal strings survive into the bundle). The route
    # itself is the actual security boundary: it 404s outside local/test, same as if
    # it didn't exist.
    if settings.environment == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    email_address = DEV_LOGIN_ACCOUNTS.get(payload.role)
    if email_address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    user = await service.get_by_email(email_address)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{email_address} not seeded -- run the seed scripts in data/seeds/",
        )

    return _issue_token(user, settings)


@router.get(
    "/me",
    response_model=UserPublic,
    response_model_by_alias=True,
)
async def me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UserPublic:
    return UserPublic(
        id=current_user.id,
        email_address=current_user.email_address,
        full_name=current_user.full_name,
        role=current_user.role,
    )
