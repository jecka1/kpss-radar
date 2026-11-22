"""FastAPI application entrypoint and REST API endpoints for KPSS Radar."""

from __future__ import annotations

import asyncio
import hashlib
import re
import sqlite3
import unicodedata
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app import database
from app.config import (
    CORS_ORIGINS,
    DEADLINE_SOON_DAYS,
    FRONTEND_DIST_DIR,
    NEW_ANNOUNCEMENT_HOURS,
)
from app.models import (
    AnnouncementDetail,
    AnnouncementItem,
    AnnouncementListResponse,
    CustomSourceCreate,
    CustomSourceItem,
    ExtractedCriteria,
    HealthResponse,
    InstitutionsCatalogResponse,
    ManualImportTextRequest,
    NitelikKoduItem,
    NotificationTestResponse,
    ScrapeStatusResponse,
    ScrapeTriggerRequest,
    ScrapeTriggerResponse,
    StatsResponse,
    UpdateStateRequest,
    UpdateStateResponse,
    UserProfile,
    UserProfileUpdate,
)
from app.nitelik_kodlari import search_nitelik_kodlari
from app.scheduler import scheduler


def _normalize_tr(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ğ": "g",
        "ğ": "g",
        "Ü": "u",
        "ü": "u",
        "Ş": "s",
        "ş": "s",
        "Ö": "o",
        "ö": "o",
        "Ç": "c",
        "ç": "c",
    }
    out = "".join(replacements.get(ch, ch) for ch in text)
    out = unicodedata.normalize("NFKD", out)
    out = "".join(ch for ch in out if not unicodedata.combining(ch))
    return out.lower().strip()


def _compute_days_remaining(deadline_date: str | None) -> int | None:
    if not deadline_date:
        return None
    try:
        dl = date.fromisoformat(deadline_date[:10])
        return (dl - date.today()).days
    except ValueError:
        return None


def _compute_is_new(publish_date: str | None, first_seen_at: str) -> bool:
    if publish_date:
        try:
            pub_date = date.fromisoformat(publish_date[:10])
            delta_days = (date.today() - pub_date).days
            return 0 <= delta_days <= 3
        except ValueError:
            pass
    if not first_seen_at:
        return False
    try:
        dt = datetime.fromisoformat(first_seen_at)
        age = datetime.now() - dt
        return 0 <= age.total_seconds() <= 24 * 3600
    except ValueError:
        return first_seen_at[:10] == date.today().isoformat()


def _build_announcement_payload(ann: dict, profile: dict, include_raw: bool = False) -> dict:
    from app.engine.matcher import evaluate_match

    raw_ext = ann.get("extracted") or {}
    extracted = ExtractedCriteria(
        kpss_types=list(raw_ext.get("kpss_types") or []),
        min_score=raw_ext.get("min_score"),
        requires_kpss=raw_ext.get("requires_kpss"),
        education_levels=list(raw_ext.get("education_levels") or []),
        departments=list(raw_ext.get("departments") or []),
        accepts_any_department=bool(raw_ext.get("accepts_any_department", False)),
        qualification_codes=list(raw_ext.get("qualification_codes") or []),
        max_age=raw_ext.get("max_age"),
        application_channel=raw_ext.get("application_channel"),
        has_pdf=bool(raw_ext.get("has_pdf", False)),
        missing_fields=list(raw_ext.get("missing_fields") or []),
        confidence=float(raw_ext.get("confidence") or 0.0),
    ).model_dump()

    cities = list(ann.get("cities") or raw_ext.get("cities") or [])
    if not cities and ann.get("city"):
        cities = [ann["city"]]

    days_remaining = _compute_days_remaining(ann.get("deadline_date"))
    is_new = _compute_is_new(ann.get("publish_date"), ann.get("first_seen_at", ""))
    match = evaluate_match(ann, profile)

    payload = {
        "id": ann["id"],
        "title": ann["title"],
        "institution": ann["institution"],
        "category": ann.get("category") or "diger",
        "city": ann.get("city") or (cities[0] if cities else None),
        "cities": cities,
        "publish_date": ann.get("publish_date"),
        "deadline_date": ann.get("deadline_date"),
        "days_remaining": days_remaining,
        "quota_count": ann.get("quota_count"),
        "summary": ann.get("summary") or raw_ext.get("summary") or "",
        "extracted": extracted,
        "sources": ann.get("sources") or [],
        "match": match,
        "user_state": ann.get("user_state") or {"status": "none", "notes": ""},
        "first_seen_at": ann.get("first_seen_at") or "",
        "is_new": is_new,
    }
    if include_raw:
        payload["raw_text"] = ann.get("raw_text") or ""
    return payload


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.init_db()
    await scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


