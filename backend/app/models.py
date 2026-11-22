"""Pydantic request and response schemas matching ARCHITECTURE.md."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.config import DEFAULT_PREFERRED_CATEGORIES, DEFAULT_SCAN_INTERVAL_MINUTES

EducationLevel = Literal["lisans", "onlisans", "ortaogretim", "ilkogretim"]
UserAnnouncementStatus = Literal["none", "saved", "applied", "dismissed"]
MatchStatus = Literal["eligible", "review", "ineligible"]
ReasonStatus = Literal["pass", "warn", "fail", "unknown"]


class ProfileScores(BaseModel):
    P3: float | None = None
    P93: float | None = None
    P94: float | None = None
    P1: float | None = None
    P2: float | None = None
    P10: float | None = None
    P121: float | None = None
    EKPSS: float | None = None
    YDS: float | None = None


class UserProfile(BaseModel):
    is_configured: bool = False
    full_name: str = "Aday"
    kpss_year: int = 2026
    education_level: EducationLevel = "lisans"
    scores: ProfileScores = Field(default_factory=ProfileScores)
    departments: list[str] = Field(default_factory=list)
    qualification_codes: list[str] = Field(default_factory=list)
    birth_year: int | None = None
    gender: str = "belirtmek_istemiyorum"
    military_status: str = "muaf_veya_yapildi"
    driver_licenses: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    preferred_cities: list[str] = Field(default_factory=list)
    all_cities: bool = True
    preferred_categories: list[str] = Field(
        default_factory=lambda: list(DEFAULT_PREFERRED_CATEGORIES)
    )
    include_no_kpss: bool = True
    scan_interval_minutes: int = Field(default=DEFAULT_SCAN_INTERVAL_MINUTES, ge=5, le=1440)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    webhook_url: str = ""


class UserProfileUpdate(UserProfile):
    is_configured: bool = True


class ExtractedCriteria(BaseModel):
    kpss_types: list[str] = Field(default_factory=list)
    min_score: float | None = None
    requires_kpss: bool | None = None
    education_levels: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)
    accepts_any_department: bool = False
    qualification_codes: list[str] = Field(default_factory=list)
    max_age: int | None = None
    application_channel: str | None = None
    has_pdf: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class AnnouncementSource(BaseModel):
    source_name: str
    source_label: str
    url: str
    pdf_url: str | None = None
    scraped_at: str


class MatchReason(BaseModel):
    field: str
    label: str
    status: ReasonStatus
    message: str


class MatchResult(BaseModel):
    match_status: MatchStatus
    match_score: int
    headline: str
    reasons: list[MatchReason] = Field(default_factory=list)


class UserAnnouncementState(BaseModel):
    status: UserAnnouncementStatus = "none"
    notes: str = ""


class AnnouncementItem(BaseModel):
    id: int
    title: str
    institution: str
    category: str
    city: str | None = None
    cities: list[str] = Field(default_factory=list)
    publish_date: str | None = None
    deadline_date: str | None = None
    days_remaining: int | None = None
    quota_count: int | None = None
    summary: str = ""
    extracted: ExtractedCriteria
    sources: list[AnnouncementSource] = Field(default_factory=list)
    match: MatchResult
    user_state: UserAnnouncementState
    first_seen_at: str
    is_new: bool


class AnnouncementDetail(AnnouncementItem):
    raw_text: str = ""


class AnnouncementListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AnnouncementItem]


class UpdateStateRequest(BaseModel):
    status: UserAnnouncementStatus
    notes: str = ""


class UpdateStateResponse(BaseModel):
    id: int
    status: UserAnnouncementStatus
    notes: str = ""


class SourceStatus(BaseModel):
    source_name: str
    source_label: str
    url: str
    status: str
    items_found: int = 0
    items_new: int = 0
    last_run_at: str | None = None
    error_message: str | None = None


class StatsResponse(BaseModel):
    total_active: int
    eligible_count: int
    review_count: int
    ineligible_count: int
    deadline_soon_count: int
    new_today_count: int
    saved_count: int
    applied_count: int
    dismissed_count: int = 0
    is_scanning: bool
    last_scan_at: str | None = None
    categories: dict[str, int] = Field(default_factory=dict)
    sources: list[SourceStatus] = Field(default_factory=list)


class ScrapeTriggerRequest(BaseModel):
    source: str = "all"


class ScrapeTriggerResponse(BaseModel):
    started: bool
    message: str


class ScrapeStatusResponse(BaseModel):
    is_scanning: bool
    current_source: str | None = None
    last_scan_at: str | None = None
    runs: list[SourceStatus] = Field(default_factory=list)


class NitelikKoduItem(BaseModel):
    code: str
    level: str
    title: str
    departments: list[str] = Field(default_factory=list)


class CustomSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    url: str = Field(..., min_length=8, max_length=500)
    keywords: list[str] = Field(default_factory=list)


class CustomSourceItem(BaseModel):
    id: int
    name: str
    url: str
    keywords: list[str] = Field(default_factory=list)
    enabled: bool = True
    last_checked_at: str | None = None
    created_at: str


class NotificationTestResponse(BaseModel):
    sent: bool
    channel: str
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    db_ok: bool
    is_scanning: bool
    announcements_count: int


class InstitutionItem(BaseModel):
    name: str
    url: str
    city: str
    status: str = "idle"
    found: int = 0


class InstitutionGroup(BaseModel):
    group_key: str
    group_label: str
    source_name: str
    count: int
    items: list[InstitutionItem] = Field(default_factory=list)


class InstitutionsCatalogResponse(BaseModel):
    total: int
    groups: list[InstitutionGroup] = Field(default_factory=list)


class ManualImportTextRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    institution: str = Field(default="Kamu Kurumu", max_length=200)
    url: str = Field(default="", max_length=500)
    raw_text: str = Field(..., min_length=1)
    source_label: str = Field(default="Manuel İçe Aktarım", max_length=120)
