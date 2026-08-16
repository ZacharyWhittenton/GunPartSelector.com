from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_contact_request_service
from site_api.services.contact_requests import (
    ContactRequestService,
    SubmitContactRequest,
)

router = APIRouter(prefix="/contact-requests", tags=["contact requests"])


class ContactRequestCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(min_length=1, max_length=200)
    email_address: EmailStr
    company: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    service: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)


class ContactRequestAccepted(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    status: str


@router.post(
    "",
    response_model=ContactRequestAccepted,
    response_model_by_alias=True,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_contact_request(
    payload: ContactRequestCreate,
    service: Annotated[ContactRequestService, Depends(get_contact_request_service)],
) -> ContactRequestAccepted:
    contact_request = await service.submit(
        SubmitContactRequest(
            name=payload.name,
            email_address=str(payload.email_address),
            company=payload.company,
            phone=payload.phone,
            service=payload.service,
            message=payload.message,
        )
    )
    return ContactRequestAccepted(id=contact_request.id, status=contact_request.status.value)