app = FastAPI(
    title="KPSS Radar API",
    description="KPSS ve Türkiye Kamu Personel Alım İlanları Takip & Sıfır-Kaçırma Eşleştirme API'si",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    db_ok = True
    count = 0
    try:
        count = database.count_announcements()
    except Exception:
        db_ok = False
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db_ok=db_ok,
        is_scanning=scheduler.is_scanning,
        announcements_count=count,
    )


@app.get("/api/profile", response_model=UserProfile)
def get_profile() -> UserProfile:
    return UserProfile(**database.get_profile())


@app.put("/api/profile", response_model=UserProfile)
def update_profile(payload: UserProfileUpdate) -> UserProfile:
    saved = database.save_profile(payload.model_dump())
    return UserProfile(**saved)


@app.get("/api/announcements", response_model=AnnouncementListResponse)
def list_announcements(
    match_status: str = Query(default="all"),
    category: str = Query(default="all"),
    source: str = Query(default="all"),
    city: str = Query(default="all"),
    user_status: str = Query(default="active"),
    deadline_soon: bool = Query(default=False),
    include_expired: bool = Query(default=False),
    q: str = Query(default=""),
    sort: str = Query(default="match_score"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=200),
) -> AnnouncementListResponse:
    profile = database.get_profile()
    raw_rows = database.list_announcements()
    norm_q = _normalize_tr(q)
    norm_city_filter = _normalize_tr(city) if city and city != "all" else ""

    filtered: list[dict] = []
    for row in raw_rows:
        item = _build_announcement_payload(row, profile, include_raw=False)
        u_status = item["user_state"]["status"]

        if user_status == "active":
            if u_status == "dismissed":
                continue
        elif user_status != "all" and u_status != user_status:
            continue

        days_rem = item["days_remaining"]
        if (
            not include_expired
            and user_status not in ("saved", "applied")
            and days_rem is not None
            and days_rem < 0
        ):
            continue

        m_status = item["match"]["match_status"]
        if match_status == "eligible_or_review":
            if m_status not in ("eligible", "review"):
                continue
        elif match_status != "all" and m_status != match_status:
            continue

        if category and category != "all" and item["category"] != category:
            continue

        if source and source != "all":
            source_names = {s.get("source_name", "") for s in item["sources"]}
            if source not in source_names:
                continue

        if norm_city_filter:
            item_cities = [_normalize_tr(c) for c in (item["cities"] or [])]
            if item["city"]:
                item_cities.append(_normalize_tr(item["city"]))
            if not any(
                norm_city_filter in c or "turkiye geneli" in c for c in item_cities
            ):
                continue

        if deadline_soon:
            days = item["days_remaining"]
            if days is None or days < 0 or days > DEADLINE_SOON_DAYS:
                continue

        if norm_q:
            searchable = _normalize_tr(
                " ".join(
                    [
                        item["title"],
                        item["institution"],
                        item["summary"],
                        item["city"] or "",
                        " ".join(item["cities"]),
                        " ".join(item["extracted"]["departments"]),
                        " ".join(item["extracted"]["qualification_codes"]),
                        row.get("raw_text", "")[:2000],
                    ]
                )
            )
            if norm_q not in searchable:
                continue

        filtered.append(item)

    if sort == "deadline":
        def _deadline_sort_key(x: dict) -> tuple:
            days = x["days_remaining"]
            if days is None:
                return (1, 99999, -x["match"]["match_score"], -x["id"])
            if days < 0:
                return (2, abs(days), -x["match"]["match_score"], -x["id"])
            return (0, days, -x["match"]["match_score"], -x["id"])

        filtered.sort(key=_deadline_sort_key)
    elif sort == "newest":
        filtered.sort(
            key=lambda x: (
                x.get("publish_date") or x.get("first_seen_at", "")[:10],
                x.get("first_seen_at", ""),
                x["id"],
            ),
            reverse=True,
        )
    else:  # match_score
        filtered.sort(
            key=lambda x: (
                -x["match"]["match_score"],
                0 if (x["days_remaining"] is None or x["days_remaining"] >= 0) else 1,
                x["days_remaining"] if x["days_remaining"] is not None else 99999,
                -x["id"],
            )
        )

    total = len(filtered)
    start_idx = (page - 1) * page_size
    page_items = filtered[start_idx : start_idx + page_size]

    return AnnouncementListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[AnnouncementItem(**i) for i in page_items],
    )


