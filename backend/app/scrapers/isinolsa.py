"""Scraper for İşin Olsa public recruitment listings (https://www.isinolsa.com/kamu-personeli-alimi/)."""

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
    stable_external_id,
    turkish_lower,
)

logger = logging.getLogger(__name__)

ISINOLSA_CATEGORY_URLS: list[str] = [
    "https://www.isinolsa.com/kamu-personeli-alimi/",
    "https://www.isinolsa.com/iskur-ilanlari/",
    "https://www.isinolsa.com/belediye-personel-alimi/",
    "https://www.isinolsa.com/memur-alimi/",
    "https://www.isinolsa.com/sozlesmeli-personel-alimi/",
    "https://www.isinolsa.com/sydv-personel-alimi/",
]
MAX_DETAIL_FETCHES = 35
DETAIL_CONCURRENCY = 6
MAX_AGE_DAYS = 30

NOISE_TITLE_TERMS = (
    "sonuç",
    "sonucu",
    "sonuçları",
    "kura çekimi sonucu",
    "taban puanları",
    "taban puan",
    "maaş",
    "maaşları",
    "ne zaman",
    "açıklandı mı",
    "ne olacak",
    "neler bekleniyor",
    "nereye atanılabilir",
    "hesaplama",
    "sınav giriş",
    "soru kitapçığı",
    "cevap anahtarı",
    "emekli",
    "zam",
    "iddiasına",
    "iddia",
    "forumu",
    "atama kararları",
    "görevden alındı",
    "gençlik programında",
    "gençlik programı",
    "zincir market",
    "a101",
    "bim",
    "şok",
    "migros",
    "carrefour",
    "denizbank",
    "garanti",
    "akbank",
    "yapı kredi",
    "iş bankası",
    "qnb",
    "bekleniyor",
    "beklenen kadro",
    "bütçe görüşme",
    "bütçesi",
    "meclis",
    "bakan açıkladı",
    "müjde",
    "rekor başvuru",
    "kontenjana",
    "özel sektör",
    "ekim ayı kamu ilanları",
    "?",
)

POSITIVE_TITLE_TERMS = (
    "alım",
    "alacak",
    "alımı",
    "personel",
    "memur",
    "işçi",
    "sözleşmeli",
    "zabıta",
    "başvuru",
    "kadro",
    "atama",
)

SKIP_URL_SUBSTRINGS = (
    "/kategori/",
    "/etiket/",
    "/sayfa/",
    "/page/",
    "/kamu-personeli-alimi",
    "/iskur-ilanlari/",
    "/memur-alimi/",
    "/sydv-personel-alimi/",
    "/sozlesmeli-personel-alimi/",
    "/belediye-personel-alimi/",
    "/banka-personel-alimi/",
    "/askeri-personel-alimi/",
    "/ozel-sektor-iskur-alimi/",
    "/iletisim",
    "/hakkimizda",
    "/kunye",
    "/gizlilik",
)


def _is_relevant_isinolsa_title(title: str) -> bool:
    low = turkish_lower(title)
    if len(low) < 18 or is_cancelled_announcement_title(title):
        return False
    if any(noise in low for noise in NOISE_TITLE_TERMS):
        return False
    return any(pos in low for pos in POSITIVE_TITLE_TERMS)


def _extract_institution(title: str) -> str:
    clean = normalize_whitespace(title)
    m = re.split(
        r"\s+(?=\d{1,4}\s+|kpss|personel|memur|işçi|sözleşmeli|zabıta|mühendis|tekniker|"
        r"alım|alacak|alımı|lise\s+mezun|önlisans|lisans|kadrolarına|üzerinden)",
        clean,
        maxsplit=1,
        flags=re.I,
    )
    if m and len(m[0].strip(" :,-")) >= 3 and len(m[0].strip()) <= 70:
        cand = m[0].strip(" :,-")
        if turkish_lower(cand) not in ("kamuya", "devlete", "belediyelere", "hastanelere", "şehir", "işkur"):
            return cand
    return "Kamu Kurumu (İşin Olsa)"


