from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_contact_request_service, require_admin
from site_api.domain.contacts import (
    ContactRequest,
    ContactRequestNotFoundError,
    ContactRequestStatus,
)
from site_api.domain.lead_notes import LeadNote
from site_api.domain.users import AuthenticatedUser
from site_api.services.contact_requests import AddLeadNote, ContactRequestService

router = APIRouter(
    prefix="/admin/contact-requests",
    tags=["admin contact requests"],
    dependencies=[Depends(require_admin)],
)


class LeadDetail(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    name: str
    email_address: str
    company: str | None
    phone: str | None
    service: str
    message: str
    status: ContactRequestStatus
    created_at: datetime
    updated_at: datetime
    follow_up_at: datetime | None


class UpdateStatusRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    status: ContactRequestStatus


class UpdateFollowUpRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    follow_up_at: datetime | None


class NoteCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class NoteResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    author_name: str
    body: str
    created_at: datetime


def _to_note_response(note: LeadNote) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        author_name=note.author_name,
        body=note.body,
        created_at=note.created_at,
    )


def to_lead_detail(contact_request: ContactRequest) -> LeadDetail:
    return LeadDetail(
        id=contact_request.id,
        name=contact_request.name,
        email_address=contact_request.email_address,
        company=contact_request.company,
        phone=contact_request.phone,
        service=contact_request.service,
        message=contact_request.message,
        status=contact_request.status,
        created_at=contact_request.created_at,
        updated_at=contact_request.updated_at,
        follow_up_at=contact_request.follow_up_at,
    )


@router.get("", response_model=list[LeadDetail], response_model_by_alias=True)
async def list_leads(
    service: Annotated[ContactRequestService, Depends(get_contact_request_service)],
    status_filter: Annotated[ContactRequestStatus | None, Query(alias="status")] = None,
) -> list[LeadDetail]:
    leads = await service.list_all(status_filter)
    return [to_lead_detail(lead) for lead in leads]


@router.patch(
    "/{contact_request_id}/status",
    response_model=LeadDetail,
    response_model_by_alias=True,
)
async def update_lead_status(
    contact_request_id: UUID,
    payload: UpdateStatusRequest,
    service: Annotated[ContactRequestService, Depends(get_contact_request_service)],
) -> LeadDetail:
    try:
        lead = await service.update_status(contact_request_id, payload.status)
    except ContactRequestNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        ) from error

    return to_lead_detail(lead)


@router.patch(
    "/{contact_request_id}/follow-up",
    response_model=LeadDetail,
    response_model_by_alias=True,
)
async def update_lead_follow_up(
    contact_request_id: UUID,
    payload: UpdateFollowUpRequest,
    service: Annotated[ContactRequestService, Depends(get_contact_request_service)],
) -> LeadDetail:
    try:
        lead = await service.set_follow_up(contact_request_id, payload.follow_up_at)
    except ContactRequestNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        ) from error

    return to_lead_detail(lead)


@router.get(
    "/{contact_request_id}/notes",
    response_model=list[NoteResponse],
    response_model_by_alias=True,
)
async def list_lead_notes(
    contact_request_id: UUID,
    service: Annotated[ContactRequestService, Depends(get_contact_request_service)],
) -> list[NoteResponse]:
    try:
        notes = await service.list_notes(contact_request_id)
    except ContactRequestNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        ) from error

    return [_to_note_response(note) for note in notes]


@router.post(
    "/{contact_request_id}/notes",
    response_model=NoteResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def add_lead_note(
    contact_request_id: UUID,
    payload: NoteCreateRequest,
    service: Annotated[ContactRequestService, Depends(get_contact_request_service)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> NoteResponse:
    try:
        note = await service.add_note(
            AddLeadNote(
                lead_id=contact_request_id,
                author_id=current_user.id,
                author_name=current_user.full_name,
                body=payload.body,
            )
        )
    except ContactRequestNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        ) from error

    return _to_note_response(note)