@app.get("/api/announcements/export/ics")
def export_ics_calendar() -> Response:
    profile = database.get_profile()
    raw_rows = database.list_announcements()
    events: list[str] = []
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for row in raw_rows:
        u_status = row["user_state"]["status"]
        if u_status == "dismissed":
            continue
        deadline_str = row.get("deadline_date")
        if not deadline_str:
            continue
        try:
            dl_date = date.fromisoformat(deadline_str[:10])
        except ValueError:
            continue
        if (dl_date - date.today()).days < 0:
            continue

        item = _build_announcement_payload(row, profile, include_raw=False)
        is_saved_or_applied = u_status in ("saved", "applied")
        is_eligible = item["match"]["match_status"] == "eligible"
        if not (is_saved_or_applied or is_eligible):
            continue

        dtstart = dl_date.strftime("%Y%m%d")
        dtend = (dl_date + timedelta(days=1)).strftime("%Y%m%d")
        summary_text = _ics_escape(f"[KPSS Radar] Son Başvuru: {item['institution']} - {item['title']}")
        urls = [s["url"] for s in item["sources"] if s.get("url")]
        desc_parts = [
            f"Kurum: {item['institution']}",
            f"Durum: {item['match']['headline']}",
        ]
        if item["extracted"].get("application_channel"):
            desc_parts.append(f"Başvuru Kanalı: {item['extracted']['application_channel']}")
        if urls:
            desc_parts.append(f"Bağlantı: {urls[0]}")
        description_text = _ics_escape("\n".join(desc_parts))

        lines = [
            "BEGIN:VEVENT",
            f"UID:kpss-radar-{item['id']}@kpssradar.local",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;VALUE=DATE:{dtstart}",
            f"DTEND;VALUE=DATE:{dtend}",
            f"SUMMARY:{summary_text}",
            f"DESCRIPTION:{description_text}",
        ]
        if urls:
            lines.append(f"URL:{urls[0]}")
        lines.append("END:VEVENT")
        events.append("\r\n".join(lines))

    calendar_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//KPSS Radar//Kamu Alim Takvimi//TR",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:KPSS Radar Başvuru Takvimi",
        *events,
        "END:VCALENDAR",
        "",
    ]
    ics_content = "\r\n".join(calendar_lines).encode("utf-8")
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="kpss-radar-takvim.ics"',
        },
    )


