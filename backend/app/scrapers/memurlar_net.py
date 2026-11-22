"""Scraper for Memurlar.net active recruitment listings (https://ilan.memurlar.net/)."""

from __future__ import annotations

import asyncio
import datetime
import logging
import re
import urllib.parse

from bs4 import BeautifulSoup

from app.scrapers.base import (
    HttpClient,
    RawAnnouncement,
    extract_quota_from_text,
    infer_application_channel,
    infer_category,
    is_cancelled_announcement_title,
    normalize_whitespace,
    parse_turkish_date,
    turkish_lower,
)

logger = logging.getLogger(__name__)

MEMURLAR_BASE_URL = "https://ilan.memurlar.net"
_PAGINATED_CATEGORIES: list[tuple[str, str]] = [
    ("/kategori/kpss-a-ilanlari/?Expire=false", "kpss_a"),
    ("/kategori/kpss-b-ilanlari/?Expire=false", "memur"),
    ("/kategori/mahalli-ilanlari/?Expire=false", "memur"),
    ("/kategori/genel-ilanlar/?Expire=false", "memur"),
    ("/kategori/4b-ilanlari/?Expire=false", "sozlesmeli_4b"),
    ("/kategori/daimi-isci-ilanlari/?Expire=false", "isci"),
    ("/kategori/gecici-isci-ilanlari/?Expire=false", "isci"),
    ("/kategori/sydv-ilanlari/?Expire=false", "sydv"),
    ("/kategori/engelli-ilanlari/?Expire=false", "engelli"),
]
CATEGORY_ENDPOINTS: list[tuple[str, str]] = [
    *(endpoint for path, cat in _PAGINATED_CATEGORIES for endpoint in ((path, cat), (f"{path}&Page=2", cat))),
    ("/kategori/lakinma-ajansi/?Expire=false", "kpss_a"),
    ("/kategori/askeri-ilanlar/?Expire=false", "askeri_emniyet"),
    ("/kategori/akademik-ilanlar-devlet/?Expire=false", "akademik"),
    ("/", "diger"),
]

MAX_DETAIL_FETCHES = 65
DETAIL_CONCURRENCY = 6


def _extract_ilan_id(href: str) -> str | None:
    m = re.search(r"/ilan/(\d+)/", href)
    return m.group(1) if m else None


def _split_institution_and_title(title: str) -> tuple[str, str]:
    """Split 'Adli Tıp Kurumu Başkanlığı 181 sözleşmeli personel alacak' cleanly."""
    clean = normalize_whitespace(title)
    if not clean:
        return "Kamu Kurumu", "Kamu Personel Alım İlanı"

    # Common comma separator: "SGK, 50 Müfettiş Yardımcısı Alacak"
    if ", " in clean:
        left, right = clean.split(", ", 1)
        if 2 <= len(left) <= 80:
            return left.strip(), clean

    # Split before quota count or recruitment role keywords
    m = re.search(
        r"\s+(?=\d{1,4}\s+|"
        r"(?:sözleşmeli|memur|işçi|daimi|geçici|personel|öğretim|araştırma|müfettiş|uzman|"
        r"denetçi|kaymakam|subay|astsubay|alım|alacak|alımı|alınacaktır)\b)",
        clean,
        re.I,
    )
    if m and m.start() >= 4:
        inst = clean[: m.start()].strip(" ,:-")
        if len(inst) >= 3:
            return inst, clean

    return "Kamu Kurumu", clean


def _parse_category_links(html: str, default_category: str) -> list[dict]:
    """Extract listing links from main content area, excluding sidebar widgets."""
    soup = BeautifulSoup(html, "lxml")

    # Remove sidebars so "Son İlanlar" widgets do not contaminate category lists
    for side in soup.select(".sidebar, aside"):
        side.decompose()

    items: list[dict] = []
    seen_ids: set[str] = set()

    for a in soup.select("a[href*='/ilan/']"):
        href = a.get("href", "").strip()
        ext_id = _extract_ilan_id(href)
        if not ext_id or ext_id in seen_ids:
            continue
        seen_ids.add(ext_id)

        title = normalize_whitespace(a.get("title") or a.get_text(" ", strip=True))
        if not title or is_cancelled_announcement_title(title):
            continue

        full_url = urllib.parse.urljoin(MEMURLAR_BASE_URL, href)
        institution, clean_title = _split_institution_and_title(title)

        items.append(
            {
                "external_id": ext_id,
                "url": full_url,
                "title": clean_title,
                "institution": institution,
                "category": default_category,
            }
        )
    return items


