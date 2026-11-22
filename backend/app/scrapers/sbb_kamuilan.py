"""Scraper for SBB Kamu İlan (https://kamuilan.sbb.gov.tr/)."""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import logging
import re
import time
import urllib.parse

from bs4 import BeautifulSoup

from app.scrapers.base import (
    HttpClient,
    RawAnnouncement,
    extract_pdf_text,
    extract_quota_from_text,
    infer_application_channel,
    infer_category,
    is_cancelled_announcement_title,
    normalize_ascii_tr,
    normalize_whitespace,
    parse_date_range,
    parse_turkish_date,
    turkish_lower,
)

logger = logging.getLogger(__name__)

SBB_BASE_URL = "https://kamuilan.sbb.gov.tr/"
MAX_PDF_DOWNLOADS = 65
PDF_TIME_BUDGET_SECONDS = 45.0
PDF_CONCURRENCY = 6


def _stable_sbb_id(institution: str, title: str, date_range_str: str) -> str:
    """SBB encrypts `kod` with a fresh IV per request, so derive ID from content."""
    key = "|".join(
        [
            normalize_ascii_tr(re.sub(r"\s+", " ", institution)),
            normalize_ascii_tr(re.sub(r"\s+", " ", title)),
            normalize_ascii_tr(re.sub(r"\s+", " ", date_range_str)),
        ]
    )
    return hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _parse_listing_entries(html: str) -> list[dict]:
    """Parse both timeline (.cbp_tmtimeline) and carousel (#manset) entries."""
    soup = BeautifulSoup(html, "lxml")
    today = datetime.date.today()
    items_by_id: dict[str, dict] = {}

    # 1. Timeline entries (have exact publish day+month in <time class="cbp_tmtime">)
    for li in soup.select(".cbp_tmtimeline > li"):
        time_el = li.select_one("time.cbp_tmtime")
        publish_date: str | None = None
        if time_el:
            day_el = time_el.select_one("h4")
            month_el = time_el.select_one("h3")
            if day_el and month_el:
                raw_pub = f"{day_el.get_text(strip=True)} {month_el.get_text(strip=True)}"
                publish_date = parse_turkish_date(raw_pub, reference_date=today)

        for a in li.select(".cbp_tmlabel a.xx[href*='ilanDetay.aspx']"):
            href = a.get("href", "").strip()
            if not href:
                continue
            inst_el = a.select_one("p.alt_p1")
            title_el = a.select_one("p.alt_p2")
            date_em = title_el.select_one("em") if title_el else None

            date_range_str = normalize_whitespace(
                re.sub(r"\s+", " ", date_em.get_text(" ", strip=True)).strip("() ")
            ) if date_em else ""
            if date_em:
                date_em.extract()

            institution = normalize_whitespace(
                re.sub(r"\s+", " ", inst_el.get_text(" ", strip=True)) if inst_el else ""
            )
            title = normalize_whitespace(
                re.sub(r"\s+", " ", title_el.get_text(" ", strip=True)) if title_el else ""
            )
            kod = _stable_sbb_id(institution, title, date_range_str)
            _, deadline_date = parse_date_range(date_range_str, reference_date=today)
            full_url = urllib.parse.urljoin(SBB_BASE_URL, href)

            items_by_id[kod] = {
                "external_id": kod,
                "url": full_url,
                "pdf_url": full_url,
                "institution": institution or "Kamu Kurumu",
                "title": title or "Kamu Personel Alım İlanı",
                "publish_date": publish_date,
                "deadline_date": deadline_date,
                "date_range_str": date_range_str,
            }

    # 2. Manset (carousel) entries — add any not in timeline, or fill missing fields
    for a in soup.select("#manset a.xx[href*='ilanDetay.aspx']"):
        href = a.get("href", "").strip()
        if not href:
            continue
        inst_el = a.select_one("span.black")
        title_el = a.select_one("span.patrol")
        date_el = a.select_one("span.h5date")

        institution = normalize_whitespace(
            re.sub(r"\s+", " ", inst_el.get_text(" ", strip=True)) if inst_el else ""
        )
        title = normalize_whitespace(
            re.sub(r"\s+", " ", title_el.get_text(" ", strip=True)) if title_el else ""
        )
        date_range_str = normalize_whitespace(
            re.sub(r"\s+", " ", date_el.get_text(" ", strip=True)) if date_el else ""
        )
        kod = _stable_sbb_id(institution, title, date_range_str)
        start_date, deadline_date = parse_date_range(date_range_str, reference_date=today)
        full_url = urllib.parse.urljoin(SBB_BASE_URL, href)

        if kod not in items_by_id:
            items_by_id[kod] = {
                "external_id": kod,
                "url": full_url,
                "pdf_url": full_url,
                "institution": institution or "Kamu Kurumu",
                "title": title or "Kamu Personel Alım İlanı",
                "publish_date": start_date,
                "deadline_date": deadline_date,
                "date_range_str": date_range_str,
            }
        else:
            existing = items_by_id[kod]
            if not existing["deadline_date"] and deadline_date:
                existing["deadline_date"] = deadline_date
            if not existing["date_range_str"] and date_range_str:
                existing["date_range_str"] = date_range_str

    return list(items_by_id.values())


