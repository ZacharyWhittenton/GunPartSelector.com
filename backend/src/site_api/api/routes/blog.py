from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import (
    get_blog_service,
    get_current_user,
    get_optional_current_user,
)
from site_api.domain.blog import (
    BlogPost,
    Comment,
    CommentNotFoundError,
    NotCommentAuthorError,
    PostNotFoundError,
    PostStatus,
)
from site_api.domain.users import AuthenticatedUser, UserRole
from site_api.services.blog import AddComment, BlogService

router = APIRouter(prefix="/blog", tags=["blog"])


class BlogPostSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    title: str
    slug: str
    excerpt: str
    cover_image_url: str | None
    tags: list[str]
    author_name: str
    status: PostStatus
    published_at: datetime | None
    created_at: datetime


class BlogPostDetail(BlogPostSummary):
    body: str
    updated_at: datetime


class CommentCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class CommentResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    author_id: UUID
    author_name: str
    body: str
    created_at: datetime


def to_summary(post: BlogPost) -> BlogPostSummary:
    return BlogPostSummary(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        cover_image_url=post.cover_image_url,
        tags=list(post.tags),
        author_name=post.author_name,
        status=post.status,
        published_at=post.published_at,
        created_at=post.created_at,
    )


def to_detail(post: BlogPost) -> BlogPostDetail:
    return BlogPostDetail(
        **to_summary(post).model_dump(),
        body=post.body,
        updated_at=post.updated_at,
    )


def to_comment(comment: Comment) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        author_id=comment.author_id,
        author_name=comment.author_name,
        body=comment.body,
        created_at=comment.created_at,
    )


@router.get("/posts", response_model=list[BlogPostSummary], response_model_by_alias=True)
async def list_posts(
    service: Annotated[BlogService, Depends(get_blog_service)],
    tag: Annotated[str | None, Query()] = None,
) -> list[BlogPostSummary]:
    posts = await service.list_published_posts(tag)
    return [to_summary(post) for post in posts]


@router.get(
    "/posts/{slug}",
    response_model=BlogPostDetail,
    response_model_by_alias=True,
)
async def get_post(
    slug: str,
    service: Annotated[BlogService, Depends(get_blog_service)],
    current_user: Annotated[AuthenticatedUser | None, Depends(get_optional_current_user)],
) -> BlogPostDetail:
    try:
        post = await service.get_post_for_viewer(slug, current_user.role if current_user else None)
    except PostNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        ) from error

    return to_detail(post)


@router.get(
    "/posts/{slug}/comments",
    response_model=list[CommentResponse],
    response_model_by_alias=True,
)
async def list_comments(
    slug: str,
    service: Annotated[BlogService, Depends(get_blog_service)],
    current_user: Annotated[AuthenticatedUser | None, Depends(get_optional_current_user)],
) -> list[CommentResponse]:
    try:
        post = await service.get_post_for_viewer(slug, current_user.role if current_user else None)
        comments = await service.list_comments(post.id, current_user.role if current_user else None)
    except PostNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        ) from error

    return [to_comment(comment) for comment in comments]


@router.post(
    "/posts/{slug}/comments",
    response_model=CommentResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    slug: str,
    payload: CommentCreateRequest,
    service: Annotated[BlogService, Depends(get_blog_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CommentResponse:
    try:
        post = await service.get_post_for_viewer(slug, current_user.role)
        comment = await service.add_comment(
            AddComment(
                post_id=post.id,
                author_id=current_user.id,
                author_name=current_user.full_name,
                body=payload.body,
            )
        )
    except PostNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        ) from error

    return to_comment(comment)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    comment_id: UUID,
    service: Annotated[BlogService, Depends(get_blog_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> None:
    try:
        await service.delete_comment(
            comment_id, current_user.id, current_user.role is UserRole.ADMIN
        )
    except CommentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        ) from error
    except NotCommentAuthorError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments",
        ) from error


@router.get("/tags", response_model=list[str])
async def list_tags(
    service: Annotated[BlogService, Depends(get_blog_service)],
) -> list[str]:
    return await service.list_tags()


@router.get("/subscriptions", response_model=list[str])
async def list_subscriptions(
    service: Annotated[BlogService, Depends(get_blog_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[str]:
    subscriptions = await service.list_subscriptions(current_user.id)
    return [subscription.tag_name for subscription in subscriptions]


@router.post("/tags/{tag_name}/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe_to_tag(
    tag_name: str,
    service: Annotated[BlogService, Depends(get_blog_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> None:
    await service.subscribe_to_tag(current_user.id, tag_name)


@router.delete("/tags/{tag_name}/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_from_tag(
    tag_name: str,
    service: Annotated[BlogService, Depends(get_blog_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> None:
    await service.unsubscribe_from_tag(current_user.id, tag_name)
