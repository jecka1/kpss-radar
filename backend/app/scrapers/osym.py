"""Scraper for ÖSYM KPSS / EKPSS central placement announcements (https://www.osym.gov.tr/)."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import re
import urllib.parse

from bs4 import BeautifulSoup

from app.scrapers.base import (
    HttpClient,
    RawAnnouncement,
    normalize_whitespace,
    parse_turkish_date,
    stable_external_id,
    turkish_lower,
)

logger = logging.getLogger(__name__)

OSYM_BASE_URL = "https://www.osym.gov.tr"
OSYM_PAGES = [
    ("https://www.osym.gov.tr/SinavGrubu/Index/3", "KPSS"),
    ("https://www.osym.gov.tr/SinavGrubu/Index/4", "EKPSS"),
    ("https://www.osym.gov.tr/", "HOME"),
]

MAX_ITEMS = 22
MAX_DETAIL_FETCHES = 15
DETAIL_CONCURRENCY = 5

OSYM_EXCLUDE_TERMS = (
    "sınava giriş",
    "nüfus müdürlük",
    "soru kitapç",
    "cevap anahtar",
    "cevap kâğıt",
    "cevap kağıt",
    "sonuçları açıklandı",
    "branş bazında",
    "değerlendirme raporu",
    "sınav takvimi",
    "sınav başvuru",
    "başvurularının alınması",
    "sınavına ilişkin açıklama",
    "sayısal bilgiler",
    "temel soru",
    "başvuru bilgileri",
)

OSYM_INCLUDE_TERMS = (
    "tercih",
    "yerleştirme",
    "atama",
    "ek yerleştirme",
    "kadro",
    "sözleşmeli personel",
    "personel alım",
)


def _is_relevant_osym_title(title: str, source_tag: str) -> bool:
    low = turkish_lower(title)
    if any(ex in low for ex in OSYM_EXCLUDE_TERMS):
        return False
    has_kpss = ("kpss" in low or "ekpss" in low or "merkezi yerleştirme" in low or source_tag in ("KPSS", "EKPSS"))
    if not has_kpss:
        return False
    return any(t in low for t in OSYM_INCLUDE_TERMS)


def _parse_osym_links(html: str, source_tag: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items: list[dict] = []
    seen_urls: set[str] = set()

    # 1. Homepage embedded announcement JSON array (if present)
    if source_tag == "HOME":
        for m in re.finditer(r'\[\s*\{"baslik"\s*:.*?\}\s*\]', html, re.S):
            try:
                arr = json.loads(m.group(0))
                for entry in arr:
                    title = normalize_whitespace(str(entry.get("baslik", "")))
                    link = str(entry.get("link", "")).strip()
                    tarih = str(entry.get("tarih", "")).strip()
                    if not title or not link:
                        continue
                    if not _is_relevant_osym_title(title, source_tag):
                        continue
                    full_url = urllib.parse.urljoin(OSYM_BASE_URL, "/" + link.lstrip("/"))
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)
                    items.append(
                        {
                            "external_id": stable_external_id("osym", link),
                            "url": full_url,
                            "title": title,
                            "publish_date": parse_turkish_date(tarih),
                            "tag": "EKPSS" if "ekpss" in turkish_lower(title) else "KPSS",
                        }
                    )
            except Exception:
                continue

    # 2. Standard announcement anchors on SinavGrubu/Index/3 & 4 and homepage
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        if any(
            skip in href.lower()
            for skip in ("/sinavgrubu/", "/duyurular/", "/belge/", "ais.osym", "twitter", "facebook", "youtube")
        ):
            continue

        raw_txt = normalize_whitespace(a.get_text(" ", strip=True))
        attr_title = normalize_whitespace(a.get("title") or "")
        title = attr_title if len(attr_title) >= 10 else raw_txt
        if len(title) < 12 or not _is_relevant_osym_title(title, source_tag):
            continue

        # Strip leading date from anchor text if attr_title wasn't present
        pub_date = parse_turkish_date(raw_txt)
        clean_title = re.sub(
            r"^\d{1,2}\s+[A-Za-zÇĞIİÖŞÜçğıöşü]+\s+20\d{2}\s+",
            "",
            title,
        ).strip()

        full_url = urllib.parse.urljoin(OSYM_BASE_URL, href)
        if full_url in seen_urls or full_url.rstrip("/") == OSYM_BASE_URL:
            continue
        seen_urls.add(full_url)

        items.append(
            {
                "external_id": stable_external_id("osym", urllib.parse.urlparse(full_url).path),
                "url": full_url,
                "title": clean_title,
                "publish_date": pub_date,
                "tag": "EKPSS" if ("ekpss" in turkish_lower(clean_title) or source_tag == "EKPSS") else "KPSS",
            }
        )

    return items


def _parse_osym_detail(html: str) -> tuple[str, str | None]:
    soup = BeautifulSoup(html, "lxml")
    container = soup.select_one(".content") or soup.select_one("main") or soup.body
    if not container:
        return "", None
    for tag in container.select("script, style, nav"):
        tag.decompose()
    lines = [normalize_whitespace(line) for line in container.get_text("\n").splitlines()]
    text = "\n".join(line for line in lines if line)

    pub_date: str | None = None
    m = re.search(r"DUYURU\s*\(([^)]+)\)", text, re.I)
    if m:
        pub_date = parse_turkish_date(m.group(1))
    return text, pub_date


async def scrape_osym(
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Scrape ÖSYM KPSS and EKPSS announcements."""
    known = known_external_ids or set()
    client = HttpClient(timeout=15.0, max_retries=2)

    async def _fetch_page(url: str, tag: str) -> list[dict]:
        try:
            html = await client.get_text(url, encoding="utf-8")
            return _parse_osym_links(html, tag)
        except Exception as exc:
            logger.warning("ÖSYM page fetch failed (%s): %s", url, exc)
            return []

    batches = await asyncio.gather(*(_fetch_page(u, t) for u, t in OSYM_PAGES))
    merged: dict[str, dict] = {}
    seen_titles: set[str] = set()
    for batch in batches:
        for item in batch:
            norm_url = item["url"].rstrip("/").lower()
            norm_title = re.sub(r"\s+", " ", turkish_lower(item["title"]))
            ext_id = stable_external_id("osym", norm_url)
            item["external_id"] = ext_id
            if ext_id in merged:
                if not merged[ext_id]["publish_date"] and item["publish_date"]:
                    merged[ext_id]["publish_date"] = item["publish_date"]
                continue
            if norm_title in seen_titles:
                continue
            seen_titles.add(norm_title)
            merged[ext_id] = item

    # Sort newest first when publish_date is known
    entries = sorted(
        merged.values(),
        key=lambda x: x["publish_date"] or "0000-00-00",
        reverse=True,
    )[:MAX_ITEMS]

    if not entries:
        logger.warning("ÖSYM returned 0 KPSS/EKPSS announcements")
        return []

    semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)
    details: dict[str, tuple[str, str | None]] = {}
    unseen = [e for e in entries if e["external_id"] not in known][:MAX_DETAIL_FETCHES]

    async def _fetch_detail(entry: dict) -> None:
        async with semaphore:
            try:
                html = await client.get_text(entry["url"], encoding="utf-8", timeout=15.0)
                details[entry["external_id"]] = _parse_osym_detail(html)
            except Exception as exc:
                logger.debug("ÖSYM detail failed (%s): %s", entry["url"], exc)

    if unseen:
        await asyncio.gather(*(_fetch_detail(e) for e in unseen), return_exceptions=True)

    results: list[RawAnnouncement] = []
    today = datetime.date.today()
    for entry in entries:
        ext_id = entry["external_id"]
        det_text, det_pub = details.get(ext_id, ("", None))
        pub_date = entry["publish_date"] or det_pub
        deadline_date: str | None = None
        if det_text:
            dl_m = re.search(
                r"(?:son\s+başvuru|tercih\w*\s+sona|tarihine\s+kadar|-\s*(\d{1,2}\s+[a-zçğıöşü]+\s+20\d{2}))",
                turkish_lower(det_text[:2500]),
            )
            if dl_m:
                deadline_date = parse_turkish_date(dl_m.group(0))
        # Skip stale ÖSYM placement announcements older than 45 days without a future deadline
        if pub_date:
            try:
                pub_dt = datetime.date.fromisoformat(pub_date[:10])
                has_future_deadline = bool(deadline_date and deadline_date >= today.isoformat())
                if (today - pub_dt).days > 45 and not has_future_deadline:
                    continue
            except ValueError:
                pass
        raw_text = det_text if det_text else f"ÖSYM Duyurusu: {entry['title']} ({entry['url']})"

        results.append(
            RawAnnouncement(
                source_name="osym",
                source_label="ÖSYM",
                external_id=ext_id,
                url=entry["url"],
                title=entry["title"],
                institution="ÖSYM (Ölçme, Seçme ve Yerleştirme Merkezi)",
                category="engelli" if entry["tag"] == "EKPSS" and "tercih" in turkish_lower(entry["title"]) else "merkezi_atama",
                publish_date=pub_date,
                deadline_date=deadline_date,
                city="Türkiye Geneli",
                quota_count=None,
                raw_text=raw_text,
                pdf_url=None,
                application_channel="ÖSYM AİS",
            )
        )

    logger.info("ÖSYM scraped %d KPSS/EKPSS announcements", len(results))
    return results