def _repair_broken_title(title: str, pdf_text: str) -> str:
    """Fix SBB titles missing a role noun like '5 ALACAK' using PDF heading or fallback."""
    clean = normalize_whitespace(title)
    m = re.fullmatch(r"(\d{1,4})\s+alacak", clean, re.I)
    if not m:
        return clean
    qty = m.group(1)
    if pdf_text:
        for line in pdf_text.splitlines()[:18]:
            line_clean = normalize_whitespace(line)
            low = turkish_lower(line_clean)
            if (
                8 <= len(line_clean) <= 100
                and any(
                    kw in low
                    for kw in (
                        "uzman personel",
                        "destek personeli",
                        "personel alım",
                        "sözleşmeli personel",
                        "memur alım",
                        "uzman yardımcısı",
                        "müfettiş yardımcısı",
                        "denetmen yardımcısı",
                        "giriş sınavı",
                    )
                )
            ):
                return f"{qty} {line_clean}" if qty not in line_clean else line_clean
    return f"{qty} Personel Alım İlanı"


async def scrape_sbb_kamuilan(
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Fetch active announcements from kamuilan.sbb.gov.tr and extract PDF texts for new items."""
    known = known_external_ids or set()
    client = HttpClient(timeout=15.0, max_retries=2)
    html = await client.get_text(SBB_BASE_URL, encoding="utf-8")
    raw_entries = _parse_listing_entries(html)
    entries = [e for e in raw_entries if not is_cancelled_announcement_title(e["title"])]

    if not entries:
        logger.warning("SBB Kamu İlan returned 0 active listing entries")
        return []

    semaphore = asyncio.Semaphore(PDF_CONCURRENCY)
    started_at = time.monotonic()
    pdf_texts: dict[str, str] = {}

    # Prioritize non-academic KPSS/public recruitment PDFs before academic faculty calls
    unseen_candidates = [e for e in entries if e["external_id"] not in known]
    for e in unseen_candidates:
        e["_prelim_cat"] = infer_category(f"{e['institution']} {e['title']}")
    unseen_candidates.sort(key=lambda e: 1 if e["_prelim_cat"] == "akademik" else 0)
    unseen = unseen_candidates[:MAX_PDF_DOWNLOADS]

    async def _fetch_pdf(entry: dict) -> None:
        if time.monotonic() - started_at > PDF_TIME_BUDGET_SECONDS:
            return
        async with semaphore:
            if time.monotonic() - started_at > PDF_TIME_BUDGET_SECONDS:
                return
            try:
                pdf_bytes, _ = await client.get_bytes(
                    entry["pdf_url"],
                    headers={"Referer": SBB_BASE_URL},
                    timeout=15.0,
                )
                txt = await asyncio.to_thread(extract_pdf_text, pdf_bytes, 6)
                if txt:
                    pdf_texts[entry["external_id"]] = txt
            except Exception as exc:
                logger.debug("SBB PDF fetch failed for %s: %s", entry["external_id"], exc)

    if unseen:
        await asyncio.gather(*(_fetch_pdf(e) for e in unseen), return_exceptions=True)

    results: list[RawAnnouncement] = []
    for entry in entries:
        ext_id = entry["external_id"]
        pdf_text = pdf_texts.get(ext_id, "")
        repaired_title = _repair_broken_title(entry["title"], pdf_text)
        if is_cancelled_announcement_title(repaired_title):
            continue
        fallback_summary = (
            f"{entry['institution']} — {repaired_title}."
            + (f" Başvuru tarihleri: {entry['date_range_str']}." if entry["date_range_str"] else "")
            + f" Resmi ilan bağlantısı: {entry['pdf_url']}"
        )
        raw_text = pdf_text if pdf_text else fallback_summary
        full_title = repaired_title
        category = infer_category(f"{entry['institution']} {full_title}", raw_text)
        quota = extract_quota_from_text(full_title, raw_text)
        channel = infer_application_channel(raw_text)

        results.append(
            RawAnnouncement(
                source_name="sbb_kamuilan",
                source_label="SBB Kamu İlan",
                external_id=ext_id,
                url=entry["url"],
                title=full_title,
                institution=entry["institution"],
                category=category,
                publish_date=entry["publish_date"],
                deadline_date=entry["deadline_date"],
                city=None,
                quota_count=quota,
                raw_text=raw_text,
                pdf_url=entry["pdf_url"],
                application_channel=channel,
            )
        )

    logger.info(
        "SBB Kamu İlan scraped %d announcements (%d PDF texts extracted)",
        len(results),
        len(pdf_texts),
    )
    return results