_INST_LINE_RE = re.compile(
    r"(?:BAKANLIĞI|ÜNİVERSİTESİ|BELEDİYESİ|BAŞKANLIĞI|GENEL\s+MÜDÜRLÜĞÜ|"
    r"VALİLİĞİ|MÜDÜRLÜĞÜ|KURUMU|REKTÖRLÜĞÜ|KOMUTANLIĞI|AJANSI)\b",
    re.IGNORECASE,
)
_TITLE_LINE_RE = re.compile(
    r"(?:ALIM\s+İLANI|ALINACAKTIR|PERSONEL|MEMUR|SÖZLEŞMELİ|İŞÇİ|SINAV\s+İLANI|DUYURU)",
    re.IGNORECASE,
)


def _infer_pdf_metadata(
    raw_text: str,
    filename: str,
    title: str,
    institution: str,
) -> tuple[str, str]:
    """Infer announcement title and institution from PDF text/filename if blank."""
    clean_lines = [
        re.sub(r"\s+", " ", ln).strip()
        for ln in (raw_text or "").splitlines()
    ]
    clean_lines = [
        ln
        for ln in clean_lines
        if ln and len(ln) >= 4 and not re.fullmatch(r"(?:sayfa\s*)?\d+(?:\s*/\s*\d+)?", ln, re.I)
    ]

    resolved_inst = institution.strip()
    if not resolved_inst:
        for ln in clean_lines[:12]:
            if 5 <= len(ln) <= 130 and _INST_LINE_RE.search(ln):
                resolved_inst = ln
                break
        if not resolved_inst:
            resolved_inst = "Kamu Kurumu"

    resolved_title = title.strip()
    if not resolved_title:
        for ln in clean_lines[:18]:
            if ln == resolved_inst:
                continue
            if 8 <= len(ln) <= 180 and _TITLE_LINE_RE.search(ln):
                resolved_title = ln
                break
        if not resolved_title and clean_lines:
            for ln in clean_lines[:5]:
                if ln != resolved_inst and len(ln) >= 6:
                    resolved_title = ln[:180]
                    break
        if not resolved_title:
            stem = Path(filename or "PDF İlan").stem.replace("_", " ").replace("-", " ").strip()
            resolved_title = stem or "PDF Kamu Personel Alım İlanı"

    return resolved_title, resolved_inst


def _save_manual_announcement(
    *,
    title: str,
    institution: str,
    url: str,
    raw_text: str,
    source_label: str,
    external_seed: str,
) -> AnnouncementDetail:
    """Run criteria extraction, deduplicated upsert, and match evaluation for manual imports."""
    from app.engine.extractor import extract_criteria
    from app.scheduler import _raw_to_item_dict
    from app.scrapers.base import RawAnnouncement, infer_category

    scraped_at = datetime.now().isoformat(timespec="seconds")
    external_id = hashlib.sha1(external_seed.encode("utf-8", errors="ignore")).hexdigest()[:24]
    category = infer_category(title, raw_text)
    raw = RawAnnouncement(
        source_name="manual_import",
        source_label=source_label or "Manuel İçe Aktarım",
        external_id=external_id,
        url=url.strip(),
        title=title.strip(),
        institution=institution.strip() or "Kamu Kurumu",
        category=category,
        publish_date=None,
        deadline_date=None,
        city=None,
        quota_count=None,
        raw_text=raw_text,
    )
    extracted = extract_criteria(raw)
    item_dict = _raw_to_item_dict(raw, extracted, scraped_at)
    upsert_res = database.upsert_announcements([item_dict])
    target_ids = upsert_res.get("ids") or upsert_res.get("new_ids") or []
    if not target_ids:
        raise HTTPException(status_code=500, detail="İlan kaydedilemedi.")
    row = database.get_announcement_by_id(target_ids[0])
    if row is None:
        raise HTTPException(status_code=500, detail="Kaydedilen ilan okunamadı.")
    profile = database.get_profile()
    return AnnouncementDetail(**_build_announcement_payload(row, profile, include_raw=True))


