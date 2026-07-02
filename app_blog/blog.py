from fastapi import APIRouter, Request, Query, Depends
from fastapi.security import HTTPBearer
from lib_blog.blog import (
    get_all_posts,
    get_post_by_slug,
    create_post,
    update_post,
    delete_post,
    get_all_tags,
    create_tag,
)
from lib_blog.models.blog import (
    BlogPostsResponse,
    BlogPostDetailResponse,
    BlogPostCreateRequest,
    BlogPostCreateResponse,
    BlogPostUpdateRequest,
    TagsResponse,
    TagCreateRequest,
    TagCreateResponse,
)
from lib_identity.identity import require_auth
from web import get_context, get_context_with_user_info
from typing import Optional

router = APIRouter(prefix="/blog", tags=["Blog"])
bearer_scheme = HTTPBearer(auto_error=False)


# ============= Public Endpoints (no auth) =============

@router.get("/posts", summary="Get all published blog posts")
def fetch_blog_posts(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
) -> BlogPostsResponse:
    context = get_context(request)
    posts, total = get_all_posts(
        conn=context.conn,
        status_filter="published",
        page=page,
        page_size=page_size
    )
    return BlogPostsResponse(
        message="Posts fetched successfully",
        posts=posts,
        total_count=total
    )


@router.get("/posts/{slug}", summary="Get single blog post by slug")
def fetch_blog_post(slug: str, request: Request) -> BlogPostDetailResponse:
    context = get_context(request)
    post = get_post_by_slug(conn=context.conn, slug=slug)
    return BlogPostDetailResponse(message="Post fetched successfully", post=post)


@router.get("/tags", summary="Get all tags")
def fetch_tags(request: Request) -> TagsResponse:
    context = get_context(request)
    tags = get_all_tags(conn=context.conn)
    return TagsResponse(message="Tags fetched successfully", tags=tags)


# ============= Admin Endpoints (auth required) =============

@router.get("/admin/posts", dependencies=[Depends(bearer_scheme)], summary="Get all posts including drafts")
@require_auth
def fetch_all_posts_admin(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    status: Optional[str] = Query(default=None),
) -> BlogPostsResponse:
    context, _, _ = get_context_with_user_info(request)
    posts, total = get_all_posts(
        conn=context.conn,
        status_filter=status,
        page=page,
        page_size=page_size
    )
    return BlogPostsResponse(
        message="Posts fetched successfully",
        posts=posts,
        total_count=total
    )


@router.post("/admin/posts", dependencies=[Depends(bearer_scheme)], summary="Create a new blog post")
@require_auth
def create_blog_post(
    data: BlogPostCreateRequest,
    request: Request,
) -> BlogPostCreateResponse:
    context, _, _ = get_context_with_user_info(request)
    result = create_post(conn=context.conn, data=data)
    return BlogPostCreateResponse(
        message="Post created successfully",
        post_id=result["post_id"],
        slug=result["slug"]
    )


@router.put("/admin/posts/{post_id}", dependencies=[Depends(bearer_scheme)], summary="Update a blog post")
@require_auth
def update_blog_post(
    post_id: int,
    data: BlogPostUpdateRequest,
    request: Request,
):
    context, _, _ = get_context_with_user_info(request)
    update_post(conn=context.conn, post_id=post_id, data=data)
    return {"message": "Post updated successfully"}


@router.delete("/admin/posts/{post_id}", dependencies=[Depends(bearer_scheme)], summary="Delete a blog post")
@require_auth
def delete_blog_post(post_id: int, request: Request):
    context, _, _ = get_context_with_user_info(request)
    delete_post(conn=context.conn, post_id=post_id)
    return {"message": "Post deleted successfully"}


@router.post("/admin/tags", dependencies=[Depends(bearer_scheme)], summary="Create a new tag")
@require_auth
def create_blog_tag(data: TagCreateRequest, request: Request) -> TagCreateResponse:
    context, _, _ = get_context_with_user_info(request)
    tag_id = create_tag(conn=context.conn, name=data.name, slug=data.slug)
    return TagCreateResponse(message="Tag created successfully", tag_id=tag_id)