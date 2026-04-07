from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = "member"
    user_group: str = "internal"
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    user_group: Optional[str] = None
    owner_admin_user_id: Optional[int] = None
    is_active: Optional[bool] = None
    must_change_password: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_admin_user_id: Optional[int] = None
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class AuthUser(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    must_change_password: bool
    is_active: bool
    session_auth_method: str = "password"


class LoginResponse(BaseModel):
    user: AuthUser


class DigestPaper(BaseModel):
    id: int
    digest_date: str
    doi: str
    journal: str
    publish_date: str
    category: str
    interest_level: str
    interest_score: int
    interest_tag: str
    title_en: str
    title_zh: str
    summary_zh: str
    abstract: str
    article_url: str
    publication_stage: str
    tags: list[str]
    is_favorited: bool = False


class PaginatedPapers(BaseModel):
    items: list[DigestPaper]
    total: int
    page: int
    page_size: int


class FavoriteCreate(BaseModel):
    paper_id: int
    user_id: Optional[int] = None


class FavoriteRead(BaseModel):
    id: int
    user_id: int
    paper_id: int
    digest_date: Optional[str] = None
    doi: str
    journal: str
    publish_date: str
    category: str
    interest_level: str
    interest_tag: str
    title_en: str
    title_zh: str
    article_url: str
    favorited_at: datetime
    review_interest_level: str = ""
    review_interest_tag: str = ""
    review_final_decision: str = ""
    review_final_category: str = ""
    reviewer_notes: str = ""
    review_updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FavoriteReviewUpdate(BaseModel):
    review_interest_level: str = ""
    review_interest_tag: str = ""
    review_final_decision: str = ""
    review_final_category: str = ""
    reviewer_notes: str = ""


class FavoriteReviewOptions(BaseModel):
    interest_levels: list[str]
    interest_tags: list[str]
    review_final_decisions: list[str]
    review_final_categories: list[str]


class PaperPushCreate(BaseModel):
    paper_id: int
    recipient_user_id: int
    note: str = ""


class PaperPushRead(BaseModel):
    id: int
    paper_id: int
    recipient_user_id: int
    sent_by_user_id: int
    note: str
    is_read: bool
    pushed_at: datetime
    read_at: Optional[datetime] = None
    title_en: str
    title_zh: str
    journal: str
    publish_date: str
    article_url: str
    sender_name: str
    recipient_name: str


class PaperPushUpdate(BaseModel):
    is_read: bool


class AnalyticsNodeRead(BaseModel):
    key: str
    label: str
    weight: int


class AnalyticsEdgeRead(BaseModel):
    source: str
    target: str
    weight: int


class TrendPoint(BaseModel):
    label: str
    value: int
    journal: Optional[str] = None


class AnalyticsResponse(BaseModel):
    scope_type: str
    period: str
    month: str
    total_papers: int
    nodes: list[AnalyticsNodeRead]
    edges: list[AnalyticsEdgeRead]
    series: list[TrendPoint]
    summary: dict[str, Any]


class ExportColumnMapping(BaseModel):
    source: str
    label: str


class ExportRequest(BaseModel):
    date: Optional[str] = None
    user_id: Optional[int] = None
    columns: list[ExportColumnMapping] = Field(default_factory=list)


class ExportJobRead(BaseModel):
    id: int
    kind: str
    status: str
    output_name: str
    content_type: str
    created_at: datetime
    finished_at: Optional[datetime] = None
    download_url: str

    model_config = ConfigDict(from_attributes=True)


class ImportResult(BaseModel):
    digest_run_id: int
    digest_date: str
    imported_papers: int