@app.post("/api/announcements/import", response_model=AnnouncementDetail, status_code=201)
def import_announcement_text(payload: ManualImportTextRequest) -> AnnouncementDetail:
    if not payload.title.strip() or not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="Başlık ve ilan metni boş olamaz.")
    seed = f"{payload.title.strip()}|{payload.institution.strip()}|{payload.url.strip()}|{payload.raw_text[:500]}"
    return _save_manual_announcement(
        title=payload.title,
        institution=payload.institution,
        url=payload.url,
        raw_text=payload.raw_text,
        source_label=payload.source_label,
        external_seed=seed,
    )


@app.post("/api/announcements/import-pdf", response_model=AnnouncementDetail, status_code=201)
async def import_announcement_pdf(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    institution: str = Form(default=""),
    url: str = Form(default=""),
) -> AnnouncementDetail:
    from app.scrapers.base import extract_pdf_text

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Yüklenen PDF dosyası boş.")
    filename = file.filename or "ilan.pdf"
    if not filename.lower().endswith(".pdf") and not pdf_bytes.lstrip().startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir PDF dosyası yükleyin.")

    raw_text = await asyncio.to_thread(extract_pdf_text, pdf_bytes, 10)
    resolved_title, resolved_inst = _infer_pdf_metadata(
        raw_text=raw_text,
        filename=filename,
        title=title,
        institution=institution,
    )
    pdf_hash = hashlib.sha1(pdf_bytes).hexdigest()
    return await asyncio.to_thread(
        _save_manual_announcement,
        title=resolved_title,
        institution=resolved_inst,
        url=url,
        raw_text=raw_text,
        source_label="PDF İçe Aktarım",
        external_seed=f"pdf|{pdf_hash}",
    )


@app.get("/api/announcements/{announcement_id}", response_model=AnnouncementDetail)
def get_announcement_detail(announcement_id: int) -> AnnouncementDetail:
    row = database.get_announcement_by_id(announcement_id)
    if row is None:
        raise HTTPException(status_code=404, detail="İlan bulunamadı.")
    profile = database.get_profile()
    payload = _build_announcement_payload(row, profile, include_raw=True)
    return AnnouncementDetail(**payload)


@app.patch("/api/announcements/{announcement_id}/state", response_model=UpdateStateResponse)
def update_announcement_state(
    announcement_id: int,
    payload: UpdateStateRequest,
) -> UpdateStateResponse:
    updated = database.update_announcement_state(
        announcement_id=announcement_id,
        status=payload.status,
        notes=payload.notes,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="İlan bulunamadı.")
    return UpdateStateResponse(**updated)


@app.get("/api/stats", response_model=StatsResponse)
def get_stats() -> StatsResponse:
    profile = database.get_profile()
    rows = database.list_announcements()

    total_active = 0
    eligible_count = 0
    review_count = 0
    ineligible_count = 0
    deadline_soon_count = 0
    new_today_count = 0
    saved_count = 0
    applied_count = 0
    dismissed_count = 0
    categories: dict[str, int] = {}

    from app.engine.matcher import evaluate_match

    for row in rows:
        u_status = row["user_state"]["status"]
        days_rem = _compute_days_remaining(row.get("deadline_date"))

        if u_status == "saved":
            saved_count += 1
        elif u_status == "applied":
            applied_count += 1
        elif u_status == "dismissed":
            if days_rem is None or days_rem >= 0:
                dismissed_count += 1
            continue

        if days_rem is not None and days_rem < 0:
            continue

        total_active += 1
        cat = row.get("category") or "diger"
        categories[cat] = categories.get(cat, 0) + 1

        if days_rem is not None and 0 <= days_rem <= DEADLINE_SOON_DAYS:
            deadline_soon_count += 1

        if _compute_is_new(row.get("publish_date"), row.get("first_seen_at", "")):
            new_today_count += 1

        match = evaluate_match(row, profile)
        m_status = match["match_status"]
        if m_status == "eligible":
            eligible_count += 1
        elif m_status == "review":
            review_count += 1
        else:
            ineligible_count += 1

    scrape_status = scheduler.get_status()
    return StatsResponse(
        total_active=total_active,
        eligible_count=eligible_count,
        review_count=review_count,
        ineligible_count=ineligible_count,
        deadline_soon_count=deadline_soon_count,
        new_today_count=new_today_count,
        saved_count=saved_count,
        applied_count=applied_count,
        dismissed_count=dismissed_count,
        is_scanning=scrape_status["is_scanning"],
        last_scan_at=scrape_status["last_scan_at"],
        categories=categories,
        sources=scrape_status["runs"],
    )


