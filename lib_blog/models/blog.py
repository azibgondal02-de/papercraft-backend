from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


# ============= Tag Models =============

class TagModel(BaseModel):
    id: int
    name: str
    slug: str


class TagCreateRequest(BaseModel):
    name: str
    slug: str


# ============= Blog Post Models =============

class BlogPostSummary(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    cover_image: Optional[str] = None
    status: str
    author_name: str
    reading_time: int
    published_at: Optional[datetime] = None
    created_at: datetime
    tags: List[TagModel] = []


class BlogPostDetail(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    cover_image: Optional[str] = None
    status: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    author_name: str
    reading_time: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    tags: List[TagModel] = []


class BlogPostCreateRequest(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    cover_image: Optional[str] = None
    status: str = "draft"
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    author_name: str = "PaperCraft Team"
    reading_time: int = 0
    tag_ids: List[int] = []


class BlogPostUpdateRequest(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    cover_image: Optional[str] = None
    status: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    author_name: Optional[str] = None
    reading_time: Optional[int] = None
    tag_ids: Optional[List[int]] = None


# ============= Response Models =============

class BlogPostsResponse(BaseModel):
    message: str
    posts: List[BlogPostSummary]
    total_count: int


class BlogPostDetailResponse(BaseModel):
    message: str
    post: BlogPostDetail


class BlogPostCreateResponse(BaseModel):
    message: str
    post_id: int
    slug: str


class TagsResponse(BaseModel):
    message: str
    tags: List[TagModel]


class TagCreateResponse(BaseModel):
    message: str
    tag_id: int


class BlogSitemapUrl(BaseModel):
    slug: str
    published_at: Optional[datetime] = None