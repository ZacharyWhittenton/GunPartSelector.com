from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_build_service
from site_api.api.routes.catalog import ProductSummary, to_product_summary
from site_api.domain.builds import Build, BuildNotFoundError, EmptyBuildError
from site_api.domain.catalog import ProductNotFoundError
from site_api.services.builds import BuildService, CreateBuild, CreateBuildItem

router = APIRouter(prefix="/builds", tags=["builds"])


class CreateBuildItemRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    product_id: UUID
    quantity: int = Field(ge=1, le=20)


class CreateBuildRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str | None = Field(default=None, max_length=120)
    items: list[CreateBuildItemRequest] = Field(min_length=1, max_length=50)


class BuildItemResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    product: ProductSummary
    quantity: int


class BuildResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    slug: str
    name: str | None
    created_at: datetime
    items: list[BuildItemResponse]


def to_build_response(build: Build) -> BuildResponse:
    return BuildResponse(
        slug=build.slug,
        name=build.name,
        created_at=build.created_at,
        items=[
            BuildItemResponse(product=to_product_summary(item.product), quantity=item.quantity)
            for item in build.items
        ],
    )


@router.post(
    "",
    response_model=BuildResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_build(
    payload: CreateBuildRequest,
    service: Annotated[BuildService, Depends(get_build_service)],
) -> BuildResponse:
    try:
        build = await service.create_build(
            CreateBuild(
                name=payload.name,
                items=[
                    CreateBuildItem(product_id=item.product_id, quantity=item.quantity)
                    for item in payload.items
                ],
            )
        )
    except EmptyBuildError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A build needs at least one part"
        ) from error
    except ProductNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One of the parts in this build no longer exists",
        ) from error

    return to_build_response(build)


@router.get("/{slug}", response_model=BuildResponse, response_model_by_alias=True)
async def get_build(
    slug: str,
    service: Annotated[BuildService, Depends(get_build_service)],
) -> BuildResponse:
    try:
        build = await service.get_build_by_slug(slug)
    except BuildNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Build not found"
        ) from error

    return to_build_response(build)