def _parse_detail_page(html: str, fallback_title: str) -> dict:
    """Extract full announcement text, dates, and official URLs from detail HTML."""
    soup = BeautifulSoup(html, "lxml")
    today = datetime.date.today()

    h1 = soup.select_one("h1.title") or soup.select_one("h1")
    title = normalize_whitespace(h1.get_text(" ", strip=True)) if h1 else fallback_title

    content_root = soup.select_one(".content-detail") or soup.select_one("article") or soup
    info_text = ""
    for info_el in content_root.select(".info"):
        info_text += " " + info_el.get_text(" ", strip=True)

    publish_date: str | None = None
    pub_match = re.search(r"İlan\s+Giriş\s*:\s*([^,\n]+)", info_text, re.I)
    if pub_match:
        parsed_pub = parse_turkish_date(pub_match.group(1), reference_date=today)
        if parsed_pub:
            try:
                pub_dt = datetime.date.fromisoformat(parsed_pub)
                if (today - pub_dt).days <= 180 and (pub_dt - today).days <= 2:
                    publish_date = parsed_pub
            except ValueError:
                pass

    detail_el = content_root.select_one(".detail") or content_root
    # Strip print/share/comments clutter
    for noise in detail_el.select("script, style, .addthis_inline_share_toolbox_1q9o, #yorumlar"):
        noise.decompose()

    # Collect external links inside announcement body for channel detection
    external_links: list[str] = []
    for a in detail_el.select("a[href^='http']"):
        href = a.get("href", "").strip()
        if href and "memurlar.net" not in href and "news.google.com" not in href:
            external_links.append(href)

    lines = [normalize_whitespace(line) for line in detail_el.get_text("\n").splitlines()]
    raw_text = "\n".join(line for line in lines if line)

    # Also grab lead paragraph above .detail if present
    lead_parts: list[str] = []
    for p in content_root.select("p"):
        if detail_el and p in detail_el.descendants:
            continue
        t = normalize_whitespace(p.get_text(" ", strip=True))
        if t and len(t) > 15:
            lead_parts.append(t)
    lead_text = "\n".join(lead_parts[:3])
    if lead_text and lead_text not in raw_text:
        raw_text = f"{lead_text}\n\n{raw_text}".strip()

    # Extract deadline from "Son başvuru tarihi ..."
    deadline_date: str | None = None
    ref = datetime.date.fromisoformat(publish_date) if publish_date else today
    for pattern in (
        r"son\s+başvuru\s+tarihi\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]20\d{2}|20\d{2}[-/]\d{1,2}[-/]\d{1,2}|[^\n.;,]{4,40})",
        r"başvurular\s+.*?(\d{1,2}[./]\d{1,2}[./]20\d{2}|\d{1,2}\s+[a-zçğıöşü]+\s+20\d{2})\s*(?:tarihine\s+kadar|mesai\s+bitimine)",
    ):
        m = re.search(pattern, turkish_lower(f"{lead_text}\n{raw_text[:3000]}"))
        if m:
            deadline_date = parse_turkish_date(m.group(1), reference_date=ref)
            if deadline_date:
                break

    channel_source = f"{raw_text}\n{' '.join(external_links)}"
    channel = infer_application_channel(channel_source)

    return {
        "title": title,
        "publish_date": publish_date,
        "deadline_date": deadline_date,
        "raw_text": raw_text,
        "application_channel": channel,
    }


async def scrape_memurlar_net(
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Scrape active Memurlar.net recruitment categories with windows-1254 decoding."""
    known = known_external_ids or set()
    client = HttpClient(timeout=15.0, max_retries=2)

    async def _fetch_cat(path: str, cat_code: str) -> list[dict]:
        url = urllib.parse.urljoin(MEMURLAR_BASE_URL, path)
        try:
            html = await client.get_text(url, encoding="cp1254")
            return _parse_category_links(html, cat_code)
        except Exception as exc:
            logger.warning("Memurlar.net category fetch failed (%s): %s", url, exc)
            return []

    cat_batches = await asyncio.gather(
        *(_fetch_cat(path, cat_code) for path, cat_code in CATEGORY_ENDPOINTS)
    )

    merged: dict[str, dict] = {}
    for batch in cat_batches:
        for item in batch:
            ext_id = item["external_id"]
            if ext_id not in merged:
                merged[ext_id] = item
            elif merged[ext_id]["category"] == "diger" and item["category"] != "diger":
                merged[ext_id]["category"] = item["category"]

    entries = list(merged.values())
    if not entries:
        logger.warning("Memurlar.net returned 0 entries across all categories")
        return []

    semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)
    details: dict[str, dict] = {}
    unseen_candidates = [e for e in entries if e["external_id"] not in known]
    # Prioritize non-academic / non-isci announcements before akademik and isci
    unseen_candidates.sort(
        key=lambda e: 2 if e["category"] == "akademik" else (1 if e["category"] == "isci" else 0)
    )
    unseen = unseen_candidates[:MAX_DETAIL_FETCHES]

    async def _fetch_detail(entry: dict) -> None:
        async with semaphore:
            try:
                html = await client.get_text(entry["url"], encoding="cp1254", timeout=15.0)
                details[entry["external_id"]] = _parse_detail_page(html, entry["title"])
            except Exception as exc:
                logger.debug("Memurlar.net detail failed (%s): %s", entry["url"], exc)

    if unseen:
        await asyncio.gather(*(_fetch_detail(e) for e in unseen), return_exceptions=True)

    results: list[RawAnnouncement] = []
    for entry in entries:
        ext_id = entry["external_id"]
        det = details.get(ext_id)
        title = det["title"] if det else entry["title"]
        if is_cancelled_announcement_title(title):
            continue
        institution, _ = _split_institution_and_title(title)
        if institution == "Kamu Kurumu":
            institution = entry["institution"]

        raw_text = (
            det["raw_text"]
            if det and det["raw_text"]
            else f"{institution} — {title}. Kaynak: {entry['url']}"
        )
        category = entry["category"]
        if category == "diger":
            category = infer_category(title, raw_text, default="memur")

        quota = extract_quota_from_text(title, raw_text)
        results.append(
            RawAnnouncement(
                source_name="memurlar_net",
                source_label="Memurlar.net",
                external_id=ext_id,
                url=entry["url"],
                title=title,
                institution=institution,
                category=category,
                publish_date=det["publish_date"] if det else None,
                deadline_date=det["deadline_date"] if det else None,
                city=None,
                quota_count=quota,
                raw_text=raw_text,
                pdf_url=None,
                application_channel=det["application_channel"] if det else infer_application_channel(raw_text),
            )
        )

    logger.info(
        "Memurlar.net scraped %d announcements (%d detail pages fetched)",
        len(results),
        len(details),
    )
    return results
