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
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    user_group: Optional[str] = None
    owner_admin_user_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_admin_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None


class LoginRequest(BaseModel):
    email: EmailStr
    name: str = ""


class AuthUser(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    is_active: bool


class LoginResponse(BaseModel):
    user: AuthUser


class DigestPaper(BaseModel):
    id: int
    canonical_key: str
    digest_date: str
    doi: str
    journal: str
    publish_date: str
    publish_date_day: str
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


class PaperLibraryGroupSummary(BaseModel):
    publish_date: str
    paper_count: int


class PaperLibraryGroup(BaseModel):
    publish_date: str
    paper_count: int
    items: list[DigestPaper]


class PaperLibraryOverview(BaseModel):
    total_papers: int
    available_publish_dates: list[str]
    available_categories: list[str]
    available_tags: list[str]
    groups: list[PaperLibraryGroupSummary]
    loaded_groups: list[PaperLibraryGroup]
    sort: str


class FavoriteCreate(BaseModel):
    paper_id: int
    user_id: Optional[int] = None


class FavoriteRead(BaseModel):
    id: int
    user_id: int
    paper_id: int
    canonical_key: str
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
    canonical_key: str
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
    digest_date: str
    source_run_id: str
    source_updated_at_utc: str
    result_status: str
    imported_items: int
    imported_memberships: int
    skipped_missing_key_count: int
    duplicate_membership_count: int
    conflict_count: int
    validation_status: str
    summary: dict[str, Any]


class ImportRunRead(BaseModel):
    digest_date: str
    run_id: str
    updated_at_utc: str
    status: str
    email_status: str
    work_dir: str
    validation_status: str
    validation_payload: dict[str, Any]
    record_count: int
    is_current: bool
    current_local_run_id: str
    current_local_updated_at_utc: str
