from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_admin_service, require_admin
from site_api.domain.account_notes import AccountNote
from site_api.domain.users import (
    AccountStatus,
    AuthenticatedUser,
    CannotModifySelfError,
    User,
    UserNotFoundError,
    UserRole,
)
from site_api.services.admin import AddAccountNote, AdminService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class AdminUserSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    email_address: str
    full_name: str
    role: UserRole
    status: AccountStatus
    created_at: datetime
    last_login_at: datetime | None


class UpdateRoleRequest(BaseModel):
    role: UserRole


class UpdateStatusRequest(BaseModel):
    status: AccountStatus


class NoteCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class NoteResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    author_name: str
    body: str
    created_at: datetime


def _to_summary(user: User) -> AdminUserSummary:
    return AdminUserSummary(
        id=user.id,
        email_address=user.email_address,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _to_note_response(note: AccountNote) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        author_name=note.author_name,
        body=note.body,
        created_at=note.created_at,
    )


@router.get(
    "/users",
    response_model=list[AdminUserSummary],
    response_model_by_alias=True,
)
async def list_users(
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> list[AdminUserSummary]:
    users = await service.list_users()
    return [_to_summary(user) for user in users]


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserSummary,
    response_model_by_alias=True,
)
async def update_user_role(
    user_id: UUID,
    payload: UpdateRoleRequest,
    service: Annotated[AdminService, Depends(get_admin_service)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> AdminUserSummary:
    try:
        user = await service.update_role(user_id, payload.role, current_user.id)
    except CannotModifySelfError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        ) from error
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from error

    return _to_summary(user)


@router.patch(
    "/users/{user_id}/status",
    response_model=AdminUserSummary,
    response_model_by_alias=True,
)
async def update_user_status(
    user_id: UUID,
    payload: UpdateStatusRequest,
    service: Annotated[AdminService, Depends(get_admin_service)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> AdminUserSummary:
    try:
        user = await service.update_status(user_id, payload.status, current_user.id)
    except CannotModifySelfError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own account status",
        ) from error
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from error

    return _to_summary(user)


@router.get(
    "/users/{user_id}/notes",
    response_model=list[NoteResponse],
    response_model_by_alias=True,
)
async def list_notes(
    user_id: UUID,
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> list[NoteResponse]:
    try:
        notes = await service.list_notes(user_id)
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from error

    return [_to_note_response(note) for note in notes]


@router.post(
    "/users/{user_id}/notes",
    response_model=NoteResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def add_note(
    user_id: UUID,
    payload: NoteCreateRequest,
    service: Annotated[AdminService, Depends(get_admin_service)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> NoteResponse:
    try:
        note = await service.add_note(
            AddAccountNote(
                user_id=user_id,
                author_id=current_user.id,
                author_name=current_user.full_name,
                body=payload.body,
            )
        )
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from error

    return _to_note_response(note)