def _parse_listing_links(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    main_el = soup.select_one("main") or soup
    for noise in main_el.select("aside, .sidebar, .widget, footer, nav"):
        noise.decompose()
    entries: list[dict] = []
    seen_urls: set[str] = set()

    for a in main_el.select("a[href]"):
        href = a.get("href", "").strip()
        if not href.startswith("https://www.isinolsa.com/"):
            continue
        if any(skip in href for skip in SKIP_URL_SUBSTRINGS):
            continue

        title = normalize_whitespace(a.get("title") or a.get_text(" ", strip=True))
        if not _is_relevant_isinolsa_title(title):
            continue

        norm_url = href.split("#")[0].rstrip("/") + "/"
        if norm_url in seen_urls:
            continue
        seen_urls.add(norm_url)

        entries.append(
            {
                "external_id": stable_external_id("isinolsa", norm_url),
                "url": norm_url,
                "title": title,
                "institution": _extract_institution(title),
            }
        )

    return entries


def _parse_detail(html: str, fallback_title: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.select_one("h1.entry-title") or soup.select_one("h1")
    title = normalize_whitespace(h1.get_text(" ", strip=True)) if h1 else fallback_title

    pub_date: str | None = None
    meta_pub = soup.select_one("meta[property='article:published_time']")
    if meta_pub and meta_pub.get("content"):
        pub_date = parse_turkish_date(meta_pub["content"][:10])
    if not pub_date:
        time_el = soup.select_one("time[datetime]")
        if time_el and time_el.get("datetime"):
            pub_date = parse_turkish_date(time_el["datetime"][:10])

    body_el = (
        soup.select_one(".entry-content")
        or soup.select_one(".post-content")
        or soup.select_one(".content-inner")
        or soup.select_one("article")
        or soup.select_one("main")
    )
    raw_text = ""
    if body_el:
        for noise in body_el.select(
            "script, style, aside, .sidebar, .related, .related-posts, .jeg_postblock, "
            ".widget, footer, .comments, nav, #ez-toc-container, .toc, .sharedaddy, "
            "[class*='related'], [class*='sidebar']"
        ):
            noise.decompose()
        lines = [normalize_whitespace(line) for line in body_el.get_text("\n").splitlines()]
        raw_text = "\n".join(line for line in lines if line)

    return {
        "title": title,
        "publish_date": pub_date,
        "raw_text": raw_text,
    }


async def scrape_isinolsa(
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Scrape active public recruitment notices across 6 specialized İşin Olsa categories."""
    known = known_external_ids or set()
    client = HttpClient(timeout=12.0, max_retries=1)

    async def _fetch_cat(cat_url: str) -> list[dict]:
        try:
            html = await client.get_text(cat_url, encoding="utf-8")
            return _parse_listing_links(html)
        except Exception as exc:
            logger.debug("İşin Olsa category fetch failed (%s): %s", cat_url, exc)
            return []

    batches = await asyncio.gather(*(_fetch_cat(u) for u in ISINOLSA_CATEGORY_URLS))
    merged_entries: dict[str, dict] = {}
    for batch in batches:
        for entry in batch:
            ext_id = entry["external_id"]
            if ext_id not in merged_entries:
                merged_entries[ext_id] = entry

    entries = list(merged_entries.values())
    if not entries:
        logger.warning("İşin Olsa returned 0 candidate recruitment entries")
        return []

    semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)
    details: dict[str, dict] = {}
    unseen = [e for e in entries if e["external_id"] not in known][:MAX_DETAIL_FETCHES]

    async def _fetch(entry: dict) -> None:
        async with semaphore:
            try:
                det_html = await client.get_text(entry["url"], encoding="utf-8", timeout=10.0)
                details[entry["external_id"]] = _parse_detail(det_html, entry["title"])
            except Exception as exc:
                logger.debug("İşin Olsa detail failed (%s): %s", entry["url"], exc)

    if unseen:
        await asyncio.gather(*(_fetch(e) for e in unseen), return_exceptions=True)

    today = datetime.date.today()
    results: list[RawAnnouncement] = []
    for entry in entries:
        ext_id = entry["external_id"]
        det = details.get(ext_id)
        title = det["title"] if det else entry["title"]
        if not _is_relevant_isinolsa_title(title):
            continue

        pub_date = det["publish_date"] if det else None
        if pub_date:
            try:
                if (today - datetime.date.fromisoformat(pub_date)).days > MAX_AGE_DAYS:
                    continue
            except ValueError:
                pass

        raw_text = det["raw_text"] if det and det["raw_text"] else f"{title}\nKaynak: {entry['url']}"
        institution = _extract_institution(title)
        category = infer_category(title, raw_text, default="memur")
        quota = extract_quota_from_text(title, raw_text)
        channel = infer_application_channel(raw_text)

        results.append(
            RawAnnouncement(
                source_name="isinolsa",
                source_label="İşin Olsa Kamu",
                external_id=ext_id,
                url=entry["url"],
                title=title,
                institution=institution,
                category=category,
                publish_date=pub_date,
                deadline_date=None,
                city=None,
                quota_count=quota,
                raw_text=raw_text,
                pdf_url=None,
                application_channel=channel,
            )
        )

    logger.info(
        "İşin Olsa scraped %d announcements (%d detail pages fetched)",
        len(results),
        len(details),
    )
    return results
