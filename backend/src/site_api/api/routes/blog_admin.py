from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import (
    get_blog_service,
    get_file_storage,
    require_admin,
)
from site_api.api.routes.blog import (
    BlogPostDetail,
    BlogPostSummary,
    to_detail,
    to_summary,
)
from site_api.core.storage import LocalFileStorage
from site_api.domain.blog import PostNotFoundError
from site_api.domain.storage import FileTooLargeError, UnsupportedFileTypeError
from site_api.domain.users import AuthenticatedUser
from site_api.services.blog import BlogService, CreatePost, UpdatePost

router = APIRouter(prefix="/admin/blog", tags=["admin blog"], dependencies=[Depends(require_admin)])


class PostWriteRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str = Field(min_length=1, max_length=200)
    excerpt: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    cover_image_url: str | None = None


class ImageUploadResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    url: str


@router.get("/posts", response_model=list[BlogPostSummary], response_model_by_alias=True)
async def list_all_posts(
    service: Annotated[BlogService, Depends(get_blog_service)],
) -> list[BlogPostSummary]:
    posts = await service.list_posts_for_admin()
    return [to_summary(post) for post in posts]


@router.post(
    "/posts",
    response_model=BlogPostDetail,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    payload: PostWriteRequest,
    service: Annotated[BlogService, Depends(get_blog_service)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> BlogPostDetail:
    post = await service.create_post(
        CreatePost(
            title=payload.title,
            excerpt=payload.excerpt,
            body=payload.body,
            tags=tuple(payload.tags),
            cover_image_url=payload.cover_image_url,
            author_id=current_user.id,
            author_name=current_user.full_name,
        )
    )
    return to_detail(post)


@router.patch(
    "/posts/{post_id}",
    response_model=BlogPostDetail,
    response_model_by_alias=True,
)
async def update_post(
    post_id: UUID,
    payload: PostWriteRequest,
    service: Annotated[BlogService, Depends(get_blog_service)],
) -> BlogPostDetail:
    try:
        post = await service.update_post(
            post_id,
            UpdatePost(
                title=payload.title,
                excerpt=payload.excerpt,
                body=payload.body,
                tags=tuple(payload.tags),
                cover_image_url=payload.cover_image_url,
            ),
        )
    except PostNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        ) from error

    return to_detail(post)


@router.post(
    "/posts/{post_id}/publish",
    response_model=BlogPostDetail,
    response_model_by_alias=True,
)
async def publish_post(
    post_id: UUID,
    service: Annotated[BlogService, Depends(get_blog_service)],
) -> BlogPostDetail:
    try:
        post = await service.publish_post(post_id)
    except PostNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        ) from error

    return to_detail(post)


@router.post(
    "/posts/{post_id}/unpublish",
    response_model=BlogPostDetail,
    response_model_by_alias=True,
)
async def unpublish_post(
    post_id: UUID,
    service: Annotated[BlogService, Depends(get_blog_service)],
) -> BlogPostDetail:
    try:
        post = await service.unpublish_post(post_id)
    except PostNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        ) from error

    return to_detail(post)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    service: Annotated[BlogService, Depends(get_blog_service)],
) -> None:
    try:
        await service.delete_post(post_id)
    except PostNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        ) from error


@router.post(
    "/images",
    response_model=ImageUploadResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    file: Annotated[UploadFile, File()],
    storage: Annotated[LocalFileStorage, Depends(get_file_storage)],
) -> ImageUploadResponse:
    content = await file.read()

    try:
        url = await storage.save_image(content, file.content_type or "")
    except UnsupportedFileTypeError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, WebP, and GIF images are supported",
        ) from error
    except FileTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Image must be 5MB or smaller",
        ) from error

    return ImageUploadResponse(url=url)
