from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_chat_service, get_optional_current_user
from site_api.domain.chat import ChatNotConfiguredError, ChatTurn
from site_api.domain.users import AuthenticatedUser
from site_api.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatTurnRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    messages: list[ChatTurnRequest] = Field(min_length=1, max_length=40)
    page_context: str | None = Field(default=None, max_length=200)


class ChatResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    message: str


@router.post(
    "/messages",
    response_model=ChatResponse,
    response_model_by_alias=True,
)
async def send_message(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    current_user: Annotated[AuthenticatedUser | None, Depends(get_optional_current_user)],
) -> ChatResponse:
    try:
        reply = await service.send_message(
            turns=[ChatTurn(role=turn.role, content=turn.content) for turn in payload.messages],
            current_user=current_user,
            page_context=payload.page_context,
        )
    except ChatNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The assistant is not configured yet.",
        ) from error

    return ChatResponse(message=reply)