@app.post("/api/scrape/trigger", response_model=ScrapeTriggerResponse)
async def trigger_scrape(
    payload: ScrapeTriggerRequest | None = Body(default=None),
) -> ScrapeTriggerResponse:
    source = payload.source if payload is not None else "all"
    result = scheduler.trigger_scan(source=source)
    return ScrapeTriggerResponse(**result)


@app.get("/api/scrape/status", response_model=ScrapeStatusResponse)
def get_scrape_status() -> ScrapeStatusResponse:
    return ScrapeStatusResponse(**scheduler.get_status())


@app.get("/api/nitelik-kodlari", response_model=list[NitelikKoduItem])
def get_nitelik_kodlari(
    q: str = Query(default=""),
    level: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[NitelikKoduItem]:
    items = search_nitelik_kodlari(query=q, level=level, limit=limit)
    return [NitelikKoduItem(**item) for item in items]


@app.get("/api/custom-sources", response_model=list[CustomSourceItem])
def get_custom_sources() -> list[CustomSourceItem]:
    return [CustomSourceItem(**cs) for cs in database.list_custom_sources()]


@app.post("/api/custom-sources", response_model=CustomSourceItem, status_code=201)
def add_custom_source(payload: CustomSourceCreate) -> CustomSourceItem:
    url_clean = payload.url.strip()
    if not (url_clean.startswith("http://") or url_clean.startswith("https://")):
        raise HTTPException(
            status_code=400,
            detail="URL http:// veya https:// ile başlamalıdır.",
        )
    try:
        created = database.create_custom_source(
            name=payload.name,
            url=url_clean,
            keywords=payload.keywords,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Bu URL zaten izleme listesinde mevcut.")
    return CustomSourceItem(**created)


@app.delete("/api/custom-sources/{source_id}")
def remove_custom_source(source_id: int) -> dict:
    deleted = database.delete_custom_source(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Özel kaynak bulunamadı.")
    return {"deleted": True, "id": source_id}


@app.post("/api/notifications/test", response_model=NotificationTestResponse)
async def test_notifications() -> NotificationTestResponse:
    from app.engine.notifier import send_test_notification

    profile = database.get_profile()
    result = await send_test_notification(profile)
    return NotificationTestResponse(**result)


@app.get("/api/institutions", response_model=InstitutionsCatalogResponse)
def get_institutions() -> InstitutionsCatalogResponse:
    import app.scrapers as scrapers_pkg

    catalog_fn = getattr(scrapers_pkg, "get_institutions_catalog_with_status", None)
    if catalog_fn is None:
        return InstitutionsCatalogResponse(total=0, groups=[])
    data = catalog_fn()
    return InstitutionsCatalogResponse(**data)


# Optional SPA static serving when frontend/dist has been built
if FRONTEND_DIST_DIR.is_dir() and (FRONTEND_DIST_DIR / "index.html").is_file():
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="spa-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="API endpoint bulunamadı.")
        candidate = (FRONTEND_DIST_DIR / full_path).resolve()
        dist_root = FRONTEND_DIST_DIR.resolve()
        if (
            full_path
            and candidate.is_file()
            and str(candidate).startswith(str(dist_root))
        ):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
