from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from lib_blog.models.blog import (
    BlogPostSummary,
    BlogPostDetail,
    BlogPostCreateRequest,
    BlogPostUpdateRequest,
    BlogSitemapUrl,
    TagModel,
)
from lib_utils.sql import sql
import re


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')


def _get_tags_for_post(conn, post_id: int) -> List[TagModel]:
    tags_data = sql(
        conn,
        """
        SELECT t.id, t.name, t.slug
        FROM blog_tags t
        JOIN blog_post_tags pt ON pt.tag_id = t.id
        WHERE pt.post_id = :post_id
        """,
        {"post_id": post_id}
    ).dicts()
    return [TagModel(**t) for t in tags_data] if tags_data else []


def _attach_tags(conn, post_id: int, tag_ids: List[int]):
    # Remove existing tags
    sql(conn, "DELETE FROM blog_post_tags WHERE post_id = :post_id", {"post_id": post_id}).run()
    # Insert new tags
    for tag_id in tag_ids:
        sql(conn, None, None).insert_one("blog_post_tags", {
            "post_id": post_id,
            "tag_id": tag_id,
        })


# ============= Post Functions =============

def get_all_posts(conn, status_filter: Optional[str] = None, page: int = 1, page_size: int = 10) -> Tuple[List[BlogPostSummary], int]:
    try:
        offset = (page - 1) * page_size
        where = "WHERE status = :status" if status_filter else ""
        params = {"limit": page_size, "offset": offset}
        if status_filter:
            params["status"] = status_filter

        count_data = sql(
            conn,
            f"SELECT COUNT(*) as total FROM blog_posts {where}",
            params
        ).dict()
        total = count_data["total"] if count_data else 0

        posts_data = sql(
            conn,
            f"""
            SELECT id, title, slug, excerpt, cover_image, status,
                   author_name, reading_time, published_at, created_at
            FROM blog_posts
            {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """,
            params
        ).dicts()

        posts = []
        for p in (posts_data or []):
            tags = _get_tags_for_post(conn, p["id"])
            posts.append(BlogPostSummary(**dict(p), tags=tags))
        return posts, total

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching posts"
        )


def get_post_by_slug(conn, slug: str) -> BlogPostDetail:
    try:
        post_data = sql(
            conn,
            "SELECT * FROM blog_posts WHERE slug = :slug",
            {"slug": slug}
        ).dict()

        if not post_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found"
            )

        tags = _get_tags_for_post(conn, post_data["id"])
        return BlogPostDetail(**post_data, tags=tags)

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching post"
        )


def create_post(conn, data: BlogPostCreateRequest) -> dict:
    try:
        # Check slug uniqueness
        existing = sql(
            conn,
            "SELECT id FROM blog_posts WHERE slug = :slug",
            {"slug": data.slug}
        ).dict()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A post with this slug already exists"
            )

        published_at = None
        if data.status == "published":
            from datetime import datetime
            published_at = datetime.utcnow()

        post_data = {
            "title": data.title,
            "slug": data.slug,
            "excerpt": data.excerpt,
            "content": data.content,
            "cover_image": data.cover_image,
            "status": data.status,
            "meta_title": data.meta_title,
            "meta_description": data.meta_description,
            "author_name": data.author_name,
            "reading_time": data.reading_time,
            "published_at": published_at,
        }

        sql(conn, None, None).insert_one("blog_posts", post_data)

        new_post = sql(
            conn,
            "SELECT id FROM blog_posts WHERE slug = :slug",
            {"slug": data.slug}
        ).dict()
        post_id = new_post["id"]

        if data.tag_ids:
            _attach_tags(conn, post_id, data.tag_ids)

        conn.commit()
        return {"post_id": post_id, "slug": data.slug}

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating post"
        )


def update_post(conn, post_id: int, data: BlogPostUpdateRequest) -> None:
    try:
        existing = sql(
            conn,
            "SELECT id, status FROM blog_posts WHERE id = :id",
            {"id": post_id}
        ).dict()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found"
            )

        update_data = data.model_dump(exclude_none=True, exclude={"tag_ids"})

        # Set published_at if being published for first time
        if update_data.get("status") == "published" and existing["status"] == "draft":
            from datetime import datetime
            update_data["published_at"] = datetime.utcnow()

        if update_data:
            sql(conn, None, None).update_one(
                "blog_posts",
                update_data,
                {"id": post_id}
            )

        if data.tag_ids is not None:
            _attach_tags(conn, post_id, data.tag_ids)

        conn.commit()

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while updating post"
        )


def delete_post(conn, post_id: int) -> None:
    try:
        existing = sql(
            conn,
            "SELECT id FROM blog_posts WHERE id = :id",
            {"id": post_id}
        ).dict()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found"
            )
        sql(conn, "DELETE FROM blog_posts WHERE id = :id", {"id": post_id}).run()
        conn.commit()

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while deleting post"
        )


# ============= Tag Functions =============

def get_all_tags(conn) -> List[TagModel]:
    try:
        tags_data = sql(
            conn,
            "SELECT id, name, slug FROM blog_tags ORDER BY name ASC"
        ).dicts()
        return [TagModel(**t) for t in tags_data] if tags_data else []
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching tags"
        )


def create_tag(conn, name: str, slug: str) -> int:
    try:
        existing = sql(
            conn,
            "SELECT id FROM blog_tags WHERE slug = :slug",
            {"slug": slug}
        ).dict()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag with this slug already exists"
            )
        sql(conn, None, None).insert_one("blog_tags", {"name": name, "slug": slug})
        new_tag = sql(conn, "SELECT id FROM blog_tags WHERE slug = :slug", {"slug": slug}).dict()
        conn.commit()
        return new_tag["id"]
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating tag"
        )

def get_sitemap_urls(conn) -> List[BlogSitemapUrl]:
    try:
        posts_data = sql(
            conn,
            """
            SELECT slug, published_at
            FROM blog_posts
            WHERE status = 'published'
            ORDER BY published_at DESC
            """,
        ).dicts()

        return [
            BlogSitemapUrl(
                slug=p["slug"],
                published_at=p["published_at"],
            )
            for p in (posts_data or [])
        ]

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching sitemap URLs"
        )